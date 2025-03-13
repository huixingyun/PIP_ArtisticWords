import numpy as np
import torch
from PIL import Image, ImageChops

from ..core.effects_processor import EffectsProcessor
from ..core.text_renderer import TextRenderer
from ..utils.tensor_utils import pil_to_tensor, tensor_to_pil


class PIPArtisticWordsFusion:
    """PIP艺术字融合节点，允许设计师在图像上添加艺术字效果"""
    
    @classmethod
    def INPUT_TYPES(cls):
        # 获取可用字体
        from ..utils.font_manager import FontManager
        font_manager = FontManager()
        available_fonts = font_manager.get_available_fonts()
        
        return {
            "required": {
                "image": ("IMAGE",),
                "文本内容": ("STRING", {"multiline": True, "default": "PIP ArtisticWords Fusion"}),
                "字体名称": (available_fonts, {"default": available_fonts[0] if available_fonts else "Arial"}),
            },
            "optional": {
                # 文本安全区域边距
                "上边距比例": ("FLOAT", {"default": 0.63, "min": 0.05, "max": 0.95, "step": 0.01}),
                "下边距比例": ("FLOAT", {"default": 0.06, "min": 0.05, "max": 0.95, "step": 0.01}),
                "左边距比例": ("FLOAT", {"default": 0.08, "min": 0.05, "max": 0.95, "step": 0.01}),
                "右边距比例": ("FLOAT", {"default": 0.08, "min": 0.05, "max": 0.95, "step": 0.01}),
                
                # 文本填充
                "启用填充": ("BOOLEAN", {"default": True}),
                "填充颜色": ("STRING", {"default": "#4096FF", "multiline": False}),
                
                # 描边
                "启用描边": ("BOOLEAN", {"default": True}),
                "描边宽度": ("INT", {"default": 5, "min": 0, "max": 50}),
                "描边透明度": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.1}),
                "描边颜色": ("STRING", {"default": "#000000", "multiline": False}),
                
                # 投影
                "启用阴影": ("BOOLEAN", {"default": True}),
                "阴影颜色": ("STRING", {"default": "#000000", "multiline": False}),
                "阴影透明度": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 1.0, "step": 0.1}),
                "阴影X偏移": ("INT", {"default": 5, "min": -100, "max": 100}),
                "阴影Y偏移": ("INT", {"default": 5, "min": -100, "max": 100}),
                "阴影模糊": ("INT", {"default": 10, "min": 0, "max": 100}),
                
                # 内阴影
                "启用内阴影": ("BOOLEAN", {"default": False}),
                "内阴影颜色": ("STRING", {"default": "#FFFFFF", "multiline": False}),
                "内阴影透明度": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.1}),
                "内阴影X偏移": ("INT", {"default": 2, "min": -50, "max": 50}),
                "内阴影Y偏移": ("INT", {"default": 2, "min": -50, "max": 50}),
                "内阴影模糊": ("INT", {"default": 2, "min": 0, "max": 50}),
                
                # 文字不透明度
                "文字透明度": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 1.0, "step": 0.05}),
                
                # 调试信息
                "显示调试信息": (["none", "basic", "detailed"], {"default": "none"}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("融合图像", "信息")
    FUNCTION = "process"
    CATEGORY = "PIP艺术字"
    
    def process(self, image, 文本内容, 字体名称, **kwargs):
        """处理节点输入并生成融合艺术字的输出图像"""
        # 重新映射参数名
        text = 文本内容
        font_name = 字体名称
        
        # 获取调试模式
        debug_info = kwargs.get("显示调试信息", "none")
        
        # 获取图像尺寸
        if len(image.shape) == 4:  # BHWC
            height = image.shape[1]
            width = image.shape[2]
        else:
            height = image.shape[0]
            width = image.shape[1]
        
        # 添加输入图像形状信息
        print(f"[PIP艺术字融合节点] 输入图像形状: {image.shape}")
        
        # 转换tensor到PIL图像用于处理
        pil_image = tensor_to_pil(image)
        width, height = pil_image.size
        
        # 参数名称映射表（中文到英文）
        param_map = {
            "上边距比例": "margin_top",
            "下边距比例": "margin_bottom",
            "左边距比例": "margin_left",
            "右边距比例": "margin_right",
            
            "启用填充": "enable_fill",
            "填充颜色": "fill_color",
            
            "启用描边": "outline_enabled",
            "描边宽度": "outline_width",
            "描边透明度": "outline_opacity",
            "描边颜色": "outline_color",
            
            "启用阴影": "shadow_enabled",
            "阴影颜色": "shadow_color",
            "阴影透明度": "shadow_opacity",
            "阴影X偏移": "shadow_offset_x",
            "阴影Y偏移": "shadow_offset_y",
            "阴影模糊": "shadow_blur",
            
            "启用内阴影": "inner_shadow_enabled",
            "内阴影颜色": "inner_shadow_color",
            "内阴影透明度": "inner_shadow_opacity",
            "内阴影X偏移": "inner_shadow_offset_x",
            "内阴影Y偏移": "inner_shadow_offset_y",
            "内阴影模糊": "inner_shadow_blur",
            
            "文字透明度": "text_opacity",
        }
        
        # 转换中文参数到英文参数
        english_params = {}
        for zh_key, value in kwargs.items():
            if zh_key in param_map:
                en_key = param_map[zh_key]
                english_params[en_key] = value
        
        # 获取边距设置
        margin_top = english_params.get('margin_top', 0.63)
        margin_bottom = english_params.get('margin_bottom', 0.06)
        margin_left = english_params.get('margin_left', 0.08)
        margin_right = english_params.get('margin_right', 0.08)
        
        # 构建样式字典
        style = self._build_style_dict(english_params)
        
        # 添加调试信息
        print(f"[PIP艺术字融合节点] 使用字体: {font_name}")
        
        # 内阴影调试
        if debug_info == "detailed" and 'inner_shadow' in style:
            inner_shadow = style['inner_shadow']
            print(f"\n[PIP艺术字融合节点-内阴影] 颜色: {inner_shadow.get('color')}")
            print(f"[PIP艺术字融合节点-内阴影] 不透明度: {inner_shadow.get('opacity')}")
            print(f"[PIP艺术字融合节点-内阴影] X偏移: {inner_shadow.get('offset_x')}")
            print(f"[PIP艺术字融合节点-内阴影] Y偏移: {inner_shadow.get('offset_y')}")
            print(f"[PIP艺术字融合节点-内阴影] 模糊: {inner_shadow.get('blur')}")
        
        # 创建特效处理器
        effects_processor = EffectsProcessor(debug_output=(debug_info == "detailed"))
        
        # 计算安全区域
        left = int(width * margin_left)
        right = width - int(width * margin_right)
        top = int(height * margin_top)
        bottom = height - int(height * margin_bottom)
        safe_area = (left, top, right, bottom)
        
        # 打印安全区域信息
        if debug_info != "none":
            print(f"[PIP艺术字融合节点] 图像尺寸: {width}x{height}")
            print(f"[PIP艺术字融合节点] 安全区域: {safe_area}")
            print(f"[PIP艺术字融合节点] 边距: 上: {margin_top*100:.1f}%, 下: {margin_bottom*100:.1f}%, 左: {margin_left*100:.1f}%, 右: {margin_right*100:.1f}%")
            # 添加安全区域宽高信息
            safe_width = right - left
            safe_height = bottom - top
            print(f"[PIP艺术字融合节点] 安全区域尺寸: {safe_width}x{safe_height}")
        
        # 创建文本渲染器
        from ..utils.font_manager import FontManager
        font_manager = FontManager()
        font_path = font_manager.get_font_path(font_name)
        
        # 根据安全区域确定合适的字体大小
        font_size = 100  # 初始字体大小
        text_renderer = TextRenderer(font_path, font_size)
        
        # 渲染基础文本图像
        base_text_image = text_renderer.create_base_text_image(
            text, 
            style, 
            width, 
            height, 
            fit_text=True, 
            safe_area=safe_area
        )
        
        # 应用样式效果
        style['actual_font_size'] = text_renderer.font_size  # 使用渲染器的实际字体大小
        
        if debug_info == "detailed":
            print(f"[PIP艺术字融合节点] 应用效果前字体大小: {text_renderer.font_size}")
            print(f"[PIP艺术字融合节点] 样式效果: {[k for k in style.keys() if k in ['outline', 'shadow', 'fill', 'inner_shadow']]}")
            
            # 内阴影调试
            if 'inner_shadow' in style:
                inner_shadow = style['inner_shadow']
                print(f"\n[PIP艺术字融合节点-内阴影] 颜色: {inner_shadow.get('color')}")
                print(f"[PIP艺术字融合节点-内阴影] 不透明度: {inner_shadow.get('opacity')}")
                print(f"[PIP艺术字融合节点-内阴影] X偏移: {inner_shadow.get('offset_x')}")
                print(f"[PIP艺术字融合节点-内阴影] Y偏移: {inner_shadow.get('offset_y')}")
                print(f"[PIP艺术字融合节点-内阴影] 模糊: {inner_shadow.get('blur')}")
        
        styled_text_result = effects_processor.apply_all_effects(base_text_image, style, style_name="pip_artistic_words")
        
        # 修复: apply_all_effects 返回 (image, layers) 元组，我们只需要第一个元素
        if isinstance(styled_text_result, tuple) and len(styled_text_result) >= 1:
            styled_text_image = styled_text_result[0]  # 获取结果图像
            print("[PIP艺术字融合节点] 成功从apply_all_effects获取结果图像")
        else:
            styled_text_image = styled_text_result  # 如果不是元组，直接使用
        
        # 创建一个新的透明图像作为结果
        result_image = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
        
        # 把原始图像粘贴到结果图上
        pil_image_rgba = pil_image.convert('RGBA')
        result_image.paste(pil_image_rgba, (0, 0))
        
        # 使用alpha_composite方法合成，这会保留所有特效
        result_image = Image.alpha_composite(result_image, styled_text_image)
        
        # 应用文字透明度设置
        text_opacity = english_params.get('text_opacity', 1.0)
        if text_opacity < 1.0:
            # 从结果图像中分离出添加了文字的部分
            r, g, b, a = result_image.split()
            # 调整透明度，但仅对添加的文字部分生效
            original_alpha = pil_image_rgba.split()[3]
            # 创建一个掩码，标记出文字添加的位置
            text_mask = Image.eval(ImageChops.subtract(a, original_alpha), lambda x: x if x > 0 else 0)
            # 按照文字透明度调整这个掩码
            adjusted_mask = text_mask.point(lambda x: int(x * text_opacity))
            # 合成新的alpha通道
            final_alpha = ImageChops.add(original_alpha, adjusted_mask)
            # 合成最终图像
            result_image = Image.merge('RGBA', (r, g, b, final_alpha))
        
        # 转换回张量 (BHWC 格式)
        result_tensor = pil_to_tensor(result_image)
        
        # 创建详细的信息字符串
        info = f"文本: {text}\n字体: {font_name} (大小: {text_renderer.font_size}pt)\n"
        
        # 添加填充信息
        if english_params.get("enable_fill", True):
            info += f"\n【填充】\n"
            info += f"颜色: {kwargs.get('填充颜色', '#4096FF')}\n"
        else:
            info += f"\n【填充】\n已禁用\n"
        
        # 添加描边信息
        if english_params.get("outline_enabled", True):
            info += f"\n【描边】\n宽度: {kwargs.get('描边宽度', 5)}\n"
            info += f"透明度: {kwargs.get('描边透明度', 1.0)}\n"
            info += f"颜色: {kwargs.get('描边颜色', '#000000')}\n"
        else:
            info += f"\n【描边】\n已禁用\n"
        
        # 添加阴影信息
        if english_params.get("shadow_enabled", True):
            info += f"\n【阴影】\n"
            info += f"颜色: {kwargs.get('阴影颜色', '#000000')}\n"
            info += f"透明度: {kwargs.get('阴影透明度', 0.6)}\n"
            info += f"偏移: X={kwargs.get('阴影X偏移', 5)}, Y={kwargs.get('阴影Y偏移', 5)}\n"
            info += f"模糊: {kwargs.get('阴影模糊', 10)}\n"
        else:
            info += f"\n【阴影】\n已禁用\n"
        
        # 添加内阴影信息
        if english_params.get("inner_shadow_enabled", False):
            info += f"\n【内阴影】\n"
            info += f"颜色: {kwargs.get('内阴影颜色', '#FFFFFF')}\n"
            info += f"透明度: {kwargs.get('内阴影透明度', 0.7)}\n"
            info += f"偏移: X={kwargs.get('内阴影X偏移', 2)}, Y={kwargs.get('内阴影Y偏移', 2)}\n"
            info += f"模糊: {kwargs.get('内阴影模糊', 2)}\n"
        else:
            info += f"\n【内阴影】\n已禁用\n"
        
        return (result_tensor, info)
    
    def _build_style_dict(self, params):
        """根据UI参数构建样式字典"""
        style = {}
        
        # 修复填充颜色被描边覆盖的问题：
        # 1. 创建一个自定义的样式处理顺序
        style['_effects_order'] = []
        
        # 添加阴影（最底层）
        if params.get('shadow_enabled', True):
            style['shadow'] = {
                'color': params.get('shadow_color', '#000000'),
                'opacity': float(params.get('shadow_opacity', 0.6)),
                'offset_x': int(params.get('shadow_offset_x', 5)),
                'offset_y': int(params.get('shadow_offset_y', 5)),
                'blur': int(params.get('shadow_blur', 10))
            }
            style['_effects_order'].append('shadow')
            
        # 添加描边（中间层）
        if params.get('outline_enabled', True):
            outline_width = params.get('outline_width', 5)
            outline_opacity = params.get('outline_opacity', 1.0)
            
            style['outline'] = {
                'width': outline_width,
                'opacity': outline_opacity,
                'color': params.get('outline_color', '#000000')
            }
            style['_effects_order'].append('outline')
        
        # 添加填充（最上层，确保在描边之上）
        if params.get('enable_fill', True):
            # 直接设置填充颜色为字符串，这样能确保正确应用
            style['fill'] = params.get('fill_color', '#4096FF')
            style['_effects_order'].append('fill')
        else:
            # 不启用填充
            style['fill'] = {'type': 'none'}
                
        # 内阴影（最后添加）
        if params.get('inner_shadow_enabled', False):
            style['inner_shadow'] = {
                'color': params.get('inner_shadow_color', '#FFFFFF'),  # 默认改为白色
                'opacity': float(params.get('inner_shadow_opacity', 0.7)),
                'offset_x': int(params.get('inner_shadow_offset_x', 2)),
                'offset_y': int(params.get('inner_shadow_offset_y', 2)),
                'blur': int(params.get('inner_shadow_blur', 2))
            }
            style['_effects_order'].append('inner_shadow')
        
        return style
    
    def _hex_to_rgba(self, hex_color, alpha=255):
        """将16进制颜色转换为RGBA元组"""
        if not hex_color:
            return (255, 255, 255, alpha)
        
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return (r, g, b, alpha)
        elif len(hex_color) == 8:
            r, g, b, a = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
            return (r, g, b, a)
        return (255, 255, 255, alpha)

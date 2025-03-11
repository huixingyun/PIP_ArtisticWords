import os
import time
import json
import numpy as np
import torch
from PIL import Image

from ..core.effects_processor import EffectsProcessor
from ..core.text_renderer import TextRenderer
from ..utils.tensor_utils import pil_to_tensor
from ..utils.svg_generator import SVGGenerator


class PIPSVGRecorder:
    """SVG样式测试与记录节点，允许设计师测试并保存艺术字样式SVG"""
    
    @classmethod
    def INPUT_TYPES(cls):
        # 获取可用字体
        from ..utils.font_manager import FontManager
        font_manager = FontManager()
        available_fonts = font_manager.get_available_fonts()
        
        # 预定义渐变方向选项
        gradient_directions = [
            "从左到右", "从右到左", "从上到下", "从下到上",
            "左上到右下", "右下到左上", "左下到右上", "右上到左下"
        ]
        
        # 渐变方向的英文映射（用于内部处理）
        cls.gradient_direction_map = {
            "从左到右": "left_right", 
            "从右到左": "right_left", 
            "从上到下": "top_bottom", 
            "从下到上": "bottom_top",
            "左上到右下": "diagonal", 
            "右下到左上": "diagonal_reverse", 
            "左下到右上": "diagonal_bottom", 
            "右上到左下": "diagonal_bottom_reverse"
        }
        
        return {
            "required": {
                "文本内容": ("STRING", {"multiline": True, "default": "艺术字"}),
                "字体名称": (available_fonts, {"default": available_fonts[0] if available_fonts else "Arial"}),
                "字体大小": ("INT", {"default": 72, "min": 8, "max": 500}),
                "操作模式": (["测试模式", "保存模式"], {"default": "测试模式"}),
                "文件名称": ("STRING", {"default": "my_style"}),
                "预览宽度": ("INT", {"default": 512, "min": 128, "max": 2048}),
                "预览高度": ("INT", {"default": 512, "min": 128, "max": 2048}),
            },
            "optional": {
                # 背景设置（仅预览使用）
                "背景颜色": ("COLOR", {"default": "#FFFFFF"}),
                "背景透明度": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.1}),
                
                # 文本填充
                "启用填充": ("BOOLEAN", {"default": True}),
                "填充类型": (["纯色", "渐变", "无填充"], {"default": "渐变"}),
                "填充颜色": ("COLOR", {"default": "#4096FF"}),
                "填充渐变类型": (["线性渐变", "径向渐变"], {"default": "线性渐变"}),
                "填充渐变方向": (gradient_directions, {"default": "从上到下"}),
                "填充渐变颜色1": ("COLOR", {"default": "#EE2883"}),
                "填充渐变颜色2": ("COLOR", {"default": "#FFDC7D"}),
                
                # 描边
                "启用描边": ("BOOLEAN", {"default": True}),
                "描边宽度": ("INT", {"default": 5, "min": 0, "max": 50}),
                "描边透明度": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.1}),
                "描边类型": (["纯色", "渐变"], {"default": "渐变"}),
                "描边颜色": ("COLOR", {"default": "#000000"}),
                "描边渐变类型": (["线性渐变", "径向渐变"], {"default": "线性渐变"}),
                "描边渐变方向": (gradient_directions, {"default": "从左到右"}),
                "描边渐变颜色1": ("COLOR", {"default": "#EE2883"}),
                "描边渐变颜色2": ("COLOR", {"default": "#FFDC7D"}),
                
                # 投影
                "启用阴影": ("BOOLEAN", {"default": True}),
                "阴影颜色": ("COLOR", {"default": "#000000"}),
                "阴影透明度": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 1.0, "step": 0.1}),
                "阴影X偏移": ("INT", {"default": 5, "min": -100, "max": 100}),
                "阴影Y偏移": ("INT", {"default": 5, "min": -100, "max": 100}),
                "阴影模糊": ("INT", {"default": 10, "min": 0, "max": 100}),
                
                # 内阴影
                "启用内阴影": ("BOOLEAN", {"default": False}),
                "内阴影颜色": ("COLOR", {"default": "#9900FF"}),
                "内阴影透明度": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.1}),
                "内阴影X偏移": ("INT", {"default": 2, "min": -50, "max": 50}),
                "内阴影Y偏移": ("INT", {"default": 2, "min": -50, "max": 50}),
                "内阴影模糊": ("INT", {"default": 2, "min": 0, "max": 50}),
                
                # 外发光
                "启用外发光": ("BOOLEAN", {"default": False}),
                "外发光颜色": ("COLOR", {"default": "#00FF00"}),
                "外发光透明度": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.1}),
                "外发光模糊": ("INT", {"default": 10, "min": 0, "max": 20}),
                "外发光强度": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.1}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("预览图", "信息")
    FUNCTION = "process"
    CATEGORY = "PIP艺术字"
    
    def process(self, 文本内容, 字体名称, 字体大小, 操作模式, 文件名称, 预览宽度, 预览高度, **kwargs):
        """处理节点输入并生成输出"""
        # 重新映射参数名
        text = 文本内容
        font_name = 字体名称
        font_size = 字体大小
        mode = 操作模式
        file_name = 文件名称
        preview_width = 预览宽度
        preview_height = 预览高度
        
        # 参数名称映射表（中文到英文）
        param_map = {
            "背景颜色": "bg_color",
            "背景透明度": "bg_opacity",
            
            "启用填充": "enable_fill",
            "填充类型": "fill_type",
            "填充颜色": "fill_color",
            "填充渐变类型": "fill_gradient_type",
            "填充渐变方向": "fill_gradient_direction",
            "填充渐变颜色1": "fill_gradient_color1",
            "填充渐变颜色2": "fill_gradient_color2",
            
            "启用描边": "outline_enabled",
            "描边宽度": "outline_width",
            "描边透明度": "outline_opacity",
            "描边类型": "outline_type",
            "描边颜色": "outline_color",
            "描边渐变类型": "outline_gradient_type",
            "描边渐变方向": "outline_gradient_direction",
            "描边渐变颜色1": "outline_gradient_color1",
            "描边渐变颜色2": "outline_gradient_color2",
            
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
            
            "启用外发光": "glow_enabled",
            "外发光颜色": "glow_color",
            "外发光透明度": "glow_opacity",
            "外发光模糊": "glow_blur",
            "外发光强度": "glow_intensity",
        }
        
        # 类型映射
        type_map = {
            "纯色": "solid",
            "渐变": "gradient",
            "无填充": "none",
            "线性渐变": "linear",
            "径向渐变": "radial"
        }
        
        # 转换中文参数到英文参数
        english_params = {}
        for zh_key, value in kwargs.items():
            if zh_key in param_map:
                en_key = param_map[zh_key]
                
                # 特殊处理填充类型和渐变类型
                if zh_key in ["填充类型", "描边类型"] and value in type_map:
                    value = type_map[value]
                elif zh_key in ["填充渐变类型", "描边渐变类型"] and value in type_map:
                    value = type_map[value]
                elif zh_key in ["填充渐变方向", "描边渐变方向"] and value in self.gradient_direction_map:
                    value = self.gradient_direction_map[value]
                
                english_params[en_key] = value
        
        # 构建样式字典
        style = self._build_style_dict(english_params)
        
        # 添加调试信息
        print(f"[SVG记录器节点] 使用字体: {font_name}, 大小: {font_size}")
        
        # 渐变填充方向调试
        if 'fill' in style and style['fill'].get('type') in ['linear', 'radial']:
            fill = style['fill']
            print(f"\n[SVG记录器节点-填充渐变] 类型: {fill.get('type')}")
            print(f"[SVG记录器节点-填充渐变] 方向: {fill.get('direction')}")
            print(f"[SVG记录器节点-填充渐变] 颜色: {fill.get('colors', [])}")
        
        # 外发光调试
        if 'glow' in style:
            glow = style['glow']
            print(f"\n[SVG记录器节点-外发光] 颜色: {glow.get('color')}")
            print(f"[SVG记录器节点-外发光] 不透明度: {glow.get('opacity')}")
            print(f"[SVG记录器节点-外发光] 半径: {glow.get('radius')}")
            print(f"[SVG记录器节点-外发光] 强度: {glow.get('intensity')}")
        
        # 内阴影调试
        if 'inner_shadow' in style:
            inner_shadow = style['inner_shadow']
            print(f"\n[SVG记录器节点-内阴影] 颜色: {inner_shadow.get('color')}")
            print(f"[SVG记录器节点-内阴影] 不透明度: {inner_shadow.get('opacity')}")
            print(f"[SVG记录器节点-内阴影] X偏移: {inner_shadow.get('offset_x')}")
            print(f"[SVG记录器节点-内阴影] Y偏移: {inner_shadow.get('offset_y')}")
            print(f"[SVG记录器节点-内阴影] 模糊: {inner_shadow.get('blur')}")
        
        # 创建特效处理器
        effects_processor = EffectsProcessor(debug_output=False)
        
        # 生成预览图像
        preview_tensor = self._generate_preview(
            text, font_name, font_size, style, 
            preview_width, preview_height, 
            bg_color=english_params.get('bg_color', "#FFFFFF"),
            bg_opacity=english_params.get('bg_opacity', 0.0)
        )
        
        # _generate_preview 已经返回 tensor 格式，不需要再次转换
        # preview_tensor = pil_to_tensor(preview_image)
        
        # 创建详细的信息字符串
        info = f"文本: {text}\n字体: {font_name} ({font_size}pt)\n"
        info += f"模式: {mode}\n"
        
        # 添加填充信息
        if "fill_type" in english_params:
            fill_type = kwargs.get("填充类型", "渐变")
            info += f"\n【填充】\n类型: {fill_type}\n"
            
            if fill_type == "纯色":
                info += f"颜色: {kwargs.get('填充颜色', '#000000')}\n"
            elif fill_type == "渐变":
                gradient_type = kwargs.get("填充渐变类型", "线性渐变")
                gradient_dir = kwargs.get("填充渐变方向", "从上到下")
                info += f"渐变: {gradient_type} ({gradient_dir})\n"
                info += f"颜色1: {kwargs.get('填充渐变颜色1', '#EE2883')}\n"
                info += f"颜色2: {kwargs.get('填充渐变颜色2', '#FFDC7D')}\n"
        else:
            info += f"\n【填充】\n已禁用\n"
        
        # 添加描边信息
        if kwargs.get("启用描边", True):
            info += f"\n【描边】\n宽度: {kwargs.get('描边宽度', 5)}\n"
            info += f"透明度: {kwargs.get('描边透明度', 1.0)}\n"
            
            outline_type = kwargs.get("描边类型", "渐变")
            info += f"类型: {outline_type}\n"
            
            if outline_type == "纯色":
                info += f"颜色: {kwargs.get('描边颜色', '#000000')}\n"
            elif outline_type == "渐变":
                gradient_type = kwargs.get("描边渐变类型", "线性渐变")
                gradient_dir = kwargs.get("描边渐变方向", "从左到右")
                info += f"渐变: {gradient_type} ({gradient_dir})\n"
                info += f"颜色1: {kwargs.get('描边渐变颜色1', '#EE2883')}\n"
                info += f"颜色2: {kwargs.get('描边渐变颜色2', '#FFDC7D')}\n"
        else:
            info += f"\n【描边】\n已禁用\n"
        
        # 添加阴影信息
        if kwargs.get("启用阴影", True):
            info += f"\n【阴影】\n"
            info += f"颜色: {kwargs.get('阴影颜色', '#000000')}\n"
            info += f"透明度: {kwargs.get('阴影透明度', 0.6)}\n"
            info += f"偏移: X={kwargs.get('阴影X偏移', 5)}, Y={kwargs.get('阴影Y偏移', 5)}\n"
            info += f"模糊: {kwargs.get('阴影模糊', 10)}\n"
        else:
            info += f"\n【阴影】\n已禁用\n"
        
        # 添加内阴影信息
        if kwargs.get("启用内阴影", False):
            info += f"\n【内阴影】\n"
            info += f"颜色: {kwargs.get('内阴影颜色', '#9900FF')}\n"
            info += f"透明度: {kwargs.get('内阴影透明度', 0.7)}\n"
            info += f"偏移: X={kwargs.get('内阴影X偏移', 2)}, Y={kwargs.get('内阴影Y偏移', 2)}\n"
            info += f"模糊: {kwargs.get('内阴影模糊', 2)}\n"
        else:
            info += f"\n【内阴影】\n已禁用\n"
            
        # 添加外发光信息
        if kwargs.get("启用外发光", False):
            info += f"\n【外发光】\n"
            info += f"颜色: {kwargs.get('外发光颜色', '#00FF00')}\n"
            info += f"透明度: {kwargs.get('外发光透明度', 0.8)}\n"
            info += f"模糊: {kwargs.get('外发光模糊', 10)}\n"
            info += f"强度: {kwargs.get('外发光强度', 1.0)}\n"
        else:
            info += f"\n【外发光】\n已禁用\n"
        
        # 如果是保存模式，添加SVG文件信息
        if mode == "保存模式":
            svg_path = self._save_svg(text, font_name, font_size, style, file_name)
            info += f"\n已保存SVG: {svg_path}"
        
        return (preview_tensor, info)
    
    def _build_style_dict(self, params):
        """根据UI参数构建样式字典"""
        style = {}
        
        # 处理填充
        if params.get('enable_fill', True):
            fill_type = params.get('fill_type', 'gradient')
            
            if fill_type == "solid":
                style['fill'] = {'type': 'solid', 'color': params.get('fill_color', '#4096FF')}
            elif fill_type == "gradient":
                fill_gradient_type = params.get('fill_gradient_type', 'linear')
                fill_gradient_direction = params.get('fill_gradient_direction', 'top_bottom')
                
                style['fill'] = {
                    'type': fill_gradient_type,
                    'direction': fill_gradient_direction,
                    'colors': [
                        params.get('fill_gradient_color1', '#EE2883'), 
                        params.get('fill_gradient_color2', '#FFDC7D')
                    ]
                }
        else:
            # 不启用填充
            style['fill'] = {'type': 'none'}
        
        # 处理描边
        if params.get('outline_enabled', True):
            outline_type = params.get('outline_type', 'gradient')
            outline_width = params.get('outline_width', 5)
            outline_opacity = params.get('outline_opacity', 1.0)
            
            if outline_type == "solid":
                style['outline'] = {
                    'width': outline_width,
                    'opacity': outline_opacity,
                    'color': params.get('outline_color', '#000000')
                }
            else:
                outline_gradient_type = params.get('outline_gradient_type', 'linear')
                outline_gradient_direction = params.get('outline_gradient_direction', 'left_right')
                
                style['outline'] = {
                    'width': outline_width,
                    'opacity': outline_opacity,
                    'gradient': {
                        'type': outline_gradient_type,
                        'direction': outline_gradient_direction,
                        'colors': [
                            params.get('outline_gradient_color1', '#EE2883'), 
                            params.get('outline_gradient_color2', '#FFDC7D')
                        ]
                    }
                }
        
        # 处理阴影
        if params.get('shadow_enabled', True):
            style['shadow'] = {
                'color': params.get('shadow_color', '#000000'),
                'opacity': float(params.get('shadow_opacity', 0.6)),
                'offset_x': int(params.get('shadow_offset_x', 5)),
                'offset_y': int(params.get('shadow_offset_y', 5)),
                'blur': int(params.get('shadow_blur', 10))
            }
        
        # 处理内阴影
        if params.get('inner_shadow_enabled', False):
            style['inner_shadow'] = {
                'color': params.get('inner_shadow_color', '#9900FF'),
                'opacity': float(params.get('inner_shadow_opacity', 0.7)),
                'offset_x': int(params.get('inner_shadow_offset_x', 2)),
                'offset_y': int(params.get('inner_shadow_offset_y', 2)),
                'blur': int(params.get('inner_shadow_blur', 2))
            }
            
        # 处理外发光
        if params.get('glow_enabled', False):
            style['glow'] = {
                'color': params.get('glow_color', '#00FF00'),
                'opacity': float(params.get('glow_opacity', 0.8)),
                'radius': int(params.get('glow_blur', 10)),
                'intensity': float(params.get('glow_intensity', 1.0))  # 添加intensity参数
            }
        
        return style
    
    def _direction_to_svg_coords(self, direction):
        """将渐变方向转换为SVG坐标"""
        directions = {
            "left_right": {"x1": "0%", "y1": "50%", "x2": "100%", "y2": "50%"},
            "right_left": {"x1": "100%", "y1": "50%", "x2": "0%", "y2": "50%"},
            "top_bottom": {"x1": "50%", "y1": "0%", "x2": "50%", "y2": "100%"},
            "bottom_top": {"x1": "50%", "y1": "100%", "x2": "50%", "y2": "0%"},
            "diagonal": {"x1": "0%", "y1": "0%", "x2": "100%", "y2": "100%"},
            "diagonal_reverse": {"x1": "100%", "y1": "100%", "x2": "0%", "y2": "0%"},
            "diagonal_bottom": {"x1": "0%", "y1": "100%", "x2": "100%", "y2": "0%"},
            "diagonal_bottom_reverse": {"x1": "100%", "y1": "0%", "x2": "0%", "y2": "100%"}
        }
        
        return directions.get(direction, {"x1": "50%", "y1": "0%", "x2": "50%", "y2": "100%"})
    
    def _generate_preview(self, text, font_name, font_size, style, width, height, bg_color="#FFFFFF", bg_opacity=0.0):
        """生成预览图像"""
        # 创建字体渲染器
        from ..utils.font_manager import FontManager
        font_manager = FontManager()
        font_path = font_manager.get_font_path(font_name)
        
        # 初始化文本渲染器
        renderer = TextRenderer(font_path, font_size)
        
        # 创建背景层
        bg_color_tuple = self._hex_to_rgba(bg_color, int(bg_opacity * 255))
        bg_image = Image.new('RGBA', (width, height), bg_color_tuple)
        
        # 在安全区域内渲染文本（留出四边的空白）
        safe_area = (width * 0.1, height * 0.1, width * 0.9, height * 0.9)
        
        # 渲染基础文本图像
        base_text_image = renderer.create_base_text_image(
            text, 
            style, 
            width, 
            height, 
            fit_text=True, 
            safe_area=safe_area
        )
        
        # 应用样式效果
        style['actual_font_size'] = renderer.font_size
        styled_text_result = EffectsProcessor(debug_output=False).apply_all_effects(
            base_text_image, 
            style, 
            style_name=text
        )
        
        # 修复: apply_all_effects 返回 (image, layers) 元组，我们只需要第一个元素
        if isinstance(styled_text_result, tuple) and len(styled_text_result) >= 1:
            styled_text_image = styled_text_result[0]  # 获取结果图像
            print("[SVG记录器节点] 成功从apply_all_effects获取结果图像")
        else:
            styled_text_image = styled_text_result  # 如果不是元组，直接使用
            
        # 将样式化文本合成到背景上
        result = Image.alpha_composite(bg_image, styled_text_image)
        
        # 转换为tensor格式
        tensor = pil_to_tensor(result)
        
        return tensor
    
    def _save_svg(self, text, font_name, font_size, style, file_name):
        """生成并保存SVG文件"""
        # 确保文件名有效
        if not file_name:
            file_name = f"style_{int(time.time())}"
        
        # 如果没有扩展名，添加.svg
        if not file_name.lower().endswith('.svg'):
            file_name += '.svg'
        
        # 构建完整路径
        svg_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'SVG')
        os.makedirs(svg_dir, exist_ok=True)
        svg_path = os.path.join(svg_dir, file_name)
        
        # 默认SVG尺寸（保持16:9的宽高比）
        width = 800
        height = 450
        
        # 生成SVG内容
        svg_generator = SVGGenerator()
        svg_content = svg_generator.generate_svg(text, font_name, font_size, style, width, height)
        
        # 保存文件
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        return svg_path
    
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

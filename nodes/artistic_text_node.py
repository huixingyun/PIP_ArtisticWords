import os
import random
from PIL import Image, ImageChops, ImageFilter
import torch
import numpy as np

# Use relative imports to maintain portability
from ..core.style_manager import StyleManager
from ..core.text_renderer import TextRenderer
from ..core.effects_processor import EffectsProcessor
from ..core.style_color_manager import StyleColorManager
from ..utils.tensor_utils import tensor_to_pil, pil_to_tensor, create_alpha_mask
from ..utils.font_manager import FontManager


class ArtisticTextNode:
    """Node for generating artistic text overlayed on images in ComfyUI."""
    
    @classmethod
    def INPUT_TYPES(cls):
        # Get available styles
        from ..core.style_manager import StyleManager
        style_manager = StyleManager()
        style_names = style_manager.get_style_names()
        
        return {
            "required": {
                "image": ("IMAGE",),
                "text": ("STRING", {"multiline": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1}),
                "style": (["random"] + style_names,),
                "color_match": (["disable", "enable"], {"default": "disable"}),
            },
            "optional": {
                "margin_top": ("FLOAT", {"default": 0.25, "min": 0.05, "max": 0.8, "step": 0.01}),
                "margin_bottom": ("FLOAT", {"default": 0.15, "min": 0.05, "max": 0.8, "step": 0.01}),
                "margin_left": ("FLOAT", {"default": 0.1, "min": 0.05, "max": 0.8, "step": 0.01}),
                "margin_right": ("FLOAT", {"default": 0.1, "min": 0.05, "max": 0.8, "step": 0.01}),
                "opacity": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 1.0, "step": 0.05}),
                "debug_info": (["none", "basic", "detailed"],),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate_artistic_text"
    CATEGORY = "PIP"
    
    def generate_artistic_text(self, image, text, seed, style="random", color_match="disable",
                               margin_top=0.25, margin_bottom=0.15, margin_left=0.1, margin_right=0.1,
                               opacity=1.0, debug_info="none"):
        """
        Generate artistic text overlayed on an image.
        
        Args:
            image: Input image tensor in BHWC format
            text: Text to render
            seed: Random seed
            style: Style to apply or "random"
            color_match: Whether to match text style with image colors
            margin_top: Top margin as fraction of image height (default: 0.25 = 25%)
            margin_bottom: Bottom margin as fraction of image height (default: 0.15 = 15%)
            margin_left: Left margin as fraction of image width (default: 0.1 = 10%)
            margin_right: Right margin as fraction of image width (default: 0.1 = 10%)
            opacity: Opacity of the text overlay (default: 1.0 = 100%)
            debug_info: Print debug information (none, basic, detailed)
        
        Returns:
            Image tensor with text overlayed
        """
        # Set random seed for reproducibility
        random.seed(seed)
        
        # Get image dimensions
        if len(image.shape) == 4:  # BHWC
            height = image.shape[1]
            width = image.shape[2]
        else:
            height = image.shape[0]
            width = image.shape[1]
        
        # 添加输入图像形状信息
        print(f"[PIP_ArtisticWords] 输入图像形状: {image.shape}")
        
        # Create style manager and load styles/fonts
        from ..core.style_manager import StyleManager
        style_manager = StyleManager()
        font_manager = FontManager()
        
        # Convert tensor to PIL image for processing (need it early for color analysis)
        pil_image = tensor_to_pil(image)
        width, height = pil_image.size
        
        # 根据color_match参数决定是否使用颜色匹配功能
        selected_style_name = style
        dominant_color_name = None
        dominant_color_rgb = None
        
        if color_match == "enable" and style == "random":
            # 创建颜色样式管理器
            style_color_manager = StyleColorManager()
            
            # 分析图像颜色并获取匹配的样式
            matched_style, color_name, color_rgb, confidence = style_color_manager.get_style_for_image(pil_image)
            
            if matched_style:
                selected_style_name = matched_style
                dominant_color_name = color_name
                dominant_color_rgb = color_rgb
                
                if debug_info != "none":
                    print(f"[PIP_ArtisticWords] 颜色匹配启用: 检测到主色调 {color_name} ({color_rgb})")
                    print(f"[PIP_ArtisticWords] 匹配样式: {matched_style} (置信度: {confidence:.2f})")
        
        # 获取样式和字体
        if selected_style_name == "random":
            style_data, font_name = style_manager.generate_random_combination()
            # Get the actual style name that was randomly selected
            for style_name, style_content in style_manager.styles.items():
                if style_content == style_data:
                    selected_style_name = style_name
                    break
        else:
            style_data = style_manager.get_style(selected_style_name)
            # 选择字体: 与Preview节点保持一致，使用相同逻辑
            if 'font' in style_data and style_data['font'] in font_manager.get_available_fonts():
                # 如果样式中指定了字体且该字体存在，则使用指定字体
                font_name = style_data['font']
            else:
                # 否则随机选择字体
                font_name = random.choice(font_manager.get_available_fonts())
        
        # 处理尚未设置字体的情况（可能是SVG样式）
        if 'font_name' not in locals() or 'font_name' not in globals():
            if 'font' in style_data and style_data['font'] in font_manager.get_available_fonts():
                font_name = style_data['font']
            else:
                font_name = random.choice(font_manager.get_available_fonts())
        
        # Print debug information
        if debug_info != "none":
            print(f"[PIP_ArtisticWords] Selected style: {selected_style_name}")
            print(f"[PIP_ArtisticWords] Selected font: {font_name}")
            print(f"[PIP_ArtisticWords] Seed: {seed}")
            
            if debug_info == "detailed":
                print(f"[PIP_ArtisticWords] Style data: {style_data}")
        
        # Get font path
        font_path = font_manager.get_font_path(font_name)
        
        # Calculate safe area based on margins
        left = int(width * margin_left)
        right = width - int(width * margin_right)
        top = int(height * margin_top)
        bottom = height - int(height * margin_bottom)
        safe_area = (left, top, right, bottom)
        
        # 检测样式中是否有发光效果
        has_glow = False
        if 'glow' in style_data:
            # 只有当glow的radius和intensity都大于0时才算有发光效果
            glow = style_data['glow']
            if glow is not None and glow.get('radius', 0) > 0 and glow.get('intensity', 0) > 0:
                has_glow = True
        
        if 'outer_glow' in style_data:
            # 只有当outer_glow的radius和intensity都大于0时才算有发光效果
            outer_glow = style_data['outer_glow']
            if outer_glow is not None and outer_glow.get('radius', 0) > 0 and outer_glow.get('intensity', 0) > 0:
                has_glow = True
        
        if debug_info != "none":
            print(f"[PIP_ArtisticWords] Image dimensions: {width}x{height}")
            print(f"[PIP_ArtisticWords] Safe area: {safe_area}")
            print(f"[PIP_ArtisticWords] Margins: Top: {margin_top*100:.1f}%, Bottom: {margin_bottom*100:.1f}%, Left: {margin_left*100:.1f}%, Right: {margin_right*100:.1f}%")
            # 添加安全区域宽高信息
            safe_width = right - left
            safe_height = bottom - top
            print(f"[PIP_ArtisticWords] Safe area dimensions: {safe_width}x{safe_height}")
        
        # Create text renderer and effects processor
        font_size = style_data.get('font_size', 100)
        text_renderer = TextRenderer(font_path, font_size)
        effects_processor = EffectsProcessor(debug_output=False)
        
        # Render base text image
        base_text_image = text_renderer.create_base_text_image(
            text, 
            style_data, 
            width, 
            height, 
            fit_text=True, 
            safe_area=safe_area
        )
        
        # Apply style effects
        style_data['actual_font_size'] = text_renderer.font_size  # 使用渲染器的实际字体大小而不是原始值
        
        # 添加更多调试信息
        if debug_info == "detailed":
            print(f"[PIP_ArtisticWords] 应用效果前字体大小: {text_renderer.font_size}")
            print(f"[PIP_ArtisticWords] 样式效果: {[k for k in style_data.keys() if k in ['outline', 'shadow', 'gradient', 'bevel', 'glow', 'inner_shadow']]}")
            
            # 渐变填充方向调试
            if 'fill' in style_data and style_data['fill'].get('type') in ['linear', 'radial']:
                fill = style_data['fill']
                print(f"\n[艺术文字节点-填充渐变] 类型: {fill.get('type')}")
                print(f"[艺术文字节点-填充渐变] 方向: {fill.get('direction')}")
                print(f"[艺术文字节点-填充渐变] 颜色: {fill.get('colors', [])}")
            
            # 外发光调试
            if 'glow' in style_data:
                glow = style_data['glow']
                print(f"\n[艺术文字节点-外发光] 颜色: {glow.get('color')}")
                print(f"[艺术文字节点-外发光] 不透明度: {glow.get('opacity')}")
                print(f"[艺术文字节点-外发光] 半径: {glow.get('radius')}")
                print(f"[艺术文字节点-外发光] 强度: {glow.get('intensity')}")
            
            # 内阴影调试
            if 'inner_shadow' in style_data:
                inner_shadow = style_data['inner_shadow']
                print(f"\n[艺术文字节点-内阴影] 颜色: {inner_shadow.get('color')}")
                print(f"[艺术文字节点-内阴影] 不透明度: {inner_shadow.get('opacity')}")
                print(f"[艺术文字节点-内阴影] X偏移: {inner_shadow.get('offset_x')}")
                print(f"[艺术文字节点-内阴影] Y偏移: {inner_shadow.get('offset_y')}")
                print(f"[艺术文字节点-内阴影] 模糊: {inner_shadow.get('blur')}")
        
        styled_text_result = effects_processor.apply_all_effects(base_text_image, style_data, style_name="artistic_text")
        
        # 修复: apply_all_effects 返回 (image, layers) 元组，我们只需要第一个元素
        if isinstance(styled_text_result, tuple) and len(styled_text_result) >= 1:
            styled_text_image = styled_text_result[0]  # 获取结果图像
            print("[艺术文字节点] 成功从apply_all_effects获取结果图像")
        else:
            styled_text_image = styled_text_result  # 如果不是元组，直接使用
        
        # 创建一个新的透明图像作为结果
        result_image = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
        
        # 把原始图像粘贴到结果图上
        pil_image_rgba = pil_image.convert('RGBA')
        result_image.paste(pil_image_rgba, (0, 0))
        
        # 使用alpha_composite方法合成，这会保留所有特效
        result_image = Image.alpha_composite(result_image, styled_text_image)
        
        # 应用透明度设置
        if opacity < 1.0:
            # 调整文字层的透明度
            r, g, b, a = result_image.split()
            a = a.point(lambda x: int(x * opacity) if x > 0 else 0)
            result_image = Image.merge('RGBA', (r, g, b, a))
        
        # 转换回张量 (BHWC 格式)
        result_tensor = pil_to_tensor(result_image)
        
        return (result_tensor,)

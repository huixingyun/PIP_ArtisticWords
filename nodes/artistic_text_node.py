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


class ArtisticTextNode:
    """Node for generating artistic text overlayed on images in ComfyUI."""
    
    @classmethod
    def INPUT_TYPES(cls):
        # Get available styles
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
        
        # Create style manager and load styles/fonts
        style_manager = StyleManager()
        
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
            if 'font' in style_data and style_data['font'] in style_manager.get_font_names():
                # 如果样式中指定了字体且该字体存在，则使用指定字体
                font_name = style_data['font']
            else:
                # 否则随机选择字体
                font_name = random.choice(style_manager.get_font_names())
        
        # 处理尚未设置字体的情况（可能是SVG样式）
        if 'font_name' not in locals() or 'font_name' not in globals():
            if 'font' in style_data and style_data['font'] in style_manager.get_font_names():
                font_name = style_data['font']
            else:
                font_name = random.choice(style_manager.get_font_names())
        
        # Print debug information
        if debug_info != "none":
            print(f"[PIP_ArtisticWords] Selected style: {selected_style_name}")
            print(f"[PIP_ArtisticWords] Selected font: {font_name}")
            print(f"[PIP_ArtisticWords] Seed: {seed}")
            
            if debug_info == "detailed":
                print(f"[PIP_ArtisticWords] Style data: {style_data}")
        
        # Get font path
        font_path = style_manager.get_font_path(font_name)
        
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
        
        if has_glow:
            # 发光效果需要更多空间，增加边距
            # 根据用户提供的边距适当增加，但确保至少有一个最小值
            glow_margin_multiplier = 1.5  # 增加50%额外空间
            
            # 计算新的安全区域，但保持纵横比例关系
            left = int(width * margin_left * glow_margin_multiplier)
            right = width - int(width * margin_right * glow_margin_multiplier)
            top = int(height * margin_top * glow_margin_multiplier)
            bottom = height - int(height * margin_bottom * glow_margin_multiplier)
            
            # 确保不会超出图像边界
            left = max(0, min(left, width // 4))
            right = min(width, max(right, width - width // 4))
            top = max(0, min(top, height // 4))
            bottom = min(height, max(bottom, height - height // 4))
            
            safe_area = (left, top, right, bottom)
            
            if debug_info != "none":
                print(f"[PIP_ArtisticWords] 检测到发光效果，增加安全区域边距")
                print(f"[PIP_ArtisticWords] 调整后安全区域: 左={left}, 上={top}, 右={right}, 下={bottom}")
        
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
        effects_processor = EffectsProcessor()
        
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
        
        styled_text_image = effects_processor.apply_all_effects(base_text_image, style_data)
        
        # 创建更智能的alpha通道处理
        # 不再简单替换alpha通道，而是通过对比和混合保留效果区域
        if debug_info == "detailed":
            print(f"[PIP_ArtisticWords] 特效应用后开始处理alpha通道")
        
        r, g, b, styled_alpha = styled_text_image.split()
        _, _, _, base_alpha_copy = base_text_image.split()
        
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
        
        if has_glow or selected_style_name in ["neon_glow", "fire_effect", "fire_flame", "cyberpunk"]:
            # 特殊处理那些含有发光效果或特定样式的情况
            # 对于有发光效果的，我们保留原始styled_alpha通道以展示发光效果
            if has_glow:
                effective_alpha = styled_alpha
                if debug_info == "detailed":
                    print(f"[PIP_ArtisticWords] 检测到发光效果，保留原始alpha通道")
            else:
                # 对于特定样式，扩展原始alpha
                expanded_alpha = base_alpha_copy.filter(ImageFilter.MaxFilter(20))  # 扩展原始alpha以包含更多发光区域
                # 使用原始styled_alpha，不过滤低透明度区域，保留发光效果
                effective_alpha = styled_alpha
                if debug_info == "detailed":
                    print(f"[PIP_ArtisticWords] 应用特殊alpha处理给样式: {selected_style_name}")
        else:
            # 通常情况：保留样式效果区域
            # 1. 保留原始文本区域
            # 2. 保留原始区域周围的效果（描边、阴影等）
            
            # 首先扩展原始alpha创建效果区域
            effect_area = base_alpha_copy.filter(ImageFilter.MaxFilter(9))  # 扩大几个像素覆盖描边范围
            
            # 保留styled_alpha中alpha值大于阈值的区域（过滤掉半透明黑色背景）
            # 修改：将所有非零alpha值设为255（完全不透明）而不是保留原始透明度值
            threshold = 40  # 低于这个阈值的透明度会被过滤掉
            filtered_styled_alpha = styled_alpha.point(lambda x: 255 if x > threshold else 0)
            
            # 将两者结合：原始扩展区域中，保留样式alpha中足够明显的部分
            effective_alpha = ImageChops.multiply(filtered_styled_alpha, effect_area)
            if debug_info == "detailed":
                print(f"[PIP_ArtisticWords] 应用标准alpha处理，保留描边和效果")
        
        # 重建最终图像
        styled_text_image = Image.merge('RGBA', (r, g, b, effective_alpha))
        
        # 检查alpha通道是否正确保留，并根据需要调整不透明度
        if opacity < 1.0:
            # Adjust the opacity of the text overlay
            r, g, b, a = styled_text_image.split()
            a = a.point(lambda x: int(x * opacity))
            styled_text_image = Image.merge('RGBA', (r, g, b, a))
        
        # 禁用对渐变效果的额外模糊处理（这会产生半透明像素）
        # Extra processing for styles that often result in black backgrounds
        # if selected_style_name in ["neon_glow", "fire_effect", "fire_flame", "cyberpunk"] or has_glow:
        #     # Apply a slight blur to soften transitions for glow effects
        #     styled_text_image = styled_text_image.filter(ImageFilter.GaussianBlur(0.5))
        #     if debug_info == "detailed":
        #         if has_glow:
        #             print(f"[PIP_ArtisticWords] 应用额外模糊处理优化发光效果")
        #         else:
        #             print(f"[PIP_ArtisticWords] 应用额外模糊处理优化特殊样式: {selected_style_name}")
        
        if debug_info != "none":
            alpha_channel = styled_text_image.getchannel('A')
            print(f"[PIP_ArtisticWords] Alpha channel stats - Min: {alpha_channel.getextrema()[0]}, Max: {alpha_channel.getextrema()[1]}")
        
        # Create a new transparent image for the compositing
        result_image = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
        
        # Paste the original image first
        pil_image_rgba = pil_image.convert('RGBA')
        result_image.paste(pil_image_rgba, (0, 0))
        
        # Use alpha_composite instead of pixel-by-pixel for better performance
        result_image = Image.alpha_composite(result_image, styled_text_image)
        
        # 确保文本区域完全不透明
        # 获取结果图像的alpha通道
        r, g, b, a = result_image.split()
        
        # 对于所有alpha值大于0的像素，将其设置为255（完全不透明）
        final_alpha = a.point(lambda x: 255 if x > 0 else x)
        
        # 合并回最终图像
        result_image = Image.merge('RGBA', (r, g, b, final_alpha))
        
        # Convert back to tensor (BHWC format)
        result_tensor = pil_to_tensor(result_image)
        
        return (result_tensor,)

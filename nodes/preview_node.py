import os
import random
from PIL import Image
import torch
import numpy as np

# Use relative imports to maintain portability
from ..core.style_manager import StyleManager
from ..core.text_renderer import TextRenderer
from ..core.effects_processor import EffectsProcessor
from ..utils.tensor_utils import pil_to_tensor, create_alpha_mask, clean_alpha_mask


class TextPreviewNode:
    """Node for generating text with transparent background for previewing in ComfyUI."""
    
    @classmethod
    def INPUT_TYPES(cls):
        # Get available styles
        style_manager = StyleManager()
        style_names = style_manager.get_style_names()
        
        return {
            "required": {
                "text": ("STRING", {"multiline": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1}),
                "seed_mode": (["random", "fixed", "increment", "decrement"],),
                "style": (["random"] + style_names,),
            },
            "optional": {
                "width": ("INT", {"default": 1440, "min": 128, "max": 4096, "step": 8}),
                "height": ("INT", {"default": 1440, "min": 128, "max": 4096, "step": 8}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "alpha_mask")
    FUNCTION = "generate_text_preview"
    CATEGORY = "PIP"
    
    def generate_text_preview(self, text, seed, seed_mode="random", style="random", 
                              width=1440, height=1440):
        """
        Generate a preview of artistic text with transparent background.
        
        Args:
            text: Text to render
            seed: Random seed
            seed_mode: Seed mode (random, fixed, increment, decrement)
            style: Style to apply or "random"
            width: Output image width
            height: Output image height
        
        Returns:
            Image tensor with text and alpha mask
        """
        # Set random seed for reproducibility
        if seed_mode == "random" or seed == 0:
            seed = random.randint(0, 0xffffffffffffffff)
        elif seed_mode == "increment":
            seed += 1
        elif seed_mode == "decrement":
            seed = max(0, seed - 1)
        
        # Use seed for reproducibility
        random.seed(seed)
        
        # Create style manager and load styles/fonts
        style_manager = StyleManager()
        
        # 获取样式和字体
        if style == "random":
            style_data, font_name = style_manager.generate_random_combination()
        else:
            style_data = style_manager.get_style(style)
            font_name = random.choice(style_manager.get_font_names())
        
        # 处理尚未设置字体的情况（可能是SVG样式）
        if 'font_name' not in locals() or 'font_name' not in globals():
            if 'font' in style_data and style_data['font'] in style_manager.get_font_names():
                font_name = style_data['font']
            else:
                font_name = random.choice(style_manager.get_font_names())
        
        # Get font path
        font_path = style_manager.get_font_path(font_name)
        
        # Create transparent image
        transparent_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # 添加安全区域，上下左右各预留10%空间，避免发光效果被截断
        margin_percent = 0.1  # 10% 边距
        left = int(width * margin_percent)
        right = width - int(width * margin_percent)
        top = int(height * margin_percent)
        bottom = height - int(height * margin_percent)
        safe_area = (left, top, right, bottom)
        
        # 检测样式中是否有发光效果，如果有则使用更大的安全区域
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
            # 发光效果需要更多空间，增加边距到15%
            glow_margin = 0.15
            left = int(width * glow_margin)
            right = width - int(width * glow_margin)
            top = int(height * glow_margin)
            bottom = height - int(height * glow_margin)
            safe_area = (left, top, right, bottom)
        
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
        styled_text_image = effects_processor.apply_all_effects(base_text_image, style_data)
        
        # Convert to tensor (BHWC format)
        result_tensor = pil_to_tensor(styled_text_image)
        
        # Create alpha mask
        alpha_mask = create_alpha_mask(result_tensor)
        
        # Clean alpha mask to remove semi-transparent pixels
        clean_mask = clean_alpha_mask(alpha_mask)
        
        return (result_tensor, clean_mask)

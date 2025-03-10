import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops, ImageOps, ImageMath
import random
import colorsys
import math

class EffectsProcessor:
    """Processes and applies various text effects based on styles."""
    
    def __init__(self, debug_output=False):
        """Initialize the effects processor.
        
        Args:
            debug_output: Whether to save debug images during processing
        """
        self.debug_output = debug_output
        
    def _save_debug_image(self, img, filename):
        """Save a debug image if debug_output is enabled."""
        if self.debug_output:
            img.save(filename)
    
    def hex_to_rgba(self, hex_color, alpha=255):
        """Convert hex color to RGBA tuple."""
        if not hex_color:
            return (255, 255, 255, alpha)
        
        hex_color = hex_color.lstrip('#')
        length = len(hex_color)
        
        if length == 6:
            return (*tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)), alpha)
        elif length == 8:
            r, g, b, a = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
            return (r, g, b, alpha if alpha != 255 else a)
        return (255, 255, 255, alpha)

    def apply_all_effects(self, base_img, style, style_name="unknown"):
        """应用所有效果在同一图像上，确保正确的叠加顺序和透明度"""
        print(f"[Style: {style_name}] 开始应用组合效果")
        
        # 确保图像有alpha通道
        img = base_img.convert('RGBA') if base_img.mode != 'RGBA' else base_img.copy()
        
        # 获取文本区域mask，用于限制效果
        original_r, original_g, original_b, text_mask = img.split()
        
        # 创建一个底层图像，用于收集所有效果
        result = Image.new('RGBA', img.size, (0, 0, 0, 0))
        
        # 保存各效果层的临时图像，用于调试
        layers = {}
        
        # 1. 首先应用阴影 (如果指定)
        if 'shadow' in style:
            shadow_img = self.apply_shadow(img, style)
            # 保存用于调试
            self._save_debug_image(shadow_img, f"debug_{style_name}_shadow.png")
            layers['shadow'] = shadow_img
            result = Image.alpha_composite(result, shadow_img)
            print(f"[Style: {style_name}] 已应用阴影效果")
            
        # 2. 应用外发光效果 (如果指定)
        if 'glow' in style:
            glow_img = self.apply_glow(img, style)
            # 保存用于调试
            self._save_debug_image(glow_img, f"debug_{style_name}_glow.png")
            layers['glow'] = glow_img
            result = Image.alpha_composite(result, glow_img)
            print(f"[Style: {style_name}] 已应用发光效果")
        
        # 3. 创建文本填充层 - 使用渐变或单色填充
        text_fill = None
        
        # 检查fill类型，确保渐变正确处理
        fill_type = None
        if 'fill' in style:
            if isinstance(style['fill'], dict):
                fill_type = style['fill'].get('type')
            elif style['fill'] == 'gradient':
                fill_type = 'gradient'
        
        if 'gradient' in style or fill_type == 'gradient':
            # 获取填充样式
            fill = style.get('fill', {})
            # 如果fill不是字典，创建一个默认字典
            if not isinstance(fill, dict):
                fill = {'type': 'gradient', 'colors': ['#FFFFFF', '#0066FF'], 'angle': 90}
                
            # 确保colors存在
            colors = fill.get('colors', ['#FFFFFF', '#0066FF'])  # 默认为白色到蓝色渐变
            if isinstance(colors, str):
                colors = [colors, '#0066FF']  # 如果只有一个颜色，创建从该颜色到蓝色的渐变
                
            angle = fill.get('angle', 90)  # SVG默认是从上到下的渐变
            
            print(f"[Style: {style_name}] 渐变填充颜色: {colors}, 角度: {angle}")
            
            # 创建渐变图像 - 使用整个图像尺寸
            gradient_img = self._create_gradient(
                img.size[0], 
                img.size[1], 
                [self.hex_to_rgba(color)[:3] for color in colors],
                angle
            )
            
            # 创建一个只包含文本形状的二值蒙版（白色=文本区域，黑色=背景）
            binary_mask = Image.new('1', img.size, 0)  # 初始化全黑二值图像
            binary_mask.paste(1, (0, 0), text_mask)  # 在文本区域粘贴白色
            
            # 使用numpy进行精确的像素级操作
            gradient_array = np.array(gradient_img)
            mask_array = np.array(binary_mask)
            
            # 扩展mask数组以匹配渐变数组的形状
            mask_array_3d = np.stack([mask_array] * 3, axis=2)
            
            # 将渐变应用到文本区域（其他区域保持黑色）
            gradient_masked = gradient_array * mask_array_3d
            
            # 转换回PIL图像并添加透明通道
            gradient_masked_img = Image.fromarray(gradient_masked.astype(np.uint8))
            gradient_masked_rgba = gradient_masked_img.convert('RGBA')
            
            # 将透明度通道设置为文本的透明度
            r, g, b, _ = gradient_masked_rgba.split()
            text_fill = Image.merge('RGBA', (r, g, b, text_mask))
            
            # 保存用于调试
            self._save_debug_image(text_fill, f"debug_{style_name}_gradient_fill.png")
            layers['fill'] = text_fill
            
            print(f"[Style: {style_name}] 已应用文本渐变效果")
        else:
            # 如果没有指定渐变，则使用单色填充
            fill_color = (64, 150, 255)  # 浅蓝色作为默认值
            if 'fill' in style:
                if isinstance(style['fill'], dict) and 'color' in style['fill']:
                    fill_color_hex = style['fill'].get('color', '#4096FF')
                    fill_color = self.hex_to_rgba(fill_color_hex)[:3]
                elif isinstance(style['fill'], str):
                    # 如果fill是直接的颜色值
                    fill_color = self.hex_to_rgba(style['fill'])[:3]
            
            print(f"[Style: {style_name}] 单色填充: {fill_color}")
            
            color_pixels = Image.new('RGB', img.size, fill_color)
            text_fill = Image.merge('RGBA', (color_pixels.split() + (text_mask,)))
            
            # 保存用于调试
            self._save_debug_image(text_fill, f"debug_{style_name}_solid_fill.png")
            layers['fill'] = text_fill
            
            print(f"[Style: {style_name}] 已应用文本颜色填充")
        
        # 4. 准备描边效果
        outline_img = None
        if 'outline' in style:
            outline = style['outline']
            
            if outline.get('width', 0) > 0 and outline.get('opacity', 0) > 0:
                # 创建基础图像用于描边
                # 使用原始图像作为基础，确保描边位于正确位置
                outline_base = img.copy()
                
                # 应用描边
                if 'gradient' in outline:
                    outline_img = self._apply_gradient_outline(outline_base, style, style_name)
                    print(f"[Style: {style_name}] 已应用渐变描边效果")
                else:
                    outline_img = self.apply_outline(outline_base, style)
                    print(f"[Style: {style_name}] 已应用普通描边效果")
                
                # 保存用于调试
                self._save_debug_image(outline_img, f"debug_{style_name}_outline.png")
                layers['outline'] = outline_img
        
        # 5. 准备内阴影效果
        inner_shadow_img = None
        if 'inner_shadow' in style:
            # 对于内阴影，我们使用原始文本形状
            inner_shadow_base = img.copy()
            inner_shadow_img = self.apply_inner_shadow(inner_shadow_base, style)
            
            # 保存用于调试  
            self._save_debug_image(inner_shadow_img, f"debug_{style_name}_inner_shadow.png")
            layers['inner_shadow'] = inner_shadow_img
            
            print(f"[Style: {style_name}] 已应用内阴影效果")
            
        # 打印当前所有层信息
        print(f"[Style: {style_name}] 图层信息: {', '.join(layers.keys())}")
        
        # 完全重构效果合成逻辑
        # =====================================================
        # 创建一个全新的透明底图
        final_result = Image.new('RGBA', img.size, (0, 0, 0, 0))
        
        # 1. 底层 - 阴影和发光
        shadow_glow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        if 'shadow' in layers:
            shadow_glow_layer = Image.alpha_composite(shadow_glow_layer, layers['shadow'])
        if 'glow' in layers:
            shadow_glow_layer = Image.alpha_composite(shadow_glow_layer, layers['glow'])
        
        final_result = Image.alpha_composite(final_result, shadow_glow_layer)
        self._save_debug_image(final_result, f"debug_{style_name}_step1_shadow_glow.png")
        print(f"[Style: {style_name}] 已合成阴影和发光图层")
        
        # 2. 文本填充层 - 直接使用text_fill
        if text_fill:
            # 在黑色背景上查看填充效果用于调试
            bg_debug = Image.new('RGBA', img.size, (0, 0, 0, 255))
            fill_on_black = Image.alpha_composite(bg_debug, text_fill)
            self._save_debug_image(fill_on_black, f"debug_{style_name}_fill_on_black.png")
            
            # 正常合成到结果中
            filled_result = Image.alpha_composite(final_result, text_fill)
            final_result = filled_result
            self._save_debug_image(final_result, f"debug_{style_name}_step2_with_fill.png")
            print(f"[Style: {style_name}] 已合成填充图层")
        
        # 3. 描边层 - 只添加文本外部的描边部分
        if outline_img:
            # 提取原始文本形状的alpha通道
            text_alpha = np.array(text_mask)
            
            # 提取描边图像的alpha通道
            outline_alpha = np.array(outline_img.split()[3])
            
            # 创建只包含描边部分的掩码（描边减去原始文本）
            outline_only_mask_array = np.clip(outline_alpha - text_alpha, 0, 255)
            
            # 转换为PIL Image
            outline_only_mask = Image.fromarray(outline_only_mask_array)
            
            # 如果未提供style_name，尝试从style字典中获取，如果都没有则使用默认值
            if style_name is None:
                style_name = style.get('name', 'unknown')
            
            # 保存调试图像    
            self._save_debug_image(outline_only_mask, f"debug_{style_name}_outline_mask.png")
            
            # 创建只含描边部分的图像
            r, g, b, _ = outline_img.split()
            outline_only = Image.merge('RGBA', (r, g, b, outline_only_mask))
            self._save_debug_image(outline_only, f"debug_{style_name}_outline_only.png")
            
            # 合成到结果中
            outlined_result = Image.alpha_composite(final_result, outline_only)
            final_result = outlined_result
            self._save_debug_image(final_result, f"debug_{style_name}_step3_with_outline.png")
            print(f"[Style: {style_name}] 已合成描边图层")
        
        # 4. 内阴影层 - 只在文本区域内
        if inner_shadow_img:
            # 提取内阴影的RGB通道
            inner_r, inner_g, inner_b, inner_a = inner_shadow_img.split()
            
            # 确保内阴影只在文本区域内
            inner_mask_array = np.minimum(np.array(text_mask), np.array(inner_a))
            
            # 创建边缘区域蒙版 - 只在文本内部边缘显示内阴影
            try:
                from PIL import ImageFilter, ImageOps
                import cv2
                
                # 获取原始文本蒙版的NumPy数组
                text_mask_array = np.array(text_mask)
                
                # 转换为OpenCV可用的格式
                text_mask_cv = text_mask_array.astype(np.uint8)
                
                # 获取内阴影参数
                inner_shadow = style.get('inner_shadow', {}) if style else {}
                
                # 获取模糊值 - 直接使用SVG中定义的模糊参数
                blur_amount = float(inner_shadow.get('blur', 2.0))
                
                # 定义内部侵蚀的程度 - 与模糊值关联，确保内阴影宽度合适
                # 根据模糊程度自适应调整侵蚀宽度，更大的模糊值对应更宽的内阴影
                erosion_pixels = max(2, int(blur_amount * 1.5))
                
                # 创建一个边缘检测使用的核
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
                
                # 先侵蚀文本区域
                eroded = cv2.erode(text_mask_cv, kernel, iterations=erosion_pixels)
                
                # 计算边缘区域 = 原始文本区域 - 侵蚀后的区域
                edge_only = text_mask_cv - eroded
                
                # 应用内阴影偏移 - 实现真正的内阴影效果
                # 获取偏移值
                offset_x = float(inner_shadow.get('offset_x', 3.0))
                offset_y = float(inner_shadow.get('offset_y', 3.0))
                
                print(f"内阴影偏移值: X={offset_x}, Y={offset_y}")
                
                # 创建原始边缘的副本
                original_edge = edge_only.copy()
                
                # 创建偏移矩阵
                M = np.float32([[1, 0, offset_x], [0, 1, offset_y]])
                
                # 应用偏移
                edge_shifted = cv2.warpAffine(original_edge, M, (original_edge.shape[1], original_edge.shape[0]))
                
                # 确保仍然在文本区域内
                edge_shifted = cv2.bitwise_and(edge_shifted, text_mask_cv)
                
                # 关键改进：连接原始边缘和偏移边缘之间的区域
                # 创建多个中间偏移，并将它们合并以形成连续区域
                steps = 8  # 中间步骤数
                inner_shadow_area = original_edge.copy()  # 从原始边缘开始
                
                for step in range(1, steps + 1):
                    # 计算当前步骤的部分偏移
                    curr_offset_x = offset_x * step / steps
                    curr_offset_y = offset_y * step / steps
                    
                    # 创建当前偏移矩阵
                    curr_M = np.float32([[1, 0, curr_offset_x], [0, 1, curr_offset_y]])
                    
                    # 应用当前偏移
                    curr_shifted = cv2.warpAffine(original_edge, curr_M, (original_edge.shape[1], original_edge.shape[0]))
                    
                    # 确保仍然在文本区域内
                    curr_shifted = cv2.bitwise_and(curr_shifted, text_mask_cv)
                    
                    # 合并到内阴影区域
                    inner_shadow_area = cv2.bitwise_or(inner_shadow_area, curr_shifted)
                
                # 使用连续的内阴影区域替代之前仅偏移的边缘
                edge_shifted = inner_shadow_area
                
                # 略微模糊边缘以获得平滑的过渡 - 使用SVG指定的模糊值
                edge_shifted = cv2.GaussianBlur(edge_shifted, (5, 5), blur_amount / 2.0)
                
                # 转回PIL格式
                edge_mask = Image.fromarray(edge_shifted)
                
                # 保存调试图像
                self._save_debug_image(edge_mask, f"debug_{style_name}_inner_shadow_edge_mask.png")
                
                # 使用边缘蒙版控制内阴影的应用范围 - 不需要反转掩码
                inner_shadow_masked = Image.merge('RGBA', (inner_r, inner_g, inner_b, edge_mask))
                
                self._save_debug_image(inner_shadow_masked, f"debug_{style_name}_inner_shadow_masked.png")
            except Exception as e:
                print(f"创建内阴影边缘蒙版失败，使用默认方式: {e}")
                inner_mask = Image.fromarray(inner_mask_array)
                inner_shadow_masked = Image.merge('RGBA', (inner_r, inner_g, inner_b, inner_mask))
            
            # 添加高斯模糊以平滑边缘 - 使用SVG中定义的模糊值
            try:
                from PIL import ImageFilter
                # 使用小半径的高斯模糊平滑边缘
                blur_radius = blur_amount / 3.0  # 轻微降低模糊半径，保留细节但平滑边缘
                inner_shadow_blurred = inner_shadow_masked.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                # 保存模糊后的内阴影用于调试
                self._save_debug_image(inner_shadow_blurred, f"debug_{style_name}_inner_shadow_blurred.png")
            except Exception as e:
                print(f"应用高斯模糊失败: {e}")
                inner_shadow_blurred = inner_shadow_masked  # 如果模糊失败，使用原始内阴影
            
            # 保存一份当前结果，以便在出错时回退
            backup_result = final_result.copy()
            
            # 使用标准alpha合成
            try:
                result_with_inner_shadow = Image.alpha_composite(final_result, inner_shadow_blurred)
                final_result = result_with_inner_shadow
                self._save_debug_image(final_result, f"debug_{style_name}_step4_with_inner_shadow.png")
                print(f"[Style: {style_name}] 已合成内阴影图层")
            except Exception as e:
                print(f"内阴影合成出错: {e}")
                print(f"回退到原始结果")
                final_result = backup_result
        
        # 最终结果
        self._save_debug_image(final_result, f"debug_{style_name}_final.png")
        
        # 带黑色背景版本
        bg = Image.new('RGBA', img.size, (0, 0, 0, 255))
        with_bg = Image.alpha_composite(bg, final_result)
        self._save_debug_image(with_bg, f"debug_{style_name}_with_bg.png")
        
        print(f"[Style: {style_name}] 所有效果应用完成")
        return final_result

    def _create_gradient(self, width, height, colors, angle=0):
        """通用渐变创建方法"""
        gradient = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Use vectorized calculations instead of loops
        x, y = np.meshgrid(np.arange(width), np.arange(height))
        
        if isinstance(angle, str) and angle == 'radial':
            # 径向渐变
            pos = np.sqrt((x - width/2)**2 + (y - height/2)**2)
            pos = pos / np.max(pos)  # 归一化到[0,1]范围
        else:
            # 线性渐变
            angle_rad = np.radians(angle)
            pos = ((x - width/2) * np.cos(angle_rad) + (y - height/2) * np.sin(angle_rad))
            pos = (pos - np.min(pos)) / (np.max(pos) - np.min(pos))  # 归一化到[0,1]范围
        
        # 插值生成渐变
        for i in range(3):  # RGB通道
            gradient[..., i] = np.interp(pos, [0, 1], [colors[0][i], colors[1][i]])
        
        return Image.fromarray(gradient, 'RGB')

    def apply_shadow(self, img, style):
        """Apply shadow effect to text."""
        if 'shadow' not in style:
            return img
            
        shadow = style['shadow']
        color = shadow.get('color', '#000000')
        blur = shadow.get('blur', 5)
        opacity = shadow.get('opacity', 0.7)
        
        # Support different offset value representations
        if 'offset' in shadow:
            offset = shadow['offset']
            offset_x, offset_y = offset if isinstance(offset, list) else (offset, offset)
        else:
            offset_x = shadow.get('offset_x', 5)
            offset_y = shadow.get('offset_y', 5)
            
        print(f"[EffectsProcessor] 阴影偏移: X={offset_x}, Y={offset_y}")
        
        # 确保透明度在有效范围内
        if isinstance(opacity, str):
            try:
                opacity = float(opacity)
            except ValueError:
                opacity = 0.7
        
        opacity = max(0.0, min(1.0, opacity))
        
        shadow_color = self.hex_to_rgba(color, int(255 * opacity))
        
        # Extract alpha channel
        mask = img.split()[3]
        
        # Create shadow layer
        shadow_layer = Image.new('RGBA', img.size, shadow_color)
        shadow_layer.putalpha(mask)
        
        # Offset shadow layer
        shadow_layer = ImageChops.offset(shadow_layer, int(round(offset_x)), int(round(offset_y)))
        
        # Apply blur
        if blur > 0:
            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=blur))
        
        # Create result image - first place the shadow, then the original image
        shadow_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        shadow_img = Image.alpha_composite(shadow_img, shadow_layer)
        
        result = Image.new('RGBA', img.size, (0, 0, 0, 0))
        result = Image.alpha_composite(result, shadow_img)
        result = Image.alpha_composite(result, img)
        
        return result
    
    def apply_outline(self, img, style):
        """Apply outline to text."""
        if 'outline' not in style:
            return img
        
        outline = style['outline']
        outline_width = outline.get('width', 1)
        outline_color = self.hex_to_rgba(outline.get('color', '#000000'))
        
        if outline_width <= 0:
            return img
        
        # Create a mask from the alpha channel
        mask = img.split()[3]
        
        # Create outline layer
        outline_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        
        # Apply dilation to the mask for each outline pixel
        dilated = mask
        for i in range(1, int(round(outline_width)) + 1):
            dilated = dilated.filter(ImageFilter.MaxFilter(3))
        
        # Create the outline
        outline_layer = Image.new('RGBA', img.size, outline_color)
        outline_layer.putalpha(dilated)
        
        # Composite with the existing outline
        outline_img = Image.alpha_composite(outline_img, outline_layer)
        
        # Composite the original image on top of the outline
        result = Image.alpha_composite(outline_img, img)
        return result
        
    def _apply_gradient_outline(self, img, style, style_name=None):
        """使用渐变效果应用描边。"""
        # Get the text mask
        mask = img.split()[3]
        
        # Handle gradient outline
        gradient = style.get('outline', {})
        width = float(gradient.get('width', 0))
        opacity = float(gradient.get('opacity', 1.0))
        
        print(f"[EffectsProcessor] 渐变描边详情 - 宽度: {width}, 透明度: {opacity}, 渐变类型: {gradient.get('type', 'linear')}")
        print(f"[EffectsProcessor] 渐变颜色: {gradient.get('colors', ['#FF0000', '#FFFF00'])}")
        
        # Create outline by dilating the mask
        dilated_mask = mask.copy()
        outline_img = img.copy()
        
        # Apply the outline width (dilate the mask)
        w = int(width)
        print(f"[EffectsProcessor] 实际使用的描边宽度: {w}")
        print(f"最终描边不透明度: {opacity}")
        
        # Only apply if width > 0
        if w > 0:
            # Apply multiple dilations for better results
            for _ in range(w):
                dilated_mask = dilated_mask.filter(ImageFilter.MaxFilter(3))
        
        # Create outline mask (only keep the dilated area, excluding the original text area)
        outline_only_mask_array = np.clip(np.array(dilated_mask) - np.array(mask), 0, 255)
        
        # 转换为PIL Image
        outline_only_mask = Image.fromarray(outline_only_mask_array)
        
        # 如果未提供style_name，尝试从style字典中获取，如果都没有则使用默认值
        if style_name is None:
            style_name = style.get('name', 'unknown')
        
        # 保存调试图像    
        self._save_debug_image(outline_only_mask, f"debug_{style_name}_outline_mask.png")
        
        # Create gradient for outline
        colors = gradient.get('colors', ['#FF0000', '#FFFF00'])
        angle = gradient.get('angle', 0)
        
        # Convert hex colors to RGB
        rgb_colors = []
        for color in colors:
            if isinstance(color, str) and color.startswith('#'):
                # Convert hex to RGB
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                rgb_colors.append((r, g, b))
            elif isinstance(color, (list, tuple)) and len(color) == 3:
                rgb_colors.append(color)
            else:
                rgb_colors.append((255, 0, 0))  # Default to red if invalid
        
        if not rgb_colors:
            rgb_colors = [(255, 0, 0), (255, 255, 0)]  # Default gradient
            
        # Create gradient
        gradient_array = self._create_gradient(img.size[0], img.size[1], rgb_colors, angle)
        gradient_img = gradient_array.convert('RGBA')
        gradient_img.putalpha(outline_only_mask)
        
        # Composite images
        result = Image.alpha_composite(outline_img, gradient_img)
        self._save_debug_image(result, f"debug_{style_name}_outline_only.png")
        
        return result
        
    def apply_glow(self, img, style):
        """Apply glow effect to text."""
        glow_key = 'glow'
        if glow_key not in style:
            glow_key = 'outer_glow'
            if glow_key not in style:
                return img
        
        glow = style[glow_key]
        if glow is None:
            return img
            
        glow_color = self.hex_to_rgba(glow.get('color', '#FFFFFF'), 100)
        radius = glow.get('radius', 10)
        intensity = glow.get('intensity', 0.5)
        
        # If radius or intensity is 0, skip the glow effect
        if radius <= 0 or intensity <= 0:
            return img
        
        # 调整发光半径
        font_size_scale = 1.0
        radius = max(radius * font_size_scale, 5)
        print(f"[EffectsProcessor] 最终发光半径: {radius:.2f} (基础半径: {radius})")
        
        # Create mask from alpha channel
        mask = img.split()[3]
        expanded_mask = mask.filter(ImageFilter.MaxFilter(3))
        
        # Create glow layer
        glow_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        glow_layer = Image.new('RGBA', img.size, glow_color)
        glow_layer.putalpha(expanded_mask)
        
        # Apply blur for the glow effect
        if radius > 0:
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius))
        
        # Enhance glow intensity
        enhanced_intensity = min(intensity * 1.2, 1.0)
        
        # Adjust intensity
        if enhanced_intensity < 1.0:
            glow_r, glow_g, glow_b, glow_a = glow_layer.split()
            glow_a = glow_a.point(lambda x: int(x * enhanced_intensity))
            glow_layer = Image.merge('RGBA', (glow_r, glow_g, glow_b, glow_a))
        
        # Apply the glow layer
        glow_img = Image.alpha_composite(glow_img, glow_layer)
        
        # For high-intensity glows, add an additional inner layer
        if intensity > 0.6:
            inner_glow = Image.new('RGBA', img.size, glow_color)
            inner_glow.putalpha(mask)
            inner_glow = inner_glow.filter(ImageFilter.GaussianBlur(radius * 0.5))
            
            # Composite the glow
            glow_img = Image.alpha_composite(glow_img, inner_glow)
            print(f"[EffectsProcessor] 应用额外的内层发光，增强边缘亮度")
        
        # Composite glow and original
        result = Image.alpha_composite(glow_img, img)
        
        return result
        
    def apply_inner_shadow(self, img, style):
        """Apply inner shadow effect to text."""
        if 'inner_shadow' not in style:
            return img
        
        inner_shadow = style['inner_shadow']
        color = inner_shadow.get('color', '#000000')
        opacity = inner_shadow.get('opacity', 0.7)
        
        # Support different offset value representations
        if 'offset' in inner_shadow:
            offset = inner_shadow['offset']
            offset_x, offset_y = offset if isinstance(offset, list) else (offset, offset)
        else:
            offset_x = inner_shadow.get('offset_x', 2)
            offset_y = inner_shadow.get('offset_y', 2)
        
        blur = inner_shadow.get('blur', 2)
        
        print(f"[EffectsProcessor] 应用内阴影效果 - 颜色: {color}, 透明度: {opacity}, 模糊: {blur}")
        print(f"[EffectsProcessor] 内阴影偏移: X={offset_x}, Y={offset_y}")
        
        # 确保透明度在有效范围内
        if isinstance(opacity, str):
            try:
                opacity = float(opacity)
            except ValueError:
                opacity = 0.5
                
        opacity = max(0.1, min(1.0, opacity))
        
        # 确保图像是RGBA模式
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 复制原始图像
        original = img.copy()
        
        # 获取原始图像的alpha通道作为蒙版
        r_orig, g_orig, b_orig, a_orig = original.split()
        mask = a_orig.copy()
        
        # 创建偏移蒙版 - 内阴影从边缘向内偏移
        offset_mask = ImageChops.offset(mask, -int(round(offset_x)), -int(round(offset_y)))
        
        # 创建内阴影蒙版 - 阴影区域是原始蒙版和偏移蒙版之间的差异
        shadow_mask = ImageChops.subtract(mask, offset_mask)
        
        # 应用高斯模糊
        if blur > 0:
            shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(blur))
        
        # 创建内阴影层
        shadow_color = self.hex_to_rgba(color)
        shadow_layer = Image.new('RGBA', img.size, shadow_color)
        
        # 应用阴影蒙版到阴影层
        r_shadow, g_shadow, b_shadow, a_shadow = shadow_layer.split()
        
        # 应用不透明度到阴影蒙版
        shadow_mask = shadow_mask.point(lambda x: int(x * opacity))
        
        # 合并阴影层
        shadow_layer = Image.merge('RGBA', (r_shadow, g_shadow, b_shadow, shadow_mask))
        
        # 创建结果图像 - 保留原始图像，仅在边缘添加内阴影
        result = Image.new('RGBA', img.size, (0, 0, 0, 0))
        result = Image.alpha_composite(result, original)
        result = Image.alpha_composite(result, shadow_layer)
        
        return result

        texture_img = texture_img.resize(img.size)
        
        # Apply texture
        result = Image.alpha_composite(img, texture_img)
        
        # Save debug image
        self._save_debug_image(result, f"debug_texture_result.png")
        
        return result

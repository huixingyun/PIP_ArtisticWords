import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops, ImageOps
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
        
        # 确定要应用的效果列表 - 按SVG标准的顺序：
        # 1. Shadow（阴影）
        # 2. Glow (外发光) 
        # 3. Fill（填充）
        # 4. Outline（描边）
        # 5. Inner Shadow（内阴影）
        effects_order = []
        
        if 'shadow' in style and style.get('shadow', {}).get('opacity', 0) > 0:
            effects_order.append('shadow')
            
        if 'glow' in style and style.get('glow', {}).get('opacity', 0) > 0:
            effects_order.append('glow')
        
        effects_order.append('fill')  # 填充始终应用
        
        if 'outline' in style and style.get('outline', {}).get('width', 0) > 0 and style.get('outline', {}).get('opacity', 0) > 0:
            effects_order.append('outline')
            
        if 'inner_shadow' in style and style.get('inner_shadow', {}).get('opacity', 0) > 0:
            effects_order.append('inner_shadow')
        
        print(f"[Style: {style_name}] 图层信息: {', '.join(effects_order)}")
        
        # 现在应用所有效果按照effects_order列表的顺序
        for effect_name in effects_order:
            if effect_name == 'shadow':
                shadow_img = self.apply_shadow(img, style)
                if shadow_img:
                    # 保存用于调试
                    self._save_debug_image(shadow_img, f"debug_{style_name}_shadow.png")
                    layers['shadow'] = shadow_img
                    result = Image.alpha_composite(result, shadow_img)
                    print(f"[Style: {style_name}] 已合成阴影图层")
                    
            elif effect_name == 'outline':
                # 创建基础图像用于描边
                outline_base = Image.new('RGBA', img.size, (0, 0, 0, 0))
                outline_base.paste(img, (0, 0), text_mask)
                
                # 应用描边
                if 'gradient' in style.get('outline', {}):
                    outline_img = self._apply_gradient_outline(outline_base, style, style_name)
                else:
                    outline_img = self.apply_outline(outline_base, style)
                
                if outline_img:
                    # 保存用于调试
                    self._save_debug_image(outline_img, f"debug_{style_name}_outline.png")
                    layers['outline'] = outline_img
                    
                    # 修改合成方式 - 只覆盖非透明部分
                    # 使用alpha_composite，而不是简单的覆盖
                    # 这样填充颜色仍然可以在透明区域显示
                    result = Image.alpha_composite(result, outline_img)
                    print(f"[Style: {style_name}] 已合成描边图层")
                    
            elif effect_name == 'fill':
                fill_img = self.apply_fill(img, style)
                if fill_img:
                    # 保存用于调试
                    self._save_debug_image(fill_img, f"debug_{style_name}_fill.png")
                    layers['fill'] = fill_img
                    result = Image.alpha_composite(result, fill_img)
                    print(f"[Style: {style_name}] 已合成填充图层")
                    
            elif effect_name == 'inner_shadow':
                inner_shadow_img = self.apply_inner_shadow(img, style)
                if inner_shadow_img:
                    # 保存用于调试
                    self._save_debug_image(inner_shadow_img, f"debug_{style_name}_inner_shadow.png")
                    layers['inner_shadow'] = inner_shadow_img
                    try:
                        # 确保inner_shadow_img是PIL图像对象
                        if hasattr(inner_shadow_img, 'format') or hasattr(inner_shadow_img, 'split'):
                            # 修改合成方式 - 保留原始填充色的可见性
                            # 获取inner_shadow的alpha通道
                            _, _, _, inner_alpha = inner_shadow_img.split()
                            
                            # 为了确保填充色可见，调整内阴影的alpha通道
                            inner_alpha = inner_alpha.point(lambda x: min(x, 200))  # 降低最大不透明度
                            
                            # 重建内阴影图像
                            r, g, b, _ = inner_shadow_img.split()
                            adjusted_inner_shadow = Image.merge('RGBA', (r, g, b, inner_alpha))
                            
                            # 使用调整后的内阴影图像进行合成
                            result = Image.alpha_composite(result, adjusted_inner_shadow)
                            print(f"[Style: {style_name}] 已合成内阴影图层 (已调整透明度)")
                        else:
                            print(f"[警告] inner_shadow_img不是有效的PIL图像对象，跳过内阴影效果")
                    except Exception as e:
                        print(f"[错误] 合成内阴影效果时出错: {e}")
        
            elif effect_name == 'glow':
                glow_img = self.apply_glow(img, style)
                if glow_img:
                    # 保存用于调试
                    self._save_debug_image(glow_img, f"debug_{style_name}_glow.png")
                    layers['glow'] = glow_img
                    
                    # 外发光直接合成，不需要特殊处理
                    # 因为我们已经在apply_glow中确保它只应用于文本外部
                    try:
                        if hasattr(glow_img, 'format') or hasattr(glow_img, 'split'):
                            result = Image.alpha_composite(result, glow_img)
                            print(f"[Style: {style_name}] 已合成发光图层")
                        else:
                            print(f"[警告] glow_img不是有效的PIL图像对象，跳过发光效果")
                    except Exception as e:
                        print(f"[错误] 合成发光效果时出错: {e}")
        
        print(f"[Style: {style_name}] 样式应用完成!")
        return result, layers

    def _create_gradient(self, width, height, colors, angle=0, direction=None):
        """创建渐变背景
        
        Args:
            width: 图像宽度
            height: 图像高度
            colors: 颜色列表
            angle: 渐变角度（度）
            direction: 预定义方向（如果指定，则忽略angle）
                可能值：'left_right', 'right_left', 'top_bottom', 'bottom_top', 
                'diagonal', 'diagonal_reverse', 'diagonal_bottom', 'diagonal_bottom_reverse'
        
        Returns:
            渐变图像
        """
        # 创建空白RGBA图像
        gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient)
        
        # 确保colors是有效的RGB颜色列表
        if not colors or not isinstance(colors, list):
            # 使用默认颜色
            colors = [(238, 40, 131), (255, 220, 125)]  # 默认粉色到黄色
        
        # 打印实际传入的颜色值和渐变方向进行调试
        print(f"\n======= 渐变填充调试 =======")
        print(f"尺寸={width}x{height}, 颜色数量={len(colors)}, 角度={angle}, 方向={direction}")
        for i, color in enumerate(colors):
            print(f"  颜色{i}: {color}")
            
        # 将角度映射到[-180, 180]范围
        if angle is not None:
            angle = angle % 360
            if angle > 180:
                angle -= 360
        
        # 预定义方向映射到角度
        if direction:
            if direction == 'left_right':
                angle = 0
                print("渐变方向: 从左到右")
            elif direction == 'right_left':
                angle = 180
                print("渐变方向: 从右到左")
            elif direction == 'top_bottom':
                angle = 90
                print("渐变方向: 从上到下")
            elif direction == 'bottom_top':
                angle = -90
                print("渐变方向: 从下到上")
            elif direction == 'diagonal':
                angle = 45
                print("渐变方向: 对角线(左上到右下)")
            elif direction == 'diagonal_reverse':
                angle = -135
                print("渐变方向: 对角线(右下到左上)")
            elif direction == 'diagonal_bottom':
                angle = 135
                print("渐变方向: 对角线(左下到右上)")
            elif direction == 'diagonal_bottom_reverse':
                angle = -45
                print("渐变方向: 对角线(右上到左下)")
        else:
            print(f"渐变方向: 自定义角度 {angle}度")
        
        # 确定渐变的起点和终点坐标
        if direction:
            # 直接使用与SVG相同的坐标映射
            if direction == 'left_right':        # 从左到右
                x1, y1, x2, y2 = 0, height//2, width, height//2
            elif direction == 'right_left':      # 从右到左
                x1, y1, x2, y2 = width, height//2, 0, height//2
            elif direction == 'top_bottom':      # 从上到下
                x1, y1, x2, y2 = width//2, 0, width//2, height
            elif direction == 'bottom_top':      # 从下到上
                x1, y1, x2, y2 = width//2, height, width//2, 0
            elif direction == 'diagonal':        # 左上到右下
                x1, y1, x2, y2 = 0, 0, width, height
            elif direction == 'diagonal_reverse': # 右下到左上
                x1, y1, x2, y2 = width, height, 0, 0
            elif direction == 'diagonal_bottom':  # 左下到右上
                x1, y1, x2, y2 = 0, height, width, 0
            elif direction == 'diagonal_bottom_reverse': # 右上到左下
                x1, y1, x2, y2 = width, 0, 0, height
            else:
                # 默认从上到下
                x1, y1, x2, y2 = width//2, 0, width//2, height
        else:
            # 如果提供角度，计算渐变线的端点
            rads = math.radians(angle)
            diagonal = math.sqrt(width**2 + height**2)
            center_x, center_y = width // 2, height // 2
            
            # 计算渐变线端点
            dx = math.cos(rads) * diagonal / 2
            dy = math.sin(rads) * diagonal / 2
            
            x1 = center_x - dx
            y1 = center_y - dy
            x2 = center_x + dx
            y2 = center_y + dy
        
        # 计算渐变线长度
        gradient_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        # 遍历图像中的每个像素
        for y in range(height):
            for x in range(width):
                # 计算像素到渐变线的投影位置
                if x2 != x1:
                    # 非垂直线
                    m = (y2 - y1) / (x2 - x1)
                    b = y1 - m * x1
                    
                    # 计算垂直于渐变线的直线方程
                    if m != 0:
                        m_perp = -1 / m
                        b_perp = y - m_perp * x
                        
                        # 计算交点
                        intersect_x = (b_perp - b) / (m - m_perp)
                        intersect_y = m * intersect_x + b
                    else:
                        # 水平渐变线
                        intersect_x = x
                        intersect_y = y1
                else:
                    # 垂直渐变线
                    intersect_x = x1
                    intersect_y = y
                
                # 计算交点在渐变线上的相对位置
                if gradient_length > 0:
                    # 计算线段参数t，表示交点在渐变线上的位置
                    if x2 != x1:
                        t = (intersect_x - x1) / (x2 - x1)
                    else:
                        t = (intersect_y - y1) / (y2 - y1)
                    
                    # 确保t在[0,1]范围内
                    t = max(0, min(1, t))
                    
                    # 根据颜色列表，计算渐变颜色
                    if len(colors) > 1:
                        # 至少有2种颜色时才需要计算渐变
                        index = int(t * (len(colors) - 1))
                        next_index = min(index + 1, len(colors) - 1)
                        
                        # 颜色位置的局部参数
                        local_t = (t * (len(colors) - 1)) - index
                        
                        # 插值计算颜色
                        r = int(colors[index][0] * (1 - local_t) + colors[next_index][0] * local_t)
                        g = int(colors[index][1] * (1 - local_t) + colors[next_index][1] * local_t)
                        b = int(colors[index][2] * (1 - local_t) + colors[next_index][2] * local_t)
                    else:
                        # 只有一种颜色时，直接使用该颜色
                        r, g, b = colors[0]
                    
                    # 设置渐变图像中的像素颜色
                    draw.point((x, y), fill=(r, g, b, 255))
        
        return gradient
    
    def apply_shadow(self, img, style):
        """Apply shadow effect to text."""
        if 'shadow' not in style:
            return None
        
        # 获取阴影参数
        shadow = style['shadow']
        color_hex = shadow.get('color', '#000000')
        # 确保使用SVG中指定的精确不透明度，而不是硬编码值
        opacity = float(shadow.get('opacity', 1.0))
        offset_x = float(shadow.get('offset_x', 5.0))
        offset_y = float(shadow.get('offset_y', 5.0))
        blur = float(shadow.get('blur', 5.0))
        
        # 如果不透明度为0，则不应用阴影
        if opacity <= 0:
            return None
        
        # 将十六进制颜色转换为RGBA
        shadow_color = self.hex_to_rgba(color_hex, int(opacity * 255))
        
        # 创建阴影画布
        shadow_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        
        # 使用alpha通道作为蒙版
        if img.mode == 'RGBA':
            mask = img.split()[3]
        else:
            mask = img.convert('L')
        
        # 根据指定偏移创建阴影图像
        shadow_canvas = Image.new('RGBA', img.size, shadow_color)
        shadow_canvas.putalpha(mask)
        
        # 应用高斯模糊
        if blur > 0:
            shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=blur))
        
        # 应用偏移
        shadow_img.paste(shadow_canvas, (int(offset_x), int(offset_y)), shadow_canvas)
        
        # 确保最终的阴影不透明度符合指定值
        r, g, b, a = shadow_img.split()
        a = a.point(lambda x: int(x * opacity))
        shadow_img = Image.merge('RGBA', (r, g, b, a))
        
        return shadow_img
    
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
        
        # 如果未提供style_name，尝试从style字典中获取，如果都没有则使用默认值
        if style_name is None:
            style_name = style.get('name', 'unknown')
        
        # Handle gradient outline
        outline_data = style.get('outline', {})
        width = float(outline_data.get('width', 0))
        opacity = float(outline_data.get('opacity', 1.0))
        
        # 获取渐变对象，确保在此之后不要覆盖它
        gradient = None
        if 'gradient' in outline_data:
            gradient = outline_data['gradient']
        else:
            gradient = outline_data
        
        # 获取颜色信息，这里仅获取原始16进制颜色用于日志显示
        hex_colors = gradient.get('colors', ['#EE2883', '#FFDC7D'])  # 使用设计指定的粉色到黄色渐变作为默认值
        
        # 处理渐变角度 - 支持SVG渐变方向
        angle = 0  # 默认从左到右（SVG: x1=0% -> x2=100%, y相同）
        
        # 检查渐变方向类型
        direction = gradient.get('direction', 'left_right')
        
        # 如果是SVG定义的方向，检查是否包含x1,y1,x2,y2坐标
        if direction == 'custom' and 'svg_coords' in gradient:
            svg_coords = gradient['svg_coords']
            try:
                x1 = float(svg_coords.get('x1', 0)) / 100  # 转换为0-1范围
                y1 = float(svg_coords.get('y1', 0)) / 100
                x2 = float(svg_coords.get('x2', 100)) / 100
                y2 = float(svg_coords.get('y2', 0)) / 100
                
                # 计算角度 - arctan2 返回弧度，convert to degrees
                if x2 != x1 or y2 != y1:  # 避免除以零
                    dx = x2 - x1
                    dy = y2 - y1
                    
                    # 在PIL中，y轴向下为正方向，所以反转y差值
                    angle_rad = math.atan2(-dy, dx)  # 注意这里反转y轴方向
                    angle = math.degrees(angle_rad)
                    # 调整角度到0-360范围
                    angle = (angle + 360) % 360
                
            except (ValueError, TypeError) as e:
                print(f"无法解析描边SVG坐标: {e}, 使用默认角度")
        # 处理预定义的方向
        elif direction == 'left_right':
            angle = 0  # 水平从左到右
        elif direction == 'right_left':
            angle = 180  # 水平从右到左
        elif direction == 'top_bottom':
            angle = 90  # 垂直从上到下
        elif direction == 'bottom_top':
            angle = 270  # 垂直从下到上
        elif direction == 'diagonal':
            angle = 45  # 对角线 左上到右下
        elif direction == 'diagonal_reverse':
            angle = 225  # 对角线 右下到左上
        elif direction == 'diagonal_bottom':
            angle = 315  # 对角线 左下到右上
        elif direction == 'diagonal_bottom_reverse':
            angle = 135  # 对角线 右上到左下
        else:
            # 使用直接指定的角度
            angle = gradient.get('angle', 0)
        
        # 检查是否是径向渐变
        if gradient.get('type') == 'radial':
            angle = 'radial'
        
        # Create outline by dilating the mask
        dilated_mask = mask.copy()
        
        # Apply the outline width (dilate the mask)
        w = int(width)
        
        # Only apply if width > 0
        if w > 0:
            # Apply multiple dilations for better results
            for _ in range(w):
                dilated_mask = dilated_mask.filter(ImageFilter.MaxFilter(3))
        
        # Create outline mask (only keep the dilated area, excluding the original text area)
        outline_only_mask_array = np.clip(np.array(dilated_mask) - np.array(mask), 0, 255)
        
        # 转换为PIL Image
        outline_only_mask = Image.fromarray(outline_only_mask_array)
        
        # 将HEX颜色转换为RGB (只处理一次颜色，不重复处理)
        rgb_colors = []
        for color in hex_colors:
            if isinstance(color, str):
                # 如果是十六进制字符串，转换为RGB
                rgb = self.hex_to_rgba(color)[:3]  # 只取RGB部分
                print(f"转换十六进制颜色 '{color}' 到RGB: {rgb}")
                rgb_colors.append(rgb)
            elif isinstance(color, (list, tuple)) and len(color) >= 3:
                # 如果已经是RGB(A)元组或列表，直接使用
                rgb = color[:3]  # 确保只取RGB部分
                print(f"使用已有RGB颜色: {rgb}")
                rgb_colors.append(rgb)
            else:
                print(f"无法识别的颜色格式: {color}，使用默认白色")
                rgb_colors.append((255, 255, 255))
        
        if not rgb_colors:
            # 如果没有有效颜色，使用默认颜色
            rgb_colors = [(238, 40, 131), (255, 220, 125)]  # 使用粉色到黄色的默认渐变
        
        # 打印方向向量进行调试
        if isinstance(angle, (int, float)):
            radians = math.radians(angle)
            dx = round(math.cos(radians), 2)
            dy = round(math.sin(radians), 2)
            print(f"描边渐变角度: {angle}度, 方向向量: [{dx:.2f}, {dy:.2f}]")
        
        # 打印最终使用的渐变信息进行调试
        print(f"[Style: {style_name}] 描边渐变填充颜色: {hex_colors}, 角度/类型: {angle}, 方向: {direction}")
        
        # 创建渐变并应用到描边
        gradient_array = self._create_gradient(
            img.size[0], 
            img.size[1], 
            rgb_colors, 
            angle,
            direction  # 确保传递方向参数
        )
        
        # 创建一个新的透明图像作为结果
        result = Image.new('RGBA', img.size, (0, 0, 0, 0))
        
        # 将渐变应用到描边区域（只有轮廓部分）
        gradient_img = gradient_array.convert('RGBA')
        
        # 确保描边只应用到轮廓上
        if opacity < 1.0:
            # 调整透明度
            outline_only_mask = outline_only_mask.point(lambda x: int(x * opacity))
        
        # 应用轮廓蒙版到渐变
        gradient_img.putalpha(outline_only_mask)
        
        # 将原始图像复制到结果中
        result = gradient_img.copy()
        
        # 保存调试图像
        self._save_debug_image(result, f"debug_{style_name}_outline_only.png")
        
        return result

    def apply_glow(self, img, style):
        """应用外发光效果"""
        # 检查是否使用了outer_glow或glow的命名
        style_glow = {}
        if 'outer_glow' in style:
            style_glow = style.get('outer_glow', {})
            print("使用outer_glow参数")
        elif 'glow' in style:
            style_glow = style.get('glow', {})
            print("使用glow参数")
        else:
            print("未找到glow或outer_glow参数")
        
        # 如果不需要发光效果，直接返回空
        if not style_glow or style_glow.get('opacity', 0) <= 0:
            return None
        
        # 获取发光参数
        glow_color = style_glow.get('color', '#ffffff')
        glow_opacity = style_glow.get('opacity', 80)
        if isinstance(glow_opacity, (int, float)) and glow_opacity <= 1:
            pass
        else:
            glow_opacity = glow_opacity / 100.0
            
        glow_radius = int(style_glow.get('radius', 10))
        glow_intensity = style_glow.get('intensity', 100)
        if isinstance(glow_intensity, (int, float)) and glow_intensity <= 1:
            pass
        else:
            glow_intensity = glow_intensity / 100.0
        
        print(f"\n======= 外发光效果调试 =======")
        print(f"颜色: {glow_color}")
        print(f"颜色源数据: {style_glow}")
        print(f"完整样式数据键: {list(style.keys())}")
        print(f"不透明度(原始值): {style_glow.get('opacity')}")
        print(f"不透明度(调整后): {glow_opacity}")
        print(f"半径: {glow_radius}")
        print(f"强度(原始值): {style_glow.get('intensity')}")
        print(f"强度(调整后): {glow_intensity}")
        
        try:
            r, g, b = self.hex_to_rgba(glow_color)[:3]
            print(f"解析RGB颜色: R={r}, G={g}, B={b}")
            
            source_alpha = img.split()[3]
            
            blurred_alpha = source_alpha.filter(ImageFilter.GaussianBlur(radius=glow_radius))
            
            # 应用强度参数 - 强度越高，发光效果越明显
            # 创建发光颜色层
            glow_img = Image.new('RGBA', img.size, (r, g, b, 0))
            
            # 强度参数影响最终的不透明度
            effective_opacity = glow_opacity * glow_intensity
            print(f"有效不透明度(opacity * intensity): {effective_opacity}")
            
            # 应用不透明度到发光蒙版
            glow_mask = blurred_alpha.point(lambda x: min(int(x * effective_opacity), 255))
            glow_img.putalpha(glow_mask)
            
            return glow_img
            
        except Exception as e:
            print(f"[错误] 创建外发光效果时出错: {e}")
            return None
        
    def apply_inner_shadow(self, img, style):
        """应用内阴影效果"""
        style_inner_shadow = style.get('inner_shadow', {})
        
        # 如果不需要内阴影效果，直接返回空
        if not style_inner_shadow or style_inner_shadow.get('opacity', 0) <= 0:
            return None
        
        # 获取内阴影参数
        shadow_color = style_inner_shadow.get('color', '#000000')
        shadow_opacity = style_inner_shadow.get('opacity', 50)
        if isinstance(shadow_opacity, (int, float)) and shadow_opacity <= 1:
            pass
        else:
            shadow_opacity = shadow_opacity / 100.0
            
        shadow_offset_x = style_inner_shadow.get('offset_x', 2)
        shadow_offset_y = style_inner_shadow.get('offset_y', 2)
        shadow_blur = style_inner_shadow.get('blur', 3)
        
        print(f"\n======= 内阴影效果调试 =======")
        print(f"颜色: {shadow_color}")
        print(f"颜色源数据: {style_inner_shadow}")
        print(f"完整样式数据: {style}")
        print(f"不透明度(原始值): {style_inner_shadow.get('opacity')}")
        print(f"不透明度(调整后): {shadow_opacity}")
        print(f"X偏移: {shadow_offset_x}")
        print(f"Y偏移: {shadow_offset_y}")
        print(f"模糊: {shadow_blur}")
        
        try:
            r, g, b = self.hex_to_rgba(shadow_color)[:3]
            
            # 获取alpha通道作为蒙版
            source_alpha = img.split()[3]
            
            # 创建偏移的alpha通道
            offset_alpha = Image.new('L', img.size, 0)
            offset_alpha.paste(source_alpha, (int(-shadow_offset_x), int(-shadow_offset_y)))
            
            # 直接跳过模糊效果，无论模糊值是多少
            print(f"跳过模糊效果，强制设置为0，原模糊值: {shadow_blur}")
            
            # 执行内阴影合成计算
            source_array = np.array(source_alpha, dtype=np.float32) / 255.0
            offset_array = np.array(offset_alpha, dtype=np.float32) / 255.0
            
            # 内阴影 = 原图 - 偏移图, 限制在[0,1]范围内
            inner_shadow_array = np.clip(source_array - offset_array, 0, 1)
            
            # 确保内阴影仅出现在文本内部
            inner_shadow_array = inner_shadow_array * source_array
            
            # 转换回PIL图像
            inner_shadow_mask = Image.fromarray((inner_shadow_array * 255).astype(np.uint8), 'L')
            
            # 创建内阴影颜色图像
            shadow_img = Image.new('RGBA', img.size, (r, g, b, 0))
            
            # 计算最终不透明度
            shadow_mask_with_opacity = inner_shadow_mask
            
            # 如果需要增强对比度，让内阴影边缘更明显
            if shadow_opacity > 0:
                # 应用对比度增强
                enhancer = ImageEnhance.Contrast(shadow_mask_with_opacity)
                shadow_mask_with_opacity = enhancer.enhance(1.5)  # 增强对比度
                
                # 应用不透明度
                shadow_mask_with_opacity = shadow_mask_with_opacity.point(lambda x: int(x * shadow_opacity))
                
            shadow_img.putalpha(shadow_mask_with_opacity)
            
            return shadow_img
            
        except Exception as e:
            print(f"[错误] 创建内阴影效果时出错: {e}")
            return None

    def apply_fill(self, img, style):
        """应用填充效果，支持纯色和渐变填充"""
        if not img:
            return None
        
        try:
            width, height = img.size
            
            binary_mask = Image.new('1', img.size, 0)  
            if img.mode == 'RGBA':
                text_mask = img.split()[3]
                binary_mask.paste(1, (0, 0), text_mask)  
            else:
                text_mask = img.convert('L')
                binary_mask.paste(1, (0, 0), text_mask)
            
            if 'fill' in style:
                fill_type = None
                
                if isinstance(style['fill'], dict):
                    fill_type = style['fill'].get('type')
                    print(f"检测到填充类型: {fill_type}")
                elif style['fill'] == 'gradient':
                    fill_type = 'gradient'
                
                if fill_type == 'gradient' or fill_type == 'linear' or fill_type == 'radial':
                    fill = style.get('fill', {})
                    if not isinstance(fill, dict):
                        fill = {'type': 'gradient', 'colors': ['#FFFFFF', '#0066FF'], 'angle': 90}
                    
                    colors = fill.get('colors', ['#FFFFFF', '#0066FF'])
                    if isinstance(colors, str):
                        colors = [colors, '#0066FF']
                    
                    rgb_colors = []
                    for color in colors:
                        if isinstance(color, str):
                            rgb = self.hex_to_rgba(color)[:3]  
                            print(f"转换十六进制颜色 '{color}' 到RGB: {rgb}")
                            rgb_colors.append(rgb)
                        elif isinstance(color, (list, tuple)) and len(color) >= 3:
                            rgb = color[:3]  
                            print(f"使用已有RGB颜色: {rgb}")
                            rgb_colors.append(rgb)
                        else:
                            print(f"无法识别的颜色格式: {color}，使用默认白色")
                            rgb_colors.append((255, 255, 255))
                    
                    if not rgb_colors:
                        rgb_colors = [(255, 255, 255), (0, 102, 255)]
                        print(f"未找到有效颜色，使用默认值: {rgb_colors}")
                    
                    print(f"渐变填充使用的最终颜色: {rgb_colors}")
                    
                    angle = fill.get('angle', 90)
                    direction = fill.get('direction', None)
                    
                    gradient_img = self._create_gradient(width, height, rgb_colors, angle, direction)
                    
                    gradient_masked_rgba = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    
                    gradient_masked_rgba.paste(gradient_img, (0, 0), text_mask)
                    
                    print(f"使用PIL直接粘贴模式应用蒙版")
                    
                    opacity = float(fill.get('opacity', 1.0))
                    if opacity < 1.0:
                        r, g, b, a = gradient_masked_rgba.split()
                        a = a.point(lambda x: int(x * opacity))
                        gradient_masked_rgba = Image.merge('RGBA', (r, g, b, a))
                    
                    return gradient_masked_rgba
                else:
                    fill_color = (64, 150, 255)  
                    if 'fill' in style:
                        if isinstance(style['fill'], dict):
                            color_value = style['fill'].get('color', '#4096FF')
                            if isinstance(color_value, str):
                                print(f"处理填充颜色: {color_value}")
                                fill_color = self.hex_to_rgba(color_value)[:3]
                                print(f"转换后的RGB颜色: {fill_color}")
                            elif isinstance(color_value, (list, tuple)) and len(color_value) >= 3:
                                fill_color = color_value[:3]
                                print(f"使用直接提供的RGB颜色: {fill_color}")
                        elif isinstance(style['fill'], str):
                            print(f"处理直接提供的颜色值: {style['fill']}")
                            fill_color = self.hex_to_rgba(style['fill'])[:3]
                            print(f"转换后的RGB颜色: {fill_color}")
                    
                    print(f"使用单色填充: RGB{fill_color}")
                    
                    fill_img = Image.new('RGB', img.size, fill_color)
                    
                    fill_rgba = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    fill_rgba.paste(fill_img, (0, 0), binary_mask)
                    
                    opacity = 1.0
                    if isinstance(style['fill'], dict) and 'opacity' in style['fill']:
                        opacity = float(style['fill']['opacity'])
                    
                    if opacity < 1.0:
                        r, g, b, a = fill_rgba.split()
                        a = a.point(lambda x: int(x * opacity))
                        fill_rgba = Image.merge('RGBA', (r, g, b, a))
                    
                    return fill_rgba
            
            fill_img = Image.new('RGB', img.size, (255, 255, 255))
            fill_rgba = Image.new('RGBA', img.size, (0, 0, 0, 0))
            fill_rgba.paste(fill_img, (0, 0), binary_mask)
            return fill_rgba
        
        except Exception as e:
            print(f"应用填充效果时出错: {e}")
            import traceback
            traceback.print_exc()
            return None

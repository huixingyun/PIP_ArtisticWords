import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import random

class TextRenderer:
    """Handles text rendering with various effects."""
    
    def __init__(self, font_path, font_size=100, **kwargs):
        """
        Initialize the text renderer.
        
        Args:
            font_path: Path to the font file
            font_size: Font size
        """
        self.font_path = font_path
        self.font_size = font_size
        
        # 添加错误处理和详细日志
        try:
            print(f"[TextRenderer] 尝试加载字体: {font_path}")
            # 检查字体文件是否存在
            if not os.path.exists(font_path):
                print(f"[TextRenderer] 错误: 字体文件不存在: {font_path}")
                # 尝试使用默认字体
                self.font = ImageFont.load_default()
                print("[TextRenderer] 已加载默认字体作为替代")
            else:
                self.font = ImageFont.truetype(font_path, font_size)
                print(f"[TextRenderer] 字体加载成功: {font_path}")
        except Exception as e:
            print(f"[TextRenderer] 加载字体时出错: {e}")
            # 使用默认字体作为备选
            self.font = ImageFont.load_default()
            print("[TextRenderer] 已加载默认字体作为替代")
        
    def apply_smart_line_breaks(self, text):
        """
        Apply smart line breaks based on number of words.
        
        Args:
            text: Text to process
        
        Returns:
            Processed text with line breaks
        """
        # Split text into words
        words = text.split()
        word_count = len(words)
        
        # Apply smart line breaks based on word count
        if word_count <= 2:
            # 1-2 words: No line breaks
            return text
        elif word_count <= 4:
            # 3-4 words: Split into 2 lines
            mid = word_count // 2
            return ' '.join(words[:mid]) + '\n' + ' '.join(words[mid:])
        elif word_count <= 6:
            # 5-6 words: Split into 3 lines
            line_words = word_count // 3
            return ' '.join(words[:line_words]) + '\n' + ' '.join(words[line_words:2*line_words]) + '\n' + ' '.join(words[2*line_words:])
        else:
            # 7+ words: Split into 4 lines max
            lines = []
            line_count = min(4, (word_count + 1) // 2)
            words_per_line = word_count // line_count
            
            for i in range(line_count - 1):
                start_idx = i * words_per_line
                end_idx = (i + 1) * words_per_line
                lines.append(' '.join(words[start_idx:end_idx]))
            
            # Add remaining words to the last line
            lines.append(' '.join(words[(line_count - 1) * words_per_line:]))
            
            return '\n'.join(lines)
    
    def find_optimal_font_size(self, text, max_width, max_height, start_size=10, max_size=300):
        """
        Find the optimal font size to fit text within constraints.
        
        Args:
            text: Text to measure
            max_width: Maximum allowed width
            max_height: Maximum allowed height
            start_size: Starting font size
            max_size: Maximum font size
        
        Returns:
            Optimal font size
        """
        low, high = start_size, max_size
        optimal_size = start_size
        
        # 检查font_path是否有效，如果无效使用默认字体
        use_default_font = False
        if not self.font_path or not os.path.exists(self.font_path):
            print(f"[TextRenderer] 警告: 在find_optimal_font_size中找不到字体 {self.font_path}，将使用默认字体")
            use_default_font = True
        
        while low <= high:
            mid = (low + high) // 2
            
            try:
                # 根据字体可用情况选择字体
                if use_default_font:
                    font = ImageFont.load_default()
                else:
                    font = ImageFont.truetype(self.font_path, mid)
                
                left, top, right, bottom = font.getbbox(text)
                width, height = right - left, bottom - top
                
                # Consider multiline text
                if '\n' in text:
                    lines = text.split('\n')
                    height = 0
                    width = 0
                    line_spacing = mid * 0.2  # 20% of font size for line spacing
                    
                    for line in lines:
                        left, top, right, bottom = font.getbbox(line)
                        line_width, line_height = right - left, bottom - top
                        width = max(width, line_width)
                        height += line_height
                    
                    # Add line spacing
                    height += line_spacing * (len(lines) - 1)
                
                if width <= max_width and height <= max_height:
                    optimal_size = mid
                    low = mid + 1
                else:
                    high = mid - 1
            except Exception as e:
                print(f"[TextRenderer] 在字体大小调整过程中出错: {e}")
                # 出错时降低尝试字号
                high = mid - 1
        
        return optimal_size
    
    def create_base_text_image(self, text, style, width, height, fit_text=True, safe_area=None):
        """
        Create a base text image with the given style.
        
        Args:
            text: Text to render
            style: Style dictionary
            width: Image width
            height: Image height
            fit_text: Whether to fit text to safe area
            safe_area: Safe area bounds (x0, y0, x1, y1) or None
        
        Returns:
            PIL.Image with rendered text
        """
        # 添加调试信息
        print(f"[TextRenderer] 创建文本图像: 尺寸={width}x{height}, 安全区域={safe_area}")
        
        # Create a transparent base image
        base_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(base_img)
        
        # Apply smart line breaks
        processed_text = self.apply_smart_line_breaks(text)
        
        # Calculate font size if fitting to safe area
        if fit_text and safe_area:
            x0, y0, x1, y1 = safe_area
            safe_width = abs(x1 - x0)
            safe_height = abs(y1 - y0)
            print(f"[TextRenderer] 安全区域大小: {safe_width}x{safe_height}")
            
            optimal_size = self.find_optimal_font_size(processed_text, safe_width, safe_height)
            print(f"[TextRenderer] 计算的最佳字体大小: {optimal_size}")
            
            self.font_size = optimal_size
            
            # 当字体大小改变后，需要重新加载字体
            try:
                if not self.font_path or not os.path.exists(self.font_path):
                    # 如果找不到字体文件，使用默认字体
                    self.font = ImageFont.load_default()
                else:
                    self.font = ImageFont.truetype(self.font_path, self.font_size)
                    print(f"[TextRenderer] 重新加载字体，大小为 {self.font_size}")
            except Exception as e:
                print(f"[TextRenderer] 重新加载字体时出错: {e}")
                self.font = ImageFont.load_default()
        
        # Get base color from style
        text_color = (255, 255, 255, 255)  # Default white
        if style and 'text_color' in style:
            text_color = self.hex_to_rgba(style['text_color'])
        
        # 使用fontbbox信息获取文本位置
        # Calculate text position to center it
        try:
            # 获取文本尺寸 - 使用适合多行文本的方法
            if '\n' in processed_text:
                lines = processed_text.split('\n')
                text_width = 0
                text_height = 0
                
                # 计算所有行的总高度和最大宽度
                for line in lines:
                    bbox = self.font.getbbox(line)
                    line_width = bbox[2] - bbox[0]
                    line_height = bbox[3] - bbox[1]
                    text_width = max(text_width, line_width)
                    text_height += line_height
                
                # 添加行间距
                line_spacing = int(self.font_size * 0.2)  # 20% of font size
                text_height += line_spacing * (len(lines) - 1)
            else:
                bbox = self.font.getbbox(processed_text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            
            print(f"[TextRenderer] 文本尺寸: {text_width}x{text_height}")
            
            # Center text in safe area or whole image
            if safe_area:
                x0, y0, x1, y1 = safe_area
                x = x0 + (safe_width - text_width) // 2
                y = y0 + (safe_height - text_height) // 2
                print(f"[TextRenderer] 文本位置: ({x}, {y}) (在安全区域内)")
            else:
                x = (width - text_width) // 2
                y = (height - text_height) // 2
                print(f"[TextRenderer] 文本位置: ({x}, {y}) (全图居中)")
            
            # 绘制多行文本
            if '\n' in processed_text:
                y_pos = y
                for line in lines:
                    bbox = self.font.getbbox(line)
                    line_width = bbox[2] - bbox[0]
                    line_height = bbox[3] - bbox[1]
                    
                    # 计算行的X坐标（居中对齐）
                    line_x = x + (text_width - line_width) // 2
                    
                    # 绘制当前行
                    draw.text((line_x, y_pos), line, fill=text_color, font=self.font)
                    
                    # 更新Y坐标
                    y_pos += line_height + line_spacing
            else:
                # 绘制单行文本
                draw.text((x, y), processed_text, fill=text_color, font=self.font)
        
        except Exception as e:
            print(f"[TextRenderer] 绘制文本时出错: {e}")
            # 出错时使用简单方法绘制
            draw.text((width//4, height//4), processed_text, fill=text_color, font=self.font)
        
        return base_img
    
    def hex_to_rgba(self, hex_color, alpha=255):
        """Convert hex color to RGBA tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return (r, g, b, alpha)
        elif len(hex_color) == 8:
            r, g, b, a = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
            return (r, g, b, a)
        return (255, 255, 255, alpha)  # Default white if invalid

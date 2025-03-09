import os
import json
import random
from pathlib import Path

# 导入SVG解析和转换模块
from .svg_parser import SVGParser
from .svg_style_converter import SVGStyleConverter


class StyleManager:
    """Manages text styles and fonts for artistic text generation."""
    
    def __init__(self, styles_dir=None, fonts_dir=None, sketch_styles_dir=None):
        """
        Initialize the style manager.
        
        Args:
            styles_dir: Directory containing JSON style files
            fonts_dir: Directory containing font files
            sketch_styles_dir: Directory containing sketch-exported style files
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.styles_dir = styles_dir or os.path.join(base_dir, 'styles')
        self.sketch_styles_dir = sketch_styles_dir or os.path.join(base_dir, 'sketchstyle')
        self.svg_dir = os.path.join(base_dir, 'SVG')  # SVG目录路径
        self.fonts_dir = fonts_dir or os.path.join(base_dir, 'fonts')
        self.styles = {}
        self.fonts = []
        self.load_styles()
        self.load_fonts()
    
    def load_styles(self):
        """直接从SVG目录加载所有SVG文件作为样式。"""
        self.styles = {}
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 只加载SVG目录中的SVG文件
        svg_dir = os.path.join(script_dir, "SVG")
        if os.path.exists(svg_dir):
            print(f"[StyleManager] 正在从 {svg_dir} 加载SVG样式文件")
            for filename in os.listdir(svg_dir):
                if filename.endswith(".svg"):
                    filepath = os.path.join(svg_dir, filename)
                    try:
                        # 使用SVG解析器和转换器
                        parser = SVGParser(filepath)
                        svg_data = parser.parse()
                        
                        # 检查解析到的数据是否有效
                        if svg_data:
                            # 使用转换器转换为样式
                            converter = SVGStyleConverter(svg_data)
                            style_name = os.path.splitext(filename)[0]
                            converter.style_name = style_name
                            style_data = converter.convert_to_json_style()
                            
                            # 确保样式有名称
                            if 'name' not in style_data:
                                style_data['name'] = style_name
                            
                            # 使用样式名称作为键
                            style_name = style_data['name']
                            
                            # 添加字体信息
                            style_data['font'] = "Random.ttf"
                            
                            # 添加到样式字典
                            self.styles[style_name] = style_data
                            print(f"[StyleManager] 已加载SVG样式: {style_name}")
                        else:
                            print(f"[StyleManager] SVG文件解析失败: {filepath}")
                    except Exception as e:
                        print(f"加载SVG样式文件出错 {filepath}: {e}")
        
        print(f"[StyleManager] 总共加载了 {len(self.styles)} 个样式")
    
    def load_fonts(self):
        """加载字体目录中的所有字体文件。"""
        try:
            # 首先检查字体目录是否存在
            if not os.path.exists(self.fonts_dir):
                os.makedirs(self.fonts_dir)
                print(f"[StyleManager] 字体目录不存在，已创建: {self.fonts_dir}")
            
            # 输出字体目录完整路径，方便调试
            abs_fonts_dir = os.path.abspath(self.fonts_dir)
            print(f"[StyleManager] 字体目录的绝对路径: {abs_fonts_dir}")
            
            # 获取所有.ttf和.otf文件 - 修复重复加载问题
            font_files = []
            
            # 使用set来避免重复
            fonts_set = set()
            
            # 获取所有字体文件（不区分扩展名大小写）
            for ext in ['*.ttf', '*.otf']:
                for font_file in Path(self.fonts_dir).glob(ext):
                    fonts_set.add(font_file.name)
                for font_file in Path(self.fonts_dir).glob(ext.upper()):
                    fonts_set.add(font_file.name)
            
            # 转换为列表
            self.fonts = list(fonts_set)
            
            # 输出找到的字体文件
            if self.fonts:
                print(f"[StyleManager] 已加载 {len(self.fonts)} 个字体文件:")
                for font in self.fonts:
                    print(f"  - {font}")
            else:
                print(f"[StyleManager] 警告: 字体目录中没有找到字体文件")
                # 如果没有找到字体，添加一个默认字体名称避免后续错误
                self.fonts = ["default.ttf"]
                print(f"[StyleManager] 已添加默认字体名称作为备选")
                
        except Exception as e:
            print(f"[StyleManager] 访问字体目录时出错: {e}")
            # 出错时使用默认字体名称
            self.fonts = ["default.ttf"]
    
    def get_style_names(self):
        """
        Get a list of all available style names.
        
        Returns:
            List of style names
        """
        # 打印所有已加载的样式名称
        print(f"[StyleManager] 可用样式列表: {list(self.styles.keys())}")
        return list(self.styles.keys())
    
    def get_font_names(self):
        """Get a list of all available font names."""
        return self.fonts
    
    def get_style(self, style_name):
        """根据名称获取样式数据，如果样式不存在则返回随机样式。"""
        if style_name in self.styles:
            style_data = self.styles[style_name]
            
            # 确保忽略样式中指定的字体，将字体设置为"随机"
            if 'font' in style_data:
                style_data['font'] = "Random.ttf"
                
            return style_data
        else:
            # 如果找不到指定样式，返回随机样式
            print(f"[StyleManager] 样式 '{style_name}' 不存在，使用随机样式")
            random_style = self.get_random_style()
            return random_style
    
    def get_random_style(self):
        """Get a random style from available styles."""
        if not self.styles:
            return None
        return self.styles[random.choice(list(self.styles.keys()))]
    
    def get_random_font(self):
        """Get a random font from available fonts."""
        if not self.fonts:
            return None
        return random.choice(self.fonts)
    
    def get_font_path(self, font_name):
        """获取字体完整路径，考虑各种命名约定。"""
        # 特殊处理：如果字体名是Random.ttf，则随机选择一个可用字体
        if font_name == "Random.ttf":
            # 随机选择一个可用字体而不是使用默认的
            font_name = random.choice(self.fonts) if self.fonts else "default.ttf"
            print(f"[StyleManager] 检测到Random.ttf请求，随机选择字体: {font_name}")
        
        # 首先尝试直接查找字体
        font_path = os.path.join(self.fonts_dir, font_name)
        if os.path.exists(font_path):
            return font_path
        
        # 如果直接查找失败，尝试几种常见的命名变体
        # 如果font_name是"Knewave.ttf"，尝试查找"Knewave-Regular.ttf"
        base_name = os.path.splitext(font_name)[0]
        ext = os.path.splitext(font_name)[1]
        
        # 常见变体命名模式
        variants = [
            f"{base_name}-Regular{ext}",
            f"{base_name}_Regular{ext}",
            f"{base_name}Regular{ext}",
            f"{base_name.replace('-', '')}{ext}",
            f"{base_name.replace('_', '')}{ext}"
        ]
        
        # 也考虑大小写变化
        for variant in variants:
            font_path = os.path.join(self.fonts_dir, variant)
            if os.path.exists(font_path):
                print(f"[StyleManager] 字体名称匹配: {font_name} → {variant}")
                return font_path
            
            # 尝试全小写
            font_path = os.path.join(self.fonts_dir, variant.lower())
            if os.path.exists(font_path):
                print(f"[StyleManager] 字体名称匹配: {font_name} → {variant.lower()}")
                return font_path
        
        # 如果所有尝试都失败，直接查找包含基本名称的任何字体
        for font_file in os.listdir(self.fonts_dir):
            if base_name.lower() in font_file.lower():
                font_path = os.path.join(self.fonts_dir, font_file)
                print(f"[StyleManager] 使用部分匹配字体: {font_name} → {font_file}")
                return font_path
    
    def get_svg_style(self, svg_filename):
        """
        通过SVG文件名获取样式

        Args:
            svg_filename: SVG文件名（不包含路径）

        Returns:
            对应SVG文件的样式数据，如果文件不存在则返回None
        """
        # 确保文件在SVG目录中存在
        svg_path = os.path.join(self.svg_dir, svg_filename)
        if not os.path.exists(svg_path):
            print(f"[StyleManager] SVG文件不存在: {svg_path}")
            return None
        
        try:
            # 使用SVG解析器和转换器
            from .svg_style_converter import SVGStyleConverter
            style_data = SVGStyleConverter.convert_svg_file_to_style(svg_path)
            
            # 确保样式有名称
            if 'name' not in style_data:
                style_name = os.path.splitext(svg_filename)[0]
                style_data['name'] = style_name
            
            # 始终将字体设置为随机，忽略SVG中指定的字体
            style_data['font'] = "Random.ttf"
            
            print(f"[StyleManager] 已加载SVG样式: {style_data['name']}")
            return style_data
        except Exception as e:
            print(f"[StyleManager] 加载SVG样式文件出错 {svg_path}: {e}")
            return None

    def generate_random_combination(self):
        """Generate a random style-font combination."""
        style = self.get_random_style()
        
        # 即使样式中已定义字体，也强制使用随机字体
        if 'font' in style:
            style['font'] = "Random.ttf"
            
        font = self.get_random_font()
        return style, font

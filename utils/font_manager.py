"""
字体管理工具 - 处理字体加载和查询
"""

import os
import glob
from pathlib import Path


class FontManager:
    """
    字体管理类，提供字体的加载、查询和获取路径功能
    """
    
    def __init__(self):
        """初始化字体管理器，扫描可用字体"""
        self.fonts = {}
        self.scan_fonts()
    
    def scan_fonts(self):
        """扫描fonts目录下的所有字体文件"""
        # 获取当前模块所在目录
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 字体目录
        font_dir = os.path.join(base_dir, 'fonts')
        
        # 如果字体目录不存在，则创建它
        if not os.path.exists(font_dir):
            os.makedirs(font_dir, exist_ok=True)
        
        # 支持的字体格式
        supported_formats = ["*.ttf", "*.otf", "*.TTF", "*.OTF"]
        
        # 扫描所有字体文件
        for fmt in supported_formats:
            font_files = glob.glob(os.path.join(font_dir, fmt))
            for font_file in font_files:
                font_name = os.path.splitext(os.path.basename(font_file))[0]
                self.fonts[font_name] = font_file
        
        # 如果没有找到字体，添加系统字体
        if not self.fonts:
            # 在Windows上查找系统字体
            system_font_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
            if os.path.exists(system_font_dir):
                # 添加一些基本字体
                for basic_font in ["arial.ttf", "simhei.ttf", "msyh.ttc"]:
                    font_path = os.path.join(system_font_dir, basic_font)
                    if os.path.exists(font_path):
                        font_name = os.path.splitext(basic_font)[0]
                        self.fonts[font_name] = font_path
    
    def get_available_fonts(self):
        """获取所有可用字体名称列表"""
        return sorted(list(self.fonts.keys()))
    
    def get_font_path(self, font_name):
        """
        根据字体名称获取字体文件路径
        
        Args:
            font_name: 字体名称
        
        Returns:
            字体文件路径，如果找不到则返回默认字体
        """
        if font_name in self.fonts:
            return self.fonts[font_name]
        
        # 如果找不到指定字体，返回第一个可用字体
        if self.fonts:
            first_font = list(self.fonts.values())[0]
            return first_font
        
        # 如果没有可用字体，返回None
        return None
    
    def register_font(self, font_path):
        """
        注册新字体
        
        Args:
            font_path: 字体文件路径
        
        Returns:
            是否成功注册
        """
        if os.path.exists(font_path):
            font_name = os.path.splitext(os.path.basename(font_path))[0]
            self.fonts[font_name] = font_path
            return True
        return False

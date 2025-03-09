import os
import json
import logging
import random
from ..utils.color_analyzer import ColorAnalyzer

logger = logging.getLogger(__name__)

class StyleColorManager:
    """管理样式与颜色的映射关系"""
    
    def __init__(self, base_path=None):
        # 获取模块所在的基础路径
        if base_path is None:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.base_path = base_path
        self.config_path = os.path.join(base_path, "config", "style_color_mapping.json")
        self.color_analyzer = ColorAnalyzer()
        self.color_mappings = {}
        self.style_descriptions = {}
        self.load_mappings()
    
    def load_mappings(self):
        """加载颜色到样式的映射配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.color_mappings = data.get("color_style_mapping", {})
                    self.style_descriptions = data.get("style_descriptions", {})
                logger.info(f"成功加载样式颜色映射: {len(self.color_mappings)} 种颜色配置")
            else:
                logger.warning(f"样式颜色映射文件不存在: {self.config_path}")
                # 创建配置目录（如果不存在）
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                
                # 创建默认映射
                self.color_mappings = {
                    "red": ["Pop Text Double Outline"],
                    "blue": ["Cyberpunk Neon"],
                    "yellow": ["Premium Metal Gold"],
                    "green": ["Multi Color Gradient"],
                    "purple": ["Dual Layer Text Effect"]
                }
                self.save_mappings()
        except Exception as e:
            logger.error(f"加载样式颜色映射失败: {str(e)}")
            self.color_mappings = {}
    
    def save_mappings(self):
        """保存映射配置到文件"""
        try:
            data = {
                "color_style_mapping": self.color_mappings,
                "style_descriptions": self.style_descriptions
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"样式颜色映射已保存到: {self.config_path}")
        except Exception as e:
            logger.error(f"保存样式颜色映射失败: {str(e)}")
    
    def get_style_for_color(self, color_name):
        """
        根据颜色名称获取匹配的样式名称
        
        Args:
            color_name: 颜色名称，如 'red', 'blue' 等
            
        Returns:
            style_name: 匹配的样式名称，若无匹配则返回None
        """
        if color_name in self.color_mappings and self.color_mappings[color_name]:
            # 随机选择一个匹配的样式
            return random.choice(self.color_mappings[color_name])
        return None
    
    def get_style_for_image(self, image):
        """
        分析图像并返回匹配的样式
        
        Args:
            image: PIL图像对象
            
        Returns:
            tuple: (style_name, color_name, dominant_color_rgb, confidence)
        """
        # 获取图像的主要颜色
        color_name, color_rgb, confidence = self.color_analyzer.get_dominant_color_name(image)
        
        # 根据颜色获取样式
        style_name = self.get_style_for_color(color_name)
        
        # 如果没有找到匹配的样式，使用默认样式
        if not style_name:
            style_name = "Dual Layer Text Effect"  # 默认样式
        
        return style_name, color_name, color_rgb, confidence
    
    def get_color_info(self, color_name):
        """
        获取颜色的相关信息
        
        Args:
            color_name: 颜色名称
            
        Returns:
            dict: 颜色信息，包括匹配的样式和描述
        """
        styles = self.color_mappings.get(color_name, [])
        descriptions = {style: self.style_descriptions.get(style, "") for style in styles}
        
        return {
            "color_name": color_name,
            "styles": styles,
            "descriptions": descriptions
        }

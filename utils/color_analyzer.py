import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import colorsys
import webcolors
import math
import logging

logger = logging.getLogger(__name__)

class ColorAnalyzer:
    """分析图像颜色的工具类，提取主要颜色并匹配样式"""
    
    def __init__(self):
        self.color_names = {
            # 基础颜色匹配表
            "red": {"lower": (340, 0.50, 0.50), "upper": (10, 1.0, 1.0)},
            "orange": {"lower": (10, 0.50, 0.50), "upper": (30, 1.0, 1.0)},
            "yellow": {"lower": (30, 0.50, 0.50), "upper": (60, 1.0, 1.0)},
            "green": {"lower": (60, 0.25, 0.25), "upper": (170, 1.0, 1.0)},
            "cyan": {"lower": (170, 0.25, 0.25), "upper": (200, 1.0, 1.0)},
            "blue": {"lower": (200, 0.25, 0.25), "upper": (260, 1.0, 1.0)},
            "purple": {"lower": (260, 0.25, 0.25), "upper": (290, 1.0, 1.0)},
            "pink": {"lower": (290, 0.25, 0.25), "upper": (340, 1.0, 1.0)},
            "brown": {"lower": (10, 0.20, 0.15), "upper": (40, 0.60, 0.58)},
            "white": {"lower": (0, 0.0, 0.85), "upper": (360, 0.10, 1.0)},
            "black": {"lower": (0, 0.0, 0.0), "upper": (360, 0.05, 0.15)},
            "gray": {"lower": (0, 0.0, 0.15), "upper": (360, 0.10, 0.85)}
        }
    
    def extract_dominant_colors(self, img, n_colors=5, samples=1000):
        """
        从图像中提取主要颜色
        
        Args:
            img: PIL图像对象
            n_colors: 要提取的颜色数量
            samples: 用于聚类的最大像素样本数
            
        Returns:
            colors: 主要颜色的RGB元组列表
            percentages: 每种颜色所占比例
        """
        # 确保图像是RGB模式
        img = img.convert('RGB')
        
        # 调整图像大小以加快处理速度，但保持宽高比
        width, height = img.size
        ratio = min(1.0, math.sqrt(samples / (width * height)))
        new_width = max(1, int(width * ratio))
        new_height = max(1, int(height * ratio))
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
        
        # 将图像转换为数组并重塑为像素列表
        img_array = np.array(img_resized)
        pixels = img_array.reshape(-1, 3)
        
        # 使用K-means聚类找到主要颜色
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        # 获取聚类中心（主要颜色）
        colors = kmeans.cluster_centers_.astype(int)
        
        # 计算每个聚类的像素数量比例
        counts = np.bincount(kmeans.labels_)
        percentages = counts / counts.sum()
        
        # 将颜色从NumPy数组转换为RGB元组列表
        rgb_colors = [tuple(color) for color in colors]
        
        return rgb_colors, percentages
    
    def get_closest_web_color(self, rgb_color):
        """
        找到与给定RGB颜色最接近的网页安全色名称
        """
        min_distance = float('inf')
        closest_color_name = None
        
        try:
            # 尝试将RGB颜色直接转换为名称
            closest_color_name = webcolors.rgb_to_name(rgb_color)
            return closest_color_name
        except ValueError:
            # 如果不是标准网页颜色，找到最接近的
            for color_name, hex_value in webcolors.CSS3_HEX_TO_NAMES.items():
                try:
                    web_rgb = webcolors.hex_to_rgb(color_name)
                except ValueError:
                    web_rgb = webcolors.hex_to_rgb(hex_value)
                
                # 计算欧几里得距离
                distance = sum((c1 - c2) ** 2 for c1, c2 in zip(rgb_color, web_rgb))
                
                if distance < min_distance:
                    min_distance = distance
                    closest_color_name = webcolors.CSS3_NAMES_TO_HEX[hex_value]
            
            return closest_color_name

    def rgb_to_hsv(self, rgb):
        """将RGB颜色转换为HSV"""
        r, g, b = [x/255.0 for x in rgb]
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        # 将H转换为度数 (0-360)
        h = h * 360
        return (h, s, v)
    
    def classify_color(self, rgb):
        """
        根据HSV值将颜色分类到基本颜色名称
        
        Args:
            rgb: RGB颜色元组 (0-255)
            
        Returns:
            color_name: 基本颜色名称
        """
        h, s, v = self.rgb_to_hsv(rgb)
        
        # 检查是否是灰度色
        if s < 0.1:  # 非常低的饱和度
            if v < 0.15:  # 非常暗
                return "black"
            elif v > 0.85:  # 非常亮
                return "white"
            else:
                return "gray"
        
        # 检查是否是棕色 (特殊情况)
        if 10 <= h <= 40 and 0.2 <= s <= 0.6 and 0.15 <= v <= 0.58:
            return "brown"
        
        # 检查其他颜色
        for name, ranges in self.color_names.items():
            h_min, s_min, v_min = ranges["lower"]
            h_max, s_max, v_max = ranges["upper"]
            
            # 对红色进行特殊处理（跨越0度）
            if name == "red":
                if (h >= h_min or h <= h_max) and s >= s_min and s <= s_max and v >= v_min and v <= v_max:
                    return name
            elif h_min <= h <= h_max and s >= s_min and s <= s_max and v >= v_min and v <= v_max:
                return name
        
        # 默认返回最接近的HSV匹配
        return self.find_closest_color_by_hsv(h, s, v)
    
    def find_closest_color_by_hsv(self, h, s, v):
        """找到与给定HSV值最接近的颜色名称"""
        min_distance = float('inf')
        closest_color = "gray"  # 默认为灰色
        
        for name, ranges in self.color_names.items():
            # 使用范围的中点作为比较点
            h_mid = (ranges["lower"][0] + ranges["upper"][0]) / 2
            s_mid = (ranges["lower"][1] + ranges["upper"][1]) / 2
            v_mid = (ranges["lower"][2] + ranges["upper"][2]) / 2
            
            # 处理红色的特殊情况（跨越0度）
            if name == "red" and h_mid > 340:
                h_mid = 0
            
            # 计算HSV空间中的距离（对H进行特殊处理）
            h_diff = min(abs(h - h_mid), 360 - abs(h - h_mid)) / 180.0  # 归一化到0-1范围
            s_diff = abs(s - s_mid)
            v_diff = abs(v - v_mid)
            
            # 给予H较小的权重，因为人眼对亮度和饱和度更敏感
            distance = math.sqrt(h_diff**2 * 0.8 + s_diff**2 * 1.2 + v_diff**2 * 1.5)
            
            if distance < min_distance:
                min_distance = distance
                closest_color = name
        
        return closest_color

    def get_dominant_color_name(self, img):
        """
        获取图像的主要颜色名称
        
        Args:
            img: PIL图像对象
            
        Returns:
            dominant_color_name: 主要颜色的名称
            dominant_color_rgb: 主要颜色的RGB值
        """
        # 提取主要颜色
        colors, percentages = self.extract_dominant_colors(img, n_colors=5)
        
        # 剔除黑白色和灰色（除非它们占比非常高）
        filtered_colors = []
        filtered_percentages = []
        
        for color, percentage in zip(colors, percentages):
            hsv = self.rgb_to_hsv(color)
            # 跳过低饱和度的颜色，除非非常亮或非常暗，或占比很大
            if hsv[1] < 0.15 and 0.15 < hsv[2] < 0.85 and percentage < 0.5:
                continue
            
            filtered_colors.append(color)
            filtered_percentages.append(percentage)
        
        # 如果过滤后没有颜色，则使用原始颜色
        if not filtered_colors:
            filtered_colors = colors
            filtered_percentages = percentages
        
        # 找到占比最高的颜色
        dominant_color = filtered_colors[np.argmax(filtered_percentages)]
        dominant_color_percentage = max(filtered_percentages)
        
        # 分类颜色
        color_name = self.classify_color(dominant_color)
        
        return color_name, tuple(dominant_color), dominant_color_percentage

    def color_to_hex(self, rgb):
        """将RGB颜色转换为十六进制字符串"""
        return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])

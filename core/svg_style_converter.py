"""
SVG Style Converter Module for PIP_ArtisticWords
This module converts the parsed SVG data into the JSON style format used by the text renderer.
"""

import os
import re
import colorsys
import logging
import random
import math
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

from .svg_parser import SVGParser

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SVGStyleConverter:
    """Converts SVG style data into JSON style format for the text renderer."""
    
    @staticmethod
    def convert_svg_file_to_style(svg_file_path: str) -> Dict[str, Any]:
        """
        静态方法，直接从SVG文件加载并转换为样式字典
        
        Args:
            svg_file_path: SVG文件路径
            
        Returns:
            样式字典，可直接用于文本渲染
        """
        # 解析SVG文件
        parser = SVGParser(svg_file_path)
        svg_data = parser.parse()
        
        # 使用SVG数据创建转换器并转换
        converter = SVGStyleConverter(svg_data)
        
        # 使用文件名作为样式名
        style_name = os.path.splitext(os.path.basename(svg_file_path))[0]
        converter.style_name = style_name
        
        # 转换为JSON样式
        return converter.convert_to_json_style()
    
    def __init__(self, svg_data: Dict[str, Any]):
        """
        Initialize the converter with parsed SVG data.
        
        Args:
            svg_data: Dictionary of parsed SVG data from SVGParser
        """
        self.svg_data = svg_data
        self.style_name = "svg_style"
    
    def convert_to_json_style(self) -> Dict[str, Any]:
        """
        转换SVG数据为JSON格式的样式定义。
        
        Returns:
            字典格式的样式定义
        """
        # 确保svg_data包含必要的键
        if not self.svg_data:
            print("警告: SVG数据为空，返回默认样式")
            return self._create_default_style()
            
        if 'text_elements' not in self.svg_data or not self.svg_data['text_elements']:
            print("警告: SVG数据中没有文本元素，返回默认样式")
            return self._create_default_style()
        
        # 从SVG数据中提取样式
        style = {}
        
        # 添加基本文本样式
        style.update(self._extract_text_properties())
        
        # 添加填充样式（纯色或渐变）
        fill_style = self._extract_fill_properties()
        if fill_style:
            style.update(fill_style)
        
        # 添加描边样式
        outline_style = self._extract_outline_properties()
        if outline_style:
            style.update(outline_style)
        
        # 添加滤镜效果（阴影和发光）
        filter_styles = self._extract_filter_effects()
        if filter_styles:
            style.update(filter_styles)
        
        # 添加3D效果
        bevel_style = self._extract_bevel_effect()
        if bevel_style:
            style.update(bevel_style)
        
        # 添加样式名称
        style["name"] = self.style_name
        
        return style
        
    def _create_default_style(self) -> Dict[str, Any]:
        """创建一个默认样式，当SVG解析失败时使用。"""
        return {
            "name": self.style_name,
            "font_family": "Arial",
            "font_size": 100,
            "font_weight": "normal",
            "fill": "#ff2edb",  # 默认使用粉红色填充
            "outline": {
                "color": "#000000",
                "width": 2
            },
            "shadow": {
                "color": "#000000",
                "offset_x": 4,
                "offset_y": 4,
                "blur": 5,
                "opacity": 0.7
            }
        }
    
    def _get_available_fonts(self) -> List[str]:
        """
        获取fonts目录中所有可用的字体文件
        
        Returns:
            字体文件名列表
        """
        fonts = []
        # 获取模块所在目录
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fonts_dir = os.path.join(base_dir, 'fonts')
        
        # 检查字体目录是否存在
        if os.path.exists(fonts_dir):
            # 搜索所有ttf和otf字体文件
            for ext in ['*.ttf', '*.otf', '*.TTF', '*.OTF']:
                for font_file in Path(fonts_dir).glob(ext):
                    fonts.append(font_file.name)
        
        # 如果没有找到字体，返回默认列表
        if not fonts:
            fonts = ["PermanentMarker-Regular.ttf", "Yesteryear-Regular.ttf", 
                    "Lobster-Regular.ttf", "Knewave-Regular.ttf"]
        
        return fonts
    
    def _get_text_properties(self) -> Dict[str, Any]:
        """
        Extract text properties from the first text element.
        
        Returns:
            Dictionary of text properties
        """
        if not self.svg_data["text_elements"]:
            logger.warning("No text elements found in SVG data")
            return {}
        
        text_element = self.svg_data["text_elements"][0]
        
        # Extract the style name from the text content if possible
        if text_element.get("content"):
            # Use the first line or first few words as the style name
            content = text_element["content"].strip()
            first_line = content.split('\n')[0] if '\n' in content else content
            words = first_line.split()
            style_name = '_'.join(words[:2]).lower() if len(words) > 1 else first_line.lower()
            style_name = re.sub(r'[^\w]', '_', style_name)  # Replace non-word chars with underscore
            self.style_name = style_name
        
        return {
            "font_family": text_element.get("font_family", "Arial"),
            "font_size": text_element.get("font_size", 100),
            "font_weight": text_element.get("font_weight", "normal"),
            "line_spacing": text_element.get("line_spacing", 0)
        }
    
    def _extract_text_properties(self) -> Dict[str, Any]:
        """
        Extract text properties from SVG data.
        
        Returns:
            Dictionary of text properties
        """
        properties = {
            "font": "Random.ttf",  # 默认字体
            "size": 72,  # 默认大小
            "alignment": "center",  # 默认对齐方式
            "spacing": 0,  # 默认字间距
            "leading": 1.2,  # 默认行高
        }
        
        # 如果SVG数据中有文本元素，则尝试提取这些属性
        if 'text_elements' in self.svg_data and self.svg_data['text_elements']:
            text_element = self.svg_data['text_elements'][0]  # 使用第一个文本元素
            
            # 提取字体和字体大小（如果存在）
            if 'font-family' in text_element:
                properties['font'] = text_element['font-family']
            
            if 'font-size' in text_element:
                try:
                    # 尝试提取数字部分
                    size_str = text_element['font-size']
                    size = float(re.findall(r'\d+\.?\d*', size_str)[0])
                    properties['size'] = size
                except (ValueError, IndexError):
                    pass  # 保持默认值
            
            # 提取对齐方式（如果存在）
            if 'text-anchor' in text_element:
                anchor = text_element['text-anchor']
                if anchor == 'start':
                    properties['alignment'] = 'left'
                elif anchor == 'middle':
                    properties['alignment'] = 'center'
                elif anchor == 'end':
                    properties['alignment'] = 'right'
            
            # 提取字间距（如果存在）
            if 'letter-spacing' in text_element:
                try:
                    spacing_str = text_element['letter-spacing']
                    spacing = float(re.findall(r'\d+\.?\d*', spacing_str)[0])
                    properties['spacing'] = spacing
                except (ValueError, IndexError):
                    pass  # 保持默认值
                    
            # 提取行高（如果存在）
            if 'line-height' in text_element:
                try:
                    leading_str = text_element['line-height']
                    leading = float(re.findall(r'\d+\.?\d*', leading_str)[0])
                    properties['leading'] = leading
                except (ValueError, IndexError):
                    pass  # 保持默认值
        
        return properties
    
    def _extract_fill_properties(self) -> Dict[str, Any]:
        """
        Extract fill properties from the SVG data.
        
        Returns:
            Dictionary with fill properties
        """
        # Default fill
        default_fill = {
            "fill": "#ff2edb",  # Default fill color
            "fill_opacity": 1
        }
        
        # Look for fill in use elements
        for use in self.svg_data["uses"]:
            if use.get("fill") and use["fill"]:
                # Solid color fill
                if use["fill"].startswith("url(#"):
                    # Extract gradient ID from 'url(#gradient-id)'
                    match = re.search(r'url\(#([^)]+)\)', use["fill"])
                    if match:
                        gradient_id = match.group(1)
                        if gradient_id in self.svg_data["gradients"]:
                            gradient = self.svg_data["gradients"][gradient_id]
                            
                            # Extract colors from stops
                            colors = [stop["color"] for stop in gradient["stops"]]
                            if not colors:
                                continue
                                
                            # If only one color, duplicate it
                            if len(colors) == 1:
                                colors.append(colors[0])
                            
                            return {
                                "fill": {
                                    "type": "gradient",
                                    "colors": colors,
                                    "direction": gradient["direction"],
                                    "angle": gradient["angle"],
                                    "intensity": 100
                                },
                                "fill_opacity": gradient["stops"][0].get("opacity", 1)
                            }
        
        return default_fill
    
    def _extract_outline_properties(self) -> Optional[Dict[str, Any]]:
        """
        Extract outline (stroke) properties from the SVG data.
        
        Returns:
            Dictionary with outline properties or None if no outline
        """
        # 首先尝试查找所有use元素中的描边信息
        stroke_candidates = []
        
        for use in self.svg_data["uses"]:
            if use.get("stroke") and use["stroke"]:
                # 收集所有有描边的use元素
                stroke_candidates.append({
                    "color": use["stroke"],
                    "width": use.get("stroke_width", 1),
                    "opacity": use.get("stroke_opacity", 1),
                })
        
        # 如果有多个描边候选项，优先选择粉红色系的描边
        if stroke_candidates:
            # 查找粉红色或紫红色描边
            for stroke in stroke_candidates:
                color = stroke["color"].upper()
                # 检查颜色是否是粉红色/紫红色系 (检查十六进制颜色中是否包含FF和D/E/F等)
                if color and color.startswith("#") and "FF" in color and any(x in color for x in ["D", "E", "C"]):
                    # 找到粉红色系描边，优先使用
                    stroke_color = color
                    stroke_width = stroke["width"]
                    stroke_opacity = stroke["opacity"]
                    
                    # 检查是否是渐变描边
                    if stroke_color and stroke_color.startswith("url(#"):
                        # 提取渐变ID
                        match = re.search(r'url\(#([^)]+)\)', stroke_color)
                        if match:
                            gradient_id = match.group(1)
                            if gradient_id in self.svg_data["gradients"]:
                                gradient = self.svg_data["gradients"][gradient_id]
                                
                                # 提取渐变信息
                                return {
                                    "outline": {
                                        "width": int(round(float(stroke_width))),
                                        "opacity": stroke_opacity,
                                        "gradient": {
                                            "type": gradient["type"],
                                            "colors": [stop["color"] for stop in gradient["stops"]],
                                            "direction": gradient["direction"],
                                            "angle": gradient["angle"],
                                            "intensity": 100,
                                            "svg_coords": {  # 添加原始SVG坐标数据
                                                "x1": gradient["x1"] * 100,  # 转换回百分比
                                                "y1": gradient["y1"] * 100,
                                                "x2": gradient["x2"] * 100,
                                                "y2": gradient["y2"] * 100
                                            }
                                        }
                                    }
                                }
                    
                    # 纯色描边
                    return {
                        "outline": {
                            "width": int(round(float(stroke_width))),
                            "opacity": stroke_opacity,
                            "color": stroke_color
                        }
                    }
            
            # 如果没有找到粉红色系描边，使用第一个描边
            stroke = stroke_candidates[0]
            stroke_color = stroke["color"]
            stroke_width = stroke["width"]
            stroke_opacity = stroke["opacity"]
            
            # 检查是否是渐变描边
            if stroke_color and stroke_color.startswith("url(#"):
                # 同上，处理渐变
                match = re.search(r'url\(#([^)]+)\)', stroke_color)
                if match:
                    gradient_id = match.group(1)
                    if gradient_id in self.svg_data["gradients"]:
                        gradient = self.svg_data["gradients"][gradient_id]
                        
                        return {
                            "outline": {
                                "width": int(round(float(stroke_width))),
                                "opacity": stroke_opacity,
                                "gradient": {
                                    "type": gradient["type"],
                                    "colors": [stop["color"] for stop in gradient["stops"]],
                                    "direction": gradient["direction"],
                                    "angle": gradient["angle"],
                                    "intensity": 100,
                                    "svg_coords": {  # 添加原始SVG坐标数据
                                        "x1": gradient["x1"] * 100,  # 转换回百分比
                                        "y1": gradient["y1"] * 100,
                                        "x2": gradient["x2"] * 100,
                                        "y2": gradient["y2"] * 100
                                    }
                                }
                            }
                        }
            
            # 纯色描边
            return {
                "outline": {
                    "width": int(round(float(stroke_width))),
                    "opacity": stroke_opacity,
                    "color": stroke_color
                }
            }
                
        return None
    
    def _extract_filter_effects(self) -> Dict[str, Any]:
        """
        从SVG数据中提取过滤器效果，包括阴影、内阴影和发光效果。
        
        Returns:
            包含所有滤镜效果的字典
        """
        effects = {}
        filter_data = self.svg_data.get("filters", {})
        defs = self.svg_data.get("defs", {})
        
        if not filter_data:
            return effects
            
        # 处理每个use元素的每个filter
        for use in self.svg_data.get("uses", []):
            filter_id = use.get("filter")
            use_id = use.get("id", "")
            
            if not filter_id:
                continue
                
            # 检查filter_id是否存在于filter_data中
            if filter_id not in filter_data:
                continue
                
            # 创建单个滤镜的数据字典
            single_filter_data = {filter_id: filter_data.get(filter_id, {})}
            
            # 特殊处理内阴影
            if "inner-shadow" in filter_id.lower():
                inner_shadow = self._extract_inner_shadow_effect(use_id, single_filter_data, defs)
                if inner_shadow and "inner_shadow" not in effects:
                    effects["inner_shadow"] = inner_shadow
            
            # 提取常规阴影效果(只处理外阴影)
            if "shadow" in filter_id.lower() and "inner" not in filter_id.lower():
                shadow_effect = self._extract_shadow_effect(use_id, single_filter_data, defs)
                if shadow_effect and shadow_effect["type"] == "shadow" and "shadow" not in effects:
                    effects["shadow"] = shadow_effect["data"]
            
            # 提取发光效果
            if "glow" in filter_id.lower() or "blur" in filter_id.lower():
                glow_effect = self._extract_glow_effect(use_id, single_filter_data, defs)
                if glow_effect and "glow" not in effects:
                    effects["glow"] = glow_effect
                
        return effects
    
    def _extract_inner_shadow_effect(self, use_id: str, filter_data: Dict[str, Any], defs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        专门提取内阴影效果。
        
        Args:
            use_id: 使用filter的元素ID
            filter_data: 包含滤镜数据的字典
            defs: SVG中的defs数据
            
        Returns:
            包含内阴影数据的字典，如果没有内阴影则返回None
        """
        # 检查filter_data是否有效
        if not filter_data:
            return None
            
        try:
            for filter_id, filter_info in filter_data.items():
                if not filter_info.get("children"):
                    continue
                
                # 查找是否存在inner-shadow相关组件
                offset_component = None
                composite_component = None
                color_matrix = None
                
                # 设置特征检测标志
                has_offset = False
                has_composite_arithmetic = False
                
                for child in filter_info.get("children", []):
                    if child.get("type") == "feOffset":
                        offset_component = child
                        has_offset = True
                    elif child.get("type") == "feComposite" and child.get("operator") == "arithmetic":
                        composite_component = child
                        has_composite_arithmetic = True
                        if child.get("k2") == "-1" and child.get("k3") == "1":
                            # 符合内阴影特征
                            pass
                    elif child.get("type") == "feColorMatrix":
                        color_matrix = child
                
                # 检查特征组合是否符合内阴影
                if has_offset and has_composite_arithmetic and composite_component and offset_component:
                    # 符合内阴影特征
                    offset_x = float(offset_component.get("dx", 0))
                    offset_y = float(offset_component.get("dy", 0))
                    
                    # 默认内阴影颜色(紫色)
                    color = "#4d0066"
                    opacity = 0.7
                    
                    # 尝试从矩阵中提取颜色
                    if color_matrix and color_matrix.get("values"):
                        matrix_values = color_matrix.get("values", "").split()
                        if len(matrix_values) >= 20:  # 完整的矩阵应该有20个值
                            try:
                                r = float(matrix_values[4])
                                g = float(matrix_values[9])
                                b = float(matrix_values[14])
                                a = float(matrix_values[19])
                                
                                # 创建颜色
                                r_hex = min(255, int(r * 255))
                                g_hex = min(255, int(g * 255))
                                b_hex = min(255, int(b * 255))
                                color = f"#{r_hex:02x}{g_hex:02x}{b_hex:02x}"
                                
                                # 使用矩阵中的Alpha通道值作为不透明度
                                if 0 <= a <= 1:
                                    opacity = a
                            except (ValueError, IndexError):
                                pass
                    
                    # 使用一个较小的模糊值，内阴影通常模糊较小
                    blur = 2.0
                    
                    return {
                        "color": color,
                        "offset_x": offset_x,
                        "offset_y": offset_y,
                        "blur": blur,
                        "opacity": opacity
                    }
        except Exception as e:
            print(f"提取内阴影效果时出错: {e}")
            
        return None
        
    def _extract_shadow_effect(self, use_id: str, filter_data: Dict[str, Any], defs: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        提取阴影效果（包括内阴影和外阴影）。
        
        Args:
            use_id: 使用filter的元素ID
            filter_data: 包含滤镜数据的字典
            defs: SVG中的defs数据
            
        Returns:
            包含阴影类型和数据的字典，如果没有阴影则返回None
        """
        # 检查filter_data是否有效
        if not filter_data:
            return None
            
        try:
            # 遍历所有filter
            for filter_id, filter_info in filter_data.items():
                if not filter_info.get("children"):
                    continue
                
                # 查找feOffset和feGaussianBlur组件
                offset_component = None
                blur_component = None
                composite_effect = None
                color_matrix = None
                
                for child in filter_info.get("children", []):
                    if child.get("type") == "feOffset":
                        offset_component = child
                    elif child.get("type") == "feGaussianBlur":
                        blur_component = child
                    elif child.get("type") == "feColorMatrix":
                        color_matrix = child
                    elif child.get("type") == "feComposite" and child.get("operator") == "arithmetic":
                        composite_effect = child
                
                # 如果找到了偏移和模糊组件，则可能是阴影
                if offset_component and blur_component:
                    # 提取阴影参数
                    offset_x = float(offset_component.get("dx", 0))
                    offset_y = float(offset_component.get("dy", 0))
                    blur_std = float(blur_component.get("stdDeviation", 0))
                    
                    # 确定是内阴影还是外阴影
                    if composite_effect and composite_effect.get("operator") == "arithmetic":
                        # 内阴影的操作符为arithmetic且有特定的k值
                        inner_shadow = True
                        k2 = float(composite_effect.get("k2", 0))
                        k3 = float(composite_effect.get("k3", 0))
                        
                        # 检查k值是否符合内阴影定义 (k2=-1, k3=1或相近值)
                        if abs(k2 + 1) > 0.5 or abs(k3 - 1) > 0.5:
                            inner_shadow = False
                            
                        if inner_shadow:
                            # 内阴影
                            color = "#4d0066"  # 默认内阴影颜色（紫色）
                            
                            # 检查color matrix是否有定义颜色
                            if color_matrix and color_matrix.get("values"):
                                matrix_values = color_matrix.get("values", "").split()
                                if len(matrix_values) >= 20:  # 完整的矩阵应该有20个值
                                    # 尝试从矩阵中提取颜色信息
                                    r = float(matrix_values[4])
                                    g = float(matrix_values[9])
                                    b = float(matrix_values[14])
                                    
                                    # 创建颜色
                                    r_hex = min(255, int(r * 255))
                                    g_hex = min(255, int(g * 255))
                                    b_hex = min(255, int(b * 255))
                                    color = f"#{r_hex:02x}{g_hex:02x}{b_hex:02x}"
                            
                            return {
                                "type": "inner_shadow",
                                "data": {
                                    "color": color,
                                    "offset_x": offset_x,
                                    "offset_y": offset_y,
                                    "blur": blur_std,
                                    "opacity": 0.7  # 默认不透明度
                                }
                            }
                    else:
                        # 外阴影
                        color = "#000000"  # 默认外阴影颜色
                        
                        # 检查color matrix是否有定义颜色
                        if color_matrix and color_matrix.get("values"):
                            matrix_values = color_matrix.get("values", "").split()
                            if len(matrix_values) >= 20:  # 完整的矩阵应该有20个值
                                # 尝试从矩阵中提取颜色信息
                                r = float(matrix_values[4])
                                g = float(matrix_values[9])
                                b = float(matrix_values[14])
                                
                                # 如果颜色值存在
                                if r or g or b:
                                    # 检查是否是粉红色系
                                    if r > 0.5 and g < 0.3 and b > 0.5:
                                        color = "#ff2edb"  # 使用粉红色
                        
                        # 根据偏移和模糊值判断是阴影还是发光效果
                        if abs(offset_x) < 0.5 and abs(offset_y) < 0.5 and blur_std > 3:
                            # 可能是发光效果，稍后会由glow方法处理
                            continue
                        
                        return {
                            "type": "shadow",
                            "data": {
                                "color": color,
                                "offset_x": offset_x,
                                "offset_y": offset_y,
                                "blur": blur_std,
                                "opacity": 0.7  # 默认不透明度
                            }
                        }
        except Exception as e:
            print(f"提取阴影效果时出错: {e}")
            
        return None
    
    def _extract_glow_effect(self, use_id: str, filter_data: Dict[str, Any], defs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        提取发光效果。
        
        Args:
            use_id: 使用filter的元素ID
            filter_data: 包含滤镜数据的字典
            defs: SVG中的defs数据
            
        Returns:
            包含发光效果数据的字典，如果没有发光效果则返回None
        """
        # 检查filter_data是否有效
        if not filter_data:
            return None
            
        try:
            # 遍历所有filter
            for filter_id, filter_info in filter_data.items():
                if not filter_info.get("children"):
                    continue
                
                # 查找feGaussianBlur和feColorMatrix组件（通常用于发光效果）
                blur_component = None
                color_matrix = None
                
                for child in filter_info.get("children", []):
                    if child.get("type") == "feGaussianBlur":
                        blur_component = child
                    elif child.get("type") == "feColorMatrix":
                        color_matrix = child
                
                # 如果找到了模糊组件，可能是发光效果
                if blur_component:
                    # 找到偏移组件以确认不是阴影
                    has_offset = False
                    for child in filter_info.get("children", []):
                        if child.get("type") == "feOffset" and (float(child.get("dx", 0)) > 0.5 or float(child.get("dy", 0)) > 0.5):
                            has_offset = True
                            break
                    
                    # 如果有明显的偏移，那么可能是阴影而不是发光
                    if has_offset:
                        continue
                    
                    # 提取发光参数
                    blur_std = float(blur_component.get("stdDeviation", 5))
                    
                    # 默认值
                    color = "#ff2edb"  # 默认发光颜色（粉红色）
                    intensity = 1.0
                    
                    # 检查color matrix是否有定义颜色
                    if color_matrix and color_matrix.get("values"):
                        matrix_values = color_matrix.get("values", "").split()
                        if len(matrix_values) >= 20:  # 完整的矩阵应该有20个值
                            # 尝试从矩阵中提取颜色信息
                            r = float(matrix_values[4])
                            g = float(matrix_values[9])
                            b = float(matrix_values[14])
                            
                            # 如果颜色值存在
                            if r or g or b:
                                # 检查是否是粉红色系
                                if r > 0.5 and g < 0.3 and b > 0.5:
                                    color = "#ff2edb"  # 使用粉红色
                                    intensity = 1.5  # 增强粉红色发光强度
                                else:
                                    # 根据RGB值创建颜色
                                    r_hex = min(255, int(r * 255))
                                    g_hex = min(255, int(g * 255))
                                    b_hex = min(255, int(b * 255))
                                    color = f"#{r_hex:02x}{g_hex:02x}{b_hex:02x}"
                    
                    return {
                        "color": color,
                        "radius": blur_std,
                        "intensity": intensity,
                        "opacity": 0.8
                    }
        except Exception as e:
            print(f"提取发光效果时出错: {e}")
            
        return None
    
    def _extract_bevel_effect(self) -> Dict[str, Any]:
        """
        Extract bevel effect from filter data.
        
        Returns:
            Dictionary of bevel effect properties
        """
        # 默认斜面效果
        default_bevel = {
            "enabled": False,
        }
        
        # 如果没有过滤器数据，则返回默认值
        if 'filters' not in self.svg_data or not self.svg_data['filters']:
            return default_bevel
            
        # 提取斜面效果的相关过滤器
        for filter_id, filter_data in self.svg_data['filters'].items():
            # 斜面效果通常使用specularLighting或feSpecularLighting元素
            for effect in filter_data.get('children', []):
                if effect.get('type') in ['feSpecularLighting', 'specularLighting']:
                    # 找到斜面效果
                    bevel_effect = {
                        "enabled": True,
                        "depth": float(effect.get('specularExponent', 10)) / 10,  # 转换为0-10范围
                        "size": float(effect.get('surfaceScale', 5)) / 5,  # 转换为0-10范围
                        "angle": 135,  # 默认角度
                        "highlight": "#ffffff",  # 默认高光颜色
                        "shadow": "#000000",  # 默认阴影颜色
                    }
                    
                    # 提取光源位置信息
                    if 'pointsAt' in effect:
                        x, y, z = effect['pointsAt'].split()
                        if x and y:
                            # 根据光源位置计算角度
                            try:
                                angle = math.degrees(math.atan2(float(y), float(x))) % 360
                                bevel_effect['angle'] = angle
                            except (ValueError, TypeError):
                                pass
                    
                    # 提取颜色
                    if 'specularConstant' in effect and float(effect['specularConstant']) > 0:
                        light_color = effect.get('lighting-color', '#ffffff')
                        bevel_effect['highlight'] = light_color
                    
                    return bevel_effect
        
        return default_bevel
    
    @staticmethod
    def _rgb_to_hex(r: float, g: float, b: float) -> str:
        """
        Convert RGB values (0-1) to hex color string.
        
        Args:
            r, g, b: RGB values between 0 and 1
            
        Returns:
            Hex color string (e.g., '#ff0000')
        """
        # Ensure values are within 0-1 range
        r = max(0, min(1, r))
        g = max(0, min(1, g))
        b = max(0, min(1, b))
        
        # Convert to 0-255 range and then to hex
        return f'#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}'

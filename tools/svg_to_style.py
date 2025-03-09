#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import base64
import colorsys
import numpy as np

def hex_to_rgba(hex_color, alpha=1.0):
    """Convert hex color to RGBA tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (r, g, b, int(alpha * 255))
    elif len(hex_color) == 8:
        r, g, b, a = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
        return (r, g, b, a)
    return (255, 255, 255, int(alpha * 255))

def rgba_to_hex(rgba):
    """Convert RGBA tuple to hex color."""
    r, g, b, a = rgba
    if a == 255:
        return f"#{r:02x}{g:02x}{b:02x}"
    else:
        return f"#{r:02x}{g:02x}{b:02x}{a:02x}"

def parse_svg(svg_file):
    """Parse SVG file and extract style information."""
    print(f"Parsing SVG file: {svg_file}")
    
    # 注册SVG命名空间
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    
    # 定义命名空间
    ns = {"svg": "http://www.w3.org/2000/svg", "xlink": "http://www.w3.org/1999/xlink"}
    
    # 解析SVG文件
    try:
        tree = ET.parse(svg_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing SVG file: {e}")
        return None
    
    # 初始化样式数据
    style_data = {
        "name": Path(svg_file).stem,
        "anti_alias": True
    }
    
    # 查找文本元素
    text_element = root.find(".//svg:text", ns)
    if text_element is None:
        text_element = root.find(".//text")  # 尝试不带命名空间查找
    
    # 解析文本样式
    if text_element is not None:
        # 提取字体
        font_family = text_element.get("font-family")
        if font_family is None and "class" in text_element.attrib:
            # 尝试从样式表中提取
            class_name = text_element.get("class")
            style_elements = root.findall(".//svg:style", ns)
            if not style_elements:
                style_elements = root.findall(".//style")
            
            for style_elem in style_elements:
                style_text = style_elem.text
                if style_text and class_name in style_text:
                    font_family_match = re.search(r"font-family:\s*([^;]+);", style_text)
                    if font_family_match:
                        font_family = font_family_match.group(1).strip()
        
        if font_family:
            # 转换为我们支持的字体名称格式（添加.ttf扩展名）
            if not font_family.endswith(".ttf"):
                style_data["font"] = f"{font_family}.ttf"
            else:
                style_data["font"] = font_family
        
        # 提取字体大小
        font_size = text_element.get("font-size")
        if font_size is None and "class" in text_element.attrib:
            class_name = text_element.get("class")
            style_elements = root.findall(".//svg:style", ns)
            if not style_elements:
                style_elements = root.findall(".//style")
            
            for style_elem in style_elements:
                style_text = style_elem.text
                if style_text and class_name in style_text:
                    font_size_match = re.search(r"font-size:\s*([^;]+);", style_text)
                    if font_size_match:
                        font_size = font_size_match.group(1).strip()
        
        if font_size:
            # 转换px、pt等单位为数字
            font_size = re.sub(r'[^0-9.]', '', font_size)
            style_data["font_size"] = int(float(font_size))
        
        # 提取文本颜色
        fill = text_element.get("fill")
        if fill and fill != "none" and not fill.startswith("url("):
            style_data["text_color"] = fill
    
    # 解析渐变
    linear_gradients = root.findall(".//svg:linearGradient", ns)
    if not linear_gradients:
        linear_gradients = root.findall(".//linearGradient")
    
    # 查找填充渐变和描边渐变
    fill_gradient = None
    stroke_gradient = None
    
    for gradient in linear_gradients:
        gradient_id = gradient.get("id")
        
        # 检查此渐变是否用于文本填充
        if text_element is not None:
            fill_value = text_element.get("fill")
            if fill_value and f"url(#{gradient_id})" in fill_value:
                fill_gradient = gradient
            
            # 检查是否用于描边
            stroke_value = text_element.get("stroke")
            if stroke_value and f"url(#{gradient_id})" in stroke_value:
                stroke_gradient = gradient
        
        # 检查CSS样式中的引用
        if "class" in text_element.attrib:
            class_name = text_element.get("class")
            style_elements = root.findall(".//svg:style", ns)
            if not style_elements:
                style_elements = root.findall(".//style")
            
            for style_elem in style_elements:
                style_text = style_elem.text
                if style_text and class_name in style_text:
                    if f"fill: url(#{gradient_id})" in style_text:
                        fill_gradient = gradient
                    if f"stroke: url(#{gradient_id})" in style_text:
                        stroke_gradient = gradient
    
    # 处理填充渐变
    if fill_gradient is not None:
        gradient_data = parse_gradient(fill_gradient)
        if gradient_data:
            style_data["gradient"] = gradient_data
    
    # 解析描边渐变和宽度
    stroke_width = None
    if text_element is not None:
        stroke_width = text_element.get("stroke-width")
        if stroke_width is None and "class" in text_element.attrib:
            class_name = text_element.get("class")
            style_elements = root.findall(".//svg:style", ns)
            if not style_elements:
                style_elements = root.findall(".//style")
            
            for style_elem in style_elements:
                style_text = style_elem.text
                if style_text and class_name in style_text:
                    stroke_width_match = re.search(r"stroke-width:\s*([^;]+);", style_text)
                    if stroke_width_match:
                        stroke_width = stroke_width_match.group(1).strip()
    
    # 添加描边信息
    if stroke_width:
        # 转换px、pt等单位为数字
        stroke_width = re.sub(r'[^0-9.]', '', stroke_width)
        outline_data = {"width": int(float(stroke_width))}
        
        # 添加描边渐变
        if stroke_gradient is not None:
            gradient_data = parse_gradient(stroke_gradient)
            if gradient_data:
                outline_data["gradient"] = gradient_data
        
        style_data["outline"] = outline_data
    
    # 解析过滤器（阴影等）
    filters = root.findall(".//svg:filter", ns)
    if not filters:
        filters = root.findall(".//filter")
    
    for filter_elem in filters:
        filter_id = filter_elem.get("id")
        
        # 检查此过滤器是否应用于文本
        applied = False
        if text_element is not None:
            filter_value = text_element.get("filter")
            if filter_value and f"url(#{filter_id})" in filter_value:
                applied = True
        
        # 检查CSS样式中的引用
        if not applied and "class" in text_element.attrib:
            class_name = text_element.get("class")
            style_elements = root.findall(".//svg:style", ns)
            if not style_elements:
                style_elements = root.findall(".//style")
            
            for style_elem in style_elements:
                style_text = style_elem.text
                if style_text and class_name in style_text and f"filter: url(#{filter_id})" in style_text:
                    applied = True
        
        if applied:
            # 寻找阴影效果
            shadow_data = parse_shadow_filter(filter_elem)
            if shadow_data:
                if "shadow" in shadow_data:
                    style_data["shadow"] = shadow_data["shadow"]
                if "inner_shadow" in shadow_data:
                    style_data["inner_shadow"] = shadow_data["inner_shadow"]
    
    return style_data

def parse_gradient(gradient_elem):
    """解析渐变元素并提取渐变信息。"""
    gradient_data = {"type": "linear", "colors": []}
    
    # 定义命名空间
    ns = {"svg": "http://www.w3.org/2000/svg"}
    
    # 提取方向信息
    x1 = gradient_elem.get("x1")
    y1 = gradient_elem.get("y1")
    x2 = gradient_elem.get("x2")
    y2 = gradient_elem.get("y2")
    
    # 确定方向
    if x1 and y1 and x2 and y2:
        # 转换为浮点数
        x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
        
        # 计算角度(弧度)
        angle = 0
        if x2 - x1 != 0:  # 避免除以零
            angle = (y2 - y1) / (x2 - x1)
            angle = np.arctan(angle)
            angle = np.degrees(angle)
        
        # 确定方向
        if abs(y2 - y1) > abs(x2 - x1):
            if y2 > y1:
                gradient_data["direction"] = "top_bottom"
            else:
                gradient_data["direction"] = "bottom_top"
        else:
            if x2 > x1:
                gradient_data["direction"] = "left_right"
            else:
                gradient_data["direction"] = "right_left"
    
    # 提取渐变点
    stops = gradient_elem.findall(".//svg:stop", ns)
    if not stops:
        stops = gradient_elem.findall(".//stop")
    
    if stops:
        # 按照偏移量排序
        stops = sorted(stops, key=lambda stop: float(stop.get("offset", "0")))
        
        for stop in stops:
            color = stop.get("stop-color")
            opacity = stop.get("stop-opacity", "1")
            
            # 如果样式中包含颜色，则使用样式中的颜色
            style = stop.get("style")
            if style:
                color_match = re.search(r"stop-color:\s*([^;]+);", style)
                if color_match:
                    color = color_match.group(1).strip()
                
                opacity_match = re.search(r"stop-opacity:\s*([^;]+);", style)
                if opacity_match:
                    opacity = opacity_match.group(1).strip()
            
            if color:
                # 添加透明度
                if opacity and float(opacity) < 1:
                    rgba = hex_to_rgba(color, float(opacity))
                    color = rgba_to_hex(rgba)
                
                gradient_data["colors"].append(color)
    
    return gradient_data

def parse_shadow_filter(filter_elem):
    """解析过滤器元素并提取阴影信息。"""
    shadow_data = {}
    
    # 定义SVG命名空间
    ns = {"svg": "http://www.w3.org/2000/svg"}
    
    # 寻找外阴影
    offset_elems = filter_elem.findall(".//svg:feOffset", ns)
    if not offset_elems:
        offset_elems = filter_elem.findall(".//feOffset")
    
    for offset_elem in offset_elems:
        # 查找与此偏移相关的高斯模糊
        result = offset_elem.get("result")
        dx = float(offset_elem.get("dx", "0"))
        dy = float(offset_elem.get("dy", "0"))
        
        # 寻找高斯模糊
        blur_elems = filter_elem.findall(f".//svg:feGaussianBlur[@result='{result}']", ns)
        if not blur_elems:
            blur_elems = filter_elem.findall(f".//feGaussianBlur[@result='{result}']")
        
        blur = 0
        if blur_elems:
            std_dev = blur_elems[0].get("stdDeviation")
            if std_dev:
                # 如果有两个值（x和y），取平均值
                if " " in std_dev:
                    std_dev_x, std_dev_y = std_dev.split()
                    blur = (float(std_dev_x) + float(std_dev_y)) / 2
                else:
                    blur = float(std_dev)
        
        # 寻找洪水填充（颜色）
        flood_elems = filter_elem.findall(f".//svg:feFlood", ns)
        if not flood_elems:
            flood_elems = filter_elem.findall(f".//feFlood")
        
        color = "#000000"
        opacity = 0.5
        for flood_elem in flood_elems:
            flood_color = flood_elem.get("flood-color")
            flood_opacity = flood_elem.get("flood-opacity")
            
            if flood_color:
                color = flood_color
            if flood_opacity:
                opacity = float(flood_opacity)
        
        # 根据in属性判断是内阴影还是外阴影
        is_inner = False
        composite_elems = filter_elem.findall(f".//svg:feComposite[@in2='{result}']", ns)
        if not composite_elems:
            composite_elems = filter_elem.findall(f".//feComposite[@in2='{result}']")
        
        if composite_elems:
            for composite_elem in composite_elems:
                operator = composite_elem.get("operator")
                if operator == "out":
                    is_inner = True
                    break
        
        # 创建阴影数据
        shadow = {
            "color": color,
            "offset": [int(dx), int(dy)],
            "blur": int(blur),
            "opacity": opacity
        }
        
        if is_inner:
            shadow_data["inner_shadow"] = shadow
        else:
            shadow_data["shadow"] = shadow
    
    return shadow_data

def svg_to_style(svg_file):
    """Convert SVG to JSON style file."""
    style_data = parse_svg(svg_file)
    if not style_data:
        print(f"Failed to parse SVG: {svg_file}")
        return
    
    # 确保输出目录存在
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sketchstyle")
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存到JSON
    output_file = os.path.join(output_dir, f"{Path(svg_file).stem}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(style_data, f, indent=2, ensure_ascii=False)
    
    print(f"Style saved to: {os.path.abspath(output_file)}")
    return output_file

if __name__ == "__main__":
    # 获取命令行参数
    if len(sys.argv) > 1:
        svg_file = sys.argv[1]
        svg_to_style(svg_file)
    else:
        print("Usage: python svg_to_style.py <svg_file>")

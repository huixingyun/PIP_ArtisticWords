#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SVG转换工具 - 将设计师的原始SVG转换为标准化的PIP_ArtisticWords格式

此脚本读取设计师格式的SVG文件，提取所有必要的样式参数，
然后创建一个新的标准格式SVG文件，保留所有视觉效果。
"""

import re
import xml.etree.ElementTree as ET
import argparse
from pathlib import Path
import colorsys

# 设置XML命名空间
namespaces = {
    'svg': 'http://www.w3.org/2000/svg',
    'xlink': 'http://www.w3.org/1999/xlink'
}

# 注册命名空间前缀以便在输出时保留
for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)

def extract_gradient_colors(gradient_element):
    """从渐变元素中提取颜色值和偏移量"""
    colors = []
    for stop in gradient_element.findall('.//svg:stop', namespaces):
        color = stop.get('stop-color')
        offset = stop.get('offset')
        if color and offset:
            colors.append((color, offset))
    return colors

def extract_gradient_coordinates(gradient_element):
    """提取渐变的坐标信息"""
    coords = {}
    for attr in ['x1', 'y1', 'x2', 'y2']:
        value = gradient_element.get(attr)
        if value:
            coords[attr] = value
    return coords

def extract_filter_values(filter_element, filter_type):
    """提取滤镜参数，根据滤镜类型返回合适的参数集"""
    values = {}
    
    # 提取基本尺寸和位置参数
    for attr in ['x', 'y', 'width', 'height']:
        value = filter_element.get(attr)
        if value:
            values[attr] = value
    
    # 根据滤镜类型提取特定参数
    if filter_type == 'shadow':
        # 查找偏移参数
        offset = filter_element.find('.//svg:feOffset', namespaces)
        if offset is not None:
            for attr in ['dx', 'dy']:
                value = offset.get(attr)
                if value:
                    values[attr] = value
        
        # 查找模糊参数
        blur = filter_element.find('.//svg:feGaussianBlur', namespaces)
        if blur is not None:
            stddev = blur.get('stdDeviation')
            if stddev:
                values['stdDeviation'] = stddev
        
        # 查找颜色矩阵
        colormatrix = filter_element.find('.//svg:feColorMatrix', namespaces)
        if colormatrix is not None:
            matrix = colormatrix.get('values')
            if matrix:
                values['colorMatrix'] = matrix
    
    elif filter_type == 'inner-shadow':
        # 内阴影参数提取
        offset = filter_element.find('.//svg:feOffset', namespaces)
        if offset is not None:
            for attr in ['dx', 'dy']:
                value = offset.get(attr)
                if value:
                    values[attr] = value
        
        # 查找合成操作和颜色矩阵
        composite = filter_element.find('.//svg:feComposite', namespaces)
        if composite is not None:
            for attr in ['operator', 'k2', 'k3']:
                value = composite.get(attr)
                if value:
                    values[attr] = value
        
        colormatrix = filter_element.find('.//svg:feColorMatrix', namespaces)
        if colormatrix is not None:
            matrix = colormatrix.get('values')
            if matrix:
                values['colorMatrix'] = matrix
    
    elif filter_type == 'glow':
        # 查找模糊参数
        blur = filter_element.find('.//svg:feGaussianBlur', namespaces)
        if blur is not None:
            stddev = blur.get('stdDeviation')
            if stddev:
                values['stdDeviation'] = stddev
        
        # 查找颜色矩阵
        colormatrix = filter_element.find('.//svg:feColorMatrix', namespaces)
        if colormatrix is not None:
            matrix = colormatrix.get('values')
            if matrix:
                values['colorMatrix'] = matrix
    
    return values

def extract_text_properties(text_element):
    """提取文本属性，包括字体、大小、内容等"""
    props = {}
    
    # 提取基本属性
    for attr in ['font-family', 'font-size', 'font-weight', 'line-spacing']:
        value = text_element.get(attr)
        if value:
            props[attr] = value
    
    # 提取文本内容
    tspans = []
    for tspan in text_element.findall('.//svg:tspan', namespaces):
        tspan_info = {
            'x': tspan.get('x'),
            'y': tspan.get('y'),
            'text': tspan.text
        }
        tspans.append(tspan_info)
    
    props['tspans'] = tspans
    return props

def extract_use_elements(svg_root):
    """提取use元素及其关联的属性"""
    uses = []
    for use in svg_root.findall('.//svg:use', namespaces):
        use_info = {
            'href': use.get('{http://www.w3.org/1999/xlink}href'),
            'fill': use.get('fill'),
            'stroke': use.get('stroke'),
            'stroke-width': use.get('stroke-width'),
            'filter': use.get('filter')
        }
        uses.append(use_info)
    return uses

def identify_filter_types(svg_root):
    """识别SVG中的滤镜类型"""
    filters = {}
    for filter_elem in svg_root.findall('.//svg:filter', namespaces):
        filter_id = filter_elem.get('id')
        
        # 判断滤镜类型
        if filter_elem.find('.//svg:feGaussianBlur', namespaces) is not None:
            if filter_elem.find('.//svg:feOffset', namespaces) is not None:
                # 如果有偏移，可能是阴影
                filters[filter_id] = 'shadow'
            else:
                # 如果只有模糊，可能是发光
                filters[filter_id] = 'glow'
        
        # 检查内阴影特征
        if filter_elem.find('.//svg:feComposite[@operator="arithmetic"]', namespaces) is not None:
            filters[filter_id] = 'inner-shadow'
    
    return filters

def extract_gradient_ids(svg_root):
    """从use元素中提取渐变ID的映射"""
    gradient_ids = {"fill": None, "stroke": None}
    
    # 查找填充和描边使用的渐变
    for use in svg_root.findall('.//svg:use', namespaces):
        fill = use.get('fill')
        stroke = use.get('stroke')
        
        # 查找填充渐变
        if fill and fill.startswith('url(#'):
            gradient_id = re.search(r'url\(#(.*?)\)', fill).group(1)
            gradient_ids["fill"] = gradient_id
        
        # 查找描边渐变
        if stroke and stroke.startswith('url(#'):
            gradient_id = re.search(r'url\(#(.*?)\)', stroke).group(1)
            gradient_ids["stroke"] = gradient_id
    
    return gradient_ids

def convert_svg(input_path, output_path):
    """转换SVG文件到标准格式"""
    # 解析输入SVG
    tree = ET.parse(input_path)
    root = tree.getroot()
    
    # 提取必要信息
    # 1. 识别滤镜类型
    filter_types = identify_filter_types(root)
    
    # 2. 查找渐变ID
    gradient_ids = extract_gradient_ids(root)
    
    # 3. 提取渐变信息
    gradients = {}
    for grad_type, grad_id in gradient_ids.items():
        if grad_id:
            gradient_elem = root.find(f'.//svg:linearGradient[@id="{grad_id}"]', namespaces)
            if gradient_elem is not None:
                gradients[grad_type] = {
                    'colors': extract_gradient_colors(gradient_elem),
                    'coords': extract_gradient_coordinates(gradient_elem)
                }
    
    # 4. 提取滤镜参数
    filters = {}
    for filter_id, filter_type in filter_types.items():
        filter_elem = root.find(f'.//svg:filter[@id="{filter_id}"]', namespaces)
        if filter_elem is not None:
            filters[filter_type] = extract_filter_values(filter_elem, filter_type)
    
    # 5. 提取文本属性
    text_elem = root.find('.//svg:text', namespaces)
    text_props = None
    if text_elem is not None:
        text_props = extract_text_properties(text_elem)
    
    # 6. 提取use元素
    uses = extract_use_elements(root)
    
    # 现在创建标准格式的SVG
    # 加载模板SVG
    template_path = Path(output_path)
    if template_path.exists():
        template_tree = ET.parse(template_path)
        template_root = template_tree.getroot()
        
        # 更新渐变
        if 'fill' in gradients:
            fill_grad = template_root.find('.//svg:linearGradient[@id="fillGradient"]', namespaces)
            if fill_grad is not None:
                # 更新坐标
                for attr, value in gradients['fill']['coords'].items():
                    fill_grad.set(attr, value)
                
                # 更新颜色
                stops = fill_grad.findall('.//svg:stop', namespaces)
                if stops and len(stops) == len(gradients['fill']['colors']):
                    for i, (stop, (color, offset)) in enumerate(zip(stops, gradients['fill']['colors'])):
                        stop.set('stop-color', color)
                        stop.set('offset', offset)
        
        if 'stroke' in gradients:
            stroke_grad = template_root.find('.//svg:linearGradient[@id="strokeGradient"]', namespaces)
            if stroke_grad is not None:
                # 更新坐标
                for attr, value in gradients['stroke']['coords'].items():
                    stroke_grad.set(attr, value)
                
                # 更新颜色
                stops = stroke_grad.findall('.//svg:stop', namespaces)
                if stops and len(stops) == len(gradients['stroke']['colors']):
                    for i, (stop, (color, offset)) in enumerate(zip(stops, gradients['stroke']['colors'])):
                        stop.set('stop-color', color)
                        stop.set('offset', offset)
        
        # 更新滤镜
        # 阴影滤镜
        if 'shadow' in filters:
            shadow_filter = template_root.find('.//svg:filter[@id="shadow-filter"]', namespaces)
            if shadow_filter is not None:
                for attr in ['x', 'y', 'width', 'height']:
                    if attr in filters['shadow']:
                        shadow_filter.set(attr, filters['shadow'][attr])
                
                offset = shadow_filter.find('.//svg:feOffset', namespaces)
                if offset is not None and 'dx' in filters['shadow'] and 'dy' in filters['shadow']:
                    offset.set('dx', filters['shadow']['dx'])
                    offset.set('dy', filters['shadow']['dy'])
                
                blur = shadow_filter.find('.//svg:feGaussianBlur', namespaces)
                if blur is not None and 'stdDeviation' in filters['shadow']:
                    blur.set('stdDeviation', filters['shadow']['stdDeviation'])
                
                colormatrix = shadow_filter.find('.//svg:feColorMatrix', namespaces)
                if colormatrix is not None and 'colorMatrix' in filters['shadow']:
                    colormatrix.set('values', filters['shadow']['colorMatrix'])
        
        # 内阴影滤镜
        if 'inner-shadow' in filters:
            inner_shadow_filter = template_root.find('.//svg:filter[@id="inner-shadow-filter"]', namespaces)
            if inner_shadow_filter is not None:
                for attr in ['x', 'y', 'width', 'height']:
                    if attr in filters['inner-shadow']:
                        inner_shadow_filter.set(attr, filters['inner-shadow'][attr])
                
                offset = inner_shadow_filter.find('.//svg:feOffset', namespaces)
                if offset is not None and 'dx' in filters['inner-shadow'] and 'dy' in filters['inner-shadow']:
                    offset.set('dx', filters['inner-shadow']['dx'])
                    offset.set('dy', filters['inner-shadow']['dy'])
                
                composite = inner_shadow_filter.find('.//svg:feComposite', namespaces)
                if composite is not None:
                    for attr in ['operator', 'k2', 'k3']:
                        if attr in filters['inner-shadow']:
                            composite.set(attr, filters['inner-shadow'][attr])
                
                colormatrix = inner_shadow_filter.find('.//svg:feColorMatrix', namespaces)
                if colormatrix is not None and 'colorMatrix' in filters['inner-shadow']:
                    colormatrix.set('values', filters['inner-shadow']['colorMatrix'])
        
        # 发光滤镜
        if 'glow' in filters:
            glow_filter = template_root.find('.//svg:filter[@id="glow-filter"]', namespaces)
            if glow_filter is not None:
                for attr in ['x', 'y', 'width', 'height']:
                    if attr in filters['glow']:
                        glow_filter.set(attr, filters['glow'][attr])
                
                blur = glow_filter.find('.//svg:feGaussianBlur', namespaces)
                if blur is not None and 'stdDeviation' in filters['glow']:
                    blur.set('stdDeviation', filters['glow']['stdDeviation'])
                
                colormatrix = glow_filter.find('.//svg:feColorMatrix', namespaces)
                if colormatrix is not None and 'colorMatrix' in filters['glow']:
                    colormatrix.set('values', filters['glow']['colorMatrix'])
        
        # 更新文本
        if text_props:
            text_main = template_root.find('.//svg:text[@id="text-main"]', namespaces)
            if text_main is not None:
                # 更新文本属性
                for attr, value in text_props.items():
                    if attr != 'tspans':
                        text_main.set(attr, value)
                
                # 更新tspan内容
                template_tspans = text_main.findall('.//svg:tspan', namespaces)
                source_tspans = text_props.get('tspans', [])
                
                # 确保有足够的tspan
                if len(template_tspans) == len(source_tspans):
                    for i, (tspan, tspan_info) in enumerate(zip(template_tspans, source_tspans)):
                        if 'x' in tspan_info:
                            tspan.set('x', tspan_info['x'])
                        if 'y' in tspan_info:
                            tspan.set('y', tspan_info['y'])
                        if 'text' in tspan_info:
                            tspan.text = tspan_info['text']
        
        # 保存转换后的SVG
        template_tree.write(output_path, encoding='utf-8', xml_declaration=True)
        print(f"已将设计师SVG转换为标准格式: {output_path}")
        
        # 输出转换信息
        print("\n===== 转换信息 =====")
        if 'fill' in gradients:
            print("填充渐变:")
            for color, offset in gradients['fill']['colors']:
                print(f"  - 颜色: {color}, 位置: {offset}")
            print(f"  - 坐标: {gradients['fill']['coords']}")
        
        if 'stroke' in gradients:
            print("\n描边渐变:")
            for color, offset in gradients['stroke']['colors']:
                print(f"  - 颜色: {color}, 位置: {offset}")
            print(f"  - 坐标: {gradients['stroke']['coords']}")
        
        for filter_type, params in filters.items():
            print(f"\n{filter_type}滤镜:")
            for param, value in params.items():
                if param == 'colorMatrix':
                    print(f"  - 颜色矩阵: (略)")
                else:
                    print(f"  - {param}: {value}")
        
        return True
    else:
        print(f"错误: 目标模板文件不存在: {output_path}")
        return False

def main():
    parser = argparse.ArgumentParser(description='将设计师SVG转换为标准格式SVG')
    parser.add_argument('input', help='设计师SVG文件路径')
    parser.add_argument('output', help='输出标准格式SVG文件路径')
    
    args = parser.parse_args()
    convert_svg(args.input, args.output)

if __name__ == "__main__":
    main()

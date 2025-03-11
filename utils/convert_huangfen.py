#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
专门用于将黄粉2.svg格式转换为test黄粉.svg格式的简单脚本
"""

import xml.etree.ElementTree as ET
import re
import os
import shutil
from pathlib import Path

# 设置XML命名空间
namespaces = {
    'svg': 'http://www.w3.org/2000/svg',
    'xlink': 'http://www.w3.org/1999/xlink'
}

# 注册命名空间前缀以便在输出时保留
for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)

def convert_huangfen_svg(source_svg, target_svg, output_svg=None):
    """
    将设计师的原始SVG（如黄粉2.svg）转换为我们的标准格式（如test黄粉.svg）
    
    参数:
        source_svg: 源SVG文件路径（设计师提供的原始SVG）
        target_svg: 目标模板SVG文件路径（我们的标准格式）
        output_svg: 输出SVG文件路径（如果为None，则覆盖目标文件）
    """
    if output_svg is None:
        output_svg = target_svg
    
    # 确保目标文件存在
    if not os.path.exists(target_svg):
        print(f"错误: 模板文件不存在: {target_svg}")
        return False
    
    # 备份目标文件
    backup_path = f"{target_svg}.bak"
    shutil.copy2(target_svg, backup_path)
    print(f"已创建备份: {backup_path}")
    
    # 解析源SVG以提取参数
    source_tree = ET.parse(source_svg)
    source_root = source_tree.getroot()
    
    # 解析目标SVG以更新
    target_tree = ET.parse(target_svg)
    target_root = target_tree.getroot()
    
    # 1. 提取填充渐变 (linearGradient-1)
    fill_gradient = source_root.find('.//svg:linearGradient[@id="linearGradient-1"]', namespaces)
    fill_colors = []
    
    if fill_gradient is not None:
        # 提取颜色
        for stop in fill_gradient.findall('.//svg:stop', namespaces):
            color = stop.get('stop-color')
            offset = stop.get('offset')
            if color and offset:
                fill_colors.append((color, offset))
        
        # 提取坐标
        fill_coords = {}
        for attr in ['x1', 'y1', 'x2', 'y2']:
            value = fill_gradient.get(attr)
            if value:
                fill_coords[attr] = value
                
        print("填充渐变信息:")
        print(f"  - 坐标: {fill_coords}")
        print(f"  - 颜色: {fill_colors}")
        
        # 更新目标SVG中的填充渐变
        target_fill = target_root.find('.//svg:linearGradient[@id="fillGradient"]', namespaces)
        if target_fill is not None:
            # 更新坐标
            for attr, value in fill_coords.items():
                target_fill.set(attr, value)
            
            # 更新颜色
            target_stops = target_fill.findall('.//svg:stop', namespaces)
            if len(target_stops) == len(fill_colors):
                for i, ((color, offset), stop) in enumerate(zip(fill_colors, target_stops)):
                    stop.set('stop-color', color)
                    stop.set('offset', offset)
    
    # 2. 提取描边渐变 (linearGradient-2)
    stroke_gradient = source_root.find('.//svg:linearGradient[@id="linearGradient-2"]', namespaces)
    stroke_colors = []
    
    if stroke_gradient is not None:
        # 提取颜色
        for stop in stroke_gradient.findall('.//svg:stop', namespaces):
            color = stop.get('stop-color')
            offset = stop.get('offset')
            if color and offset:
                stroke_colors.append((color, offset))
        
        # 提取坐标
        stroke_coords = {}
        for attr in ['x1', 'y1', 'x2', 'y2']:
            value = stroke_gradient.get(attr)
            if value:
                stroke_coords[attr] = value
                
        print("\n描边渐变信息:")
        print(f"  - 坐标: {stroke_coords}")
        print(f"  - 颜色: {stroke_colors}")
        
        # 更新目标SVG中的描边渐变
        target_stroke = target_root.find('.//svg:linearGradient[@id="strokeGradient"]', namespaces)
        if target_stroke is not None:
            # 更新坐标 - 这里将百分比转换为我们的格式
            # 从"x1=\"100%\" y1=\"59.1509623%\" x2=\"6.48187971%\" y2=\"41.1878409%\""转换为简单的对角线格式
            target_stroke.set('x1', '0%')
            target_stroke.set('y1', '0%')
            target_stroke.set('x2', '100%')
            target_stroke.set('y2', '100%')
            
            # 更新颜色
            target_stops = target_stroke.findall('.//svg:stop', namespaces)
            if len(target_stops) == len(stroke_colors):
                for i, ((color, offset), stop) in enumerate(zip(stroke_colors, target_stops)):
                    stop.set('stop-color', color)
                    stop.set('offset', offset)
    
    # 3. 提取文本属性
    source_text = source_root.find('.//svg:text', namespaces)
    if source_text is not None:
        text_props = {}
        # 提取基本属性
        for attr in ['font-family', 'font-size', 'font-weight', 'line-spacing']:
            value = source_text.get(attr)
            if value:
                text_props[attr] = value
        
        # 提取tspan内容
        tspans = []
        for tspan in source_text.findall('.//svg:tspan', namespaces):
            tspan_info = {
                'x': tspan.get('x'),
                'y': tspan.get('y'),
                'text': tspan.text
            }
            tspans.append(tspan_info)
        
        # 更新目标文本
        target_text = target_root.find('.//svg:text[@id="text-main"]', namespaces)
        if target_text is not None:
            # 更新文本属性
            for attr, value in text_props.items():
                if attr != 'tspans':
                    target_text.set(attr, value)
            
            # 更新tspan内容
            target_tspans = target_text.findall('.//svg:tspan', namespaces)
            if len(target_tspans) == len(tspans):
                for i, (tspan, tspan_info) in enumerate(zip(target_tspans, tspans)):
                    if 'x' in tspan_info and tspan_info['x']:
                        tspan.set('x', tspan_info['x'])
                    if 'y' in tspan_info and tspan_info['y']:
                        tspan.set('y', tspan_info['y'])
                    if 'text' in tspan_info and tspan_info['text']:
                        tspan.text = tspan_info['text']
    
    # 4. 提取滤镜属性（发光、阴影、内阴影）
    # 阴影滤镜 (filter-4)
    shadow_filter = source_root.find('.//svg:filter[@id="filter-4"]', namespaces)
    if shadow_filter is not None:
        shadow_params = {}
        # 提取尺寸参数
        for attr in ['x', 'y', 'width', 'height']:
            value = shadow_filter.get(attr)
            if value:
                shadow_params[attr] = value
        
        # 提取偏移参数
        offset = shadow_filter.find('.//svg:feOffset', namespaces)
        if offset is not None:
            dx = offset.get('dx')
            dy = offset.get('dy')
            if dx and dy:
                shadow_params['dx'] = dx
                shadow_params['dy'] = dy
        
        # 提取模糊参数
        blur = shadow_filter.find('.//svg:feGaussianBlur', namespaces)
        if blur is not None:
            stddev = blur.get('stdDeviation')
            if stddev:
                shadow_params['stdDeviation'] = stddev
        
        # 提取颜色矩阵
        colormatrix = shadow_filter.find('.//svg:feColorMatrix', namespaces)
        if colormatrix is not None:
            matrix = colormatrix.get('values')
            if matrix:
                shadow_params['colorMatrix'] = matrix
        
        print("\n阴影滤镜参数:")
        for param, value in shadow_params.items():
            print(f"  - {param}: {value}")
        
        # 更新目标阴影滤镜
        target_shadow = target_root.find('.//svg:filter[@id="shadow-filter"]', namespaces)
        if target_shadow is not None:
            # 更新尺寸
            for attr in ['x', 'y', 'width', 'height']:
                if attr in shadow_params:
                    target_shadow.set(attr, shadow_params[attr])
            
            # 更新偏移
            target_offset = target_shadow.find('.//svg:feOffset', namespaces)
            if target_offset is not None and 'dx' in shadow_params and 'dy' in shadow_params:
                target_offset.set('dx', shadow_params['dx'])
                target_offset.set('dy', shadow_params['dy'])
            
            # 更新模糊
            target_blur = target_shadow.find('.//svg:feGaussianBlur', namespaces)
            if target_blur is not None and 'stdDeviation' in shadow_params:
                target_blur.set('stdDeviation', shadow_params['stdDeviation'])
            
            # 更新颜色矩阵
            target_colormatrix = target_shadow.find('.//svg:feColorMatrix', namespaces)
            if target_colormatrix is not None and 'colorMatrix' in shadow_params:
                target_colormatrix.set('values', shadow_params['colorMatrix'])
    
    # 内阴影滤镜 (filter-5 & filter-6)
    inner_shadow_filter = source_root.find('.//svg:filter[@id="filter-5"]', namespaces)
    if inner_shadow_filter is not None:
        inner_params = {}
        # 提取尺寸参数
        for attr in ['x', 'y', 'width', 'height']:
            value = inner_shadow_filter.get(attr)
            if value:
                inner_params[attr] = value
        
        # 提取偏移参数
        offset = inner_shadow_filter.find('.//svg:feOffset', namespaces)
        if offset is not None:
            dx = offset.get('dx')
            dy = offset.get('dy')
            if dx and dy:
                inner_params['dx'] = dx
                inner_params['dy'] = dy
        
        # 提取合成操作
        composite = inner_shadow_filter.find('.//svg:feComposite', namespaces)
        if composite is not None:
            for attr in ['operator', 'k2', 'k3']:
                value = composite.get(attr)
                if value:
                    inner_params[attr] = value
        
        # 提取颜色矩阵
        colormatrix = inner_shadow_filter.find('.//svg:feColorMatrix', namespaces)
        if colormatrix is not None:
            matrix = colormatrix.get('values')
            if matrix:
                inner_params['colorMatrix'] = matrix
        
        print("\n内阴影滤镜参数:")
        for param, value in inner_params.items():
            print(f"  - {param}: {value}")
        
        # 更新目标内阴影滤镜
        target_inner = target_root.find('.//svg:filter[@id="inner-shadow-filter"]', namespaces)
        if target_inner is not None:
            # 更新尺寸
            for attr in ['x', 'y', 'width', 'height']:
                if attr in inner_params:
                    target_inner.set(attr, inner_params[attr])
            
            # 更新偏移
            target_offset = target_inner.find('.//svg:feOffset', namespaces)
            if target_offset is not None and 'dx' in inner_params and 'dy' in inner_params:
                target_offset.set('dx', inner_params['dx'])
                target_offset.set('dy', inner_params['dy'])
            
            # 更新合成操作
            target_composite = target_inner.find('.//svg:feComposite', namespaces)
            if target_composite is not None:
                for attr in ['operator', 'k2', 'k3']:
                    if attr in inner_params:
                        target_composite.set(attr, inner_params[attr])
            
            # 更新颜色矩阵
            target_colormatrix = target_inner.find('.//svg:feColorMatrix', namespaces)
            if target_colormatrix is not None and 'colorMatrix' in inner_params:
                target_colormatrix.set('values', inner_params['colorMatrix'])
    
    # 保存更新后的SVG
    target_tree.write(output_svg, encoding='utf-8', xml_declaration=True)
    print(f"\n已成功将 {source_svg} 转换为标准格式并保存至 {output_svg}")
    return True

if __name__ == "__main__":
    # 当前脚本所在目录
    script_dir = Path(__file__).parent.parent
    
    # SVG文件路径
    source_svg = script_dir / "SVG" / "黄粉2.svg"
    target_svg = script_dir / "SVG" / "test黄粉.svg"
    
    # 运行转换
    convert_huangfen_svg(source_svg, target_svg)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量SVG转换工具 - 将设计师的原始SVG批量转换为标准化的PIP_ArtisticWords格式
"""

import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# 设置XML命名空间
namespaces = {
    'svg': 'http://www.w3.org/2000/svg',
    'xlink': 'http://www.w3.org/1999/xlink'
}

# 注册命名空间前缀以便在输出时保留
for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)

def convert_svg_file(source_svg, template_svg, output_svg):
    """将设计师SVG转换为标准格式"""
    print(f"\n正在处理: {source_svg}")
    
    # 备份输出文件（如果已存在）
    if os.path.exists(output_svg):
        backup_path = f"{output_svg}.bak"
        shutil.copy2(output_svg, backup_path)
        print(f"已创建备份: {backup_path}")
    
    # 解析源SVG以提取参数
    source_tree = ET.parse(source_svg)
    source_root = source_tree.getroot()
    
    # 解析模板SVG
    template_tree = ET.parse(template_svg)
    template_root = template_tree.getroot()
    
    # 创建新的输出SVG，基于模板
    shutil.copy2(template_svg, output_svg)
    output_tree = ET.parse(output_svg)
    output_root = output_tree.getroot()
    
    # 1. 寻找所有线性渐变
    gradients = {}
    for grad in source_root.findall('.//svg:linearGradient', namespaces):
        grad_id = grad.get('id')
        if grad_id:
            colors = []
            for stop in grad.findall('.//svg:stop', namespaces):
                color = stop.get('stop-color')
                offset = stop.get('offset')
                if color and offset:
                    colors.append((color, offset))
            
            coords = {}
            for attr in ['x1', 'y1', 'x2', 'y2']:
                value = grad.get(attr)
                if value:
                    coords[attr] = value
            
            gradients[grad_id] = {
                'colors': colors,
                'coords': coords
            }
    
    # 2. 判断哪些渐变用于填充和描边
    fill_id = None
    stroke_id = None
    
    # 查找使用了渐变的use元素
    for use in source_root.findall('.//svg:use', namespaces):
        fill = use.get('fill')
        if fill and 'url(#' in fill:
            import re
            match = re.search(r'url\(#(.*?)\)', fill)
            if match:
                fill_id = match.group(1)
        
        stroke = use.get('stroke')
        if stroke and 'url(#' in stroke:
            match = re.search(r'url\(#(.*?)\)', stroke)
            if match:
                stroke_id = match.group(1)
    
    # 如果没有在use元素找到，尝试在g元素中查找
    if not fill_id or not stroke_id:
        for path in source_root.findall('.//svg:path', namespaces):
            fill = path.get('fill')
            if fill and 'url(#' in fill:
                import re
                match = re.search(r'url\(#(.*?)\)', fill)
                if match:
                    fill_id = match.group(1)
            
            stroke = path.get('stroke')
            if stroke and 'url(#' in stroke:
                match = re.search(r'url\(#(.*?)\)', stroke)
                if match:
                    stroke_id = match.group(1)
    
    # 3. 如果没有明确的填充和描边渐变，使用前两个找到的渐变
    gradient_ids = list(gradients.keys())
    if gradient_ids and not fill_id:
        fill_id = gradient_ids[0]
    if len(gradient_ids) > 1 and not stroke_id:
        stroke_id = gradient_ids[1]
    
    # 4. 更新填充渐变
    if fill_id and fill_id in gradients:
        fill_gradient = gradients[fill_id]
        target_fill = output_root.find('.//svg:linearGradient[@id="fillGradient"]', namespaces)
        if target_fill is not None:
            # 更新坐标
            for attr, value in fill_gradient['coords'].items():
                target_fill.set(attr, value)
            
            # 更新颜色
            target_stops = target_fill.findall('.//svg:stop', namespaces)
            fill_colors = fill_gradient['colors']
            if len(target_stops) == len(fill_colors):
                for i, ((color, offset), stop) in enumerate(zip(fill_colors, target_stops)):
                    stop.set('stop-color', color)
                    stop.set('offset', offset)
            
            print(f"已更新填充渐变 (ID: {fill_id}):")
            for color, offset in fill_colors:
                print(f"  - 颜色: {color}, 位置: {offset}")
    
    # 5. 更新描边渐变
    if stroke_id and stroke_id in gradients:
        stroke_gradient = gradients[stroke_id]
        target_stroke = output_root.find('.//svg:linearGradient[@id="strokeGradient"]', namespaces)
        if target_stroke is not None:
            # 保持标准对角线格式但使用原始颜色
            target_stroke.set('x1', '0%')
            target_stroke.set('y1', '0%')
            target_stroke.set('x2', '100%')
            target_stroke.set('y2', '100%')
            
            # 更新颜色
            target_stops = target_stroke.findall('.//svg:stop', namespaces)
            stroke_colors = stroke_gradient['colors']
            if len(target_stops) == len(stroke_colors):
                for i, ((color, offset), stop) in enumerate(zip(stroke_colors, target_stops)):
                    stop.set('stop-color', color)
                    stop.set('offset', offset)
            
            print(f"已更新描边渐变 (ID: {stroke_id}):")
            for color, offset in stroke_colors:
                print(f"  - 颜色: {color}, 位置: {offset}")
    
    # 6. 提取文本内容
    source_text = source_root.find('.//svg:text', namespaces)
    if source_text is not None:
        # 提取文本属性
        text_props = {}
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
        
        # 更新文本元素
        target_text = output_root.find('.//svg:text[@id="text-main"]', namespaces)
        if target_text is not None:
            # 更新属性
            for attr, value in text_props.items():
                target_text.set(attr, value)
            
            # 更新tspan，确保数量匹配
            target_tspans = target_text.findall('.//svg:tspan', namespaces)
            if len(target_tspans) == len(tspans):
                for i, (tspan, tspan_info) in enumerate(zip(target_tspans, tspans)):
                    if 'x' in tspan_info and tspan_info['x']:
                        tspan.set('x', tspan_info['x'])
                    if 'y' in tspan_info and tspan_info['y']:
                        tspan.set('y', tspan_info['y'])
                    if 'text' in tspan_info and tspan_info['text']:
                        tspan.text = tspan_info['text']
            print("已更新文本内容")
    
    # 7. 提取滤镜参数（阴影、内阴影等）
    filters = {}
    for filter_elem in source_root.findall('.//svg:filter', namespaces):
        filter_id = filter_elem.get('id')
        
        # 判断滤镜类型
        if filter_elem.find('.//svg:feGaussianBlur', namespaces) is not None:
            if filter_elem.find('.//svg:feOffset', namespaces) is not None:
                filters[filter_id] = 'shadow'
            else:
                filters[filter_id] = 'glow'
        
        if filter_elem.find('.//svg:feComposite[@operator="arithmetic"]', namespaces) is not None:
            filters[filter_id] = 'inner-shadow'
    
    # 8. 处理找到的每种滤镜
    for filter_id, filter_type in filters.items():
        filter_elem = source_root.find(f'.//svg:filter[@id="{filter_id}"]', namespaces)
        
        if filter_type == 'shadow':
            # 提取阴影参数
            shadow_params = {}
            for attr in ['x', 'y', 'width', 'height']:
                value = filter_elem.get(attr)
                if value:
                    shadow_params[attr] = value
            
            offset = filter_elem.find('.//svg:feOffset', namespaces)
            if offset is not None:
                for attr in ['dx', 'dy']:
                    value = offset.get(attr)
                    if value:
                        shadow_params[attr] = value
            
            blur = filter_elem.find('.//svg:feGaussianBlur', namespaces)
            if blur is not None:
                value = blur.get('stdDeviation')
                if value:
                    shadow_params['stdDeviation'] = value
            
            colormatrix = filter_elem.find('.//svg:feColorMatrix', namespaces)
            if colormatrix is not None:
                value = colormatrix.get('values')
                if value:
                    shadow_params['colorMatrix'] = value
            
            # 更新目标SVG中的阴影滤镜
            target = output_root.find('.//svg:filter[@id="shadow-filter"]', namespaces)
            if target is not None:
                for attr in ['x', 'y', 'width', 'height']:
                    if attr in shadow_params:
                        target.set(attr, shadow_params[attr])
                
                target_offset = target.find('.//svg:feOffset', namespaces)
                if target_offset is not None and 'dx' in shadow_params and 'dy' in shadow_params:
                    target_offset.set('dx', shadow_params['dx'])
                    target_offset.set('dy', shadow_params['dy'])
                
                target_blur = target.find('.//svg:feGaussianBlur', namespaces)
                if target_blur is not None and 'stdDeviation' in shadow_params:
                    target_blur.set('stdDeviation', shadow_params['stdDeviation'])
                
                target_colormatrix = target.find('.//svg:feColorMatrix', namespaces)
                if target_colormatrix is not None and 'colorMatrix' in shadow_params:
                    target_colormatrix.set('values', shadow_params['colorMatrix'])
            
            print(f"已更新阴影滤镜 (ID: {filter_id})")
        
        elif filter_type == 'inner-shadow':
            # 提取内阴影参数
            inner_params = {}
            for attr in ['x', 'y', 'width', 'height']:
                value = filter_elem.get(attr)
                if value:
                    inner_params[attr] = value
            
            offset = filter_elem.find('.//svg:feOffset', namespaces)
            if offset is not None:
                for attr in ['dx', 'dy']:
                    value = offset.get(attr)
                    if value:
                        inner_params[attr] = value
            
            composite = filter_elem.find('.//svg:feComposite', namespaces)
            if composite is not None:
                for attr in ['operator', 'k2', 'k3']:
                    value = composite.get(attr)
                    if value:
                        inner_params[attr] = value
            
            colormatrix = filter_elem.find('.//svg:feColorMatrix', namespaces)
            if colormatrix is not None:
                value = colormatrix.get('values')
                if value:
                    inner_params['colorMatrix'] = value
            
            # 更新目标SVG中的内阴影滤镜
            target = output_root.find('.//svg:filter[@id="inner-shadow-filter"]', namespaces)
            if target is not None:
                for attr in ['x', 'y', 'width', 'height']:
                    if attr in inner_params:
                        target.set(attr, inner_params[attr])
                
                target_offset = target.find('.//svg:feOffset', namespaces)
                if target_offset is not None and 'dx' in inner_params and 'dy' in inner_params:
                    target_offset.set('dx', inner_params['dx'])
                    target_offset.set('dy', inner_params['dy'])
                
                target_composite = target.find('.//svg:feComposite', namespaces)
                if target_composite is not None:
                    for attr in ['operator', 'k2', 'k3']:
                        if attr in inner_params:
                            target_composite.set(attr, inner_params[attr])
                
                target_colormatrix = target.find('.//svg:feColorMatrix', namespaces)
                if target_colormatrix is not None and 'colorMatrix' in inner_params:
                    target_colormatrix.set('values', inner_params['colorMatrix'])
            
            print(f"已更新内阴影滤镜 (ID: {filter_id})")
        
        elif filter_type == 'glow':
            # 提取发光参数
            glow_params = {}
            for attr in ['x', 'y', 'width', 'height']:
                value = filter_elem.get(attr)
                if value:
                    glow_params[attr] = value
            
            blur = filter_elem.find('.//svg:feGaussianBlur', namespaces)
            if blur is not None:
                value = blur.get('stdDeviation')
                if value:
                    glow_params['stdDeviation'] = value
            
            colormatrix = filter_elem.find('.//svg:feColorMatrix', namespaces)
            if colormatrix is not None:
                value = colormatrix.get('values')
                if value:
                    glow_params['colorMatrix'] = value
            
            # 更新目标SVG中的发光滤镜
            target = output_root.find('.//svg:filter[@id="glow-filter"]', namespaces)
            if target is not None:
                for attr in ['x', 'y', 'width', 'height']:
                    if attr in glow_params:
                        target.set(attr, glow_params[attr])
                
                target_blur = target.find('.//svg:feGaussianBlur', namespaces)
                if target_blur is not None and 'stdDeviation' in glow_params:
                    target_blur.set('stdDeviation', glow_params['stdDeviation'])
                
                target_colormatrix = target.find('.//svg:feColorMatrix', namespaces)
                if target_colormatrix is not None and 'colorMatrix' in glow_params:
                    target_colormatrix.set('values', glow_params['colorMatrix'])
            
            print(f"已更新发光滤镜 (ID: {filter_id})")
    
    # 保存更新后的SVG
    output_tree.write(output_svg, encoding='utf-8', xml_declaration=True)
    print(f"已成功转换并保存到: {output_svg}")
    return True

def process_directory(source_dir, target_dir, template_svg):
    """处理源目录中的所有SVG文件"""
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"创建目标目录: {target_dir}")
    
    processed = 0
    source_path = Path(source_dir)
    for svg_file in source_path.glob("*.svg"):
        output_path = Path(target_dir) / svg_file.name
        success = convert_svg_file(svg_file, template_svg, output_path)
        if success:
            processed += 1
    
    print(f"\n处理完成! 共转换了 {processed} 个SVG文件")
    return processed

if __name__ == "__main__":
    # 设置路径
    base_dir = Path(r"C:\COMFYUI\ComfyUI_windows_portable\ComfyUI\custom_nodes\PIP_ArtisticWords")
    source_dir = base_dir / "设计导出"
    target_dir = base_dir / "SVG"
    template_svg = base_dir / "SVG" / "test黄粉.svg"
    
    # 确认模板存在
    if not template_svg.exists():
        print(f"错误: 模板文件不存在: {template_svg}")
    else:
        print(f"使用模板: {template_svg}")
        print(f"源目录: {source_dir}")
        print(f"目标目录: {target_dir}")
        process_directory(source_dir, target_dir, template_svg)

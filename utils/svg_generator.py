"""
SVG生成器 - 根据提供的文本和样式生成标准格式的SVG文件
"""

import os
import re
import math

class SVGGenerator:
    """生成SVG文本内容的类"""
    
    def __init__(self):
        """初始化SVG生成器"""
        pass
    
    def generate_svg(self, text, font_name, font_size, style, width=600, height=400):
        """生成SVG内容
        
        Args:
            text: 要渲染的文本
            font_name: 字体名称
            font_size: 字体大小
            style: 样式字典，包含各种效果
            width: SVG宽度
            height: SVG高度
            
        Returns:
            生成的SVG内容字符串
        """
        # 创建SVG头部
        svg = f'<?xml version="1.0" encoding="UTF-8"?>\n'
        svg += f'<svg width="{width}px" height="{height}px" viewBox="0 0 {width} {height}" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">\n'
        svg += f'    <title>PIP Text Style</title>\n'
        svg += f'    <defs>\n'
        
        # 处理文本定义
        text_id = "text-main"
        svg += f'        <!-- 文本定义 -->\n'
        svg += f'        <text id="{text_id}" font-family="{font_name}, sans-serif" font-size="{font_size}" font-weight="normal">\n'
        
        # 分割多行文本
        lines = text.split('\n')
        y_offset = int(font_size * 1.2)  # 行高约为字体大小的1.2倍
        
        # 如果只有一行，居中显示
        if len(lines) == 1:
            x_pos = width // 2
            y_pos = height // 2
            svg += f'            <tspan x="{x_pos}" y="{y_pos}" text-anchor="middle">{lines[0]}</tspan>\n'
        else:
            # 多行文本处理
            x_pos = 20
            y_pos = int(font_size * 1.5)  # 第一行的y位置
            
            for line in lines:
                svg += f'            <tspan x="{x_pos}" y="{y_pos}">{line}</tspan>\n'
                y_pos += y_offset
        
        svg += f'        </text>\n\n'
        
        # 确保所有引用的元素都有定义
        needs_fill_gradient = False
        needs_stroke_gradient = False
        needs_shadow_filter = False
        needs_inner_shadow_filter = False
        needs_glow_filter = False
        
        # 填充层
        fill = style.get('fill', {})
        if isinstance(fill, dict) and fill.get('type') != 'none':
            if fill.get('type') != 'solid':  # 渐变填充
                needs_fill_gradient = True
        
        # 描边层
        if 'outline' in style:
            outline = style['outline']
            width_val = outline.get('width', 5)
            if width_val > 0 and 'gradient' in outline:
                needs_stroke_gradient = True
        
        # 阴影层
        if 'shadow' in style:
            needs_shadow_filter = True
        
        # 内阴影层
        if 'inner_shadow' in style:
            needs_inner_shadow_filter = True
        
        # 外发光层
        if 'glow' in style:
            needs_glow_filter = True
        
        # 处理填充渐变
        if needs_fill_gradient:
            svg += self._generate_fill_gradient(style)
        
        # 处理描边渐变
        if needs_stroke_gradient:
            svg += self._generate_stroke_gradient(style)
        
        # 处理阴影效果
        if needs_shadow_filter:
            svg += self._generate_shadow_filter(style)
        
        # 处理内阴影效果
        if needs_inner_shadow_filter:
            svg += self._generate_inner_shadow_filter(style)
            
        # 处理外发光效果
        if needs_glow_filter:
            svg += self._generate_glow_filter(style)
        
        svg += f'    </defs>\n'
        
        # 绘制元素组
        svg += f'    <g id="PIP-Text-Group" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">\n'
        svg += f'        <g id="PIP-Text-Effects" fill-rule="nonzero">\n'
        
        # 应用顺序：阴影 -> 发光 -> 填充 -> 描边 -> 内阴影
        
        # 投影层
        if 'shadow' in style:
            svg += f'            <!-- 投影层 -->\n'
            svg += f'            <use id="shadow-use" filter="url(#shadow-filter)" xlink:href="#{text_id}"></use>\n\n'
        
        # 外发光层
        if 'glow' in style:
            svg += f'            <!-- 外发光层 -->\n'
            svg += f'            <use id="glow-use" filter="url(#glow-filter)" xlink:href="#{text_id}"></use>\n\n'
        
        # 填充层
        if isinstance(fill, dict) and fill.get('type') != 'none':
            svg += f'            <!-- 填充层 -->\n'
            
            if fill.get('type') == 'solid':
                fill_color = fill.get('color', '#000000')
                svg += f'            <use id="fill-use" fill="{fill_color}" xlink:href="#{text_id}"></use>\n\n'
            else:  # 渐变填充
                svg += f'            <use id="fill-use" fill="url(#fillGradient)" xlink:href="#{text_id}"></use>\n\n'
        
        # 描边层
        if 'outline' in style:
            outline = style['outline']
            width_val = outline.get('width', 5)
            
            if width_val > 0:
                svg += f'            <!-- 描边层 -->\n'
                
                if 'gradient' in outline:
                    svg += f'            <use id="stroke-use" stroke="url(#strokeGradient)" stroke-width="{width_val}" xlink:href="#{text_id}"></use>\n\n'
                else:
                    outline_color = outline.get('color', '#000000')
                    svg += f'            <use id="stroke-use" stroke="{outline_color}" stroke-width="{width_val}" xlink:href="#{text_id}"></use>\n\n'
        
        # 内阴影层
        if 'inner_shadow' in style:
            svg += f'            <!-- 内阴影层 -->\n'
            svg += f'            <use id="inner-shadow-use" filter="url(#inner-shadow-filter)" xlink:href="#{text_id}"></use>\n\n'
        
        svg += f'        </g>\n'
        svg += f'    </g>\n'
        svg += f'</svg>'
        
        return svg
    
    def _has_gradient_fill(self, style):
        """检查是否有渐变填充"""
        fill = style.get('fill', {})
        
        # 如果fill是字符串，那么它是颜色值，不是渐变
        if isinstance(fill, str):
            return False
            
        # 如果fill是字典，检查类型
        if isinstance(fill, dict):
            if fill.get('type') == 'gradient' or fill.get('type') == 'radial':
                return True
        
        return False
    
    def _has_gradient_outline(self, style):
        """检查是否有渐变描边"""
        if 'outline' not in style:
            return False
            
        outline = style['outline']
        return 'gradient' in outline
    
    def _generate_fill_gradient(self, style):
        """生成填充渐变定义"""
        fill = style.get('fill', {})
        
        # 确保fill是字典类型
        if not isinstance(fill, dict):
            return ""
            
        # 获取颜色
        colors = fill.get('colors', ['#FFFFFF', '#0066FF'])
        if len(colors) < 2:
            colors = ['#FFFFFF', '#0066FF']  # 默认白到蓝
        
        # 获取方向类型
        gradient_type = fill.get('type', 'linear')
        
        # 生成SVG渐变定义
        svg = f'        <!-- 文本填充渐变 -->\n'
        
        if gradient_type == 'radial':
            # 径向渐变
            svg += f'        <radialGradient cx="50%" cy="50%" r="75%" fx="50%" fy="50%" id="fillGradient">\n'
            svg += f'            <stop stop-color="{colors[0]}" offset="0%"></stop>\n'
            svg += f'            <stop stop-color="{colors[1]}" offset="100%"></stop>\n'
            svg += f'        </radialGradient>\n\n'
        else:
            # 线性渐变 - 根据方向设置坐标
            x1, y1, x2, y2 = self._get_gradient_coordinates(fill.get('direction', 'top_bottom'))
            
            svg += f'        <linearGradient x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" id="fillGradient">\n'
            svg += f'            <stop stop-color="{colors[0]}" offset="0%"></stop>\n'
            svg += f'            <stop stop-color="{colors[1]}" offset="100%"></stop>\n'
            svg += f'        </linearGradient>\n\n'
            
        return svg
    
    def _generate_stroke_gradient(self, style):
        """生成描边渐变定义"""
        outline = style.get('outline', {})
        gradient = outline.get('gradient', {})
        
        # 获取颜色
        colors = gradient.get('colors', ['#FF0000', '#FFFF00'])
        if len(colors) < 2:
            colors = ['#FF0000', '#FFFF00']  # 默认红到黄
        
        # 获取方向和类型
        gradient_type = gradient.get('type', 'linear')
        
        # 生成SVG渐变定义
        svg = f'        <!-- 描边渐变 -->\n'
        
        if gradient_type == 'radial':
            # 径向渐变
            svg += f'        <radialGradient cx="50%" cy="50%" r="75%" fx="50%" fy="50%" id="strokeGradient">\n'
            svg += f'            <stop stop-color="{colors[0]}" offset="0%"></stop>\n'
            svg += f'            <stop stop-color="{colors[1]}" offset="100%"></stop>\n'
            svg += f'        </radialGradient>\n\n'
        else:
            # 线性渐变 - 根据方向设置坐标
            x1, y1, x2, y2 = self._get_gradient_coordinates(gradient.get('direction', 'left_right'))
            
            svg += f'        <linearGradient x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" id="strokeGradient">\n'
            svg += f'            <stop stop-color="{colors[0]}" offset="0%"></stop>\n'
            svg += f'            <stop stop-color="{colors[1]}" offset="100%"></stop>\n'
            svg += f'        </linearGradient>\n\n'
            
        return svg
    
    def _generate_shadow_filter(self, style):
        """生成阴影滤镜定义"""
        shadow = style.get('shadow', {})
        
        # 获取参数
        color = shadow.get('color', '#000000')
        opacity = shadow.get('opacity', 0.6)
        blur = shadow.get('blur', 10)
        offset_x = shadow.get('offset_x', 5)
        offset_y = shadow.get('offset_y', 5)
        
        # 转换颜色为RGB值（用于feColorMatrix）
        rgb = self._hex_to_rgb_normalized(color)
        
        # 生成SVG滤镜定义
        svg = f'        <!-- 阴影效果 -->\n'
        svg += f'        <filter x="-20%" y="-20%" width="140%" height="140%" filterUnits="objectBoundingBox" id="shadow-filter">\n'
        svg += f'            <feOffset dx="{offset_x}" dy="{offset_y}" in="SourceAlpha" result="shadowOffsetOuter1"></feOffset>\n'
        svg += f'            <feGaussianBlur stdDeviation="{blur/2}" in="shadowOffsetOuter1" result="shadowBlurOuter1"></feGaussianBlur>\n'
        svg += f'            <feColorMatrix values="0 0 0 0 {rgb[0]}   0 0 0 0 {rgb[1]}   0 0 0 0 {rgb[2]}  0 0 0 {opacity} 0" type="matrix" in="shadowBlurOuter1"></feColorMatrix>\n'
        svg += f'        </filter>\n\n'
        
        return svg
    
    def _generate_inner_shadow_filter(self, style):
        """生成内阴影滤镜定义"""
        inner_shadow = style.get('inner_shadow', {})
        
        # 获取参数
        color = inner_shadow.get('color', '#000000')
        opacity = inner_shadow.get('opacity', 0.5)
        blur = inner_shadow.get('blur', 2)
        offset_x = inner_shadow.get('offset_x', 2)
        offset_y = inner_shadow.get('offset_y', 2)
        
        # 转换颜色为RGB值（用于feColorMatrix）
        rgb = self._hex_to_rgb_normalized(color)
        
        # 生成SVG滤镜定义
        svg = f'        <!-- 内阴影效果 -->\n'
        svg += f'        <filter x="-10%" y="-10%" width="120%" height="120%" filterUnits="objectBoundingBox" id="inner-shadow-filter">\n'
        svg += f'            <feOffset dx="{offset_x}" dy="{offset_y}" in="SourceAlpha" result="shadowOffset"></feOffset>\n'
        svg += f'            <feComposite in="shadowOffset" in2="SourceAlpha" operator="arithmetic" k2="-1" k3="1" result="shadowDifference"></feComposite>\n'
        svg += f'            <feGaussianBlur stdDeviation="{blur/2}" in="shadowDifference" result="shadowBlur"></feGaussianBlur>\n'
        svg += f'            <feColorMatrix values="0 0 0 0 {rgb[0]}   0 0 0 0 {rgb[1]}   0 0 0 0 {rgb[2]}  0 0 0 {opacity} 0" type="matrix" in="shadowBlur"></feColorMatrix>\n'
        svg += f'        </filter>\n\n'
        
        return svg
        
    def _generate_glow_filter(self, style):
        """生成外发光滤镜定义"""
        glow = style.get('glow', {})
        
        # 获取参数
        color = glow.get('color', '#FFCC00')
        opacity = glow.get('opacity', 0.8)
        radius = glow.get('radius', 10)
        
        # 转换颜色为RGB值（用于feColorMatrix）
        rgb = self._hex_to_rgb_normalized(color)
        
        # 生成SVG滤镜定义
        svg = f'        <!-- 外发光效果 -->\n'
        svg += f'        <filter x="-20%" y="-20%" width="140%" height="140%" filterUnits="objectBoundingBox" id="glow-filter">\n'
        svg += f'            <feGaussianBlur stdDeviation="{radius}" in="SourceAlpha" result="glowBlur"></feGaussianBlur>\n'
        svg += f'            <feColorMatrix values="0 0 0 0 {rgb[0]}   0 0 0 0 {rgb[1]}   0 0 0 0 {rgb[2]}  0 0 0 {opacity} 0" type="matrix" in="glowBlur"></feColorMatrix>\n'
        svg += f'        </filter>\n\n'
        
        return svg
        
    def _get_gradient_coordinates(self, direction):
        """根据方向获取渐变坐标
        
        Returns:
            x1, y1, x2, y2 的百分比值
        """
        # 默认从上到下
        x1, y1, x2, y2 = "50%", "0%", "50%", "100%"
        
        # 根据不同方向设置坐标
        if direction == 'left_right':
            x1, y1, x2, y2 = "0%", "50%", "100%", "50%"
        elif direction == 'right_left':
            x1, y1, x2, y2 = "100%", "50%", "0%", "50%"
        elif direction == 'top_bottom':
            x1, y1, x2, y2 = "50%", "0%", "50%", "100%"
        elif direction == 'bottom_top':
            x1, y1, x2, y2 = "50%", "100%", "50%", "0%"
        elif direction == 'diagonal':
            x1, y1, x2, y2 = "0%", "0%", "100%", "100%"
        elif direction == 'diagonal_reverse':
            x1, y1, x2, y2 = "100%", "100%", "0%", "0%"
        elif direction == 'diagonal_bottom':
            x1, y1, x2, y2 = "0%", "100%", "100%", "0%"
        elif direction == 'diagonal_bottom_reverse':
            x1, y1, x2, y2 = "100%", "0%", "0%", "100%"
        
        return x1, y1, x2, y2
    
    def _hex_to_rgb_normalized(self, hex_str):
        """将十六进制颜色转换为归一化的RGB值（0-1范围）"""
        hex_str = hex_str.lstrip('#')
        
        if len(hex_str) == 6:
            r = int(hex_str[0:2], 16) / 255.0
            g = int(hex_str[2:4], 16) / 255.0
            b = int(hex_str[4:6], 16) / 255.0
            return (r, g, b)
        
        return (0, 0, 0)  # 默认黑色

"""
测试修复后的StyleConverter能否正确处理SVG中的所有效果。
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont
from core.svg_parser import SVGParser
from core.svg_style_converter import SVGStyleConverter
from core.effects_processor import EffectsProcessor
from core.text_renderer import TextRenderer

def test_style_rendering(style_name="all-effects-test", text="Effect", output_path="test_output"):
    """测试指定样式的渲染效果"""
    # 创建输出目录
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    # 加载SVG样式
    base_dir = os.path.dirname(os.path.abspath(__file__))
    svg_path = os.path.join(base_dir, "SVG", f"{style_name}.svg")
    
    if not os.path.exists(svg_path):
        print(f"错误: 未找到SVG文件: {svg_path}")
        return None
    
    # 解析SVG文件
    parser = SVGParser(svg_path)
    svg_data = parser.parse()
    
    # 使用修复后的转换器
    print(f"[测试] 正在解析样式: {style_name}")
    converter = SVGStyleConverter(svg_data)
    converter.style_name = style_name
    
    # 转换为样式字典
    style = converter.convert_to_json_style()
    
    # 显示检测到的效果
    effect_keys = [key for key in style.keys() if key in ['shadow', 'inner_shadow', 'glow', 'outline', 'fill']]
    print(f"[测试] 样式中发现的效果:", effect_keys)
    print(f"[测试] 样式完整数据:", style)
    
    # 设置图像尺寸和安全区域
    width, height = 600, 400
    safe_area = (50, 50, 550, 350)  # (x0, y0, x1, y1)
    
    # 获取字体路径
    font_name = style.get("font", "Knewave-Regular.ttf")
    fonts_dir = os.path.join(base_dir, "fonts")
    font_path = os.path.join(fonts_dir, font_name)
    
    # 如果字体不存在，使用默认字体
    if not os.path.exists(font_path):
        default_fonts = ["Knewave-Regular.ttf", "Lobster-Regular.ttf", "MaldiniBold.ttf"]
        for default_font in default_fonts:
            default_path = os.path.join(fonts_dir, default_font)
            if os.path.exists(default_path):
                font_path = default_path
                break
    
    # 创建渲染器
    renderer = TextRenderer(font_path, style.get("size", 72))
    
    # 创建两张测试图像 - 一张正常渲染，一张仅渲染指定的效果
    print(f"[测试] 正在渲染文本...")
    
    # 创建效果处理器
    effects_processor = EffectsProcessor()
    
    # 渲染所有效果
    base_img_all = renderer.create_base_text_image(text, style, width, height, True, safe_area)
    img_all = effects_processor.apply_all_effects(base_img_all, style)
    
    # 针对不同效果，创建单独渲染的图像以便比较
    
    # 1. 仅渲染填充效果
    fill_style = style.copy()
    for key in ['shadow', 'inner_shadow', 'glow', 'outline']:
        if key in fill_style:
            del fill_style[key]
    base_img_fill = renderer.create_base_text_image(text, fill_style, width, height, True, safe_area)
    img_fill = effects_processor.apply_all_effects(base_img_fill, fill_style)
    
    # 2. 仅渲染内阴影效果
    if 'inner_shadow' in style:
        inner_shadow_style = {
            'font': style.get('font'),
            'size': style.get('size'),
            'alignment': style.get('alignment'),
            'spacing': style.get('spacing'),
            'leading': style.get('leading'),
            'fill': {'type': 'solid', 'color': '#FFFFFF'},  # 白色填充，使内阴影更明显
            'fill_opacity': 1.0,
            'inner_shadow': style['inner_shadow']
        }
        base_img_inner = renderer.create_base_text_image(text, inner_shadow_style, width, height, True, safe_area)
        img_inner_shadow = effects_processor.apply_all_effects(base_img_inner, inner_shadow_style)
    
    # 3. 仅渲染外阴影效果
    if 'shadow' in style:
        shadow_style = {
            'font': style.get('font'),
            'size': style.get('size'),
            'alignment': style.get('alignment'),
            'spacing': style.get('spacing'),
            'leading': style.get('leading'),
            'fill': {'type': 'solid', 'color': '#FFFFFF'},  # 白色填充
            'fill_opacity': 1.0,
            'shadow': style['shadow']
        }
        base_img_shadow = renderer.create_base_text_image(text, shadow_style, width, height, True, safe_area)
        img_shadow = effects_processor.apply_all_effects(base_img_shadow, shadow_style)
    
    # 4. 仅渲染发光效果
    if 'glow' in style:
        glow_style = {
            'font': style.get('font'),
            'size': style.get('size'),
            'alignment': style.get('alignment'),
            'spacing': style.get('spacing'),
            'leading': style.get('leading'),
            'fill': {'type': 'solid', 'color': '#FFFFFF'},  # 白色填充
            'fill_opacity': 1.0,
            'glow': style['glow']
        }
        base_img_glow = renderer.create_base_text_image(text, glow_style, width, height, True, safe_area)
        img_glow = effects_processor.apply_all_effects(base_img_glow, glow_style)
    
    # 5. 渲染所有效果（自定义样式）
    all_effects_style = {
        'name': 'all-effects-test',  # 添加样式标识
        'fill': {
            'type': 'gradient',
            'colors': ['#0066FF80', '#00FF0080'],  # 半透明蓝绿渐变
            'direction': 'top_bottom'
        },
        'outline': {
            'width': 6,  # 增加描边宽度
            'gradient': {
                'colors': ['#FF0000', '#0000FF'],  # 高对比红蓝渐变
                'type': 'linear',
                'direction': 'left_right'
            }
        },
        'inner_shadow': {
            'color': '#FF0000CC',  # 半透明红色
            'offset_x': 8,
            'offset_y': 8,
            'blur': 10,            # 增强模糊
            'opacity': 0.9
        },
        'debug_layers': True
    }
    base_img_all_effects = renderer.create_base_text_image(text, all_effects_style, width, height, True, safe_area)
    img_all_effects = effects_processor.apply_all_effects(base_img_all_effects, all_effects_style)
    
    # 保存图像
    output_base = os.path.join(output_path, f"{style_name}")
    img_all.save(f"{output_base}_all.png")
    img_fill.save(f"{output_base}_fill.png")
    
    if 'inner_shadow' in style:
        img_inner_shadow.save(f"{output_base}_inner_shadow.png")
    if 'shadow' in style:
        img_shadow.save(f"{output_base}_shadow.png")
    if 'glow' in style:
        img_glow.save(f"{output_base}_glow.png")
    img_all_effects.save(f"{output_base}_all_effects.png")
    
    print(f"[测试] 渲染结果已保存到: {output_path}目录")
    return img_all

if __name__ == "__main__":
    # 从命令行获取样式名称
    if len(sys.argv) > 1:
        style_name = sys.argv[1]
    else:
        style_name = "all-effects-test"  # 默认使用全效果测试
    
    # 运行测试
    test_style_rendering(style_name)

"""
创建一个可视化工具，显示效果渲染中的各个图层及其叠加效果
"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
from core.svg_parser import SVGParser
from core.svg_style_converter import SVGStyleConverter
from core.effects_processor import EffectsProcessor
from core.text_renderer import TextRenderer

def visualize_effect_layers(style_name="all-effects-test", text="Effect", output_path="test_output"):
    """可视化效果图层"""
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
    
    # 使用转换器
    print(f"[测试] 正在解析样式: {style_name}")
    converter = SVGStyleConverter(svg_data)
    converter.style_name = style_name
    
    # 转换为样式字典
    style = converter.convert_to_json_style()
    
    # 显示检测到的效果
    effect_keys = [key for key in style.keys() if key in ['shadow', 'inner_shadow', 'glow', 'outline', 'fill']]
    print(f"[测试] 样式中发现的效果:", effect_keys)
    
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
    effects_processor = EffectsProcessor()
    
    # 创建基础图像并确保是RGBA模式
    base_img = renderer.create_base_text_image(text, style, width, height, True, safe_area)
    if base_img.mode != 'RGBA':
        base_img = base_img.convert('RGBA')
    
    # 保存单独的效果图层
    layers = {}
    steps = []
    
    # 1. 绘制基础图层 - 完全不透明的白色填充文本
    base_style = {
        'font': style.get('font'),
        'size': style.get('size'),
        'alignment': style.get('alignment'),
        'spacing': style.get('spacing'),
        'leading': style.get('leading'),
        'fill': {'type': 'solid', 'color': '#FFFFFF'},
        'fill_opacity': 1.0
    }
    
    # 创建带有文本轮廓的透明图像
    base_text_img = renderer.create_base_text_image(text, base_style, width, height, True, safe_area)
    
    # 确保文本区域是完全不透明的白色填充
    # 从alpha通道创建一个遮罩
    _, _, _, a = base_text_img.split()
    
    # 创建纯白色背景图像
    solid_white = Image.new('RGB', base_text_img.size, (255, 255, 255))
    
    # 使用文本的alpha通道作为遮罩，创建实心白色文本
    base_white = Image.new('RGBA', base_text_img.size, (0, 0, 0, 255))  # 黑色背景
    base_white.paste(solid_white, (0, 0), a)
    
    layers["base"] = base_white
    steps.append(("base", base_white))
    output_path_base = os.path.join(output_path, f"{style_name}_layer_0_base.png")
    base_white.save(output_path_base)
    
    # 2. 应用描边效果
    if 'outline' in style and style['outline'].get('width', 0) > 0:
        outline_style = style.copy()
        # 只保留描边效果
        for key in ['shadow', 'inner_shadow', 'glow']:
            if key in outline_style:
                del outline_style[key]
        # 将填充改为透明
        if 'fill' in outline_style:
            outline_style['fill'] = {'type': 'solid', 'color': '#FFFFFF00'}
            
        outline_base = renderer.create_base_text_image(text, outline_style, width, height, True, safe_area)
        if 'gradient' in style.get('outline', {}):
            outline_img = effects_processor._apply_gradient_outline(outline_base, style)
        else:
            outline_img = effects_processor.apply_outline(outline_base, style)
        layers["outline"] = outline_img
        steps.append(("outline", outline_img))
        output_path_outline = os.path.join(output_path, f"{style_name}_layer_1_outline.png")
        outline_img.save(output_path_outline)
    
    # 3. 应用阴影效果
    if 'shadow' in style:
        shadow_style = {
            'font': style.get('font'),
            'size': style.get('size'),
            'alignment': style.get('alignment'),
            'spacing': style.get('spacing'),
            'leading': style.get('leading'),
            'fill': {'type': 'solid', 'color': '#FFFFFF'},
            'shadow': style['shadow']
        }
        shadow_base = renderer.create_base_text_image(text, shadow_style, width, height, True, safe_area)
        shadow_img = effects_processor.apply_shadow(shadow_base, shadow_style)
        layers["shadow"] = shadow_img
        steps.append(("shadow", shadow_img))
        output_path_shadow = os.path.join(output_path, f"{style_name}_layer_2_shadow.png")
        shadow_img.save(output_path_shadow)
    
    # 4. 应用渐变填充
    if 'fill' in style and style['fill'].get('type') == 'gradient':
        # 创建渐变填充效果
        fill_style = {
            'font': style.get('font'),
            'size': style.get('size'),
            'alignment': style.get('alignment'),
            'spacing': style.get('spacing'),
            'leading': style.get('leading'),
            'fill': style['fill'].copy(),
            'fill_opacity': style.get('fill_opacity', 1.0)
        }
        
        # 获取原始文本mask - 确保只有文本区域是可见的
        _, _, _, text_mask = base_text_img.split()  # 使用原始文本图像的alpha通道
        
        # 创建渐变图像
        gradient = effects_processor._create_gradient(
            width, 
            height, 
            [effects_processor.hex_to_rgba(color)[:3] for color in style['fill'].get('colors', ['#FFFFFF', '#0000FF'])],
            style['fill'].get('angle', 0)
        )
        
        # 创建一个只包含文本形状的二值蒙版（白色=文本区域，黑色=背景）
        binary_mask = Image.new('1', (width, height), 0)  # 初始化全黑二值图像
        binary_mask.paste(1, (0, 0), text_mask)  # 在文本区域粘贴白色
        
        # 使用numpy进行精确的像素级操作
        gradient_array = np.array(gradient)
        mask_array = np.array(binary_mask)
        
        # 扩展mask数组以匹配渐变数组的形状
        mask_array_3d = np.stack([mask_array] * 3, axis=2)
        
        # 将渐变应用到文本区域（其他区域保持黑色）
        gradient_masked = gradient_array * mask_array_3d
        
        # 转换回PIL图像并添加透明通道
        gradient_masked_img = Image.fromarray(gradient_masked.astype(np.uint8))
        gradient_masked_rgba = gradient_masked_img.convert('RGBA')
        
        # 将透明度通道设置为文本的透明度
        r, g, b, _ = gradient_masked_rgba.split()
        fill_img = Image.merge('RGBA', (r, g, b, text_mask))
        
        layers["fill"] = fill_img
        steps.append(("fill", fill_img))
        output_path_fill = os.path.join(output_path, f"{style_name}_layer_3_fill.png")
        fill_img.save(output_path_fill)
    
    # 5. 应用内阴影效果
    if 'inner_shadow' in style:
        inner_shadow_style = {
            'font': style.get('font'),
            'size': style.get('size'),
            'alignment': style.get('alignment'),
            'spacing': style.get('spacing'),
            'leading': style.get('leading'),
            'fill': {'type': 'solid', 'color': '#FFFFFF'},
            'inner_shadow': style['inner_shadow']
        }
        inner_base = renderer.create_base_text_image(text, inner_shadow_style, width, height, True, safe_area)
        inner_img = effects_processor.apply_inner_shadow(inner_base, inner_shadow_style)
        layers["inner_shadow"] = inner_img
        steps.append(("inner_shadow", inner_img))
        output_path_inner = os.path.join(output_path, f"{style_name}_layer_4_inner_shadow.png")
        inner_img.save(output_path_inner)
    
    # 6. 应用发光效果
    if 'glow' in style:
        glow_style = {
            'font': style.get('font'),
            'size': style.get('size'),
            'alignment': style.get('alignment'),
            'spacing': style.get('spacing'),
            'leading': style.get('leading'),
            'fill': {'type': 'solid', 'color': '#FFFFFF'},
            'glow': style['glow']
        }
        glow_base = renderer.create_base_text_image(text, glow_style, width, height, True, safe_area)
        glow_img = effects_processor.apply_glow(glow_base, glow_style)
        layers["glow"] = glow_img
        steps.append(("glow", glow_img))
        output_path_glow = os.path.join(output_path, f"{style_name}_layer_5_glow.png")
        glow_img.save(output_path_glow)
    
    # 7. 所有效果组合 - 使用修改后的合成方法
    # 创建一个干净的基础图像作为起点
    # 我们不使用base_white，因为它已经有黑色背景和白色文本
    # 而是使用原始的透明背景文本图像
    base_for_effects = renderer.create_base_text_image(text, style, width, height, True, safe_area)
    # 添加name参数，解决style_name未正确传递的问题
    all_img = effects_processor.apply_all_effects(base_for_effects, style, style_name)
    
    output_path_all = os.path.join(output_path, f"{style_name}_layer_all.png")
    all_img.save(output_path_all)
    
    # 也保存一个带黑色背景的版本，便于查看
    bg = Image.new('RGBA', all_img.size, (0, 0, 0, 255))  # 黑色背景
    with_bg = Image.alpha_composite(bg, all_img)
    with_bg.save(os.path.join(output_path, f"{style_name}_layer_all_with_bg.png"))
    
    # 创建可视化图像
    from matplotlib import pyplot as plt
    
    # 设置黑色背景
    plt.rcParams['figure.facecolor'] = 'black'
    plt.rcParams['axes.facecolor'] = 'black'
    plt.rcParams['savefig.facecolor'] = 'black'
    
    plt.figure(figsize=(15, 10))
    plt.suptitle(f"Effects Layers Visualization - {style_name}", fontsize=16, color='white')
    
    # 创建两行三列的布局
    total_layers = len(layers) + 1  # 所有图层加上一个组合效果
    cols = 3
    rows = (total_layers + cols - 1) // cols
    
    # 按顺序显示图层
    for i, (name, img) in enumerate(steps):
        plt.subplot(rows, cols, i + 1)
        plt.title(f"Layer: {name}", color='white')
        plt.imshow(np.array(img))
        plt.axis('off')
    
    # 在最后一个位置添加组合效果
    plt.subplot(rows, cols, len(steps) + 1)
    plt.title("All Effects Combined", color='white')
    plt.imshow(np.array(all_img))
    plt.axis('off')
    
    # 保存可视化图像
    visualization_path = os.path.join(output_path, f"{style_name}_visualization.png")
    plt.tight_layout()
    plt.savefig(visualization_path, dpi=100)
    plt.close()
    
    print(f"[测试] 可视化图层已保存到: {output_path}目录")
    return all_img

if __name__ == "__main__":
    # 从命令行获取样式名称
    if len(sys.argv) > 1:
        style_name = sys.argv[1]
    else:
        style_name = "all-effects-test"
    
    # 运行可视化
    visualize_effect_layers(style_name)

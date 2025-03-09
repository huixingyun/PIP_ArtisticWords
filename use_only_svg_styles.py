"""
这个脚本帮助修改PIP_ArtisticWords节点包，使其只加载SVG目录下的样式，
而不加载sketchstyle目录下的样式。

使用方法:
1. 将此脚本复制到ComfyUI_windows_portable\ComfyUI\custom_nodes\PIP_ArtisticWords目录
2. 在该目录下运行此脚本
3. 重启ComfyUI
"""

import os
import sys
import re

"""
PIP Artistic Words SVG-Only 样式系统

该文件标记 PIP Artistic Words 扩展现在直接使用 SVG 文件作为样式源，
不再需要中间 JSON 转换步骤。

使用方法：
1. 将设计师导出的 SVG 文件放置在 'SVG' 目录下
2. 重启 ComfyUI，样式将会被自动加载
3. 在 ComfyUI 中使用文本节点时，样式名称将与 SVG 文件名相同

优势：
- 简化工作流程，无需中间转换步骤
- 设计师可以直接导出 SVG 并用于生成文本
- 直接从 SVG 中提取所有样式信息，包括字体、颜色、效果等

注意：
- 确保 SVG 文件包含文本元素，以便正确提取样式
- 推荐使用 Sketch、Illustrator 或 Figma 等工具导出 SVG
"""

# SVG 样式系统标记
SVG_STYLES_ENABLED = True

# 寻找样式管理器文件
style_manager_path = None
for root, dirs, files in os.walk('.'):
    for file in files:
        if file == "style_manager.py":
            style_manager_path = os.path.join(root, file)
            break
    if style_manager_path:
        break

if not style_manager_path:
    print("找不到style_manager.py文件")
    sys.exit(1)

print(f"找到样式管理器文件: {style_manager_path}")

# 读取原始文件内容
with open(style_manager_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找加载JSON样式的函数
json_load_pattern = r'def\s+load_json_styles\s*\([^)]*\):'
json_load_match = re.search(json_load_pattern, content)

if not json_load_match:
    print("无法找到load_json_styles函数")
    sys.exit(1)

# 找到函数体的开始位置
func_start = json_load_match.end()
indent_match = re.search(r'\n(\s+)', content[func_start:])
if not indent_match:
    print("无法确定函数缩进")
    sys.exit(1)

indent = indent_match.group(1)

# 创建修改后的函数
modified_func = """def load_json_styles(self):
        \"\"\"加载JSON格式的样式文件，但只加载SVG目录下的样式\"\"\"
        # 跳过sketchstyle目录下的样式
        print("[StyleManager] 根据设置跳过sketchstyle目录下的JSON样式")
        
        # 仅处理SVG样式
        self.load_svg_styles()
        
        # 加载完成后的信息
        print(f"[StyleManager] 总共加载了 {len(self.styles)} 个样式")
"""

# 替换函数
new_content = re.sub(json_load_pattern + r'.*?(?=\n\S|\Z)', modified_func, content, flags=re.DOTALL)

# 备份原始文件
backup_path = style_manager_path + '.backup'
with open(backup_path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"已创建原始文件备份: {backup_path}")

# 写入修改后的内容
with open(style_manager_path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print(f"已修改样式管理器，现在将只加载SVG目录下的样式")
print("请重启ComfyUI以使修改生效")

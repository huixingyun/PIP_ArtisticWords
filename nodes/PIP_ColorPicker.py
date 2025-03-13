import comfy
import torch
import numpy as np
from PIL import Image
import colorsys

class PIPColorPicker:
    """PIP 颜色拾取节点（修复越界问题版）"""
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "grid_blocks": ("INT", {
                    "default": 40,
                    "min": 1,
                    "max": 200,
                    "step": 1
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("填充色", "描边色", "阴影色")
    FUNCTION = "process"
    CATEGORY = "PIP"

    def process(self, image: torch.Tensor, grid_blocks=40):
        # 将 ComfyUI 的 Tensor 转换为 PIL 图像
        img = self.tensor2pil(image)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        # 获取平均颜色
        avg_color = self.get_average_color(img, grid_blocks)
        if not avg_color:
            return ("#000000", "#000000", "#000000")
        
        # 生成三个颜色变体
        fill_color = self.adjust_brightness(avg_color, 0.3)
        shadow_color = self.adjust_brightness(avg_color, -0.3)
        
        return (
            self.rgb_to_hex(fill_color),
            self.rgb_to_hex(avg_color),
            self.rgb_to_hex(shadow_color)
        )

    def tensor2pil(self, image: torch.Tensor) -> Image.Image:
        """修复Tensor转换问题"""
        img = 255. * image.cpu().numpy()[0]
        img = np.clip(img, 0, 255).astype(np.uint8)
        return Image.fromarray(img)

    def get_average_color(self, img: Image.Image, grid_blocks: int) -> tuple:
        """动态计算步长，避免越界"""
        width, height = img.size
        block_w = max(1, width // grid_blocks)
        block_h = max(1, height // grid_blocks)
        
        total_r = total_g = total_b = count = 0
        
        for y in range(0, height, block_h):
            for x in range(0, width, block_w):
                if x >= width or y >= height:
                    continue  # 跳过越界点
                try:
                    r, g, b, a = img.getpixel((x, y))
                    if a < 10:
                        continue
                    total_r += r
                    total_g += g
                    total_b += b
                    count += 1
                except:
                    pass
        
        if count == 0:
            return None
        
        return (
            int(total_r / count),
            int(total_g / count),
            int(total_b / count)
        )

    # 新增缺失的两个方法
    def adjust_brightness(self, rgb: tuple, delta: float) -> tuple:
        """通过 HSV 调整亮度"""
        r, g, b = [x / 255.0 for x in rgb]
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        v = max(0.0, min(1.0, v + delta))
        new_r, new_g, new_b = colorsys.hsv_to_rgb(h, s, v)
        return (
            int(new_r * 255),
            int(new_g * 255),
            int(new_b * 255)
        )

    def rgb_to_hex(self, rgb: tuple) -> str:
        """RGB转十六进制"""
        return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])

# 节点注册
NODE_CLASS_MAPPINGS = {
    "PIPColorPicker": PIPColorPicker
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PIPColorPicker": "🔴 PIP 颜色拾取"
}
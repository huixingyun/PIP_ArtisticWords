import comfy
import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import colorsys
from collections import Counter
import os

class PIPAdvancedColorAnalyzer:
    """PIP 高级颜色分析节点"""
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "num_dominant_colors": ("INT", {
                    "default": 8,
                    "min": 2,
                    "max": 20,
                    "step": 1
                }),
            },
            "hidden": {
                "auto_sample": ("BOOLEAN", {"default": True}),
                "sample_points": ("INT", {"default": 1000}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT", "FLOAT", "IMAGE")
    RETURN_NAMES = ("主导色", "辅助色", "平均亮度", "平均饱和度", "分析图")
    FUNCTION = "process"
    CATEGORY = "PIP"

    def process(self, image: torch.Tensor, auto_sample=True, sample_points=1000, num_dominant_colors=8):
        # 将 ComfyUI 的 Tensor 转换为 PIL 图像
        img = self.tensor2pil(image)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        # 如果启用了自动采样，则根据图片尺寸计算采样点数
        if auto_sample:
            width, height = img.size
            # 根据图片的像素总数动态计算采样点数
            # 使用更高的采样比例，确保有足够多的数据点进行准确分析
            total_pixels = width * height
            # 基础采样点数目提高，并使用更大的比例因子
            sample_points = int(min(50000, max(2000, total_pixels ** 0.5 * 1.5)))
            print(f"自动计算的采样点数: {sample_points}, 图片尺寸: {width}x{height}")
        
        # 分析颜色
        dominant_colors, color_counts = self.get_dominant_colors(img, sample_points, num_dominant_colors)
        
        if not dominant_colors:
            return ("#000000", "#000000", 0.0, 0.0, image)
        
        # 计算主导色和辅助色
        main_color = dominant_colors[0]
        
        # 查找与主导色有足够区分度的辅助色
        secondary_color = self.find_distinct_secondary_color(dominant_colors, color_counts, main_color)
        
        # 计算主导色和辅助色的占比
        total_samples = sum(color_counts)
        main_percentage = (color_counts[0] / total_samples) * 100
        
        # 找出辅助色在原始列表中的索引，以获取其占比
        if secondary_color in dominant_colors:
            sec_idx = dominant_colors.index(secondary_color)
            secondary_percentage = (color_counts[sec_idx] / total_samples) * 100
        else:
            # 如果辅助色是派生的，使用第二常见颜色的占比或估计值
            secondary_percentage = (color_counts[1] / total_samples) * 100 if len(color_counts) > 1 else 0
        
        # 计算平均亮度和饱和度
        avg_brightness, avg_saturation = self.calculate_avg_brightness_saturation(img, sample_points)
        
        # 生成分析图片
        analysis_image = self.create_analysis_image(
            main_color, 
            secondary_color, 
            main_percentage, 
            secondary_percentage, 
            avg_brightness, 
            avg_saturation,
            dominant_colors,
            color_counts,
            total_samples
        )
        
        # 转换为ComfyUI格式
        analysis_tensor = self.pil2tensor(analysis_image)
        
        return (
            self.rgb_to_hex(main_color),
            self.rgb_to_hex(secondary_color),
            float(avg_brightness),
            float(avg_saturation),
            analysis_tensor
        )
    
    def get_dominant_colors(self, img, sample_points, num_dominant_colors):
        """获取图像中的主导颜色，使用混合采样策略"""
        width, height = img.size
        pixels = []
        
        # 第一阶段：使用均匀网格采样
        # 计算网格大小，确保网格数足够密集
        grid_size = min(int(sample_points ** 0.5 * 1.5), min(width, height))
        # 确保至少有50个网格
        grid_size = max(50, grid_size)
        block_w = max(1, width // grid_size)
        block_h = max(1, height // grid_size)
        
        print(f"采样策略: 均匀网格法, 网格尺寸: {grid_size}x{grid_size}, 块大小: {block_w}x{block_h}")
        
        # 使用均匀网格采样
        count = 0
        color_freq_map = {}  # 用于存储颜色频率
        
        # 第一阶段：统计图像颜色
        # 1. 将图像缩小以加快处理速度
        scale_factor = max(1, min(width, height) // 200)  # 保证缩小后至少200px
        small_img = img.resize((width // scale_factor, height // scale_factor), Image.Resampling.LANCZOS)
        small_width, small_height = small_img.size
        
        print(f"缩小图像以分析整体颜色分布: {small_width}x{small_height}")
        
        # 2. 扫描整个缩小后的图像
        for y in range(small_height):
            for x in range(small_width):
                try:
                    r, g, b, a = small_img.getpixel((x, y))
                    if a < 10:  # 忽略透明像素
                        continue
                    
                    # 量化颜色 (降低精度来合并相似颜色)
                    qr = r // 8
                    qg = g // 8
                    qb = b // 8
                    color_key = (qr, qg, qb)
                    
                    if color_key in color_freq_map:
                        color_freq_map[color_key] += 1
                    else:
                        color_freq_map[color_key] = 1
                        
                    count += 1
                except:
                    pass
        
        # 3. 按频率排序颜色
        sorted_colors = sorted(color_freq_map.items(), key=lambda x: x[1], reverse=True)
        
        # 4. 转换回RGB空间
        for (qr, qg, qb), freq in sorted_colors[:num_dominant_colors * 3]:
            r = (qr * 8) + 4
            g = (qg * 8) + 4
            b = (qb * 8) + 4
            # 添加多个样本点，按照频率比例
            samples_to_add = max(1, int((freq / count) * sample_points))
            pixels.extend([(r, g, b)] * samples_to_add)
        
        # 第二阶段：特定区域精细采样
        # 使用网格采样获取更多细节
        grid_samples = []
        for y in range(0, height, block_h):
            for x in range(0, width, block_w):
                if x >= width or y >= height:
                    continue  # 跳过越界点
                
                try:
                    r, g, b, a = img.getpixel((x, y))
                    if a < 10:  # 忽略透明像素
                        continue
                    grid_samples.append((r, g, b))
                except:
                    pass
        
        # 将网格采样结果添加到像素列表中，赋予一定权重
        grid_weight = min(1.0, 0.3 * (sample_points / len(grid_samples)) if grid_samples else 0)
        grid_samples_to_add = int(len(grid_samples) * grid_weight)
        
        if grid_samples:
            import random
            # 随机选择一部分网格样本添加到像素列表
            pixels.extend(random.sample(grid_samples, min(grid_samples_to_add, len(grid_samples))))
        
        print(f"总采样点数: {len(pixels)}, 其中频率采样: {len(pixels) - min(grid_samples_to_add, len(grid_samples))}, 网格采样: {min(grid_samples_to_add, len(grid_samples))}")
        
        if not pixels:
            return [], []
        
        # 使用K-means聚类找出主导颜色
        try:
            import numpy as np
            from sklearn.cluster import KMeans
            
            # 转换为numpy数组
            pixel_array = np.array(pixels)
            
            # 根据颜色数量决定聚类数量
            n_clusters = min(num_dominant_colors * 2, 8)  # 最多8个聚类
            
            # 应用K-means聚类
            kmeans = KMeans(n_clusters=n_clusters, n_init=3, random_state=0)
            labels = kmeans.fit_predict(pixel_array)
            
            # 计算每个聚类的大小
            cluster_sizes = np.bincount(labels)
            
            # 获取聚类中心（即主导颜色）
            centers = kmeans.cluster_centers_
            
            # 将聚类结果转换回整数RGB值
            dominant_colors = []
            color_counts = []
            
            # 按聚类大小排序
            sorted_indices = np.argsort(cluster_sizes)[::-1]
            
            for idx in sorted_indices[:num_dominant_colors]:
                center = centers[idx]
                dominant_colors.append((int(center[0]), int(center[1]), int(center[2])))
                color_counts.append(int(cluster_sizes[idx]))
            
            print("使用K-means聚类结果:")
        except ImportError:
            print("无法导入sklearn，退回到传统颜色量化方法")
            # 使用传统量化方法作为备选
            # 计算每个量化颜色的频率
            from collections import Counter
            quantized_pixels = []
            for r, g, b in pixels:
                qr = r // 8  # 约0-31
                qg = g // 8  # 约0-31
                qb = b // 8  # 约0-31
                quantized_pixels.append((qr, qg, qb))
            
            color_counter = Counter(quantized_pixels)
            # 获取最常见的颜色
            common_colors = color_counter.most_common(num_dominant_colors * 3)
            
            # 将量化的颜色转换回RGB
            candidate_colors = []
            for (qr, qg, qb), count in common_colors:
                r = (qr * 8) + 4
                g = (qg * 8) + 4
                b = (qb * 8) + 4
                candidate_colors.append(((r, g, b), count))
            
            # 合并相似颜色
            merged_colors = []
            merged_counts = []
            
            # 处理每个候选颜色
            for color, count in candidate_colors:
                # 检查这个颜色是否与已经处理过的颜色相似
                is_similar = False
                for i, existing_color in enumerate(merged_colors):
                    distance = self.calculate_color_distance(color, existing_color)
                    if distance < 25:  # 如果颜色距离小于阈值，认为是相似颜色
                        # 合并颜色 (加权平均)
                        total_count = merged_counts[i] + count
                        weight1 = merged_counts[i] / total_count
                        weight2 = count / total_count
                        
                        r = int(existing_color[0] * weight1 + color[0] * weight2)
                        g = int(existing_color[1] * weight1 + color[1] * weight2)
                        b = int(existing_color[2] * weight1 + color[2] * weight2)
                        
                        merged_colors[i] = (r, g, b)
                        merged_counts[i] += count
                        is_similar = True
                        break
                
                # 如果不相似，添加为新颜色
                if not is_similar:
                    merged_colors.append(color)
                    merged_counts.append(count)
            
            # 按出现频率排序
            sorted_colors = [(color, count) for color, count in zip(merged_colors, merged_counts)]
            sorted_colors.sort(key=lambda x: x[1], reverse=True)
            
            # 限制颜色数量
            dominant_colors = [color for color, _ in sorted_colors[:num_dominant_colors]]
            color_counts = [count for _, count in sorted_colors[:num_dominant_colors]]
        
        # 打印调试信息
        print("最终颜色列表:")
        for i, (color, count) in enumerate(zip(dominant_colors, color_counts)):
            r, g, b = color
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            percentage = (count / sum(color_counts)) * 100
            print(f"  {i+1}. {hex_color} - 占比: {percentage:.1f}%")
        
        return dominant_colors, color_counts
        
    def find_distinct_secondary_color(self, dominant_colors, color_counts, main_color):
        """找到与主导色有足够区分度的辅助色"""
        # 如果只有一个颜色，使用互补色
        if len(dominant_colors) <= 1:
            print("只有一个主导色，使用互补色作为辅助色")
            r, g, b = main_color
            
            # 转换为HSV，旋转色相
            h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
            
            # 互补色（色相旋转180度）
            h = (h + 0.5) % 1.0
            
            # 如果是低饱和度颜色，增加饱和度以创造更鲜明的对比
            if s < 0.2:
                s = min(1.0, s + 0.4)
            
            # 如果是低亮度颜色，略微提高亮度
            if v < 0.2:
                v = min(1.0, v + 0.3)
            
            # 转回RGB
            r2, g2, b2 = [int(c * 255) for c in colorsys.hsv_to_rgb(h, s, v)]
            
            return (r2, g2, b2)
            
        # 计算每个颜色与主导色的距离
        distances = []
        for i, color in enumerate(dominant_colors):
            if i == 0:  # 跳过主导色自身
                continue
            
            # 计算RGB空间的欧氏距离
            distance = self.calculate_color_distance(main_color, color)
            
            # 转换为HSV计算色相差异
            r1, g1, b1 = main_color
            r2, g2, b2 = color
            h1, s1, v1 = colorsys.rgb_to_hsv(r1/255.0, g1/255.0, b1/255.0)
            h2, s2, v2 = colorsys.rgb_to_hsv(r2/255.0, g2/255.0, b2/255.0)
            
            # 计算色相差异（0-0.5范围）
            hue_diff = min(abs(h1 - h2), 1 - abs(h1 - h2))
            
            # 权重：更重视色相差异，其次是整体距离
            combined_score = (hue_diff * 200) + distance
            
            distances.append((combined_score, color, i))
        
        # 按综合得分排序
        distances.sort(reverse=True)
        
        # 检查最高分的颜色是否有足够的区分度
        if distances and distances[0][0] > 30:
            selected_color = distances[0][1]
            selected_idx = distances[0][2]
            print(f"选择了索引为{selected_idx}的颜色作为辅助色，得分: {distances[0][0]:.1f}")
            return selected_color
            
        # 如果没有足够区分度的颜色，生成一个新的辅助色
        print("无足够区分度的颜色，生成变体作为辅助色")
        r, g, b = main_color
        
        # 转换为HSV以便于操作
        h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        
        # 饱和度和色调偏移，以创建视觉差异
        if s < 0.1:  # 对于接近灰色的颜色
            h = 0.6  # 使用蓝色调
            s = 0.5  # 增加饱和度
        else:
            h = (h + 0.33) % 1.0  # 在色轮上移动120度
            
        # 亮度对比：如果主色暗，辅助色亮一点；反之亦然
        v = 1.0 - v if 0.3 < v < 0.7 else (min(1.0, v + 0.3) if v <= 0.3 else max(0.0, v - 0.3))
        
        # 转回RGB
        r2, g2, b2 = [int(c * 255) for c in colorsys.hsv_to_rgb(h, s, v)]
        
        return (r2, g2, b2)
    
    def calculate_color_distance(self, color1, color2):
        """计算两个颜色之间的距离"""
        r1, g1, b1 = color1
        r2, g2, b2 = color2
        return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5
    
    def calculate_avg_brightness_saturation(self, img, sample_points):
        """计算图像的平均亮度和饱和度"""
        width, height = img.size
        brightness_sum = 0
        saturation_sum = 0
        count = 0
        
        import random
        for _ in range(sample_points):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            try:
                r, g, b, a = img.getpixel((x, y))
                if a > 10:  # 忽略透明像素
                    r, g, b = r/255.0, g/255.0, b/255.0
                    h, s, v = colorsys.rgb_to_hsv(r, g, b)
                    brightness_sum += v
                    saturation_sum += s
                    count += 1
            except:
                pass
        
        if count == 0:
            return 0, 0
        
        return brightness_sum / count, saturation_sum / count
    
    def create_analysis_image(self, main_color, secondary_color, main_percentage, 
                             secondary_percentage, avg_brightness, avg_saturation,
                             dominant_colors, color_counts, total_samples):
        """创建颜色分析图像"""
        # 创建一个白色背景的图像
        width, height = 800, 600
        img = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # 尝试加载字体，如果失败则使用默认字体
        font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts", "方正风雅宋.ttf")
        try:
            title_font = ImageFont.truetype(font_path, 28)
            large_font = ImageFont.truetype(font_path, 20)
            small_font = ImageFont.truetype(font_path, 16)
        except:
            # 如果无法加载字体，使用默认字体
            title_font = ImageFont.load_default()
            large_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # 绘制标题
        draw.text((width//2, 30), "颜色分析报告", fill=(0, 0, 0), font=title_font, anchor="mm")
        
        # 绘制主导色和辅助色信息
        # 主导色
        y_pos = 100
        draw.rectangle([(50, y_pos), (150, y_pos+50)], fill=main_color, outline=(0, 0, 0))
        draw.text((180, y_pos+10), f"主导色: {self.rgb_to_hex(main_color)}", fill=(0, 0, 0), font=large_font)
        draw.text((180, y_pos+35), f"占比: {main_percentage:.1f}%", fill=(0, 0, 0), font=small_font)
        
        # 辅助色
        y_pos = 170
        draw.rectangle([(50, y_pos), (150, y_pos+50)], fill=secondary_color, outline=(0, 0, 0))
        draw.text((180, y_pos+10), f"辅助色: {self.rgb_to_hex(secondary_color)}", fill=(0, 0, 0), font=large_font)
        draw.text((180, y_pos+35), f"占比: {secondary_percentage:.1f}%", fill=(0, 0, 0), font=small_font)
        
        # 绘制平均亮度和饱和度
        y_pos = 250
        draw.text((50, y_pos), f"平均亮度: {avg_brightness:.2f}", fill=(0, 0, 0), font=large_font)
        y_pos += 40
        draw.text((50, y_pos), f"平均饱和度: {avg_saturation:.2f}", fill=(0, 0, 0), font=large_font)
        
        # 绘制亮度和饱和度条
        y_pos = 340
        # 亮度条
        draw.text((50, y_pos), "亮度:", fill=(0, 0, 0), font=small_font)
        draw.rectangle([(120, y_pos), (700, y_pos+20)], outline=(0, 0, 0))
        draw.rectangle([(120, y_pos), (120 + int(580 * avg_brightness), y_pos+20)], 
                      fill=(int(255*avg_brightness), int(255*avg_brightness), int(255*avg_brightness)))
        
        # 饱和度条
        y_pos += 40
        draw.text((50, y_pos), "饱和度:", fill=(0, 0, 0), font=small_font)
        draw.rectangle([(120, y_pos), (700, y_pos+20)], outline=(0, 0, 0))
        
        # 渐变填充饱和度条
        for i in range(580):
            # 创建从灰色到饱和色的渐变
            saturation = i / 580
            r, g, b = colorsys.hsv_to_rgb(colorsys.rgb_to_hsv(*[c/255 for c in main_color])[0], saturation, 0.8)
            draw.line([(120+i, y_pos+1), (120+i, y_pos+19)], 
                     fill=(int(r*255), int(g*255), int(b*255)))
        
        # 标记当前饱和度位置
        marker_pos = 120 + int(580 * avg_saturation)
        draw.polygon([(marker_pos, y_pos-5), (marker_pos-5, y_pos-15), (marker_pos+5, y_pos-15)], fill=(0, 0, 0))
        
        # 绘制颜色分布图
        y_pos = 420
        draw.text((width//2, y_pos), "颜色分布", fill=(0, 0, 0), font=large_font, anchor="mm")
        
        # 绘制色块和百分比
        y_pos += 30
        palette_width = 700
        total_width = 0
        x_pos = 50
        
        for i, (color, count) in enumerate(zip(dominant_colors, color_counts)):
            percentage = (count / total_samples) * 100
            block_width = int((palette_width * percentage) / 100)
            if block_width < 5:  # 确保每个色块至少有最小宽度
                block_width = 5
            
            # 绘制色块
            draw.rectangle([(x_pos, y_pos), (x_pos + block_width, y_pos + 40)], fill=color, outline=(0, 0, 0))
            
            # 如果色块足够宽，在色块上绘制百分比
            if block_width > 30:
                # 检查颜色的亮度，决定文本颜色
                r, g, b = color
                brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                text_color = (0, 0, 0) if brightness > 0.5 else (255, 255, 255)
                draw.text((x_pos + block_width//2, y_pos + 20), f"{percentage:.1f}%", 
                         fill=text_color, font=small_font, anchor="mm")
            
            x_pos += block_width
            total_width += block_width
            
            if total_width >= palette_width or i >= 10:  # 最多显示前10种颜色
                break
        
        return img
    
    def tensor2pil(self, image: torch.Tensor) -> Image.Image:
        """Tensor转换为PIL图像"""
        img = 255. * image.cpu().numpy()[0]
        img = np.clip(img, 0, 255).astype(np.uint8)
        return Image.fromarray(img)
    
    def pil2tensor(self, image: Image.Image) -> torch.Tensor:
        """PIL图像转换为Tensor"""
        img_np = np.array(image).astype(np.float32) / 255.0
        # 添加批次维度并转换为BCHW格式
        img_tensor = torch.from_numpy(img_np).unsqueeze(0)
        # 如果图像是RGB，则转换为CHW格式
        if len(img_tensor.shape) == 3:
            img_tensor = img_tensor.permute(0, 3, 1, 2)
        return img_tensor

    def rgb_to_hex(self, rgb: tuple) -> str:
        """RGB转十六进制"""
        return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])


class PIPColorWheel:
    """PIP 色轮节点"""
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "color": ("STRING", {"default": "#ff0000", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("互补色", "类似色", "三等分色", "分裂互补色", "单色调", "配色方案图")
    FUNCTION = "process"
    CATEGORY = "PIP"

    def process(self, color):
        # 打印输入的颜色，用于调试
        print(f"输入的颜色: {color}")
        
        # 解析输入的十六进制颜色
        try:
            # 确保颜色格式正确（以#开头）
            if not color.startswith('#'):
                color = '#' + color
                
            r, g, b = self.hex_to_rgb(color)
            print(f"解析后的RGB: {r}, {g}, {b}")
        except Exception as e:
            # 如果解析失败，使用黑色作为默认值
            print(f"颜色解析错误: {e}")
            r, g, b = 0, 0, 0
        
        # 转换为HSV
        h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        print(f"HSV值: {h}, {s}, {v}")
        
        # 特殊处理黑色和接近黑色的情况
        # 如果亮度太低(接近黑色)，适当提高亮度以显示色相差异
        is_very_dark = v < 0.1
        if is_very_dark:
            v_adjusted = 0.3  # 提供一个基本亮度以显示色相
        else:
            v_adjusted = v
            
        # 特殊处理白色和接近白色的情况
        # 如果饱和度太低(接近白色)，适当提高饱和度以显示色相
        is_very_unsaturated = s < 0.1
        if is_very_unsaturated:
            s_adjusted = 0.5  # 提供一个基本饱和度以显示色相
            # 对于接近白色的情况，使用一个默认的色相值，除非已经有色相
            if r == g == b:  # 灰度颜色
                h = 0.0  # 默认使用红色作为基准色相
        else:
            s_adjusted = s
        
        # 计算互补色 (对面的颜色，色相差180°)
        complementary = self.hsv_to_hex((h + 0.5) % 1.0, 
                                       s_adjusted if is_very_unsaturated else s, 
                                       v_adjusted if is_very_dark else v)
        
        # 计算类似色 (相邻的颜色，色相差30°)
        analogous = self.hsv_to_hex((h + 0.083) % 1.0, 
                                   s_adjusted if is_very_unsaturated else s, 
                                   v_adjusted if is_very_dark else v)
        
        # 计算三等分色 (色相差120°)
        triadic = self.hsv_to_hex((h + 0.333) % 1.0, 
                                 s_adjusted if is_very_unsaturated else s, 
                                 v_adjusted if is_very_dark else v)
        
        # 计算分裂互补色 (与互补色相邻的颜色，色相差150°)
        split_complementary = self.hsv_to_hex((h + 0.417) % 1.0, 
                                             s_adjusted if is_very_unsaturated else s, 
                                             v_adjusted if is_very_dark else v)
        
        # 计算单色调 (相同色相，不同饱和度和亮度)
        # 对于黑色或白色，确保单色调有一些可见的变化
        if is_very_dark or is_very_unsaturated:
            mono_s = max(0.4, s_adjusted * 0.8)
            mono_v = max(0.4, v_adjusted * 0.8)
        else:
            mono_s = max(0.1, s * 0.6)
            mono_v = min(0.95, v * 1.2)
            
        monochromatic = self.hsv_to_hex(h, mono_s, mono_v)
        
        # 打印所有生成的颜色，用于调试
        print(f"互补色: {complementary}")
        print(f"类似色: {analogous}")
        print(f"三等分色: {triadic}")
        print(f"分裂互补色: {split_complementary}")
        print(f"单色调: {monochromatic}")
        
        # 创建颜色图
        color_image = self.create_color_image(
            color, 
            complementary, 
            analogous, 
            triadic, 
            split_complementary, 
            monochromatic
        )
        
        return (complementary, analogous, triadic, split_complementary, monochromatic, color_image)
    
    def hex_to_rgb(self, hex_color):
        """十六进制转RGB"""
        hex_color = hex_color.lstrip('#')
        # 确保hex_color是6位长度
        if len(hex_color) == 3:
            # 如果是短格式(#RGB)，转换为标准格式(#RRGGBB)
            hex_color = ''.join([c*2 for c in hex_color])
        elif len(hex_color) != 6:
            # 如果长度不是6，则使用黑色
            hex_color = '000000'
            
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            # 如果转换失败，返回黑色
            return (0, 0, 0)
    
    def hsv_to_hex(self, h, s, v):
        """HSV转十六进制"""
        try:
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            # 将[0,1]的RGB值转换为[0,255]的整数RGB值
            r, g, b = [int(c * 255) for c in [r, g, b]]
            # 确保RGB值在有效范围内
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            # 转换为十六进制
            return f'#{r:02x}{g:02x}{b:02x}'
        except Exception as e:
            print(f"HSV转HEX错误: {e}, 输入HSV: {h}, {s}, {v}")
            return '#000000'  # 错误时返回黑色
        
    def create_color_image(self, input_color, complementary, analogous, triadic, split_complementary, monochromatic):
        """创建颜色图"""
        # 创建一个白色背景的图像
        width, height = 600, 600
        img = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # 尝试加载字体
        font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts", "方正风雅宋.ttf")
        try:
            title_font = ImageFont.truetype(font_path, 28)
            color_font = ImageFont.truetype(font_path, 20)
        except:
            # 如果无法加载字体，使用默认字体
            title_font = ImageFont.load_default()
            color_font = ImageFont.load_default()
        
        # 绘制标题
        draw.text((width//2, 40), "色轮配色", fill=(0, 0, 0), font=title_font, anchor="mm")
        
        # 定义颜色块的参数
        block_height = 60
        block_width = 200
        label_width = 150
        total_width = block_width + label_width
        x_start = (width - total_width) // 2
        
        # 绘制输入色
        y_pos = 100
        draw.text((x_start, y_pos), "输入色:", fill=(0, 0, 0), font=color_font)
        input_rgb = self.hex_to_rgb(input_color)
        draw.rectangle([(x_start + label_width, y_pos), (x_start + label_width + block_width, y_pos + block_height)], 
                       fill=input_rgb, outline=(0, 0, 0))
        draw.text((x_start + label_width + block_width//2, y_pos + block_height + 15), input_color, 
                  fill=(0, 0, 0), font=color_font, anchor="mm")
        
        # 绘制互补色
        y_pos += block_height + 40
        draw.text((x_start, y_pos), "互补色:", fill=(0, 0, 0), font=color_font)
        complementary_rgb = self.hex_to_rgb(complementary)
        draw.rectangle([(x_start + label_width, y_pos), (x_start + label_width + block_width, y_pos + block_height)], 
                       fill=complementary_rgb, outline=(0, 0, 0))
        draw.text((x_start + label_width + block_width//2, y_pos + block_height + 15), complementary, 
                  fill=(0, 0, 0), font=color_font, anchor="mm")
        
        # 绘制类似色
        y_pos += block_height + 40
        draw.text((x_start, y_pos), "类似色:", fill=(0, 0, 0), font=color_font)
        analogous_rgb = self.hex_to_rgb(analogous)
        draw.rectangle([(x_start + label_width, y_pos), (x_start + label_width + block_width, y_pos + block_height)], 
                       fill=analogous_rgb, outline=(0, 0, 0))
        draw.text((x_start + label_width + block_width//2, y_pos + block_height + 15), analogous, 
                  fill=(0, 0, 0), font=color_font, anchor="mm")
        
        # 绘制三等分色
        y_pos += block_height + 40
        draw.text((x_start, y_pos), "三等分色:", fill=(0, 0, 0), font=color_font)
        triadic_rgb = self.hex_to_rgb(triadic)
        draw.rectangle([(x_start + label_width, y_pos), (x_start + label_width + block_width, y_pos + block_height)], 
                       fill=triadic_rgb, outline=(0, 0, 0))
        draw.text((x_start + label_width + block_width//2, y_pos + block_height + 15), triadic, 
                  fill=(0, 0, 0), font=color_font, anchor="mm")
        
        # 绘制分裂互补色
        y_pos += block_height + 40
        draw.text((x_start, y_pos), "分裂互补色:", fill=(0, 0, 0), font=color_font)
        split_complementary_rgb = self.hex_to_rgb(split_complementary)
        draw.rectangle([(x_start + label_width, y_pos), (x_start + label_width + block_width, y_pos + block_height)], 
                       fill=split_complementary_rgb, outline=(0, 0, 0))
        draw.text((x_start + label_width + block_width//2, y_pos + block_height + 15), split_complementary, 
                  fill=(0, 0, 0), font=color_font, anchor="mm")
        
        # 绘制单色调
        y_pos += block_height + 40
        draw.text((x_start, y_pos), "单色调:", fill=(0, 0, 0), font=color_font)
        monochromatic_rgb = self.hex_to_rgb(monochromatic)
        draw.rectangle([(x_start + label_width, y_pos), (x_start + label_width + block_width, y_pos + block_height)], 
                       fill=monochromatic_rgb, outline=(0, 0, 0))
        draw.text((x_start + label_width + block_width//2, y_pos + block_height + 15), monochromatic, 
                  fill=(0, 0, 0), font=color_font, anchor="mm")
        
        # 转换为Tensor
        return self.pil2tensor(img)
    
    def pil2tensor(self, image: Image.Image) -> torch.Tensor:
        """PIL图像转换为Tensor"""
        img_np = np.array(image).astype(np.float32) / 255.0
        # 添加批次维度并转换为BCHW格式
        img_tensor = torch.from_numpy(img_np).unsqueeze(0)
        # 如果图像是RGB，则转换为CHW格式
        if len(img_tensor.shape) == 3:
            img_tensor = img_tensor.permute(0, 3, 1, 2)
        return img_tensor

# 节点注册
NODE_CLASS_MAPPINGS = {
    "PIPAdvancedColorAnalyzer": PIPAdvancedColorAnalyzer,
    "PIPColorWheel": PIPColorWheel
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PIPAdvancedColorAnalyzer": "🎨 PIP 高级颜色分析",
    "PIPColorWheel": "🔄 PIP 色轮"
}

import torch
import numpy as np
from PIL import Image

def tensor_to_pil(tensor):
    """
    Convert a PyTorch tensor to a PIL Image.
    Uses ComfyUI's standard BHWC format with values in [0,1].
    
    Args:
        tensor: PyTorch tensor in BHWC format with values in [0,1]
        
    Returns:
        PIL.Image object
    """
    # Handle different tensor shapes
    if tensor.ndim == 4:
        # BHWC format - take first image if batched
        tensor = tensor[0]
    
    # Convert to numpy and scale to [0, 255]
    img_np = (tensor.cpu().numpy() * 255.0).astype(np.uint8)
    
    # Create appropriate PIL image based on number of channels
    if img_np.shape[2] == 4:  # RGBA
        img = Image.fromarray(img_np, 'RGBA')
    elif img_np.shape[2] == 3:  # RGB
        img = Image.fromarray(img_np, 'RGB')
    elif img_np.shape[2] == 1:  # Grayscale
        img = Image.fromarray(img_np.squeeze(2), 'L')
    else:
        raise ValueError(f"Unsupported tensor shape: {tensor.shape}")
    
    return img

def pil_to_tensor(img):
    """
    Convert a PIL Image to a PyTorch tensor.
    Returns tensor in ComfyUI's standard BHWC format with float32 [0,1] range.
    
    Args:
        img: PIL Image
        
    Returns:
        PyTorch tensor in BHWC format with float32 [0,1] range
    """
    # 添加类型检查以避免元组错误
    if isinstance(img, tuple):
        print("[警告] pil_to_tensor接收到元组而不是PIL图像，正在提取第一个元素")
        if len(img) > 0 and hasattr(img[0], 'mode'):
            img = img[0]  # 尝试使用元组的第一个元素
        else:
            print("[错误] 无法从元组中提取有效图像")
            # 创建一个1x1的黑色图像作为后备方案
            img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    
    # 检查是否是PIL图像对象
    if not hasattr(img, 'mode'):
        print(f"[错误] 无效的图像对象类型: {type(img)}")
        # 创建一个1x1的黑色图像作为后备方案
        img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        
    # Convert to RGB or RGBA if needed
    if img.mode not in ('RGB', 'RGBA'):
        if 'A' in img.mode:
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')
    
    # Convert to numpy array and normalize to [0, 1]
    img_np = np.array(img).astype(np.float32) / 255.0
    
    # Add batch dimension for BHWC format
    tensor = torch.from_numpy(img_np).unsqueeze(0)
    
    return tensor

def create_alpha_mask(tensor):
    """
    Create a single-channel alpha mask from an RGBA tensor.
    
    Args:
        tensor: PyTorch tensor in BHWC format with RGBA channels
        
    Returns:
        Alpha mask tensor in BHWC format with a single channel
    """
    if tensor.shape[3] != 4:
        return None
    
    # Extract alpha channel and keep batch dimension
    alpha = tensor[:, :, :, 3:4]
    
    return alpha

def clean_alpha_mask(mask_tensor):
    """
    Clean up alpha mask by removing any semi-transparent pixels.
    
    Args:
        mask_tensor: Alpha mask tensor in BHWC format (B, H, W, 1)
        
    Returns:
        Cleaned alpha mask tensor (B, H, W, 1)
    """
    if mask_tensor is None:
        return None
    
    # Threshold the mask to make it binary
    threshold = 0.05
    cleaned_mask = (mask_tensor > threshold).float()
    
    return cleaned_mask

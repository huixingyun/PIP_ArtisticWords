import numpy as np
from PIL import Image
import torch

def pil2tensor(image):
    """
    Convert a PIL Image to a PyTorch tensor in BHWC format.
    
    Args:
        image: PIL.Image object
        
    Returns:
        PyTorch tensor in BHWC format with float32 [0,1] range
    """
    # Convert to numpy array
    if image.mode == 'RGBA':
        # Handle RGBA images
        rgb_image = Image.new('RGB', image.size, (0, 0, 0))
        rgb_image.paste(image, mask=image.split()[3])  # Use alpha as mask
        
        # Create the RGB part
        img = np.array(rgb_image).astype(np.float32) / 255.0
        
        # Create the alpha part
        alpha = np.array(image.split()[3]).astype(np.float32) / 255.0
        
        # Add batch dimension and expand alpha to 3D
        img_tensor = torch.from_numpy(img).unsqueeze(0)
        alpha_tensor = torch.from_numpy(alpha).unsqueeze(0).unsqueeze(-1)
        
        return img_tensor, alpha_tensor
    else:
        # Handle RGB images (or convert to RGB)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array, scale to [0, 1]
        img = np.array(image).astype(np.float32) / 255.0
        
        # Add batch dimension
        img_tensor = torch.from_numpy(img).unsqueeze(0)
        
        return img_tensor, None

def tensor2pil(tensor):
    """
    Convert a PyTorch tensor to a PIL Image.
    
    Args:
        tensor: PyTorch tensor in BHWC format with values in [0,1]
        
    Returns:
        PIL.Image object
    """
    # Remove batch dimension
    if len(tensor.shape) == 4:
        tensor = tensor.squeeze(0)
    
    # Convert to numpy, scale to [0, 255], and convert to uint8
    img_np = (tensor.cpu().numpy() * 255.0).astype(np.uint8)
    
    # Convert to PIL Image
    if img_np.shape[-1] == 4:  # RGBA
        img = Image.fromarray(img_np, 'RGBA')
    elif img_np.shape[-1] == 3:  # RGB
        img = Image.fromarray(img_np, 'RGB')
    elif img_np.shape[-1] == 1:  # Gray
        img = Image.fromarray(img_np.squeeze(-1), 'L')
    else:
        raise ValueError(f"Unsupported tensor shape: {tensor.shape}")
    
    return img

def alpha_to_mask(alpha_tensor):
    """
    Convert an alpha channel tensor to a mask tensor.
    
    Args:
        alpha_tensor: Alpha channel tensor (B, H, W, 1)
        
    Returns:
        Mask tensor (B, H, W, 1)
    """
    if alpha_tensor is None:
        return None
    
    # Ensure proper shape
    if len(alpha_tensor.shape) == 3:
        alpha_tensor = alpha_tensor.unsqueeze(-1)
    
    # Already in correct format (B, H, W, 1) with values in [0,1]
    return alpha_tensor

def overlay_text_on_image(base_image, text_image, alpha=None):
    """
    Overlay text image on base image.
    
    Args:
        base_image: PIL.Image base image
        text_image: PIL.Image text to overlay
        alpha: Optional alpha channel for text_image
        
    Returns:
        PIL.Image with text overlaid
    """
    # Ensure images are same size
    if base_image.size != text_image.size:
        text_image = text_image.resize(base_image.size, Image.LANCZOS)
    
    # If alpha provided, use it for compositing
    if alpha is not None:
        # Convert alpha to PIL image mask
        alpha_img = Image.fromarray((alpha.squeeze().cpu().numpy() * 255.0).astype(np.uint8), 'L')
        
        # Resize alpha if needed
        if alpha_img.size != base_image.size:
            alpha_img = alpha_img.resize(base_image.size, Image.LANCZOS)
        
        # Composite using alpha as mask
        result = base_image.copy()
        result.paste(text_image, (0, 0), alpha_img)
    else:
        # Use text image's alpha channel if it's RGBA
        if text_image.mode == 'RGBA':
            result = base_image.copy()
            result.paste(text_image, (0, 0), text_image)
        else:
            # Fallback to simple alpha blend
            result = Image.blend(base_image, text_image, 0.7)
    
    return result

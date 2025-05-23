from ..core.style_manager import StyleManager

# Initialize StyleManager instance for global use
style_manager = StyleManager(verbose=False)
style_names = style_manager.get_style_names()

__all__ = ['style_names']

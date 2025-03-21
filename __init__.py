import os
import sys

# Add the current directory to sys.path to ensure modules can be found
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import node classes
from .nodes.artistic_text_node import ArtisticTextNode
from .nodes.preview_node import TextPreviewNode
from .nodes.svg_recorder_node import PIPSVGRecorder
from .nodes.PIP_artistic_words_fusion import PIPArtisticWordsFusion
from .nodes.PIP_ColorPicker import PIPColorPicker
from .nodes.PIP_AdvancedColorAnalyzer import PIPAdvancedColorAnalyzer, PIPColorWheel

# Node mapping for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PIP Artistic Text Generator": ArtisticTextNode,
    "PIP Text Preview": TextPreviewNode,
    "PIP SVG Recorder": PIPSVGRecorder,
    "PIP ArtisticWords Fusion": PIPArtisticWordsFusion,
    "PIP ColorPicker": PIPColorPicker,
    "PIPAdvancedColorAnalyzer": PIPAdvancedColorAnalyzer,
    "PIPColorWheel": PIPColorWheel
}

# Display names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "PIP Artistic Text Generator": "PIP Artistic Text Generator",
    "PIP Text Preview": "PIP Text Preview",
    "PIP SVG Recorder": "PIP SVG Recorder",
    "PIP ArtisticWords Fusion": "PIP ArtisticWords Fusion",
    "PIP ColorPicker": "🔴 PIP 颜色拾取",
    "PIPAdvancedColorAnalyzer": "📊 PIP 高级颜色分析",
    "PIPColorWheel": "🎨 PIP 色轮"
}

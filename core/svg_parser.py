"""
SVG Parser Module for PIP_ArtisticWords
This module handles parsing SVG files exported from Sketch and extracting style information.
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Tuple, Optional
import logging
import math

# Register the SVG namespace for ElementTree
ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SVGParser:
    """Parser for SVG files exported from Sketch with artistic text styles."""
    
    def __init__(self, svg_path: str):
        """
        Initialize the SVG parser with the path to an SVG file.
        
        Args:
            svg_path: Path to the SVG file
        """
        self.svg_path = svg_path
        self.root = None
        self.namespaces = {
            'svg': 'http://www.w3.org/2000/svg',
            'xlink': 'http://www.w3.org/1999/xlink'
        }
        self.parsed_data = {
            'gradients': {},
            'filters': {},
            'text_elements': [],
            'uses': [],
            'defs': {}  # Added dedicated storage for defs
        }
        
        self._parse_svg()
    
    def _parse_svg(self) -> None:
        """Parse the SVG file and extract the XML root element."""
        try:
            tree = ET.parse(self.svg_path)
            self.root = tree.getroot()
            logger.info(f"Successfully parsed SVG file: {self.svg_path}")
        except Exception as e:
            logger.error(f"Failed to parse SVG file: {e}")
            raise ValueError(f"Failed to parse SVG file: {e}")
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse the SVG file and extract all style information.
        This is a convenience method that calls extract_styles.
        
        Returns:
            Dictionary containing all extracted style information
        """
        return self.extract_styles()
    
    def extract_styles(self) -> Dict[str, Any]:
        """
        Extract all style information from the SVG file.
        
        Returns:
            Dictionary containing all extracted style information
        """
        if not self.root:
            raise ValueError("SVG file not parsed yet")
        
        # Extract all style components
        self._extract_defs()  # Extract defs first as other elements may reference them
        self._extract_gradients()
        self._extract_filters()
        self._extract_text_elements()
        self._extract_uses()
        
        logger.info(f"Extracted styles from SVG: {self.svg_path}")
        return self.parsed_data
    
    def _extract_defs(self) -> None:
        """Extract all definitions from the SVG file's defs section."""
        defs_elements = self.root.findall('.//svg:defs', self.namespaces)
        if not defs_elements:
            logger.warning("No defs section found in SVG file")
            return
            
        # Process each defs section
        for defs in defs_elements:
            # Process each child of the defs element
            for child in defs:
                # Get the tag name without namespace
                tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                child_id = child.get('id')
                
                if not child_id:
                    continue
                    
                # Store the element attributes
                element_data = {
                    'type': tag_name,
                    'attributes': {k: v for k, v in child.attrib.items()}
                }
                
                # Process children if any
                if len(child) > 0:
                    element_data['children'] = []
                    for subchild in child:
                        subtag = subchild.tag.split('}')[-1] if '}' in subchild.tag else subchild.tag
                        element_data['children'].append({
                            'type': subtag,
                            'attributes': {k: v for k, v in subchild.attrib.items()}
                        })
                
                # Store in the defs dictionary
                self.parsed_data['defs'][child_id] = element_data
                
        logger.debug(f"Extracted {len(self.parsed_data['defs'])} definitions from defs")
    
    def _extract_gradients(self) -> None:
        """Extract gradient definitions from the SVG file."""
        # Find all linearGradient elements
        for gradient in self.root.findall('.//svg:linearGradient', self.namespaces):
            gradient_id = gradient.get('id')
            stops = []
            
            # Get gradient attributes
            x1 = self._parse_percentage(gradient.get('x1', '0%'))
            y1 = self._parse_percentage(gradient.get('y1', '0%'))
            x2 = self._parse_percentage(gradient.get('x2', '100%'))
            y2 = self._parse_percentage(gradient.get('y2', '100%'))
            
            # Extract stops
            for stop in gradient.findall('.//svg:stop', self.namespaces):
                color = stop.get('stop-color', '#000000')
                offset = self._parse_percentage(stop.get('offset', '0%'))
                opacity = float(stop.get('stop-opacity', '1'))
                stops.append({
                    'color': color,
                    'offset': offset,
                    'opacity': opacity
                })
            
            # Calculate direction and angle from coordinates
            direction, angle = self._calculate_gradient_direction(x1, y1, x2, y2)
            
            self.parsed_data['gradients'][gradient_id] = {
                'type': 'linear',
                'x1': x1,
                'y1': y1,
                'x2': x2,
                'y2': y2,
                'stops': stops,
                'direction': direction,
                'angle': angle
            }
            
            logger.debug(f"Extracted gradient: {gradient_id}")
    
    def _extract_filters(self) -> None:
        """Extract filter definitions from the SVG file."""
        for filter_elem in self.root.findall('.//svg:filter', self.namespaces):
            filter_id = filter_elem.get('id')
            filter_info = {
                'id': filter_id,
                'filterUnits': filter_elem.get('filterUnits', 'objectBoundingBox'),
                'width': self._parse_percentage(filter_elem.get('width', '100%')),
                'height': self._parse_percentage(filter_elem.get('height', '100%')),
                'x': self._parse_percentage(filter_elem.get('x', '0%')),
                'y': self._parse_percentage(filter_elem.get('y', '0%')),
                'children': []  # Changed from 'effects' to 'children' to match reference in style converter
            }
            
            # Process filter effects
            for effect in filter_elem:
                effect_type = effect.tag.split('}')[-1]  # Remove namespace prefix
                effect_info = {
                    'type': effect_type,  # Changed from 'name' to 'type' to match style converter expectations
                }
                
                # Extract all attributes
                for key, value in effect.attrib.items():
                    # Handle namespaced attributes
                    attr_name = key.split('}')[-1] if '}' in key else key
                    effect_info[attr_name] = value
                
                # Add to the filter's children list
                filter_info['children'].append(effect_info)
            
            self.parsed_data['filters'][filter_id] = filter_info
            logger.debug(f"Extracted filter: {filter_id}")
    
    def _extract_text_elements(self) -> None:
        """Extract text elements and their properties from the SVG file."""
        for text_elem in self.root.findall('.//svg:text', self.namespaces):
            text_id = text_elem.get('id', '')
            font_family = text_elem.get('font-family', 'Arial')
            font_size = text_elem.get('font-size', '16')
            font_weight = text_elem.get('font-weight', 'normal')
            line_spacing = text_elem.get('line-spacing', '0')
            
            # Clean up font family name (remove fallbacks)
            if ',' in font_family:
                font_family = font_family.split(',')[0].strip()
            
            # Remove suffixes like "-Regular" from font name
            if '-' in font_family:
                cleaned_font = font_family.split('-')[0].strip()
                font_variant = font_family.split('-')[-1].strip().lower()
                if font_variant in ['regular', 'bold', 'italic', 'light', 'medium']:
                    font_family = cleaned_font
            
            text_info = {
                'id': text_id,
                'font_family': font_family,
                'font_size': self._parse_unit_value(font_size),
                'font_weight': font_weight,
                'line_spacing': self._parse_unit_value(line_spacing) if line_spacing else 0,
                'tspans': [],
                'content': ''
            }
            
            # Extract tspan elements for multi-line text
            full_text = ""
            for tspan in text_elem.findall('.//svg:tspan', self.namespaces):
                x = self._parse_unit_value(tspan.get('x', '0'))
                y = self._parse_unit_value(tspan.get('y', '0'))
                text_content = tspan.text or ""
                
                text_info['tspans'].append({
                    'x': x,
                    'y': y,
                    'text': text_content
                })
                
                full_text += text_content + "\n"
            
            # Remove trailing newline
            if full_text.endswith("\n"):
                full_text = full_text[:-1]
                
            text_info['content'] = full_text
            self.parsed_data['text_elements'].append(text_info)
            logger.debug(f"Extracted text element: {text_id}")
    
    def _extract_uses(self) -> None:
        """Extract 'use' elements which reference and style other elements."""
        for use in self.root.findall('.//svg:use', self.namespaces):
            href = use.get('{http://www.w3.org/1999/xlink}href', '')
            if not href:
                continue
            
            # Remove the '#' prefix from href (e.g., '#text-3' -> 'text-3')
            if href.startswith('#'):
                href = href[1:]
            
            use_info = {
                'href': href,
                'fill': use.get('fill', None),
                'fill_opacity': use.get('fill-opacity', 1),
                'stroke': use.get('stroke', None),
                'stroke_width': self._parse_unit_value(use.get('stroke-width', '0')),
                'stroke_opacity': float(use.get('stroke-opacity', '1')),
                'filter': None
            }
            
            # Extract filter reference
            filter_url = use.get('filter', '')
            if filter_url:
                # Extract filter ID from 'url(#filter-id)'
                match = re.search(r'url\(#([^)]+)\)', filter_url)
                if match:
                    use_info['filter'] = match.group(1)
            
            self.parsed_data['uses'].append(use_info)
            logger.debug(f"Extracted use element referencing: {href}")
    
    @staticmethod
    def _parse_percentage(value: str) -> float:
        """
        Parse a percentage value to a float between 0 and 1.
        
        Args:
            value: Percentage string (e.g., '50%')
            
        Returns:
            Float between 0 and 1
        """
        if not value:
            return 0.0
            
        if value.endswith('%'):
            return float(value.rstrip('%')) / 100.0
        return float(value)
    
    @staticmethod
    def _parse_unit_value(value: str) -> float:
        """
        Parse a CSS unit value to a float.
        
        Args:
            value: CSS unit value (e.g., '16px', '2em')
            
        Returns:
            Float value
        """
        if not value:
            return 0.0
            
        # Extract numeric part
        match = re.match(r'([0-9.]+)([a-z%]*)', value)
        if match:
            num_value = float(match.group(1))
            unit = match.group(2)
            
            # We ignore units for now and just return the numeric value
            # In a real implementation, you might want to convert different units
            return num_value
        
        try:
            return float(value)
        except ValueError:
            return 0.0
    
    @staticmethod
    def _calculate_gradient_direction(x1: float, y1: float, x2: float, y2: float) -> Tuple[str, float]:
        """
        Calculate the gradient direction and angle from coordinate points.
        
        Args:
            x1, y1: Start point coordinates (0-1)
            x2, y2: End point coordinates (0-1)
            
        Returns:
            Tuple of (direction_name, angle_in_degrees)
        """
        # Standard directions
        if x1 == 0.5 and y1 == 0 and x2 == 0.5 and y2 == 1:
            return "top_bottom", 180
        elif x1 == 0.5 and y1 == 1 and x2 == 0.5 and y2 == 0:
            return "bottom_top", 0
        elif x1 == 0 and y1 == 0.5 and x2 == 1 and y2 == 0.5:
            return "left_right", 90
        elif x1 == 1 and y1 == 0.5 and x2 == 0 and y2 == 0.5:
            return "right_left", 270
        
        # Diagonal directions
        elif x1 == 0 and y1 == 0 and x2 == 1 and y2 == 1:
            return "diagonal", 45
        elif x1 == 1 and y1 == 0 and x2 == 0 and y2 == 1:
            return "diagonal_reverse", 135
        elif x1 == 0 and y1 == 1 and x2 == 1 and y2 == 0:
            return "diagonal_bottom", 315
        elif x1 == 1 and y1 == 1 and x2 == 0 and y2 == 0:
            return "diagonal_bottom_reverse", 225
        
        # Custom angle calculation
        else:
            dx = x2 - x1
            dy = y2 - y1
            angle_rad = math.atan2(dy, dx)
            angle_deg = math.degrees(angle_rad)
            
            # Convert to positive angle (0-360)
            if angle_deg < 0:
                angle_deg += 360
                
            return "custom", angle_deg

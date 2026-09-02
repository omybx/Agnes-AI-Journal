#!/usr/bin/env python3
"""
ASCII Mandala Generator with Color Options
===========================================
Generates beautiful ASCII mandalas with configurable patterns, colors, and sizes.
Supports ANSI color codes for terminal display and multiple symmetry types.
"""

import math
import random
import sys
import argparse
from typing import List, Tuple, Optional

# ANSI Color Codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright foreground
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # 256-color mode (for gradient support)
    @staticmethod
    def fg_256(code: int) -> str:
        return f'\033[38;5;{code}m'
    
    @staticmethod
    def bg_256(code: int) -> str:
        return f'\033[48;5;{code}m'
    
    # True color (24-bit)
    @staticmethod
    def fg_rgb(r: int, g: int, b: int) -> str:
        return f'\033[38;2;{r};{g};{b}m'
    
    @staticmethod
    def bg_rgb(r: int, g: int, b: int) -> str:
        return f'\033[48;2;{r};{g};{b}m'

# Color palettes
PALETTES = {
    'rainbow': [
        Colors.RED, Colors.YELLOW, Colors.GREEN, Colors.CYAN, 
        Colors.BLUE, Colors.MAGENTA, Colors.BRIGHT_RED
    ],
    'ocean': [
        Colors.BLUE, Colors.CYAN, Colors.BRIGHT_CYAN, Colors.BRIGHT_BLUE,
        Colors.BLUE, Colors.MAGENTA, Colors.BRIGHT_MAGENTA
    ],
    'fire': [
        Colors.RED, Colors.YELLOW, Colors.BRIGHT_YELLOW, Colors.BRIGHT_RED,
        Colors.MAGENTA, Colors.RED, Colors.BRIGHT_RED
    ],
    'forest': [
        Colors.GREEN, Colors.BRIGHT_GREEN, Colors.YELLOW, Colors.BRIGHT_YELLOW,
        Colors.CYAN, Colors.GREEN, Colors.BRIGHT_BLACK
    ],
    'sunset': [
        Colors.RED, Colors.BRIGHT_RED, Colors.YELLOW, Colors.BRIGHT_YELLOW,
        Colors.MAGENTA, Colors.BRIGHT_MAGENTA, Colors.RED
    ],
    'monochrome': [
        Colors.WHITE, Colors.BRIGHT_BLACK, Colors.BLACK, Colors.BRIGHT_WHITE,
        Colors.BRIGHT_BLACK, Colors.WHITE, Colors.BLACK
    ],
    'pastel': [
        Colors.fg_rgb(255, 179, 186),  # pink
        Colors.fg_rgb(255, 223, 186),  # peach
        Colors.fg_rgb(255, 255, 186),  # light yellow
        Colors.fg_rgb(186, 255, 201),  # mint
        Colors.fg_rgb(186, 225, 255),  # light blue
        Colors.fg_rgb(215, 186, 255),  # lavender
        Colors.fg_rgb(255, 186, 250),  # light pink
    ],
    'neon': [
        Colors.fg_rgb(255, 0, 255),    # neon magenta
        Colors.fg_rgb(0, 255, 255),    # neon cyan
        Colors.fg_rgb(255, 255, 0),    # neon yellow
        Colors.fg_rgb(0, 255, 0),      # neon green
        Colors.fg_rgb(255, 128, 0),    # neon orange
        Colors.fg_rgb(128, 0, 255),    # neon purple
        Colors.fg_rgb(255, 0, 128),    # neon pink
    ],
    'earth': [
        Colors.fg_rgb(139, 69, 19),    # saddle brown
        Colors.fg_rgb(160, 82, 45),    # sienna
        Colors.fg_rgb(205, 133, 63),   # peru
        Colors.fg_rgb(210, 180, 140),  # tan
        Colors.fg_rgb(188, 143, 143),  # rosy brown
        Colors.fg_rgb(139, 137, 137),  # gray
        Colors.fg_rgb(105, 105, 105),  # dim gray
    ],
}

# ASCII characters for different densities
CHAR_SETS = {
    'dense': '█▓▒░·',
    'medium': '█▓▒░:.',
    'sparse': '▓▒░:-. ',
    'dots': '●○•· ',
    'geometric': '◆◇◈◊◎●○◐◑◒◓',
    'flowers': '✿✾✽❀❁❃❇❈❉❊❋',
    'stars': '★☆✦✧✩✪✫✬✭✮✯✰',
    'mandala': '○●◎◉◐◑◒◓◔◕◴◵◶◷',
}

class MandalaGenerator:
    def __init__(
        self,
        width: int = 80,
        height: int = 40,
        symmetry: int = 8,
        palette: str = 'rainbow',
        char_set: str = 'mandala',
        center_char: str = '●',
        bg_char: str = ' ',
        animate: bool = False,
        frames: int = 30,
    ):
        self.width = width
        self.height = height
        self.symmetry = symmetry
        self.palette_name = palette
        self.palette = PALETTES.get(palette, PALETTES['rainbow'])
        self.chars = CHAR_SETS.get(char_set, CHAR_SETS['mandala'])
        self.center_char = center_char
        self.bg_char = bg_char
        self.animate = animate
        self.frames = frames
        self.center_x = width // 2
        self.center_y = height // 2
        self.max_radius = min(width, height) // 2 - 2
        
    def _get_color_for_radius(self, radius: float, max_radius: float, frame: int = 0) -> str:
        """Get color based on radius with optional animation."""
        if not self.palette:
            return Colors.WHITE
        
        # Normalize radius to 0-1
        norm = min(radius / max_radius, 1.0)
        
        # Add animation offset
        if self.animate:
            norm = (norm + frame * 0.05) % 1.0
        
        # Map to palette index
        idx = int(norm * (len(self.palette) - 1))
        return self.palette[idx]
    
    def _get_char_for_density(self, density: float) -> str:
        """Get character based on density (0-1)."""
        idx = int(density * (len(self.chars) - 1))
        return self.chars[min(idx, len(self.chars) - 1)]
    
    def _calculate_pattern(self, x: int, y: int, frame: int = 0) -> Tuple[float, float]:
        """Calculate pattern value for a point. Returns (radius, density)."""
        dx = x - self.center_x
        dy = y - self.center_y
        radius = math.sqrt(dx*dx + dy*dy)
        
        if radius == 0:
            return 0.0, 1.0
        
        angle = math.atan2(dy, dx)
        
        # Base mandala pattern with multiple frequency components
        pattern = 0.0
        
        # Radial waves
        pattern += math.sin(radius * 0.3 + frame * 0.1) * 0.3
        
        # Angular symmetry
        pattern += math.sin(angle * self.symmetry + frame * 0.05) * 0.4
        
        # Concentric rings
        pattern += math.sin(radius * 0.5) * 0.2
        
        # Spiral arms
        pattern += math.sin(radius * 0.2 - angle * self.symmetry * 0.5 + frame * 0.08) * 0.2
        
        # Petal-like structures
        pattern += math.sin(angle * self.symmetry * 2 + radius * 0.1) * 0.15
        
        # Normalize to 0-1
        density = (pattern + 1.5) / 3.0
        density = max(0.0, min(1.0, density))
        
        return radius, density
    
    def _calculate_kaleidoscope(self, x: int, y: int, frame: int = 0) -> Tuple[float, float]:
        """Kaleidoscope-style pattern with mirror symmetry."""
        dx = x - self.center_x
        dy = y - self.center_y
        radius = math.sqrt(dx*dx + dy*dy)
        
        if radius == 0:
            return 0.0, 1.0
        
        angle = math.atan2(dy, dx)
        
        # Fold angle for mirror symmetry
        fold_angle = (angle * self.symmetry / 2) % (2 * math.pi)
        if fold_angle > math.pi:
            fold_angle = 2 * math.pi - fold_angle
        
        pattern = 0.0
        pattern += math.sin(radius * 0.4 + fold_angle * 3 + frame * 0.1) * 0.4
        pattern += math.cos(radius * 0.2 - fold_angle * 2) * 0.3
        pattern += math.sin(radius * 0.6 + frame * 0.05) * 0.2
        
        density = (pattern + 1.5) / 2.5
        density = max(0.0, min(1.0, density))
        
        return radius, density
    
    def _calculate_flower_of_life(self, x: int, y: int, frame: int = 0) -> Tuple[float, float]:
        """Flower of Life inspired pattern."""
        dx = x - self.center_x
        dy = y - self.center_y
        radius = math.sqrt(dx*dx + dy*dy)
        
        if radius == 0:
            return 0.0, 1.0
        
        angle = math.atan2(dy, dx)
        
        pattern = 0.0
        # Multiple overlapping circles
        for i in range(self.symmetry):
            circle_angle = i * 2 * math.pi / self.symmetry
            dist = math.sqrt(
                (radius * math.cos(angle) - self.max_radius * 0.3 * math.cos(circle_angle))**2 +
                (radius * math.sin(angle) - self.max_radius * 0.3 * math.sin(circle_angle))**2
            )
            pattern += math.sin(dist * 0.5 + frame * 0.1) * 0.15
        
        # Central pattern
        pattern += math.sin(radius * 0.4 + frame * 0.05) * 0.3
        pattern += math.sin(angle * self.symmetry + radius * 0.1) * 0.2
        
        density = (pattern + 1.0) / 2.0
        density = max(0.0, min(1.0, density))
        
        return radius, density
    
    def _calculate_geometric(self, x: int, y: int, frame: int = 0) -> Tuple[float, float]:
        """Geometric sacred geometry pattern."""
        dx = x - self.center_x
        dy = y - self.center_y
        radius = math.sqrt(dx*dx + dy*dy)
        
        if radius == 0:
            return 0.0, 1.0
        
        angle = math.atan2(dy, dx)
        
        pattern = 0.0
        # Polygon edges
        for i in range(3, self.symmetry + 3):
            poly_angle = angle * i
            pattern += abs(math.sin(poly_angle / 2)) * 0.15
        
        # Radial lines
        pattern += abs(math.sin(angle * self.symmetry / 2)) * 0.3
        
        # Concentric polygons
        pattern += math.sin(radius * 0.3) * 0.25
        
        # Center star
        pattern += math.sin(radius * 0.6 + angle * self.symmetry) * 0.2
        
        density = (pattern + 0.5) / 1.5
        density = max(0.0, min(1.0, density))
        
        return radius, density
    
    def generate_frame(self, frame: int = 0, pattern_type: str = 'mandala') -> List[str]:
        """Generate a single frame of the mandala."""
        lines = []
        
        # Select pattern function
        pattern_funcs = {
            'mandala': self._calculate_pattern,
            'kaleidoscope': self._calculate_kaleidoscope,
            'flower': self._calculate_flower_of_life,
            'geometric': self._calculate_geometric,
        }
        calc_func = pattern_funcs.get(pattern_type, self._calculate_pattern)
        
        for y in range(self.height):
            line_chars = []
            for x in range(self.width):
                radius, density = calc_func(x, y, frame)
                
                if radius < 1.0:
                    # Center
                    color = self._get_color_for_radius(0, self.max_radius, frame)
                    char = self.center_char
                elif radius > self.max_radius:
                    # Outside
                    char = self.bg_char
                    color = ''
                else:
                    # Pattern area
                    color = self._get_color_for_radius(radius, self.max_radius, frame)
                    char = self._get_char_for_density(density)
                
                if color:
                    line_chars.append(f"{color}{char}{Colors.RESET}")
                else:
                    line_chars.append(char)
            
            lines.append(''.join(line_chars))
        
        return lines
    
    def render(self, pattern_type: str = 'mandala', output_file: Optional[str] = None) -> str:
        """Render mandala to string or file."""
        if self.animate:
            # Generate animation frames
            all_frames = []
            for frame in range(self.frames):
                frame_lines = self.generate_frame(frame, pattern_type)
                all_frames.append('\n'.join(frame_lines))
            
            # Create animation with ANSI escape codes for clearing
            animation = ''
            for i, frame in enumerate(all_frames):
                if i > 0:
                    # Move cursor up to overwrite
                    esc = '\033['
                    animation += f'{esc}{self.height}A'
                animation += frame + '\n'
                if i < self.frames - 1:
                    animation += '\n' * 2  # Space between frames in file
            
            result = animation
        else:
            # Single frame
            frame_lines = self.generate_frame(0, pattern_type)
            result = '\n'.join(frame_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"Mandala saved to {output_file}")
        
        return result
    
    def render_to_html(self, pattern_type: str = 'mandala', output_file: Optional[str] = None) -> str:
        """Render mandala as HTML with CSS colors for web viewing."""
        frame_lines = self.generate_frame(0, pattern_type)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ASCII Mandala</title>
    <style>
        body {{
            background: #1a1a2e;
            color: #eee;
            font-family: 'Monospace', monospace;
            line-height: 1.1;
            white-space: pre;
            padding: 20px;
            font-size: 12px;
        }}
        .mandala {{ letter-spacing: 0.5px; }}
    </style>
</head>
<body>
<pre class="mandala">
{self._ansi_to_html(chr(10).join(frame_lines))}
</pre>
</body>
</html>"""
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"HTML mandala saved to {output_file}")
        
        return html
    
    def _ansi_to_html(self, text: str) -> str:
        """Convert ANSI codes to HTML spans."""
        # Simple conversion for basic colors
        color_map = {
            Colors.RED: '#ff4444',
            Colors.GREEN: '#44ff44',
            Colors.YELLOW: '#ffff44',
            Colors.BLUE: '#4444ff',
            Colors.MAGENTA: '#ff44ff',
            Colors.CYAN: '#44ffff',
            Colors.WHITE: '#ffffff',
            Colors.BRIGHT_RED: '#ff8888',
            Colors.BRIGHT_GREEN: '#88ff88',
            Colors.BRIGHT_YELLOW: '#ffff88',
            Colors.BRIGHT_BLUE: '#8888ff',
            Colors.BRIGHT_MAGENTA: '#ff88ff',
            Colors.BRIGHT_CYAN: '#88ffff',
            Colors.BRIGHT_WHITE: '#ffffff',
            Colors.BRIGHT_BLACK: '#888888',
            Colors.BLACK: '#444444',
        }
        
        result = text
        for ansi, hex_color in color_map.items():
            result = result.replace(ansi, f'<span style="color:{hex_color}">')
        result = result.replace(Colors.RESET, '</span>')
        result = result.replace(Colors.BOLD, '<strong>')
        return result


def main():
    parser = argparse.ArgumentParser(description='ASCII Mandala Generator with Color Options')
    parser.add_argument('-w', '--width', type=int, default=80, help='Width in characters')
    parser.add_argument('-H', '--height', type=int, default=40, help='Height in characters')
    parser.add_argument('-s', '--symmetry', type=int, default=8, help='Symmetry order (number of segments)')
    parser.add_argument('-p', '--palette', choices=list(PALETTES.keys()), default='rainbow', help='Color palette')
    parser.add_argument('-c', '--charset', choices=list(CHAR_SETS.keys()), default='mandala', help='Character set')
    parser.add_argument('-t', '--type', choices=['mandala', 'kaleidoscope', 'flower', 'geometric'], default='mandala', help='Pattern type')
    parser.add_argument('-a', '--animate', action='store_true', help='Generate animation frames')
    parser.add_argument('-f', '--frames', type=int, default=30, help='Number of animation frames')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('--html', action='store_true', help='Output as HTML instead of ANSI')
    parser.add_argument('--list-palettes', action='store_true', help='List available palettes')
    parser.add_argument('--list-charsets', action='store_true', help='List available character sets')
    parser.add_argument('--list-patterns', action='store_true', help='List available pattern types')
    
    args = parser.parse_args()
    
    if args.list_palettes:
        print("Available palettes:")
        for name in PALETTES:
            print(f"  {name}")
        return
    
    if args.list_charsets:
        print("Available character sets:")
        for name, chars in CHAR_SETS.items():
            print(f"  {name}: {chars[:20]}...")
        return
    
    if args.list_patterns:
        print("Available pattern types:")
        print("  mandala      - Classic radial mandala")
        print("  kaleidoscope - Mirror symmetry kaleidoscope")
        print("  flower       - Flower of Life inspired")
        print("  geometric    - Sacred geometry polygons")
        return
    
    # Create generator
    generator = MandalaGenerator(
        width=args.width,
        height=args.height,
        symmetry=args.symmetry,
        palette=args.palette,
        char_set=args.charset,
        animate=args.animate,
        frames=args.frames,
    )
    
    # Generate output
    if args.html:
        output = generator.render_to_html(args.type, args.output)
        if not args.output:
            print(output)
    else:
        output = generator.render(args.type, args.output)
        if not args.output:
            print(output)


if __name__ == '__main__':
    main()
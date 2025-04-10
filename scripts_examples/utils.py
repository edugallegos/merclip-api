import xml.etree.ElementTree as ET
import subprocess
from matplotlib.colors import to_hex, to_rgb

def parse_color(color):
    try:
        return to_hex(color)
    except:
        raise ValueError(f"Invalid color: {color}")

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

def interpolate_color(from_hex, to_hex, progress):
    from_rgb = hex_to_rgb(from_hex)
    to_rgb = hex_to_rgb(to_hex)
    new_rgb = tuple(
        int(f + (t - f) * progress) for f, t in zip(from_rgb, to_rgb)
    )
    return rgb_to_hex(new_rgb)

def load_svg(path):
    return ET.parse(path).getroot()

def save_svg(svg_root, path):
    tree = ET.ElementTree(svg_root)
    tree.write(path)

def svg_to_png(svg_path, png_path, width, height):
    subprocess.run(["rsvg-convert", svg_path, "-w", str(width), "-h", str(height), "-o", png_path])

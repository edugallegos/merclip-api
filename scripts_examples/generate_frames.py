import os
import json
import shutil
import argparse
from utils import load_svg, save_svg, interpolate_color, svg_to_png, parse_color

def apply_global_color_morph(svg_tree, from_color, to_color, frame, total_frames):
    progress = frame / total_frames

    for elem in svg_tree.iter():
        fill = elem.get("fill")
        if fill:
            # Convert RGB format to hex if needed
            if fill.startswith("rgb("):
                # Extract RGB values
                rgb_values = fill[4:-1].split(",")
                r, g, b = map(int, rgb_values)
                # Convert to hex
                current_color = f"#{r:02x}{g:02x}{b:02x}"
            else:
                current_color = fill
            
            # Only change colors that are not the background (not white/light colors)
            if current_color.startswith("#") and current_color != "#fefefe":
                new_color = interpolate_color(from_color, to_color, progress)
                elem.set("fill", new_color)

def apply_sequential_reveal(svg_tree, frame, total_frames):
    # Get all path elements that are not the background
    paths = [elem for elem in svg_tree.iter() if elem.tag.endswith('path') and 
             elem.get("fill") != "rgb(254,254,254)"]
    
    # Calculate how many shapes should be visible at this frame
    total_shapes = len(paths)
    shapes_per_frame = total_shapes / total_frames
    visible_shapes = int(frame * shapes_per_frame)
    
    # Hide all shapes first
    for path in paths:
        path.set("opacity", "0")
    
    # Show the appropriate number of shapes
    for i in range(visible_shapes):
        if i < len(paths):
            paths[i].set("opacity", "1")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--animation', choices=['color', 'reveal', 'both'], default='color',
                      help='Type of animation to apply: color morph, sequential reveal, or both')
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    from_color = parse_color(config["from"])
    to_color = parse_color(config["to"])
    duration = config.get("duration", 5)
    fps = config.get("fps", 30)
    # Default to 9:16 aspect ratio (1080x1920 is a common resolution for this ratio)
    width = config.get("width", 1080)
    height = config.get("height", 1920)  # Changed from 1080 to 1920 to maintain 9:16 ratio

    # Round to nearest integer to handle decimal durations
    total_frames = round(duration * fps)

    if os.path.exists(args.output):
        shutil.rmtree(args.output)
    os.makedirs(args.output, exist_ok=True)

    for frame in range(total_frames):
        svg_tree = load_svg(args.input)
        
        if args.animation in ['color', 'both']:
            apply_global_color_morph(svg_tree, from_color, to_color, frame, total_frames)
        
        if args.animation in ['reveal', 'both']:
            apply_sequential_reveal(svg_tree, frame, total_frames)

        tmp_svg = 'tmp.svg'
        save_svg(svg_tree, tmp_svg)
        output_path = f'{args.output}/frame_{frame:04d}.png'
        svg_to_png(tmp_svg, output_path, width, height)

if __name__ == '__main__':
    main()

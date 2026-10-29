"""
App Icon Processor & Multi-Resolution Windows ICO Generator.
Removes solid backgrounds and cast shadows with sub-pixel raycast boundary extraction
and generates transparent PNG and multi-size Windows .ico files.
"""

import math
import os
import sys
from PIL import Image, ImageDraw, ImageFilter

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(PROJECT_ROOT, "images")


def extract_squircle_icon(img: Image.Image) -> Image.Image:
    """
    Traces the exact outer perimeter of the 3D squircle badge using radial ray-casting
    from the center outward, eliminating the flat white background and ambient cast shadow
    while preserving the glass bevels, highlights, and neon refraction.
    """
    img = img.convert("RGB")
    w, h = img.size
    cx, cy = w // 2, h // 2

    points = []
    num_rays = 1440
    for i in range(num_rays):
        angle = 2 * math.pi * i / num_rays
        dx = math.cos(angle)
        dy = math.sin(angle)
        
        # Bottom half (dy > 0.15) has the ambient shadow beneath the glass rim
        if dy > 0.15:
            # Rim is dark (RGB < 145), shadow is >= 150
            threshold = 145
        else:
            # Top half has white background (> 230), glass rim is <= 220
            threshold = 230

        hit_r = 0
        for r in range(int(min(w, h) * 0.48), int(min(w, h) * 0.25), -2):
            x = int(round(cx + r * dx))
            y = int(round(cy + r * dy))
            if 0 <= x < w and 0 <= y < h:
                pix = img.getpixel((x, y))
                if min(pix) < threshold:
                    hit_r = r
                    break
        points.append((cx + hit_r * dx, cy + hit_r * dy))

    # Build anti-aliased alpha mask
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(points, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2.0))

    rgba = img.convert("RGBA")
    rgba.putalpha(mask)

    # Crop to squircle bounding box
    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)

    # Pad into a centered square with 3% margin
    cw, ch = rgba.size
    side = max(cw, ch)
    margin = int(side * 0.03)
    final_side = side + (margin * 2)

    square_img = Image.new("RGBA", (final_side, final_side), (0, 0, 0, 0))
    offset_x = (final_side - cw) // 2
    offset_y = (final_side - ch) // 2
    square_img.paste(rgba, (offset_x, offset_y), rgba)

    return square_img


def process_icon(input_filename: str = None):
    # Auto-detect input image if not specified
    if not input_filename:
        for candidate in ["logo_raw.jpg", "logo_raw.png", "logo_raw.jpeg"]:
            if os.path.exists(os.path.join(IMAGES_DIR, candidate)):
                input_filename = candidate
                break

    if not input_filename:
        print("[!] No logo_raw image found in images/ folder.")
        return False

    input_path = os.path.join(IMAGES_DIR, input_filename)
    if not os.path.exists(input_path):
        print(f"[!] Input image not found: {input_path}")
        return False

    print(f"[*] Processing logo: {input_filename}...")
    raw_img = Image.open(input_path)
    
    # 1. Extract icon with clean transparent alpha
    transparent_img = extract_squircle_icon(raw_img)

    # 2. Save transparent high-res PNG (512x512)
    out_png = os.path.join(IMAGES_DIR, "app_icon.png")
    png_512 = transparent_img.resize((512, 512), Image.Resampling.LANCZOS)
    png_512.save(out_png, "PNG")
    print(f"[+] Transparent PNG saved to: {out_png} (512x512)")

    # 3. Save multi-resolution Windows ICO with per-layer Lanczos and adaptive sharpening
    # (prevents Windows Taskbar downscaling blur at 16x16, 24x24, 32x32, 48x48)
    out_ico = os.path.join(IMAGES_DIR, "app_icon.ico")
    sizes = [256, 128, 64, 48, 32, 24, 16]
    ico_layers = []
    for s in sizes:
        resized = transparent_img.resize((s, s), Image.Resampling.LANCZOS)
        # Apply gentle unsharp masking to small icons so glowing edges stay crisp on taskbar
        if s <= 48:
            unsharp_amount = 180 if s <= 32 else 130
            resized = resized.filter(ImageFilter.UnsharpMask(radius=0.8, percent=unsharp_amount, threshold=1))
        ico_layers.append(resized)

    ico_layers[0].save(
        out_ico,
        format="ICO",
        append_images=ico_layers[1:],
        sizes=[(s, s) for s in sizes],
    )
    print(f"[+] Multi-size sharpened Windows ICO saved to: {out_ico} ({[f'{s}x{s}' for s in sizes]})")
    print("[OK] App icon conversion successfully completed!")
    return True


if __name__ == "__main__":
    fname = sys.argv[1] if len(sys.argv) > 1 else None
    process_icon(fname)

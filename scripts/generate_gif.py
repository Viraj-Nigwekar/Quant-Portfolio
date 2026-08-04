#!/usr/bin/env python3
"""
generate_gif.py

Creates a cinematic 1920x1080 MP4 and an optimized GIF (palette-based) called:
- portfolio_showcase.mp4
- portfolio_showcase.gif

Usage:
  python scripts/generate_gif.py --out-dir outputs --mode auto
  python scripts/generate_gif.py --out-dir outputs --mode paths --scene-images s1.png s2.png ... s7.png

Notes:
 - Requires ffmpeg installed on system (used to make an optimized GIF).
 - The script will try to download Inter font into .cache/fonts if not present.
 - If there are less than 7 images found, the script generates title cards for missing scenes.
"""
from pathlib import Path
import argparse
import os
import glob
import random
import subprocess
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont
import numpy as np

# moviepy imports
from moviepy.editor import (
    ImageClip, TextClip, CompositeVideoClip, concatenate_videoclips,
    ImageSequenceClip, ColorClip
)
from moviepy.video.fx.all import resize

# ---------- CONFIG ----------
WIDTH, HEIGHT = 1920, 1080
FPS = 24
OUTPUT_MP4 = "portfolio_showcase.mp4"
OUTPUT_GIF = "portfolio_showcase.gif"
FONT_DIR = Path(".cache/fonts")
INTER_REGULAR_URL = "https://github.com/rsms/inter/raw/main/docs/Inter-Regular.ttf"
INTER_BOLD_URL = "https://github.com/rsms/inter/raw/main/docs/Inter-Bold.ttf"
# ----------------------------

def ensure_font():
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    regular = FONT_DIR / "Inter-Regular.ttf"
    bold = FONT_DIR / "Inter-Bold.ttf"
    import urllib.request
    for url, path in ((INTER_REGULAR_URL, regular), (INTER_BOLD_URL, bold)):
        if not path.exists():
            try:
                print("Downloading font:", url)
                urllib.request.urlretrieve(url, str(path))
            except Exception as e:
                print("Warning: failed to download font:", e)
    # choose regular if exists, else fallback to system default
    if regular.exists():
        return str(regular)
    return None

def find_candidate_images():
    patterns = [
        "assets/figures/**/*.png",
        "assets/figures/**/*.jpg",
        "figures/**/*.png",
        "figures/**/*.jpg",
        "notebooks/**/figures/**/*.png",
        "notebooks/**/figures/**/*.jpg",
        "notebooks/**/*.png",
        "notebooks/**/*.jpg",
        "images/**/*.png",
        "images/**/*.jpg",
        "*.png", "*.jpg",
    ]
    found = []
    for p in patterns:
        found += glob.glob(p, recursive=True)
    # filter small files
    found = [f for f in found if Path(f).stat().st_size > 1024]
    found = sorted(list(dict.fromkeys(found)))
    return found

def make_particle_frames(duration_seconds=6, n_frames=None):
    if n_frames is None:
        n_frames = int(duration_seconds * FPS)
    frames = []
    rng = np.random.RandomState(1337)
    n_dots = 220
    xs = rng.rand(n_dots) * WIDTH
    ys = rng.rand(n_dots) * HEIGHT
    vxs = (rng.rand(n_dots) - 0.5) * 0.6
    vys = (rng.rand(n_dots) - 0.5) * 0.6
    for i in range(n_frames):
        img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for j, (x, y) in enumerate(zip(xs.astype(int), ys.astype(int))):
            alpha = int(10 + 60 * rng.rand())
            r = 1 + int(rng.rand() * 2)
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(255,255,255,alpha))
        xs += vxs
        ys += vys
        xs %= WIDTH
        ys %= HEIGHT
        frames.append(np.array(img))
    return frames

def ken_burns_clip(image_path, duration, start_scale=1.05, end_scale=1.15, pan_strength=0.06):
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img)
    clip = ImageClip(arr).set_duration(duration)
    # compute resize to cover the frame while preserving aspect ratio
    iw, ih = arr.shape[1], arr.shape[0]
    scale0 = max(WIDTH/iw, HEIGHT/ih) * start_scale
    scale1 = max(WIDTH/iw, HEIGHT/ih) * end_scale
    # moviepy resize function driven by time
    def zoom(t):
        return scale0 + (scale1 - scale0) * (t / duration)
    clip = clip.resize(lambda t: zoom(t))
    # subtle pan direction
    pan_x = random.uniform(-pan_strength, pan_strength)
    pan_y = random.uniform(-pan_strength/2, pan_strength/2)
    # position interpolation
    def pos(t):
        cur_scale = zoom(t)
        w = iw * cur_scale
        h = ih * cur_scale
        x0 = (WIDTH - w) / 2.0 + pan_x * WIDTH * 0.4
        y0 = (HEIGHT - h) / 2.0 + pan_y * HEIGHT * 0.4
        x1 = (WIDTH - w) / 2.0 - pan_x * WIDTH * 0.4
        y1 = (HEIGHT - h) / 2.0 - pan_y * HEIGHT * 0.4
        frac = t / duration
        return (x0 + (x1 - x0) * frac, y0 + (y1 - y0) * frac)
    clip = clip.set_position(lambda t: pos(t))
    return clip

def text_image_clip(text, fontsize=64, duration=2.0, y_offset=120, font_path=None, weight='regular'):
    # create a transparent image with centered text
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    try:
        if font_path:
            fnt = ImageFont.truetype(font_path, fontsize)
        else:
            fnt = ImageFont.load_default()
    except Exception:
        fnt = ImageFont.load_default()
    # wrap text to multiple lines
    max_width = int(WIDTH * 0.85)
    lines = textwrap.wrap(text, width=28)
    # compute total height
    line_h = fnt.getsize("Ay")[1]
    total_h = line_h * len(lines)
    y0 = HEIGHT - y_offset - total_h
    for i, line in enumerate(lines):
        w,h = draw.textsize(line, font=fnt)
        draw.text(((WIDTH-w)/2, y0 + i*line_h), line, font=fnt, fill=(255,255,255,255))
    return ImageClip(np.array(img)).set_duration(duration)

def make_card(title, subtitle=None, duration=2.0, font_path=None):
    img = Image.new("RGB",(WIDTH,HEIGHT),(8,8,10))
    draw = ImageDraw.Draw(img)
    # gradient
    for i in range(HEIGHT//2):
        c = 10 + int(i * 0.03)
        draw.rectangle([0, i, WIDTH, i+1], fill=(c,c,c))
    try:
        f_title = ImageFont.truetype(font_path, 88) if font_path else ImageFont.load_default()
        f_sub = ImageFont.truetype(font_path, 36) if font_path else ImageFont.load_default()
    except Exception:
        f_title = ImageFont.load_default()
        f_sub = ImageFont.load_default()
    w1,h1 = draw.textsize(title, font=f_title)
    draw.text(((WIDTH-w1)/2, HEIGHT*0.33), title, font=f_title, fill=(255,255,255))
    if subtitle:
        w2,h2 = draw.textsize(subtitle, font=f_sub)
        draw.text(((WIDTH-w2)/2, HEIGHT*0.55), subtitle, font=f_sub, fill=(200,200,200))
    return ImageClip(np.array(img)).set_duration(duration)

def build_video(scene_images, out_dir, font_path):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # durations (total ~15s). first scene is the hook (3s).
    durations = [3.0, 2.0, 2.0, 2.0, 2.0, 2.5, 1.5]
    # titles (first scene picks a hook at random)
    opening_hooks = [
        "What if portfolio optimization wasn't so sensitive to estimation error?",
        "One year of building open-source quantitative finance projects...",
        "From portfolio optimization to financial machine learning...",
    ]
    titles = [
        random.choice(opening_hooks),
        "📈 Portfolio Optimization",
        "⚠️ Risk Analysis",
        "📊 Factor Models",
        "🤖 Financial Machine Learning",
        "Multi-Axis Robust Portfolio Optimization\n• SSRN Paper  • GitHub Repository  • Open Source",
        "Quant Portfolio\ngithub.com/Viraj-Nigwekar/Quant-Portfolio\n⭐ Open Source  📚 Research  🐍 Python"
    ]

    total_duration = sum(durations)
    particle_frames = make_particle_frames(duration_seconds=total_duration, n_frames=int(total_duration*FPS))
    particle_clip = ImageSequenceClip(list(particle_frames), fps=FPS).set_duration(total_duration).set_opacity(0.12)

    clips = []
    elapsed = 0.0
    for idx, d in enumerate(durations):
        title = titles[idx]
        img_path = scene_images[idx] if idx < len(scene_images) and scene_images[idx] else None
        if img_path and Path(img_path).exists():
            clip = ken_burns_clip(img_path, d)
        else:
            # for scene 1 prefer a bold card
            if idx == 0:
                clip = make_card(title, subtitle=None, duration=d, font_path=font_path)
            else:
                clip = make_card("", subtitle=None, duration=d, font_path=font_path)
        # text overlay
        if idx == 0:
            text_clip = text_image_clip(title, fontsize=56, duration=d, y_offset=220, font_path=font_path)
        else:
            text_clip = text_image_clip(title, fontsize=64, duration=d, y_offset=140, font_path=font_path)
        bg = ColorClip(size=(WIDTH, HEIGHT), color=(6,6,8)).set_duration(d)
        # composite: background -> clip -> particle -> text
        # clip may be larger/smaller; center it
        clip = clip.resize(height=int(HEIGHT*1.02)).set_position(("center","center"))
        particle_sub = particle_clip.subclip(elapsed, elapsed+d).set_position(("center","center"))
        comp = CompositeVideoClip([bg, clip, particle_sub, text_clip.set_start(0)])
        comp = comp.set_duration(d)
        if idx > 0:
            comp = comp.crossfadein(0.35)
        clips.append(comp)
        elapsed += d

    final = concatenate_videoclips(clips, method="compose")
    final = final.set_fps(FPS)
    mp4_path = out_dir / OUTPUT_MP4
    gif_path = out_dir / OUTPUT_GIF

    print("Rendering MP4 (this may take a while)...")
    final.write_videofile(str(mp4_path), codec="libx264", audio=False, threads=4, fps=FPS, preset="medium", bitrate="4000k")
    # Create an optimized GIF using ffmpeg palette method
    # First write an intermediate low-fps segment for gif creation
    tmp_webm = out_dir / "tmp_for_gif.mp4"
    final.write_videofile(str(tmp_webm), codec="libx264", audio=False, threads=2, fps=12, preset="fast", bitrate="2500k", verbose=False, logger=None)

    # Use ffmpeg palettegen & paletteuse to generate optimized gif
    print("Generating optimized GIF via ffmpeg palette (requires ffmpeg installed)...")
    palette = out_dir / "palette.png"
    # palettegen
    cmd1 = [
        "ffmpeg", "-y", "-i", str(tmp_webm),
        "-vf", "fps=12,scale=1200:-1:flags=lanczos,palettegen",
        "-palettegen_max_colors", "256",
        str(palette)
    ]
    # paletteuse to create gif
    cmd2 = [
        "ffmpeg", "-y", "-i", str(tmp_webm), "-i", str(palette),
        "-lavfi", "fps=12,scale=1200:-1:flags=lanczos [x];[x][1:v] paletteuse=dither=bayer",
        str(gif_path)
    ]
    try:
        subprocess.check_call(cmd1)
        subprocess.check_call(cmd2)
        # cleanup
        try:
            palette.unlink()
            tmp_webm.unlink()
        except Exception:
            pass
    except Exception as e:
        print("ffmpeg palette method failed; falling back to moviepy GIF (may be large)", e)
        try:
            final.write_gif(str(gif_path), fps=12, program='ffmpeg')
        except Exception as e2:
            print("GIF fallback failed:", e2)
    print("Done. Outputs:", mp4_path, gif_path)
    return mp4_path, gif_path

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default="outputs")
    p.add_argument("--mode", choices=("auto", "paths"), default="auto")
    p.add_argument("--scene-images", nargs="*", help="7 image paths for scenes 1..7", default=[])
    return p.parse_args()

def main():
    args = parse_args()
    font_path = ensure_font()
    if args.mode == "auto":
        found = find_candidate_images()
        # scoring: prefer images with relevant keywords
        def score(f):
            s = 0
            fn = f.lower()
            if "markowitz" in fn or "optimization" in fn: s += 5
            if "monte" in fn or "montecarlo" in fn: s += 5
            if "backtest" in fn or "equity" in fn: s += 4
            if "factor" in fn: s += 4
            if "risk" in fn: s += 4
            if "ml" in fn or "model" in fn or "regress" in fn: s += 2
            return s
        if len(found) >= 7:
            found_sorted = sorted(found, key=lambda f: (-score(f), len(f)))
            chosen = found_sorted[:7]
        else:
            chosen = found[:7]
        # pad
        while len(chosen) < 7:
            chosen.append(None)
        print("Using image set:", chosen)
        build_video(chosen, args.out_dir, font_path)
    else:
        imgs = args.scene_images
        if len(imgs) < 7:
            print("Error: please provide exactly 7 image paths for --mode paths")
            sys.exit(2)
        build_video(imgs[:7], args.out_dir, font_path)

if __name__ == "__main__":
    main()

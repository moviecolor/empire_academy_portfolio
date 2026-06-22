"""Star Wars-style crawl v12 — CORRECT 3D perspective (OpenCV).
- Text at TOP is NARROW (small, far away) — CORRECT
- Text at BOTTOM is WIDE (large, close) — CORRECT
- Uses OpenCV warpPerspective (source rect -> dest trapezoid)
- Final text from user 2026-06-21
- 1080x1080 square, starfield, Star Wars yellow, ffmpeg encoding
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import subprocess, os, tempfile, math, time, sys

W = H = 1080
FPS = 24
DURATION = 120  # slightly longer for more text
TOTAL_FRAMES = DURATION * FPS
FFMPEG = r"C:\Program Files\Shotcut\ffmpeg.exe"
OUT = r"C:\ai\ComfyUI\output\hard_seals_crawl_v12.mp4"
TMP = tempfile.mkdtemp(prefix="crawl4_")

SW_YELLOW = (255, 232, 31)
BG_COLOR = (5, 3, 18)

# ── TEXT (user's final version 2026-06-21 v2) ──
LINES = [
    ("ALL AI ENGINEERED",                    "title"),
    ("",                                     "spacer"),
    ("by one",                               "subtitle"),
    ("",                                     "spacer"),
    ("ComfyUI creator",                      "subtitle"),
    ("Vibe Coder",                           "body"),
    ("16yr TV/Film Veteran",                 "body"),
    ("Digital Imaging Technician / Colorist","body"),
    ("",                                     "spacer"),
    ("Not made with slot machine AI",        "emphasis"),
    ("All images, video and audio",          "body"),
    ("created on local air-gapped hardware", "body"),
    ("to keep client assets safe",           "body"),
    ("using open source models",             "body"),
    ("with MIT or Apache licenses",          "body"),
    ("with Mac Studio Ultra",                "body"),
    ("and custom AI workstation",            "body"),
    ("with an RTX 5090",                     "emphasis"),
    ("",                                     "spacer"),
    ("Wanna see what else",                  "body"),
    ("I can build for you?",                 "body"),
    ("Portfolio LINK IN BIO",                "emphasis"),
    ("",                                     "spacer"),
    ("Details:",                             "subtitle"),
    ("vibe coded with openCode",             "body"),
    ("local  FREE LLMs",                     "body"),
    ("and customized Agents,",               "body"),
    ("subagents and skills",                 "body"),
    ("",                                     "spacer"),
    ("Tools Used:",                          "subtitle"),
    ("Image and video generation",           "body"),
    ("with comfyUI Ollama and local LLMs",   "body"),
    ("Models: Z-Image Turbo, Qwen3, LTX 2.3","emphasis"),
    ("",                                     "spacer"),
    ("Audio:",                               "subtitle"),
    ("Voice sampling and cloning",           "body"),
    ("via Qwen3-TTS in ComfyUI",             "body"),
    ("",                                     "spacer"),
    ("Credit crawl was completely",          "body"),
    ("hands off vibe coded",                 "body"),
    ("requiring aproximately 30 iterations", "body"),
    ("",                                     "spacer"),
    ("Video  / Image iteration output:",     "subtitle"),
    ("Video clips — about 20 iterations each","body"),
    ("Audio — 50 to 70 takes",               "body"),
    ("to compile the dialogue",              "body"),
    ("",                                     "spacer"),
    ("Assembled and edited",                 "body"),
    ("in DaVinci Resolve",                   "body"),
    ("",                                     "spacer"),
    ("IF you made it this far",              "emphasis"),
    ("and are still listening",              "emphasis"),
    ("you should probably click",            "emphasis"),
    ("the link in the bio.",                 "emphasis"),
    ("",                                     "spacer"),
    ("let's connect",                        "title"),
]

FONTS = {
    "title":    ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 100),
    "subtitle": ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 52),
    "body":     ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 44),
    "emphasis": ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 48),
    "spacer":   None,
}
LINE_SPACING = 22

# ── STEP 1: Render text block ──
print("=" * 50)
print("STEP 1: Rendering text block...")

line_heights = []
for text, style in LINES:
    if style == "spacer":
        h = LINE_SPACING * 2
    else:
        bbox = FONTS[style].getbbox(text)
        h = (bbox[3] - bbox[1]) + LINE_SPACING
    line_heights.append(h)

total_text_h = sum(line_heights) + 200
text_img = Image.new("RGBA", (W, total_text_h), (0, 0, 0, 0))
draw = ImageDraw.Draw(text_img)

y_pos = 100
for (text, style), lh in zip(LINES, line_heights):
    if style == "spacer":
        y_pos += lh
        continue
    font = FONTS[style]
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    draw.text((x + 3, y_pos + 3), text, font=font, fill=(0, 0, 0, 220))
    draw.text((x, y_pos), text, font=font, fill=SW_YELLOW + (255,))
    y_pos += lh

TEXT_H = text_img.height
print(f"  Text image: {W} x {TEXT_H} px")

# Convert to numpy for OpenCV
text_np = np.array(text_img)

# ── STEP 2: Starfield ──
print("STEP 2: Generating starfield...")
rng = np.random.RandomState(42)
STARS = []
for _ in range(1200):
    sx = rng.randint(0, W)
    sy = rng.randint(0, H)
    bright = rng.uniform(0.3, 1.0)
    tspeed = rng.uniform(0.3, 2.5)
    tphase = rng.uniform(0, math.pi * 2)
    size = 1 if rng.random() < 0.7 else 2
    STARS.append((sx, sy, bright, tspeed, tphase, size))

def make_starfield(t):
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    for sx, sy, bright, tspeed, tphase, size in STARS:
        twinkle = 0.4 + 0.6 * max(0, math.sin(t * tspeed + tphase))
        b = int(bright * twinkle * 220) + 35
        b = min(b, 255)
        draw.ellipse([sx-size, sy-size, sx+size, sy+size],
                     fill=(max(0,b-20), max(0,b-10), b))
    return img

# ── STEP 3 (was 4): Top fade ──
def make_top_fade():
    fade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pixels = fade.load()
    fade_start = int(H * 0.12)
    for y in range(fade_start):
        alpha = int(200 * (1 - y / fade_start))
        for x in range(W):
            pixels[x, y] = BG_COLOR + (alpha,)
    return fade

top_fade = make_top_fade()

# ── STEP 4: Perspective with OpenCV ──
# CORRECT approach:
# Source = full rectangle in text image (the normal text)
# Dest = trapezoid on screen (narrow at top, wide at bottom)
# This makes text at top of screen appear SMALLER (compressed)

def get_perspective_matrix(scroll_y, narrow_top=500):
    """
    Compute perspective matrix using OpenCV.
    Source points: rectangle in the text image
    Dest points: trapezoid in the output (narrow at top, wide at bottom)
    """
    cx = W / 2
    
    # Source: full rectangle in text image (where the text lives)
    src_pts = np.float32([
        [0, scroll_y],           # top-left of source slice
        [W, scroll_y],           # top-right of source slice
        [W, scroll_y + H],       # bottom-right of source slice
        [0, scroll_y + H],       # bottom-left of source slice
    ])
    
    # Dest: trapezoid — narrow at top, wide at bottom
    dst_pts = np.float32([
        [cx - narrow_top/2, 0],  # top-left (narrow, centered)
        [cx + narrow_top/2, 0],  # top-right (narrow, centered)
        [W, H],                  # bottom-right (full width)
        [0, H],                  # bottom-left (full width)
    ])
    
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    return M

# ── STEP 5: Render frames ──
print("STEP 5: Rendering frames with CORRECT 3D perspective...")

CRAWL_START_T = 5.0
CRAWL_END_T = DURATION - 2.0
CRAWL_DURATION = CRAWL_END_T - CRAWL_START_T

SCROLL_START = -H + 100
SCROLL_END = TEXT_H + 200
TOTAL_SCROLL = SCROLL_END - SCROLL_START
SCROLL_SPEED = TOTAL_SCROLL / CRAWL_DURATION

print(f"  Text height: {TEXT_H}px")
print(f"  Scroll speed: {SCROLL_SPEED:.1f} px/s over {CRAWL_DURATION:.0f}s")
print(f"  Rendering {TOTAL_FRAMES} frames...")

progress_step = max(1, TOTAL_FRAMES // 20)
start_time = time.time()

for idx in range(TOTAL_FRAMES):
    t = idx / FPS
    
    # Starfield
    bg = make_starfield(t)
    bg_np = np.array(bg)
    
    # Main crawl
    if CRAWL_START_T <= t <= CRAWL_END_T:
        crawl_t = t - CRAWL_START_T
        scroll_y = SCROLL_START + crawl_t * SCROLL_SPEED
        
        M = get_perspective_matrix(scroll_y, narrow_top=500)
        
        # Warp the text image using OpenCV
        # The text is RGBA, so we warp each channel
        # M maps source->dest. warpPerspective internally inverts M
        # to map each dest pixel back to source for sampling.
        warped = cv2.warpPerspective(
            text_np, M, (W, H),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0)
        )
        
        # Composite warped text onto background
        alpha = warped[:, :, 3:] / 255.0
        bg_np = (bg_np * (1 - alpha) + warped[:, :, :3] * alpha).astype(np.uint8)
    
    # Apply top fade
    fade_np = np.array(top_fade)
    alpha = fade_np[:, :, 3:] / 255.0
    bg_np = (bg_np * (1 - alpha) + fade_np[:, :, :3] * alpha).astype(np.uint8)
    
    # Save frame
    Image.fromarray(bg_np).save(os.path.join(TMP, f"frame_{idx:06d}.png"))
    
    if idx % progress_step == 0:
        elapsed = time.time() - start_time
        pct = idx / TOTAL_FRAMES * 100
        eta = (elapsed / max(1, idx)) * (TOTAL_FRAMES - idx) if idx > 0 else 0
        print(f"  {pct:.0f}% ({idx}/{TOTAL_FRAMES})  {elapsed:.0f}s  ETA:{eta:.0f}s")

elapsed = time.time() - start_time
print(f"  Rendered {TOTAL_FRAMES} frames in {elapsed:.1f}s")

# ── STEP 6: Encode ──
print("STEP 6: Encoding video...")
encode_start = time.time()

cmd = [
    FFMPEG, "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(TMP, "frame_%06d.png"),
    "-c:v", "libx264",
    "-preset", "veryslow",
    "-crf", "17",
    "-pix_fmt", "yuv420p",
    "-vf", f"scale={W}:{H}:flags=lanczos",
    "-movflags", "+faststart",
    OUT
]

result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print(f"  FFMPEG ERROR: {result.stderr[:500]}")
    sys.exit(1)

encode_elapsed = time.time() - encode_start
size_mb = os.path.getsize(OUT) / 1024 / 1024
print(f"  Encoded in {encode_elapsed:.1f}s -> {size_mb:.1f}MB")

# Verify
probe_cmd = [FFMPEG.replace("ffmpeg", "ffprobe"), "-v", "error",
    "-show_entries", "format=duration,size,bit_rate",
    "-show_entries", "stream=codec_name,width,height,r_frame_rate",
    "-of", "default=noprint_wrappers=1", OUT]
subprocess.run(probe_cmd)
print(f"  File: {OUT}  ({size_mb:.1f}MB)")

import shutil
shutil.rmtree(TMP, ignore_errors=True)

print("=" * 50)
print(f"DONE: {OUT}")
print(f"      {DURATION}s | 1080x1080 | 24fps | {size_mb:.1f}MB")
print(f"      Story: full AI engineered cred + portfolio CTA bookends")
print(f"      3D perspective (narrow_top=500) | OpenCV warpPerspective")

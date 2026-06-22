"""Star Wars-style crawl v3.1 — FIXED top fade, bigger fonts, gentler perspective.
1080x1080 square, starfield, yellow 3D perspective, ffmpeg encoding.

CHANGES FROM v3:
  - Top fade reduced from 35% to 12% (was hiding the perspective effect)
  - Body font increased 46 -> 52px
  - narrow_top increased 400 -> 480 (gentler 3D look)
  - BICUBIC resampling (crisper text at all sizes)
  - Longer crawl window (38s instead of 36s)
  - Stronger text shadow for readability
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import subprocess, os, tempfile, math, time, sys

# ── CONFIG ──
W = H = 1080
FPS = 24
DURATION = 46           # seconds
TOTAL_FRAMES = DURATION * FPS
FFMPEG = r"C:\Program Files\Shotcut\ffmpeg.exe"
OUT = r"C:\ai\ComfyUI\output\hard_seals_crawl_v3.mp4"
TMP = tempfile.mkdtemp(prefix="crawl3_")

SW_YELLOW = (255, 232, 31)      # Official Star Wars yellow #FFE81F

LINES = [
    ("A",                              "title"),
    ("HARD SEALS",                     "title"),
    ("PRODUCTION",                     "title"),
    ("",                               "spacer"),
    ("Built with:",                    "subtitle"),
    ("ComfyUI  ·  Ollama  ·  DaVinci Resolve  ·  OpenCode", "body"),
    ("",                               "spacer"),
    ("All frames generated locally.",  "body"),
    ("Air-gapped hardware.",           "body"),
    ("Your assets stay yours.",        "body"),
    ("",                               "spacer"),
    ("Wanna see what else",            "body"),
    ("I can build for you?",           "body"),
    ("PORTFOLIO LINK IN BIO",          "emphasis"),
    ("",                               "spacer"),
    ("Vibe coder  ·  ComfyUI creator", "body"),
    ("15+ yrs TV/Film veteran",        "body"),
    ("",                               "spacer"),
    ("(c) 2026 Hard Seals",            "body"),
]

FONTS = {
    "title":    ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 100),
    "subtitle": ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 58),
    "body":     ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 52),
    "emphasis": ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 58),
    "spacer":   None,
}

LINE_SPACING = 22

# ── STEP 1: Render full text block ──
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
    # Stronger shadow (offset 3px, more opaque) for readability
    draw.text((x + 3, y_pos + 3), text, font=font, fill=(0, 0, 0, 220))
    draw.text((x, y_pos), text, font=font, fill=SW_YELLOW + (255,))
    y_pos += lh

TEXT_H = text_img.height
print(f"  Text image: {W} x {TEXT_H} px")

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
    img = Image.new("RGB", (W, H), (5, 3, 18))
    draw = ImageDraw.Draw(img)
    for sx, sy, bright, tspeed, tphase, size in STARS:
        twinkle = 0.4 + 0.6 * max(0, math.sin(t * tspeed + tphase))
        b = int(bright * twinkle * 220) + 35
        b = min(b, 255)
        r = max(0, b - 20)
        g = max(0, b - 10)
        draw.ellipse([sx-size, sy-size, sx+size, sy+size], fill=(r, g, b))
    return img

print(f"  {len(STARS)} stars")

# ── STEP 3: Perspective coefficients ──
def compute_perspective_coeffs(scroll_y, narrow_top=480):
    cx = W / 2
    src = np.array([
        [cx - narrow_top/2, scroll_y],
        [cx + narrow_top/2, scroll_y],
        [W, scroll_y + H],
        [0, scroll_y + H],
    ], dtype=np.float64)
    dst = np.array([
        [0, 0], [W, 0], [W, H], [0, H],
    ], dtype=np.float64)
    A_mat = []
    B_vec = []
    for (xd, yd), (xs, ys) in zip(dst, src):
        A_mat.append([xd, yd, 1, 0, 0, 0, -xd*xs, -yd*xs])
        B_vec.append(xs)
        A_mat.append([0, 0, 0, xd, yd, 1, -xd*ys, -yd*ys])
        B_vec.append(ys)
    coeffs = np.linalg.solve(np.array(A_mat), np.array(B_vec))
    return coeffs.tolist()

# ── STEP 4: Gentle top fade ──
def make_top_fade():
    """Fade to background at top — only 12% of frame, gradual."""
    fade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pixels = fade.load()
    fade_start = int(H * 0.12)  # fade begins at 12% from top
    for y in range(fade_start):
        alpha = int(255 * (1 - y / fade_start))  # 0 to 255
        for x in range(W):
            pixels[x, y] = (5, 3, 18, alpha)
    return fade

# ── STEP 5: Render frames ──
print("STEP 3: Rendering frames...")

CRAWL_START_T = 5.0
CRAWL_END_T = DURATION - 2.0
CRAWL_DURATION = CRAWL_END_T - CRAWL_START_T  # ~39s

SCROLL_START = -H + 100
SCROLL_END = TEXT_H + 200
TOTAL_SCROLL = SCROLL_END - SCROLL_START
SCROLL_SPEED = TOTAL_SCROLL / CRAWL_DURATION

print(f"  Text height: {TEXT_H}px")
print(f"  Scroll speed: {SCROLL_SPEED:.1f} px/s over {CRAWL_DURATION:.0f}s")
print(f"  Rendering {TOTAL_FRAMES} frames...")

top_fade = make_top_fade()

def render_opener(t):
    if t < 0.5 or t > 7.0:
        return None
    if t < 2.0:
        alpha = int(255 * (t - 0.5) / 1.5)
    elif t < 4.5:
        alpha = 255
    else:
        alpha = int(255 * (7.0 - t) / 2.5)
    if alpha < 10:
        return None
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 38)
    text = "A long time ago in a galaxy far, far away...."
    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    d.text(((W - tw) // 2, H // 2 - 80), text, font=font, fill=(60, 130, 255, alpha))
    return overlay

progress_step = max(1, TOTAL_FRAMES // 20)
start_time = time.time()

for idx in range(TOTAL_FRAMES):
    t = idx / FPS

    # Background
    frame = make_starfield(t)

    # Opener
    opener = render_opener(t)
    if opener is not None:
        frame = Image.alpha_composite(frame.convert("RGBA"), opener)

    # Main crawl
    if CRAWL_START_T <= t <= CRAWL_END_T:
        crawl_t = t - CRAWL_START_T
        scroll_y = SCROLL_START + crawl_t * SCROLL_SPEED
        coeffs = compute_perspective_coeffs(scroll_y, narrow_top=480)

        warped = text_img.transform(
            (W, H),
            Image.PERSPECTIVE,
            coeffs,
            resample=Image.BICUBIC
        )
        frame = Image.alpha_composite(frame.convert("RGBA"), warped)

    # Top fade (gentle)
    frame = Image.alpha_composite(frame.convert("RGBA"), top_fade)

    # Save
    frame.convert("RGB").save(os.path.join(TMP, f"frame_{idx:06d}.png"))

    if idx % progress_step == 0:
        elapsed = time.time() - start_time
        pct = idx / TOTAL_FRAMES * 100
        eta = (elapsed / max(1, idx)) * (TOTAL_FRAMES - idx) if idx > 0 else 0
        print(f"  {pct:.0f}% ({idx}/{TOTAL_FRAMES})  {elapsed:.0f}s  ETA:{eta:.0f}s")

elapsed = time.time() - start_time
print(f"  Rendered {TOTAL_FRAMES} frames in {elapsed:.1f}s")

# ── STEP 6: Encode ──
print("STEP 4: Encoding video...")
encode_start = time.time()

cmd = [
    FFMPEG,
    "-y",
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
    print(f"  FFMPEG ERROR: {result.stderr}")
    sys.exit(1)

encode_elapsed = time.time() - encode_start
size_mb = os.path.getsize(OUT) / 1024 / 1024
print(f"  Encoded in {encode_elapsed:.1f}s -> {size_mb:.1f}MB")

# ── Verify ──
print("STEP 5: Verifying...")
probe_cmd = [
    FFMPEG.replace("ffmpeg", "ffprobe"),
    "-v", "error",
    "-show_entries", "format=duration,size,bit_rate",
    "-show_entries", "stream=codec_name,width,height,r_frame_rate",
    "-of", "default=noprint_wrappers=1",
    OUT
]
probe = subprocess.run(probe_cmd, capture_output=True, text=True)
print(f"  {probe.stdout}")

# Cleanup
import shutil
shutil.rmtree(TMP, ignore_errors=True)

print("=" * 50)
print(f"DONE: {OUT}")
print(f"      {DURATION}s | 1080x1080 | 24fps | {size_mb:.1f}MB")
print(f"      Star Wars yellow (#FFE81F) | 3D perspective (narrow_top=480)")
print(f"      Gentle 12% top fade | BICUBIC resampling | libx264 yuv420p")

#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10"]
# ///
"""Render the repo demo GIF.

It shows the answer, not the process. No terminal recording, no typing
animation, no waiting. The verdict is on screen inside the first frame of each
beat, because that is the thing being sold: you get a decision, fast.

    uv run assets/make_demo.py
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 520
PAPER = (237, 227, 210)
NAVY = (26, 40, 64)
RUST = (200, 97, 45)
GREEN = (92, 122, 90)
MUTED = (120, 116, 108)

MONO = "/System/Library/Fonts/Menlo.ttc"
SANS = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
SANS_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"

OUT = Path(__file__).parent


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


BEATS = [
    {
        "command": "aws s3 rm s3://prod-backups --recursive",
        "verdict": "DENIED",
        "colour": RUST,
        "detail": "destructive  p=0.96",
        "meta": "371ms   $0.000019",
    },
    {
        "command": "git stash clear",
        "verdict": "DENIED",
        "colour": RUST,
        "detail": "hard rule, no model call",
        "meta": "2ms   free",
    },
    {
        "command": "git status",
        "verdict": "ALLOWED",
        "colour": GREEN,
        "detail": "fast path, no model call",
        "meta": "1ms   free",
    },
    {
        "command": "docker system prune -a --volumes -f",
        "verdict": "ASK",
        "colour": NAVY,
        "detail": "low confidence  0.23",
        "meta": "402ms   $0.000018",
    },
]


def rounded(draw: ImageDraw.ImageDraw, box, radius, fill=None, outline=None, width=3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def frame(beat: dict, reveal: float) -> Image.Image:
    """reveal 0..1 controls only the stamp's entrance, never the command."""
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    # faint ruled lines, the brand's notebook paper
    for y in range(90, H, 46):
        draw.line([(0, y), (W, y)], fill=(224, 213, 195), width=1)

    draw.text((56, 44), "jev-gate", font=font(SANS, 30), fill=NAVY)
    draw.text((176, 52), "every tool call, checked before it runs", font=font(SANS_REG, 20), fill=MUTED)

    # the proposed command
    rounded(draw, (56, 128, W - 56, 236), 14, fill=(28, 38, 52))
    draw.text((84, 150), "$", font=font(MONO, 26), fill=(140, 160, 150))
    draw.text((116, 150), beat["command"], font=font(MONO, 26), fill=(226, 232, 226))
    draw.text((84, 192), "proposed by the agent", font=font(SANS_REG, 17), fill=(130, 145, 140))

    if reveal <= 0:
        return img

    # the verdict stamp, scaled in fast
    scale = 0.86 + 0.14 * reveal
    stamp_w, stamp_h = int(340 * scale), int(104 * scale)
    x0, y0 = 56, 290
    rounded(draw, (x0, y0, x0 + stamp_w, y0 + stamp_h), 14,
            fill=beat["colour"], outline=NAVY, width=4)
    vf = font(SANS, int(46 * scale))
    tw = draw.textlength(beat["verdict"], font=vf)
    draw.text((x0 + (stamp_w - tw) / 2, y0 + (stamp_h - 46 * scale) / 2 - 4),
              beat["verdict"], font=vf, fill=PAPER)

    if reveal > 0.55:
        draw.text((x0 + stamp_w + 36, y0 + 14), beat["detail"], font=font(SANS, 25), fill=NAVY)
        draw.text((x0 + stamp_w + 36, y0 + 54), beat["meta"], font=font(MONO, 21), fill=MUTED)

    draw.line([(56, 448), (W - 56, 448)], fill=(210, 198, 180), width=2)
    draw.text((56, 466), "github.com/eugeniughelbur/jev-engineering", font=font(MONO, 19), fill=MUTED)
    return img


def main() -> None:
    frames: list[tuple[Image.Image, int]] = []  # image, centiseconds
    for beat in BEATS:
        frames.append((frame(beat, 0.0), 6))    # command visible
        frames.append((frame(beat, 0.45), 4))   # stamp lands, under 0.1s later
        frames.append((frame(beat, 1.0), 90))   # answer holds

    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for i, (img, _) in enumerate(frames):
            path = Path(tmp) / f"f{i:03d}.png"
            img.save(path)
            paths.append(path)

        gif = OUT / "demo.gif"
        frames[0][0].save(
            gif,
            save_all=True,
            append_images=[f for f, _ in frames[1:]],
            duration=[d * 10 for _, d in frames],
            loop=0,
            optimize=True,
        )
        print(f"{gif}  {gif.stat().st_size // 1024}KB")

        # a still for the GitHub social card
        social = frame(BEATS[0], 1.0).resize((1280, 640), Image.LANCZOS)
        social.save(OUT / "social-card.png")
        print(f"{OUT / 'social-card.png'}")


if __name__ == "__main__":
    main()

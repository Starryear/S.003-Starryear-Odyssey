#!/usr/bin/env python3
"""Compose an exact-source-pixel upper panel with a generated abstract lower panel."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


def font_for(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def load_rgb(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGB")


def verify(source_path: Path, output_path: Path) -> None:
    source = load_rgb(source_path)
    output = load_rgb(output_path)
    if output.width != source.width or output.height <= source.height:
        raise ValueError("Output must equal the source width and be taller than the source.")
    top = output.crop((0, 0, source.width, source.height))
    if ImageChops.difference(source, top).getbbox() is not None:
        raise ValueError("Verification failed: upper-panel pixels differ from the source.")
    print(f"verified: top {source.width}x{source.height} is pixel-identical")


def blend_seam_from_source(source: Image.Image, lower: Image.Image, seam_ratio: float) -> Image.Image:
    """Continue source-edge color into the lower panel without touching source pixels."""
    seam_height = min(lower.height // 5, max(0, round(source.height * seam_ratio)))
    if seam_height == 0:
        return lower
    sample_height = min(source.height, max(8, seam_height // 3))
    edge = source.crop((0, source.height - sample_height, source.width, source.height))
    edge = edge.resize((lower.width, seam_height), Image.Resampling.BICUBIC)
    edge = edge.filter(ImageFilter.GaussianBlur(radius=max(2, seam_height / 18)))
    alpha = Image.new("L", (lower.width, seam_height))
    alpha.putdata([round(255 * (1 - y / max(1, seam_height - 1)) ** 1.35) for y in range(seam_height) for _ in range(lower.width)])
    transitioned = lower.copy()
    transitioned.paste(edge, (0, 0), alpha)
    return transitioned


def compose(args: argparse.Namespace) -> None:
    source = load_rgb(args.source)
    lower = load_rgb(args.abstract)
    if lower.width != source.width:
        target_height = max(1, round(lower.height * source.width / lower.width))
        lower = lower.resize((source.width, target_height), Image.Resampling.LANCZOS)
    lower = blend_seam_from_source(source, lower, args.seam_ratio)

    canvas = Image.new("RGB", (source.width, source.height + lower.height))
    canvas.paste(source, (0, 0))
    canvas.paste(lower, (0, source.height))

    draw = ImageDraw.Draw(canvas)
    margin = max(24, round(source.width * 0.025))
    title_size = max(22, round(source.width * 0.018))
    meta_size = max(15, round(title_size * 0.55))
    title_font = font_for(title_size)
    meta_font = font_for(meta_size)
    lower_top = source.height
    x = margin
    title_y = lower_top + lower.height - margin - title_size
    meta_y = title_y - round(meta_size * 1.7)

    label = f"{args.number}   {args.date}"
    boxes = [draw.textbbox((x, meta_y), label, font=meta_font), draw.textbbox((x, title_y), args.title, font=title_font)]
    right = max(box[2] for box in boxes) + round(margin * 0.45)
    top = min(box[1] for box in boxes) - round(margin * 0.3)
    bottom = max(box[3] for box in boxes) + round(margin * 0.3)
    draw.rounded_rectangle((x - round(margin * 0.35), top, right, bottom), radius=max(4, margin // 8), fill=(12, 15, 17))
    draw.text((x, meta_y), label, font=meta_font, fill=(190, 184, 165))
    draw.text((x, title_y), args.title, font=title_font, fill=(238, 234, 220))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, format="PNG", optimize=True)
    verify(args.source, args.output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--abstract", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--number", default="NO. 001")
    parser.add_argument("--date", default="")
    parser.add_argument("--title", default="THE LONG RETURN")
    parser.add_argument("--seam-ratio", type=float, default=0.05, help="Transition depth as a fraction of source height; use 0 to disable")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if not args.verify_only and args.abstract is None:
        parser.error("--abstract is required unless --verify-only is used")
    if not 0 <= args.seam_ratio <= 0.12:
        parser.error("--seam-ratio must be between 0 and 0.12")
    return args


def main() -> int:
    args = parse_args()
    try:
        if args.verify_only:
            verify(args.source, args.output)
        else:
            compose(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

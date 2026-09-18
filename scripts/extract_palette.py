#!/usr/bin/env python3
"""Extract a compact, prompt-ready palette from a source photograph."""

from __future__ import annotations

import argparse
import colorsys
import json
from pathlib import Path

from PIL import Image


def hex_color(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{channel:02X}" for channel in rgb)


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (channel / 255 for channel in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def extract(path: Path, count: int) -> dict:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
    quantized = image.quantize(colors=count, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()
    histogram = sorted(quantized.getcolors() or [], reverse=True)
    colors = []
    for pixels, index in histogram:
        rgb = tuple(palette[index * 3:index * 3 + 3])
        h, s, _ = colorsys.rgb_to_hsv(*(channel / 255 for channel in rgb))
        colors.append({"hex": hex_color(rgb), "rgb": rgb, "share": round(pixels / (image.width * image.height), 4), "luminance": round(luminance(rgb), 4), "saturation": round(s, 4)})
    darkest = min(colors, key=lambda item: item["luminance"])
    lightest = max(colors, key=lambda item: item["luminance"])
    # Detect small vivid accents separately so a thin red rail or orange lamp is not
    # erased by the dominant neutral quantization.
    vivid = image.quantize(colors=max(64, count * 8), method=Image.Quantize.MEDIANCUT)
    vivid_palette = vivid.getpalette()
    accent_candidates = []
    for pixels, index in vivid.getcolors() or []:
        rgb = tuple(vivid_palette[index * 3:index * 3 + 3])
        _, saturation, value = colorsys.rgb_to_hsv(*(channel / 255 for channel in rgb))
        share = pixels / (image.width * image.height)
        if share >= 0.001:
            accent_candidates.append({"hex": hex_color(rgb), "rgb": rgb, "share": round(share, 4), "luminance": round(luminance(rgb), 4), "saturation": round(saturation, 4), "score": saturation * (0.25 + value) * share ** 0.08})
    accent = max(accent_candidates, key=lambda item: item["score"])
    accent.pop("score", None)
    return {"source": str(path), "dominant": colors[0], "shadow": darkest, "highlight": lightest, "accent": accent, "palette": colors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--colors", type=int, default=7, choices=range(5, 10))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = extract(args.source, args.colors)
    rendered = json.dumps(data, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()

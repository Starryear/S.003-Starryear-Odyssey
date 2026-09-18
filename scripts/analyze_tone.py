#!/usr/bin/env python3
"""Report tonal coverage and warn when an abstract panel is excessively crushed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageStat


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--max-near-black", type=float, default=0.25)
    parser.add_argument("--max-dead-black", type=float, default=0.08)
    args = parser.parse_args()

    with Image.open(args.image) as opened:
        image = opened.convert("L")
    image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
    histogram = image.histogram()
    total = image.width * image.height
    dead_black = sum(histogram[:9]) / total
    near_black = sum(histogram[:26]) / total
    dark = sum(histogram[:65]) / total
    mean = ImageStat.Stat(image).mean[0] / 255
    report = {
        "image": str(args.image),
        "mean_luminance": round(mean, 4),
        "dead_black_share_0_8": round(dead_black, 4),
        "near_black_share_0_25": round(near_black, 4),
        "dark_share_0_64": round(dark, 4),
        "passes": dead_black <= args.max_dead_black and near_black <= args.max_near_black,
    }
    print(json.dumps(report, indent=2))
    if not report["passes"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

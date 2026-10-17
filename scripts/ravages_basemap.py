"""Base map for the army tracker: the original drawing layers (4401 x 2037)
in their own colours, the height tiers, rivers, roads and settlement markers
laid over one another as drawn. The drawing leaves the sea transparent; it
gets the sea blue of the climate-target painting (#70a9ff).

    python -I scripts/ravages_basemap.py ravages/base.webp
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ORIG = Path(__file__).resolve().parents[1] / "data" / "source" / "original"
SEA = (112, 169, 255)


def main(out):
    base = Image.new("RGBA", Image.open(ORIG / "terrain.png").size, SEA + (255,))
    for layer in ("terrain", "rivers", "roads_settlements"):
        base = Image.alpha_composite(base, Image.open(ORIG / f"{layer}.png").convert("RGBA"))
    base.convert("RGB").save(out, quality=92, method=6)
    print(out, Path(out).stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1])

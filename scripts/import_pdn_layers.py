"""Save the political layers of the campaign map (a Paint.NET .pdn) as PNGs.

    pip install pypdn
    python3 -I scripts/import_pdn_layers.py MAP.pdn --out data/source/ravages_v8

Layers are matched by name; each is written as an RGBA PNG on the map's own
4401 x 2037 canvas (the canvas of data/source/original/). A manifest lists
the layers, their opaque pixel counts and the .pdn's SHA-256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

LAYERS = {
    "Roads & Trade Routes": "roads.png",
    "Cities/Towns/Forts": "settlements.png",
    "Borders": "borders.png",
    "Borders Fill": "borders_fill.png",
    "Polities": "polity_names.png",
    "Core Commandries": "commanderies_core.png",
    "Frontier Commandries": "commanderies_frontier.png",
    "Provinces Commandries": "commanderies_provinces.png",
    "Commandery IDS": "commandery_ids.png",
    "Imperial Legions": "legions.png",
    "08/03 Warlord Hexfill": "warlords.png",
    "Stronghold names": "stronghold_names.png",
    "Provinces Names": "province_names.png",
    "Region names": "region_names.png",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdn", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    import pypdn
    doc = pypdn.read(str(a.pdn))
    a.out.mkdir(parents=True, exist_ok=True)
    manifest = dict(source_sha256=hashlib.sha256(a.pdn.read_bytes()).hexdigest(), width=doc.width, height=doc.height,
                    layers={})
    for layer in doc.layers:
        name = LAYERS.get(layer.name)
        if name is None:
            continue
        image = np.asarray(layer.image)
        Image.fromarray(image).save(a.out / name, optimize=True)
        manifest["layers"][name] = dict(pdn_layer=layer.name, opaque_px=int((image[..., 3] > 0).sum()))
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(manifest, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Add the language-areas preview to an atlas as a 'Languages' topic (illustrative).

Three layers, from scripts/language_map_preview.compute on the atlas's own
(Earth-corrected, where it has one) climate:
  language_density      languages per 10,000 km2 (layer 2c on farmland, adopted;
                        FORGE density / 3,000 elsewhere, illustrative)
  language_territories  one random draw of territories, with the de jure borders
  language_edges        where language boundaries are likely (20 draws), with the
                        de jure borders

    python -I scripts/add_language_layers.py atlases/earth_fit [atlases/free_fit ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from harvest.export import color_image, tiers  # noqa: E402
from language_map_preview import compute  # noqa: E402

IDS = ("language_density", "language_territories", "language_edges")
SEA = np.array([214, 227, 240], np.uint8)


def save(rgb, meta, coast, path):
    image = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype("uint8")).resize((meta["width"], meta["height"]), Image.Resampling.NEAREST)
    px = np.asarray(image).copy()
    if coast is not None and coast.shape == px.shape[:2]:
        px[~coast] = SEA
    Image.fromarray(px).save(path, "WEBP", quality=88, method=4)


def add(atlas: Path):
    from rotclimate.geography import source_layers
    R = compute(atlas)
    data = atlas / "data"
    meta = json.loads((data / "atlas.json").read_text())
    blob = (data / "atlas.bin").read_bytes()
    s = meta["arrays"]["elev"]
    elev = np.frombuffer(blob, dtype=s["dtype"], count=int(np.prod(s["shape"])), offset=s["offset"]).reshape(s["shape"]).astype(float)
    try:
        coast = source_layers()["land"]
    except Exception:
        coast = None
    land, farm, dens, owner, freq, pol, edge_p, rows, summ = (R[k] for k in
        ("land", "farm", "dens", "owner", "freq", "pol", "edge_p", "rows", "summary"))
    h, w = land.shape
    border = ndi.binary_dilation(edge_p)
    # 1. density
    palette = ["#f6efe3", "#e9c99b", "#d4906a", "#a95a63", "#6b3561", "#33204d"]; lo, hi = 0.05, 10.0
    tier = tiers(palette, lo, hi, True)
    for suffix, use in (("", None), ("_tiers", tier)):
        rgb = color_image(np.where(land, dens * 1e4, np.nan).astype(np.float32), land, elev, palette, lo, hi, True, tiered=use)
        save(rgb, meta, coast, data / f"language_density{suffix}.webp")
    tier["file"] = "language_density_tiers.webp"
    # 2. one draw of territories
    n = int(owner.max()) + 1
    pal = np.random.default_rng(7).random((n, 3)) * 0.5 + 0.45
    rgb = np.ones((h, w, 3)) * SEA / 255.0
    own = land & (owner >= 0)
    rgb[own] = pal[owner[own]]
    hatch = land & (pol < 0) & ((np.add.outer(np.arange(h), np.arange(w)) % 10) == 0)
    rgb[hatch] = 0.35
    rgb[border] = 0.05
    save(rgb, meta, coast, data / "language_territories.webp")
    # 3. likely edges
    top = max(float(np.percentile(freq[land], 99)), 1e-6)
    g = 0.95 - 0.75 * np.clip(freq / top, 0, 1)
    rgb = np.stack([g, g, g * 0.98 + 0.02], -1)
    rgb[~land] = SEA / 255.0
    rgb[border] = [0.80, 0.10, 0.12]
    save(rgb, meta, coast, data / "language_edges.webp")

    top_pol = sorted(rows, key=lambda r: -r["land_km2"])[:5]
    pol_txt = "; ".join(f"{r['polity']} about {r['expected_languages']:.0f}" for r in top_pol)
    clim = "the Earth-corrected climate" if summ["climate"] == "corrected" else "the simulated climate"
    common = ("Illustrative, grown from the land, not from the polities. ")
    layers = [
        dict(id="language_density", file="language_density.webp", label="Language density", kind="ramp", group="Languages",
             unit="languages per 10,000 km² (expected)", vmin=lo, vmax=hi, stops=palette, log=True, tiers=tier, controls=[],
             note=common + f"On farmland: how many languages a region holds, from its warmth, rain, productivity, terrain "
                  f"ruggedness and the patchiness of its farmland, fitted on 2,733 Earth blocks of farmable land against "
                  f"Glottolog's languages and tested on each continent held out (R² 0.34 against 0.28 for climate alone; "
                  f"adopted). Where no crop takes root: FORGE forager density ÷ 3,000 people per language (not adopted on Earth). "
                  f"From {clim}. Expected on this map: {summ['expected_languages']:.0f} languages."),
        dict(id="language_territories", file="language_territories.webp", label="Language territories (one draw)", kind="categories",
             group="Languages", controls=[],
             items=[dict(color="#b9c7a0", label="one language's territory (colours arbitrary)"),
                    dict(color="#0d0d0d", label="de jure polity border"),
                    dict(color="#595959", label="hatched: unclaimed land")],
             note=common + "One random draw: language seeds placed at the expected density, each place joined to the seed "
                  "it reaches first on foot (Tobler's hiking speed; sea crossings three times slower). Another draw would "
                  "move every border; the counts hold. Expected languages within the largest claims: " + pol_txt + ". "
                  "Language families (who spread farming, from where) are not drawn: the map's hearths are the owner's choice."),
        dict(id="language_edges", file="language_edges.webp", label="Likely language boundaries", kind="ramp", group="Languages",
             unit=f"share of {summ['draws']} draws with a language edge within ~7 km (dark: often)", vmin=0.0,
             vmax=round(top, 2), stops=["#f2f2f0", "#8c8c8a", "#333331"], log=False, controls=[],
             note=common + f"Where boundaries fall again and again across random draws: mountain lines, straits and narrow "
                  f"necks. Red: de jure polity borders. Along them the share is "
                  f"{summ['language_edge_frequency_on_polity_borders']:.2f}, against {summ['language_edge_frequency_on_land']:.2f} "
                  f"over all land: on this low, open map the drawn borders mostly cut across language country rather than "
                  f"following natural divides."),
    ]
    meta["layers"] = [L for L in meta["layers"] if L["id"] not in IDS] + layers
    meta["languages"] = dict(summary={k: v for k, v in summ.items() if k != "polities"}, polities=summ["polities"],
                             method="reports/LANGUAGE_AREAS_20261101.md (layers 1-2d)")
    (data / "atlas.json").write_text(json.dumps(meta))
    print(atlas, f"{summ['expected_languages']:.0f} languages; climate {summ['climate']}; edge share {summ['language_edge_frequency_on_polity_borders']:.2f} vs {summ['language_edge_frequency_on_land']:.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("atlases", nargs="+", type=Path)
    a = ap.parse_args()
    for atlas in a.atlases:
        add(atlas)


if __name__ == "__main__":
    main()

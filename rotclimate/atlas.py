"""Export data + layer images for the interactive atlas page (atlas/index.html).

    python -m rotclimate.atlas --params calibration/best_params.json

Writes atlas/data/: layer images (.webp), atlas.json (metadata) and atlas.bin
(packed arrays the page reads with fetch()).
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from . import calendar as cal
from .config import REPO, SOURCE, Params
from .geography import (TARGET_CLASSES, TARGET_DRAW_COLORS, TARGET_LABELS, load_places,
                        source_layers, target_fullres)
from .koppen import CODES, COLORS, DESCRIPTIONS, rgb_image

ATLAS = REPO / "atlas"


def _save_webp(rgb, path, q=88):
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(path, "WEBP", quality=q,
                                                                      method=6)


def _cmap_img(field, cmap, vmin, vmax, fr, levels=None):
    import matplotlib.pyplot as plt

    from .render import OCEAN_RGB, hillshade

    x = np.clip((field - vmin) / (vmax - vmin), 0, 1)
    if levels is not None:
        x = np.floor(x * levels) / levels + 0.5 / levels
    rgb = plt.get_cmap(cmap)(x)[..., :3]
    hs = hillshade(fr.elev)
    rgb = rgb * (0.72 + 0.28 * 1.4 * hs[..., None]).clip(0, 1.1)
    rgb[~fr.land] = OCEAN_RGB
    return _overlay_rivers(rgb.clip(0, 1))


def _overlay_rivers(rgb):
    L = source_layers()
    out = rgb.copy()
    out[L["rivers"]] = out[L["rivers"]] * 0.35 + np.array([0.1, 0.3, 0.8]) * 0.65
    edge = ndi.binary_dilation(L["land"]) & ~L["land"]
    out[edge] = out[edge] * 0.4
    return out


def build(result, fr, ev, outdir: Path = ATLAS / "data"):
    from .render import shaded_rgb

    outdir.mkdir(parents=True, exist_ok=True)
    p = result.params
    g = result.grid
    k = fr.koppen()
    ix = fr._ix

    # ---------------------------------------------------------------- images
    _save_webp(_overlay_rivers(shaded_rgb(rgb_image(k).astype(float) / 255.0, fr, 0.42)),
               outdir / "koppen.webp")
    _save_webp(_cmap_img(ix["MAT"], "turbo", -10, 30, fr, 20), outdir / "t_annual.webp")
    _save_webp(_cmap_img(ix["Tcold"], "turbo", -25, 25, fr, 25), outdir / "t_cold.webp")
    _save_webp(_cmap_img(ix["Thot"], "turbo", 0, 40, fr, 20), outdir / "t_hot.webp")
    _save_webp(_cmap_img(np.log10(np.maximum(ix["MAP"], 50)), "YlGnBu", np.log10(100),
                         np.log10(3000), fr, 14), outdir / "precip.webp")
    tgt = target_fullres()
    timg = np.ones(tgt.shape + (3,)) * np.array([0.84, 0.89, 0.94])
    timg[fr.land] = 0.9
    import matplotlib.colors as mc

    for cid, col in TARGET_DRAW_COLORS.items():
        timg[tgt == cid] = mc.to_rgb(col)
    _save_webp(_overlay_rivers(timg), outdir / "target.webp")
    # labels overlay (transparent png with a soft halo)
    lab = np.array(Image.open(SOURCE / "labels.webp").convert("RGBA")).astype(float) / 255.0
    a = lab[..., 3]
    halo = ndi.grey_dilation(a, size=(3, 3)) * 0.75
    rgba = np.zeros(a.shape + (4,))
    rgba[..., :3] = (1 - a[..., None]) * 1.0          # white halo, black text
    rgba[..., 3] = np.maximum(a, halo)
    Image.fromarray((rgba * 255).astype(np.uint8)).save(outdir / "labels.png", optimize=True)

    # ---------------------------------------------------------------- arrays
    H, W = fr.H, fr.W
    cls = np.where(fr.land, k, 255).astype(np.uint8)[::2, ::2]
    elev = np.where(fr.land, fr.elev, 0).astype(np.uint16)[::2, ::2]
    # local-month climate on the coarse grid (map region), sea-level temps
    groups = cal.month_slices(result.nt)
    ny_m, nx_m = int(np.ceil(H / g.f)), int(np.ceil(W / g.f))
    sl = (slice(g.pad, g.pad + ny_m), slice(g.pad, g.pad + nx_m))
    fill_iy, fill_ix = fr._fill
    Tsl = result.Tsl[:, fill_iy, fill_ix]           # keep land values on coastal cells
    P = result.P[:, fill_iy, fill_ix]
    Tm = np.stack([Tsl[gi].mean(0)[sl] for gi in groups])
    Tlo = np.stack([Tsl[gi].min(0)[sl] for gi in groups])
    Thi = np.stack([Tsl[gi].max(0)[sl] for gi in groups])
    Pm = np.stack([P[gi].sum(0)[sl] * cal.YEAR_DAYS / result.nt for gi in groups])
    snow = np.stack([fr.coarse_fill(result.snow[gi].mean(0))[sl] for gi in groups])
    # thin to <= 260 cells wide to keep the download small
    step = max(1, int(np.ceil(nx_m / 260)))
    if step > 1:
        def thin(a):
            n, hh, ww = a.shape
            hh2, ww2 = hh // step * step, ww // step * step
            return a[:, :hh2, :ww2].reshape(n, hh2 // step, step, ww2 // step, step).mean(axis=(2, 4))
        Tm, Tlo, Thi, Pm, snow = map(thin, (Tm, Tlo, Thi, Pm, snow))
    cell_px = g.f * step
    arrays = {
        "cls": cls, "elev": elev,
        "Tm": np.round(Tm * 10).astype(np.int16), "Tlo": np.round(Tlo * 10).astype(np.int16),
        "Thi": np.round(Thi * 10).astype(np.int16),
        "P": np.round(np.clip(Pm, 0, 65000)).astype(np.uint16),
        "snow": np.round(np.clip(snow, 0, 65000)).astype(np.uint16),
    }
    offsets, blob = {}, bytearray()
    for name, arr in arrays.items():
        while len(blob) % 4:
            blob.append(0)
        offsets[name] = dict(offset=len(blob), dtype=str(arr.dtype), shape=list(arr.shape))
        blob += np.ascontiguousarray(arr).tobytes()
    (outdir / "atlas.bin").write_bytes(bytes(blob))

    places = [dict(name=pl["name"], x=pl["x"], y=pl["y"], kind=pl["kind"]) for pl in load_places()]
    present = [c for c in CODES if CODES.index(c) in set(np.unique(k[fr.land]).tolist())]
    share = {c: float((k[fr.land] == CODES.index(c)).mean()) for c in present}
    meta = dict(
        width=W, height=H, mi_per_px=p.map_width_mi / W, lapse=p.lapse_rate,
        lat_center=p.lat_center, km_per_deg=111.195, cell_px=cell_px,
        arrays=offsets,
        koppen=[dict(code=c, rgb=COLORS[c], desc=DESCRIPTIONS[c], share=share.get(c, 0.0))
                for c in CODES],
        present=present,
        months=[dict(name=m.name, short=m.short, season=m.season, days=cal.MONTH_DAYS)
                for m in cal.MONTHS] + [dict(name=cal.HOLY.name, short=cal.HOLY.short,
                                             season=cal.HOLY.season, days=cal.HOLY_DAYS)],
        places=places,
        zones=[dict(key=key, label=TARGET_LABELS[cid], color=TARGET_DRAW_COLORS[cid],
                    score=ev["per_class"][key]) for cid, key, _, _ in TARGET_CLASSES],
        score=ev["total"], accuracy=ev["accuracy"],
        world=dict(lat_south=p.lat_center - H * p.map_width_mi / W * 1.609344 / 111.195 / 2,
                   lat_north=p.lat_center + H * p.map_width_mi / W * 1.609344 / 111.195 / 2,
                   tilt=p.tilt, retrograde=p.retrograde, tier_tops=list(p.tier_tops),
                   beyond=dict(north=p.beyond_north_land, south=p.beyond_south_land,
                               west=p.beyond_west_land, east=p.beyond_east_land)
                   if p.beyond_style == "procedural" else None),
    )
    (outdir / "atlas.json").write_text(json.dumps(meta, ensure_ascii=False))
    return meta


def copy_media(outdir: Path = ATLAS / "data", src: Path = REPO / "output"):
    for name in ("year_temperature.gif", "year_precipitation.gif", "improvement.gif",
                 "tilt_sweep.gif", "spin_flip.gif", "surroundings.gif", "comparison.png",
                 "climographs.png", "world_context.png"):
        if (src / name).exists():
            shutil.copy(src / name, outdir / name)


def main():
    from .__main__ import simulate
    from .render import FullRes, fullres_memberships  # noqa: F401
    from .score import evaluate

    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default=str(REPO / "calibration" / "best_params.json"))
    ap.add_argument("--downsample", type=int, default=4)
    ap.add_argument("--steps", type=int, default=73)
    a = ap.parse_args()
    p = Params.from_json(a.params).replace(downsample=a.downsample, steps_per_year=a.steps,
                                           picard_iters=3)
    r = simulate(p)
    ev = evaluate(r)
    fr = FullRes(r)
    build(r, fr, ev)
    copy_media()
    print("atlas data written to", ATLAS / "data")


if __name__ == "__main__":
    main()

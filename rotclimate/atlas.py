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
from .geography import elevation_fullres
from .koppen import CODES, COLORS, DESCRIPTIONS, monthly_stats, rgb_image

ATLAS = REPO / "atlas"


class HiRes:
    """FullRes at `scale` x the source resolution (smooth coasts, sharp class
    edges): fields are interpolated from the model grid, temperature is
    re-cooled with the up-sampled terrain."""

    def __new__(cls, result, scale=3):
        from .render import FullRes

        class _Hi(FullRes):
            def __init__(self, r, sc):
                g = r.grid
                L = source_layers()
                H0, W0 = L["land"].shape
                self.r, self.H, self.W, self.px_m = r, H0 * sc, W0 * sc, 1770.0 / sc
                yy, xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
                sy, sx = (yy + 0.5) / sc - 0.5, (xx + 0.5) / sc - 0.5
                del yy, xx
                up = lambda a, o=1: ndi.map_coordinates(a, [sy, sx], order=o, mode="nearest")
                self.land = up(ndi.gaussian_filter(L["land"].astype(np.float32), 0.8)) > 0.5
                self.elev = np.where(self.land, up(elevation_fullres(p_tops(r)).astype(np.float32)), 0)
                self.rivers = up(ndi.gaussian_filter(L["rivers"].astype(np.float32), 0.6)) > 0.28
                tgt = target_fullres()
                stack = np.stack([up(ndi.gaussian_filter((tgt == c).astype(np.float32), 0.8))
                                  for c in range(8)])
                self.target = stack.argmax(0).astype(np.int8)
                del stack
                self.cy = (sy + 0.5) / g.f - 0.5 + g.pad
                self.cx = (sx + 0.5) / g.f - 0.5 + g.pad
                _, (iy, ix) = ndi.distance_transform_edt(~g.land, return_indices=True)
                self._fill = (iy, ix)
                self._lapse = r.params.lapse_rate

            def monthly(self):
                st = monthly_stats(self.r.Tsl, self.r.P, self.r.days, self.r.params.year_days,
                                   summer_solstice=self.r.params.winter_solstice_day
                                   + self.r.params.year_days / 2)
                Tm = np.stack([self.temperature(t).astype(np.float32) for t in st["Tm"]])
                Pm = np.stack([np.maximum(self.up(q), 0).astype(np.float32) for q in st["Pm"]])
                return Tm, Pm, st["summer"]

        return _Hi(result, scale)


def p_tops(r):
    return tuple(r.params.tier_tops)


def build_hires_layers(result, scale=3, outdir: Path = ATLAS / "data"):
    """Re-render every map layer at `scale` x resolution (same file names)."""
    from .render import shaded_rgb

    fr = HiRes(result, scale)
    k = fr.koppen()
    ix = fr._ix
    _save_webp(_overlay_rivers(shaded_rgb(rgb_image(k).astype(float) / 255.0, fr, 0.42), fr),
               outdir / "koppen.webp")
    _save_webp(_cmap_img(ix["MAT"], "turbo", -10, 30, fr, 20), outdir / "t_annual.webp")
    _save_webp(_cmap_img(ix["Tcold"], "turbo", -25, 25, fr, 25), outdir / "t_cold.webp")
    _save_webp(_cmap_img(ix["Thot"], "turbo", 0, 40, fr, 20), outdir / "t_hot.webp")
    _save_webp(_cmap_img(np.log10(np.maximum(ix["MAP"], 50)), "YlGnBu", np.log10(100),
                         np.log10(3000), fr, 14), outdir / "precip.webp")
    import matplotlib.colors as mc

    timg = np.ones(fr.target.shape + (3,), np.float32) * np.array([0.84, 0.89, 0.94], np.float32)
    timg[fr.land] = 0.9
    for cid, col in TARGET_DRAW_COLORS.items():
        timg[fr.target == cid] = mc.to_rgb(col)
    _save_webp(_overlay_rivers(timg, fr), outdir / "target.webp")
    agreement_layer(fr, outdir)


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
    hs = hillshade(fr.elev, getattr(fr, "px_m", 1770.0))
    rgb = rgb * (0.72 + 0.28 * 1.4 * hs[..., None]).clip(0, 1.1)
    rgb[~fr.land] = OCEAN_RGB
    return _overlay_rivers(rgb.clip(0, 1), fr)


def _overlay_rivers(rgb, fr=None):
    L = source_layers()
    riv = getattr(fr, "rivers", L["rivers"]) if fr is not None else L["rivers"]
    land = fr.land if fr is not None else L["land"]
    out = rgb.copy()
    out[riv & land] = out[riv & land] * 0.35 + np.array([0.1, 0.3, 0.8]) * 0.65
    edge = ndi.binary_dilation(land, iterations=max(1, land.shape[1] // 2000)) & ~land
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
    agreement_layer(fr, outdir)
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
    from .analogs import model_bins, reference_payload, reference_source

    T12, P12 = model_bins(Tsl, P, result.days, p.winter_solstice_day, p.year_days)
    T12, P12 = T12[(slice(None),) + sl], P12[(slice(None),) + sl]
    # thin to <= 260 cells wide to keep the download small
    step = max(1, int(np.ceil(nx_m / 260)))
    if step > 1:
        def thin(a):
            n, hh, ww = a.shape
            hh2, ww2 = hh // step * step, ww // step * step
            return a[:, :hh2, :ww2].reshape(n, hh2 // step, step, ww2 // step, step).mean(axis=(2, 4))
        Tm, Tlo, Thi, Pm, snow, T12, P12 = map(thin, (Tm, Tlo, Thi, Pm, snow, T12, P12))
    cell_px = g.f * step
    arrays = {
        "cls": cls, "elev": elev,
        "Tm": np.round(Tm * 10).astype(np.int16), "Tlo": np.round(Tlo * 10).astype(np.int16),
        "Thi": np.round(Thi * 10).astype(np.int16),
        "P": np.round(np.clip(Pm, 0, 65000)).astype(np.uint16),
        "snow": np.round(np.clip(snow, 0, 65000)).astype(np.uint16),
        "T12": np.round(T12 * 10).astype(np.int16),
        "P12": np.round(np.clip(P12, 0, 65000)).astype(np.uint16),
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
        layers=_layer_meta(),
        reference=reference_payload(), reference_source=reference_source(),
        solstice_day=p.winter_solstice_day,
        world=dict(lat_south=p.lat_center - H * p.map_width_mi / W * 1.609344 / 111.195 / 2,
                   lat_north=p.lat_center + H * p.map_width_mi / W * 1.609344 / 111.195 / 2,
                   tilt=p.tilt, retrograde=p.retrograde, tier_tops=list(p.tier_tops),
                   beyond=dict(north=p.beyond_north_land, south=p.beyond_south_land,
                               west=p.beyond_west_land, east=p.beyond_east_land)
                   if p.beyond_style == "procedural" else None),
    )
    (outdir / "atlas.json").write_text(json.dumps(meta, ensure_ascii=False))
    return meta


def agreement_layer(fr, outdir: Path = ATLAS / "data"):
    """Per-pixel agreement with each painted zone's rule (the accuracy map)."""
    import matplotlib.pyplot as plt

    from .render import OCEAN_RGB, fullres_memberships

    mem = fullres_memberships(fr)
    tgt = getattr(fr, "target", None)
    tgt = target_fullres() if tgt is None else tgt
    agree = np.full(tgt.shape, np.nan)
    for cid, key, _, _ in TARGET_CLASSES:
        m = (tgt == cid) & fr.land
        agree[m] = mem[key][m]
    rgb = np.ones(tgt.shape + (3,)) * 0.86
    ok = ~np.isnan(agree)
    rgb[ok] = plt.get_cmap("RdYlGn")(agree[ok])[:, :3]
    # thin dark outlines around the painted zones
    edge = np.zeros(tgt.shape, bool)
    for cid in range(1, 8):
        m = tgt == cid
        edge |= m & ~ndi.binary_erosion(m, iterations=2)
    rgb[edge & fr.land] *= 0.45
    rgb[~fr.land] = OCEAN_RGB
    _save_webp(_overlay_rivers(rgb, fr), outdir / "agreement.webp")


def _layer_meta():
    import matplotlib.pyplot as plt
    import matplotlib.colors as mc

    def stops(cmap, n=9):
        cm = plt.get_cmap(cmap)
        return [mc.to_hex(cm(i / (n - 1))) for i in range(n)]

    return [
        dict(id="koppen", file="koppen.webp", label="Köppen", kind="koppen"),
        dict(id="target", file="target.webp", label="Your zones", kind="target"),
        dict(id="agreement", file="agreement.webp", label="Match accuracy", kind="ramp",
             unit="agreement with your painted zone's rule (grey = unpainted land)",
             vmin=0, vmax=1, stops=stops("RdYlGn")),
        dict(id="t_annual", file="t_annual.webp", label="Mean temperature", kind="ramp",
             unit="°C, year mean", vmin=-10, vmax=30, stops=stops("turbo")),
        dict(id="t_cold", file="t_cold.webp", label="Coldest month", kind="ramp",
             unit="°C, coldest month", vmin=-25, vmax=25, stops=stops("turbo")),
        dict(id="t_hot", file="t_hot.webp", label="Warmest month", kind="ramp",
             unit="°C, warmest month", vmin=0, vmax=40, stops=stops("turbo")),
        dict(id="precip", file="precip.webp", label="Precipitation", kind="ramp",
             unit="mm per year", vmin=100, vmax=3000, log=True, stops=stops("YlGnBu")),
    ]


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

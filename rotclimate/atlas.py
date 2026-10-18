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
from .geography import elevation_fullres, map_lat_range
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
    zones_layer(fr, outdir)
    extra_layers(result, fr, outdir)


WIND_VMAX = 6.0      # m/s at the top of the wind layers' colour scale


def _season_steps(result, season):
    """Model steps in the local calendar's months of `season` ("winter", "summer")."""
    idx = [k for k, d in enumerate(result.days)
           if season in cal.month_of_day(int(d))[0].season.split(" / ")[0]]
    return np.array(idx, int)


def _land_grey(rgb, fr, sea_rgb=None):
    """Hill-shaded light grey on land (for maps of the sea)."""
    from .render import hillshade

    hs = hillshade(fr.elev, getattr(fr, "px_m", 1770.0))
    grey = (0.80 + 0.18 * (hs - 0.5))[..., None] * np.ones(3)
    return np.where(fr.land[..., None], grey, rgb if sea_rgb is None else sea_rgb)


def _wind_layer(result, fr, steps, path, vmax=WIND_VMAX, spacing_km=110.0):
    """Mean surface wind over `steps`: speed in colour (land hill-shaded) and
    arrows every ~spacing_km, length proportional to speed."""
    import matplotlib.pyplot as plt
    from PIL import ImageDraw

    from .render import hillshade

    g = result.grid
    u, v = result.u[steps].mean(0), result.v[steps].mean(0)
    sp = fr.up(np.hypot(u, v), land_fill=False)
    rgb = plt.get_cmap("YlGnBu")(0.08 + 0.8 * np.clip(sp / vmax, 0, 1))[..., :3]
    hs = hillshade(fr.elev, getattr(fr, "px_m", 1770.0))
    rgb = np.where(fr.land[..., None], rgb * (0.78 + 0.3 * hs[..., None]).clip(0, 1.08), rgb * 0.92 + 0.08)
    rgb = _overlay_rivers(rgb.clip(0, 1), fr)
    im = Image.fromarray((rgb * 255).astype(np.uint8))
    draw = ImageDraw.Draw(im)
    sc = fr.W / source_layers()["land"].shape[1]          # image px per source px
    step = max(1, int(round(spacing_km / g.cell_km)))
    seg = spacing_km / g.cell_km * g.f * sc                # arrow spacing in image px
    width = max(3, int(round(fr.W / 1700)))
    for i in range(g.pad + step // 2, g.ny - g.pad, step):
        for j in range(g.pad + step // 2, g.nx - g.pad, step):
            x = ((j - g.pad + 0.5) * g.f) * sc
            y = ((i - g.pad + 0.5) * g.f) * sc
            if not (0 <= x < fr.W and 0 <= y < fr.H):
                continue
            s = float(np.hypot(u[i, j], v[i, j]))
            if s < 0.3:
                continue
            L = seg * 0.85 * float(np.clip(s / vmax, 0.3, 1.0))     # weak winds still show their direction
            dx, dy = u[i, j] / s * L, -v[i, j] / s * L
            x0, y0, x1, y1 = x - dx / 2, y - dy / 2, x + dx / 2, y + dy / 2
            draw.line([(x0, y0), (x1, y1)], fill=(20, 24, 40), width=width)
            hl = max(4.0, 0.35 * L)
            for a in (2.6, -2.6):
                ca, sa = np.cos(a), np.sin(a)
                hx, hy = (dx * ca - dy * sa) / L * hl, (dx * sa + dy * ca) / L * hl
                draw.line([(x1, y1), (x1 + hx, y1 + hy)], fill=(20, 24, 40), width=width)
    im.save(path, "WEBP", quality=88, method=6)


def extra_layers(result, fr, outdir: Path):
    """More layers from the same run: seasonal and day/night swing, warm
    months, snow cover, rain season, wetness against Koppen's dry limit, the
    driest month, winds and sea temperature in local winter and summer, and
    temperature and rain month by month on the local calendar."""
    ix = fr._ix
    land = fr.land
    _save_webp(_cmap_img(ix["Thot"] - ix["Tcold"], "YlOrRd", 0, 40, fr, 20), outdir / "t_range.webp")
    from .diurnal import available, grid_dtr12

    if available():
        D = np.nanmean(grid_dtr12(result), axis=0)
        _save_webp(_cmap_img(fr.up(np.nan_to_num(D, nan=np.nanmean(D))), "OrRd", 4, 20, fr, 16),
                   outdir / "t_daynight.webp")
    _save_webp(_cmap_img(ix["Tmon10"].astype(float), "YlGn", 0, 12, fr, 12), outdir / "warm_months.webp")
    snow_months = 12.0 * (result.snow > 10.0).mean(0)
    _save_webp(_cmap_img(fr.up(snow_months), "PuBu", 0, 8, fr, 16), outdir / "snow.webp")
    share = np.where(ix["MAP"] > 30, ix["Psum"] / np.maximum(ix["MAP"], 1e-6), 0.5)
    _save_webp(_cmap_img(share, "PuOr", 0.1, 0.9, fr, 16), outdir / "rain_season.webp")
    _save_webp(_cmap_img(np.log10(np.clip(ix["aridity"], 0.1, 10)), "BrBG", np.log10(0.2), np.log10(5), fr, 14),
               outdir / "wetness.webp")
    _save_webp(_cmap_img(np.log10(np.maximum(ix["Pdry"], 1)), "YlGnBu", 0, np.log10(200), fr, 12),
               outdir / "p_driest.webp")
    import matplotlib.pyplot as plt

    for season in ("winter", "summer"):
        steps = _season_steps(result, season)
        _wind_layer(result, fr, steps, outdir / f"wind_{season}.webp")
        sea = fr.up(result.T[steps].mean(0), land_fill=False)
        rgb = plt.get_cmap("turbo")((np.clip((sea + 2) / 32, 0, 1) * 16).round() / 16)[..., :3]
        _save_webp(_overlay_rivers(_land_grey(rgb, fr), fr), outdir / f"sea_{season}.webp")
    # month by month on the local calendar (10 months + the holy days), at half size
    months = outdir / "months"
    months.mkdir(exist_ok=True)
    groups = cal.month_slices(result.nt)
    for k, gi in enumerate(groups):
        T = fr.temperature(result.Tsl[gi].mean(0))
        P = np.maximum(fr.up(result.P[gi].mean(0)), 0) * 30.0                 # mm per 30 days
        for name, rgb in (("t", _cmap_img(T, "turbo", -25, 40, fr, 26)),
                          ("p", _cmap_img(np.log10(np.maximum(P, 3)), "YlGnBu", np.log10(5), np.log10(500), fr, 14))):
            im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
            im.resize((fr.W // 2, fr.H // 2), Image.LANCZOS).save(months / f"{name}_{k + 1:02d}.webp", "WEBP",
                                                                  quality=85, method=6)
        del T, P


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


def _beyond_facts(p) -> dict:
    """Land fraction beyond each edge; the north and south edges may be split
    into west and east halves (physics v6, negative = same as the whole edge)."""
    b = dict(north=p.beyond_north_land, south=p.beyond_south_land,
             west=p.beyond_west_land, east=p.beyond_east_land)
    if p.beyond_northeast_land >= 0:
        b["northeast"] = p.beyond_northeast_land
    if p.beyond_southeast_land >= 0:
        b["southeast"] = p.beyond_southeast_land
    return b


def build(result, fr, ev, outdir: Path = ATLAS / "data"):
    from .render import shaded_rgb
    from .__main__ import numerical_settings

    outdir.mkdir(parents=True, exist_ok=True)
    p = result.params
    g = result.grid
    k = fr.koppen()
    ix = fr._ix

    # ---------------------------------------------------------------- images (3x)
    build_hires_layers(result, scale=3, outdir=outdir)
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
    # day/night range (Earth-trained, rotclimate/diurnal.py) in the same bins
    from .diurnal import available, grid_dtr12

    D12 = (np.nan_to_num(grid_dtr12(result)[:, fill_iy, fill_ix][(slice(None),) + sl], nan=0.0)
           if available() else np.zeros_like(T12))
    # thin to <= 260 cells wide to keep the download small
    step = max(1, int(np.ceil(nx_m / 260)))
    if step > 1:
        def thin(a):
            n, hh, ww = a.shape
            hh2, ww2 = hh // step * step, ww // step * step
            return a[:, :hh2, :ww2].reshape(n, hh2 // step, step, ww2 // step, step).mean(axis=(2, 4))
        Tm, Tlo, Thi, Pm, snow, T12, P12, D12 = map(thin, (Tm, Tlo, Thi, Pm, snow, T12, P12, D12))
    cell_px = g.f * step
    arrays = {
        "cls": cls, "elev": elev,
        "Tm": np.round(Tm * 10).astype(np.int16), "Tlo": np.round(Tlo * 10).astype(np.int16),
        "Thi": np.round(Thi * 10).astype(np.int16),
        "P": np.round(np.clip(Pm, 0, 65000)).astype(np.uint16),
        "snow": np.round(np.clip(snow, 0, 65000)).astype(np.uint16),
        "T12": np.round(T12 * 10).astype(np.int16),
        "P12": np.round(np.clip(P12, 0, 65000)).astype(np.uint16),
        "D12": np.round(D12 * 10).astype(np.int16),
    }
    offsets, blob = {}, bytearray()
    for name, arr in arrays.items():
        while len(blob) % 4:
            blob.append(0)
        offsets[name] = dict(offset=len(blob), dtype=str(arr.dtype), shape=list(arr.shape))
        blob += np.ascontiguousarray(arr).tobytes()
    (outdir / "atlas.bin").write_bytes(bytes(blob))
    save_settlements(outdir)

    places = [dict(name=pl["name"], x=pl["x"], y=pl["y"], kind=pl["kind"]) for pl in load_places()]
    places_climate_csv(result, fr, k, places, outdir / "places_climate.csv")
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
        numerics=numerical_settings(p),
        label_policy_audit=ev["label_policy_audit"],
        layers=_layer_meta(),
        zones_extra=[dict(label=lab, color=col) for _, lab, col in ZONE_EXTRAS],
        rivers_sim=river_segments(result),
        reference=reference_payload(), reference_source=reference_source(),
        towns=town_markers(),
        solstice_day=p.winter_solstice_day,
        north_bearing=p.north_bearing,
        world=dict(lat_south=map_lat_range(p)[0], lat_north=map_lat_range(p)[1],
                   north_bearing=p.north_bearing, tilt=p.tilt, retrograde=p.retrograde, tier_tops=list(p.tier_tops),
                   beyond=_beyond_facts(p) if p.beyond_style == "procedural" else None),
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


def river_segments(result, q_min=15.0):
    """Simulated river network as [x1, y1, x2, y2, q] segments in map pixels
    (cell centre to downstream cell centre, discharge q in m3/s)."""
    from .hydrology import analyse

    g = result.grid
    hyd = analyse(result)
    q = hyd["discharge"]
    recv = hyd["recv"]
    ny, nx = q.shape
    segs = []
    sel = np.flatnonzero((q.ravel() > q_min) & g.land.ravel() & g.inmap.ravel())
    for c in sel:
        r = recv[c]
        if r < 0:
            continue
        i, j = divmod(int(c), nx)
        ri, rj = divmod(int(r), nx)
        segs.append([round((j - g.pad + 0.5) * g.f, 1), round((i - g.pad + 0.5) * g.f, 1),
                     round((rj - g.pad + 0.5) * g.f, 1), round((ri - g.pad + 0.5) * g.f, 1),
                     round(float(q.ravel()[c]), 1)])
    return segs


# extra display categories for the simulated-zones map (not part of the score)
ZONE_EXTRAS = [
    (8, "Mountain (cold highland)", "#a3abb3"),
    (9, "Grassland (semi-dry margin)", "#cdbb88"),
    (10, "Transitional", "#dcdcdc"),
]


def zone_classes(mem, land, threshold=0.3, ix=None, elev=None, koppen=None):
    """Best-matching painted-zone type per pixel.

    With climate indices and elevation, high cold ground becomes "Mountain"
    (8) and places that fit none of the painted zones become "Grassland" (9, the
    semi-dry margins) or "Transitional" (10); otherwise they are 0."""
    from .score import display_zones

    return display_zones(mem, land, threshold, ix, elev, koppen)


def zones_layer(fr, outdir: Path = ATLAS / "data"):
    import matplotlib.colors as mc

    from .render import OCEAN_RGB, fullres_memberships, hillshade

    mem = fullres_memberships(fr)
    z = zone_classes(mem, fr.land, ix=fr._ix, elev=fr.elev, koppen=fr.koppen())
    rgb = np.ones(z.shape + (3,), np.float32) * 0.86
    for cid, col in list(TARGET_DRAW_COLORS.items()) + [(c, col) for c, _, col in ZONE_EXTRAS]:
        rgb[z == cid] = mc.to_rgb(col)
    hs = hillshade(fr.elev, getattr(fr, "px_m", 1770.0))
    rgb = rgb * (0.78 + 0.22 * 1.4 * hs[..., None]).clip(0, 1.1)
    rgb[~fr.land] = OCEAN_RGB
    _save_webp(_overlay_rivers(rgb.clip(0, 1), fr), outdir / "zones.webp")
    return z


def places_climate_csv(result, fr, k, places, path: Path):
    """Every named place's climate in the local calendar's months (as the
    click panel shows it): temperature at the place's own height, rain, and
    its Koppen class, latitude and elevation."""
    import csv

    g = result.grid
    groups = cal.month_slices(result.nt)
    fill_iy, fill_ix = fr._fill
    Tsl = result.Tsl[:, fill_iy, fill_ix]
    P = result.P[:, fill_iy, fill_ix]
    Tm = np.stack([Tsl[gi].mean(0) for gi in groups])
    Pm = np.stack([P[gi].sum(0) * cal.YEAR_DAYS / result.nt for gi in groups])
    months = cal.MONTHS + [cal.HOLY]
    lapse = result.params.lapse_rate
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "kind", "x_px", "y_px", "latitude", "elevation_m", "koppen", "mean_temp_C",
                    "rain_mm_year"] + [f"temp_C_{m.short}" for m in months] + [f"rain_mm_{m.short}" for m in months])
        for pl in places:
            x = int(min(max(round(pl["x"]), 0), fr.W - 1))
            y = int(min(max(round(pl["y"]), 0), fr.H - 1))
            i = int(min(max(round((y + 0.5) / g.f - 0.5 + g.pad), 0), g.ny - 1))
            j = int(min(max(round((x + 0.5) / g.f - 0.5 + g.pad), 0), g.nx - 1))
            h = float(fr.elev[y, x]) if fr.land[y, x] else 0.0
            T = Tm[:, i, j] - lapse * h / 1000.0
            R = Pm[:, i, j]
            days = np.array([cal.MONTH_DAYS] * len(cal.MONTHS) + [cal.HOLY_DAYS], float)
            w.writerow([pl["name"], pl["kind"], round(pl["x"], 1), round(pl["y"], 1), round(float(g.lat[i, j]), 2),
                        round(h), CODES[k[y, x]] if fr.land[y, x] and k[y, x] >= 0 else "sea",
                        round(float((T * days).sum() / days.sum()), 1), round(float(R.sum()))]
                       + [round(float(v), 1) for v in T] + [round(float(v)) for v in R])


def _layer_meta():
    import matplotlib.pyplot as plt
    import matplotlib.colors as mc

    def stops(cmap, n=9):
        cm = plt.get_cmap(cmap)
        return [mc.to_hex(cm(i / (n - 1))) for i in range(n)]

    base = [
        dict(id="koppen", file="koppen.webp", label="Köppen", kind="koppen"),
        dict(id="target", file="target.webp", label="Your zones", kind="target"),
        dict(id="zones", file="zones.webp", label="Simulated zones", kind="zones"),
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
    from .diurnal import available

    months = [m.name for m in cal.MONTHS] + [cal.HOLY.name]
    frames = lambda v: [f"months/{v}_{k + 1:02d}.webp" for k in range(len(months))]
    extra = [
        dict(id="t_range", file="t_range.webp", label="Seasonal swing", kind="ramp", group="Temperature",
             unit="°C, warmest minus coldest month", vmin=0, vmax=40, stops=stops("YlOrRd")),
        *([dict(id="t_daynight", file="t_daynight.webp", label="Day/night swing", kind="ramp", group="Temperature",
                unit="°C, average daily range over the year (Earth-trained)", vmin=4, vmax=20,
                stops=stops("OrRd"))] if available() else []),
        dict(id="warm_months", file="warm_months.webp", label="Warm months", kind="ramp", group="Temperature",
             unit="months above 10 °C (forest needs at least one)", vmin=0, vmax=12, stops=stops("YlGn")),
        dict(id="snow", file="snow.webp", label="Snow cover", kind="ramp", group="Temperature",
             unit="months with lasting snow on the ground", vmin=0, vmax=8, stops=stops("PuBu")),
        dict(id="rain_season", file="rain_season.webp", label="Rain season", kind="ramp", group="Water",
             unit="% of the year's rain in the warm half-year (orange: winter rain, purple: summer rain)",
             vmin=10, vmax=90, stops=stops("PuOr")),
        dict(id="wetness", file="wetness.webp", label="Wetness", kind="ramp", group="Water",
             unit="rain ÷ Köppen's dry limit (below 1 steppe, below 0.5 desert)", vmin=0.2, vmax=5, log=True,
             stops=stops("BrBG")),
        dict(id="p_driest", file="p_driest.webp", label="Driest month", kind="ramp", group="Water",
             unit="mm in the driest month", vmin=1, vmax=200, log=True, stops=stops("YlGnBu")),
        dict(id="wind_winter", file="wind_winter.webp", label="Winds, winter", kind="ramp", group="Air and sea",
             unit="m/s, mean surface wind over the winter months (arrows: direction)", vmin=0, vmax=WIND_VMAX,
             stops=[mc.to_hex(plt.get_cmap("YlGnBu")(0.08 + 0.8 * i / 8)) for i in range(9)]),
        dict(id="wind_summer", file="wind_summer.webp", label="Winds, summer", kind="ramp", group="Air and sea",
             unit="m/s, mean surface wind over the summer months (arrows: direction)", vmin=0, vmax=WIND_VMAX,
             stops=[mc.to_hex(plt.get_cmap("YlGnBu")(0.08 + 0.8 * i / 8)) for i in range(9)]),
        dict(id="sea_winter", file="sea_winter.webp", label="Sea, winter", kind="ramp", group="Air and sea",
             unit="°C, air over the sea in the winter months", vmin=-2, vmax=30, stops=stops("turbo")),
        dict(id="sea_summer", file="sea_summer.webp", label="Sea, summer", kind="ramp", group="Air and sea",
             unit="°C, air over the sea in the summer months", vmin=-2, vmax=30, stops=stops("turbo")),
        dict(id="t_month", file=frames("t")[0], label="Temperature", kind="ramp", group="Month by month",
             unit="°C, month mean", vmin=-25, vmax=40, stops=stops("turbo"), frames=frames("t"),
             frame_labels=months),
        dict(id="p_month", file=frames("p")[0], label="Rain", kind="ramp", group="Month by month",
             unit="mm per 30 days", vmin=5, vmax=500, log=True, stops=stops("YlGnBu"), frames=frames("p"),
             frame_labels=months),
    ]
    for d in base:
        d.setdefault("group", "Climate" if d["id"] in ("koppen", "target", "zones", "agreement") else
                     "Temperature" if d["id"].startswith("t_") else "Water")
    order = ["Climate", "Temperature", "Water", "Air and sea", "Month by month"]
    return sorted(base + extra, key=lambda d: order.index(d["group"]))     # stable: keeps order within a group


SETTLEMENTS = REPO / "data" / "source" / "settlements.png"     # lossless, 2.2x the map's pixels


def _settlement_pixels(path: Path = SETTLEMENTS):
    """RGBA array of the settlement layer and its scale (layer px per map px)."""
    a = np.array(Image.open(path).convert("RGBA"))
    return a, a.shape[1] / 2000.0, a.shape[0] / 926.0


def town_markers() -> list:
    """The pixel-art settlement markers (coloured towns and cities, white
    villages): [x, y, half-height] of each, in map pixels."""
    from .geography import settlement_markers

    return [[round(float(x), 1), round(float(y), 1), round(float(h), 2)] for x, y, h in settlement_markers()]


def save_settlements(outdir: Path = ATLAS / "data"):
    """The settlement layer as vector pixel art: every pixel becomes an exact
    square (runs of one colour merged, one path per colour), so it stays
    sharp at any zoom and keeps its exact colours."""
    if not SETTLEMENTS.exists():
        return
    a, _, _ = _settlement_pixels()
    h, w = a.shape[:2]
    on = a[..., 3] > 0
    key = (a[..., 0].astype(np.int64) << 16) | (a[..., 1].astype(np.int64) << 8) | a[..., 2]
    paths = {}
    for y in range(h):
        xs = np.flatnonzero(on[y])
        if not xs.size:
            continue
        ks = key[y, xs]
        brk = np.flatnonzero((np.diff(xs) != 1) | (np.diff(ks) != 0)) + 1
        for seg in np.split(np.arange(xs.size), brk):
            x0, x1, k = xs[seg[0]], xs[seg[-1]] + 1, int(ks[seg[0]])
            paths.setdefault(k, []).append(f"M{x0} {y}h{x1 - x0}v1h-{x1 - x0}z")
    body = "".join(f'<path fill="#{k:06x}" d="{"".join(d)}"/>' for k, d in sorted(paths.items()))
    (outdir / "towns.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'preserveAspectRatio="none" shape-rendering="crispEdges">{body}</svg>')


def copy_media(outdir: Path = ATLAS / "data", src: Path = REPO / "output"):
    for name in ("year_temperature.gif", "year_precipitation.gif", "improvement.gif",
                 "tilt_sweep.gif", "spin_flip.gif", "surroundings.gif", "comparison.png",
                 "climographs.png", "world_context.png"):
        if (src / name).exists():
            shutil.copy(src / name, outdir / name)


def main():
    from .__main__ import simulate, add_render_numerics, render_params
    from .render import FullRes, fullres_memberships  # noqa: F401
    from .score import evaluate

    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default=str(REPO / "calibration" / "best_params.json"))
    add_render_numerics(ap)
    a = ap.parse_args()
    p = render_params(Params.from_json(a.params), a)
    r = simulate(p)
    ev = evaluate(r)
    fr = FullRes(r)
    build(r, fr, ev)
    copy_media()
    print("atlas data written to", ATLAS / "data")


if __name__ == "__main__":
    main()

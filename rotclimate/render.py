"""Maps, GIFs and charts.

Model fields live on a coarse grid; for display they are interpolated back
to the 2000 x 926 source resolution.  Temperature is interpolated at sea
level and then re-cooled with the full-resolution terrain, so mountains keep
their sharp cold crests (and their own Koppen classes).
"""
from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LightSource, ListedColormap, BoundaryNorm  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from . import calendar as cal  # noqa: E402
from .geography import (TARGET_CLASSES, TARGET_DRAW_COLORS, TARGET_LABELS,  # noqa: E402
                        elevation_fullres, load_places, source_layers, target_fullres)
from .koppen import (CODES, COLORS, DESCRIPTIONS, classify, climate_indices,  # noqa: E402
                     monthly_stats, rgb_image)

OCEAN_RGB = np.array([214, 228, 240]) / 255.0
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})


# --------------------------------------------------------------------- fields
class FullRes:
    """Interpolates a Result's coarse fields onto the source pixels."""

    def __init__(self, result):
        self.r = result
        g = result.grid
        L = source_layers()
        self.land = L["land"]
        self.H, self.W = self.land.shape
        self.elev = elevation_fullres(result.params.tier_tops)
        yy, xx = np.mgrid[0:self.H, 0:self.W]
        self.cy = (yy + 0.5) / g.f - 0.5 + g.pad
        self.cx = (xx + 0.5) / g.f - 0.5 + g.pad
        # index of the nearest coarse land cell (to keep sea values off the coast)
        _, (iy, ix) = ndi.distance_transform_edt(~g.land, return_indices=True)
        self._fill = (iy, ix)
        self._lapse = result.params.lapse_rate

    def coarse_fill(self, a):
        iy, ix = self._fill
        return a[iy, ix]

    def up(self, a, land_fill=True):
        """Bilinear interpolation of a coarse 2-D field to full resolution."""
        a = np.asarray(a, float)
        sea = ndi.map_coordinates(a, [self.cy, self.cx], order=1, mode="nearest")
        if not land_fill:
            return sea
        lnd = ndi.map_coordinates(self.coarse_fill(a), [self.cy, self.cx], order=1, mode="nearest")
        return np.where(self.land, lnd, sea)

    def temperature(self, Tsl):
        return np.where(self.land, self.up(Tsl) - self._lapse * self.elev / 1000.0,
                        self.up(Tsl, land_fill=False))

    def monthly(self):
        r = self.r
        st = monthly_stats(r.Tsl, r.P, r.days, r.params.year_days,
                           summer_solstice=r.params.winter_solstice_day + r.params.year_days / 2)
        Tm = np.stack([self.temperature(t) for t in st["Tm"]])
        Pm = np.stack([np.maximum(self.up(p), 0) for p in st["Pm"]])
        return Tm, Pm, st["summer"]

    def koppen(self):
        if not hasattr(self, "_k"):
            Tm, Pm, summer = self.monthly()
            self._k = classify(Tm, Pm, summer)
            self._ix = climate_indices(Tm, Pm, summer)
            self._Tm, self._Pm = Tm, Pm
        return self._k


def hillshade(elev, dx=1770.0):
    ls = LightSource(azdeg=315, altdeg=40)
    return ls.hillshade(elev, vert_exag=0.02, dx=dx, dy=dx)


def decorate(ax, fr: FullRes, rivers=True, labels=True, roads=False, coast=True):
    L = source_layers()
    if rivers:
        riv = np.zeros(L["rivers"].shape + (4,))
        riv[L["rivers"]] = (0.12, 0.35, 0.85, 0.85)
        ax.imshow(riv, interpolation="nearest")
    if roads:
        rd = L["roads"].astype(float) / 255.0
        rd[..., 3] *= 0.55
        ax.imshow(rd, interpolation="nearest")
    if coast:
        ax.contour(fr.land, levels=[0.5], colors="#222", linewidths=0.6)
    if labels:
        from .config import SOURCE

        lab = np.array(Image.open(SOURCE / "labels.webp").convert("RGBA")).astype(float) / 255.0
        txt = np.zeros_like(lab)
        txt[..., 3] = lab[..., 3]
        # white halo for legibility
        halo = ndi.grey_dilation(lab[..., 3], size=(3, 3))
        hal = np.ones_like(lab)
        hal[..., 3] = halo * 0.55
        ax.imshow(hal, interpolation="bilinear")
        ax.imshow(txt, interpolation="bilinear")
    ax.set_xlim(0, fr.W)
    ax.set_ylim(fr.H, 0)
    ax.axis("off")


def shaded_rgb(rgb, fr: FullRes, strength=0.45):
    hs = hillshade(fr.elev, getattr(fr, "px_m", 1770.0))
    out = rgb * ((1 - strength) + strength * 1.6 * hs[..., None]).clip(0, 1.25)
    out = out.clip(0, 1)
    out[~fr.land] = OCEAN_RGB
    return out


def koppen_legend(ax_or_fig, classes, loc="lower left", ncol=1, fontsize=9, **kw):
    present = [c for c in CODES if c in classes]
    handles = [Patch(color=np.array(COLORS[c]) / 255, label=f"{c}  {DESCRIPTIONS[c]}") for c in present]
    return ax_or_fig.legend(handles=handles, loc=loc, ncol=ncol, fontsize=fontsize, frameon=True, **kw)


def scale_bar(ax, fr, miles=200):
    px = miles / (fr.r.params.map_width_mi / fr.W)
    x0, y0 = 60, fr.H - 40
    ax.plot([x0, x0 + px], [y0, y0], color="k", lw=3)
    ax.text(x0 + px / 2, y0 - 12, f"{miles} mi", ha="center", va="bottom", fontsize=9)


def lat_ticks(ax, fr):
    g = fr.r.grid
    lat0 = fr.r.params.lat_center
    km_px = fr.r.params.map_width_mi * 1.609344 / fr.W
    for lat in range(int(np.floor(lat0 - 9)), int(np.ceil(lat0 + 9)) + 1):
        y = fr.H / 2 - (lat - lat0) * 111.195 / km_px
        if 5 < y < fr.H - 5:
            ax.axhline(y, color="k", lw=0.3, alpha=0.35, ls=(0, (4, 4)))
            ax.text(fr.W - 4, y - 3, f"{lat}°{'N'}", ha="right", va="bottom", fontsize=8, alpha=0.7)
    del g


# --------------------------------------------------------------------- maps
def koppen_map(fr: FullRes, path, title=None, labels=True):
    k = fr.koppen()
    rgb = rgb_image(k).astype(float) / 255.0
    rgb = shaded_rgb(rgb, fr)
    fig = plt.figure(figsize=(25, 10.2), dpi=100)
    ax = fig.add_axes([0.0, 0.0, 0.80, 0.95])
    ax.imshow(rgb, interpolation="nearest")
    decorate(ax, fr, labels=labels)
    lat_ticks(ax, fr)
    scale_bar(ax, fr)
    present = set(CODES[i] for i in np.unique(k[fr.land]) if i >= 0)
    lax = fig.add_axes([0.80, 0.0, 0.2, 0.95])
    lax.axis("off")
    koppen_legend(lax, present, loc="center left", fontsize=11, title="Köppen-Geiger", title_fontsize=13)
    fig.suptitle(title or "Köppen-Geiger climate classification", fontsize=18, y=0.985)
    fig.savefig(path)
    plt.close(fig)


def comparison_map(fr: FullRes, mem, path, title=None):
    """Target zones vs. simulated Koppen, plus a per-pixel agreement map."""
    k = fr.koppen()
    tgt = target_fullres()
    fig = plt.figure(figsize=(26, 13.2), dpi=80)
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.08, wspace=0.03,
                          left=0.01, right=0.99, top=0.93, bottom=0.01)
    ax0, ax1, ax2 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 0])
    lax = fig.add_subplot(gs[1, 1])
    lax.axis("off")
    # target
    img = np.ones(tgt.shape + (3,))
    img[fr.land] = 0.9
    for cid, col in TARGET_DRAW_COLORS.items():
        img[tgt == cid] = matplotlib.colors.to_rgb(col)
    ax0.imshow(img)
    decorate(ax0, fr, rivers=False, labels=False)
    ax0.set_title("Target (your painted zones)", fontsize=16)
    # model koppen with target outlines
    rgb = shaded_rgb(rgb_image(k).astype(float) / 255.0, fr, 0.35)
    ax1.imshow(rgb)
    for cid, col in TARGET_DRAW_COLORS.items():
        ax1.contour(tgt == cid, levels=[0.5], colors=[col], linewidths=2.4)
    decorate(ax1, fr, rivers=False, labels=False)
    ax1.set_title("Simulated Köppen (outlines = target zones)", fontsize=16)
    # agreement
    agree = np.full(tgt.shape, np.nan)
    for cid, key, _, _ in TARGET_CLASSES:
        m = (tgt == cid) & fr.land
        agree[m] = mem[key][m]
    cm = plt.get_cmap("RdYlGn")
    a_img = np.ones(tgt.shape + (3,))
    a_img[fr.land] = 0.88
    ok = ~np.isnan(agree)
    a_img[ok] = cm(agree[ok])[:, :3]
    ax2.imshow(a_img)
    decorate(ax2, fr, rivers=False, labels=False)
    ax2.set_title("Agreement with each zone's rule (green = match, red = miss)", fontsize=16)
    # legends
    present = set(CODES[i] for i in np.unique(k[fr.land]) if i >= 0)
    l1 = lax.legend(handles=[Patch(color=TARGET_DRAW_COLORS[c], label=TARGET_LABELS[c]) for c in range(1, 8)],
                    loc="upper left", fontsize=12, title="Target zones", title_fontsize=13,
                    bbox_to_anchor=(0.0, 1.0))
    lax.add_artist(l1)
    koppen_legend(lax, present, loc="upper left", fontsize=11, ncol=2,
                  bbox_to_anchor=(0.0, 0.55), title="Köppen classes present", title_fontsize=13)
    sm = plt.cm.ScalarMappable(cmap=cm, norm=plt.Normalize(0, 1))
    cax = fig.add_axes([0.52, 0.05, 0.2, 0.018])
    fig.colorbar(sm, cax=cax, orientation="horizontal", label="agreement with the zone's rule")
    if title:
        fig.suptitle(title, fontsize=19)
    fig.savefig(path)
    plt.close(fig)


def zones_map(fr: FullRes, mem, path, title=None):
    """Your painted zones next to the whole simulated map classified into them."""
    from .atlas import zone_classes

    z = zone_classes(mem, fr.land)
    tgt = target_fullres()
    fig, axs = plt.subplots(1, 2, figsize=(26, 6.8), dpi=80)
    for ax, cls, ttl in ((axs[0], tgt, "Your painted zones"),
                         (axs[1], z, "Simulated climate, classified into your zones")):
        img = np.ones(cls.shape + (3,)) * 0.86
        for cid, col in TARGET_DRAW_COLORS.items():
            img[cls == cid] = matplotlib.colors.to_rgb(col)
        img = shaded_rgb(img, fr, 0.3) if cls is z else img
        img[~fr.land] = OCEAN_RGB
        ax.imshow(img)
        decorate(ax, fr, rivers=False, labels=False)
        ax.set_title(ttl, fontsize=16)
    handles = [Patch(color=TARGET_DRAW_COLORS[c], label=TARGET_LABELS[c]) for c in range(1, 8)]
    handles.append(Patch(color="0.86", label="unpainted / fits none of the zones"))
    fig.legend(handles=handles, loc="lower center", ncol=8, fontsize=11, frameon=False)
    if title:
        fig.suptitle(title, fontsize=18)
    fig.tight_layout(rect=(0, 0.06, 1, 0.97))
    fig.savefig(path)
    plt.close(fig)


def fullres_memberships(fr: FullRes):
    from .score import memberships

    fr.koppen()
    return memberships(fr._ix)


def field_map(fr, field, path, title, cmap, vmin, vmax, unit, levels=None, extend="both"):
    fig = plt.figure(figsize=(21, 10), dpi=95)
    ax = fig.add_axes([0.0, 0.0, 0.92, 0.94])
    if levels is not None:
        norm = BoundaryNorm(levels, plt.get_cmap(cmap).N, extend=extend)
        im = ax.imshow(np.ma.masked_where(~fr.land, field), cmap=cmap, norm=norm, interpolation="nearest")
    else:
        im = ax.imshow(np.ma.masked_where(~fr.land, field), cmap=cmap, vmin=vmin, vmax=vmax)
    hs = hillshade(fr.elev)
    shade = np.zeros(hs.shape + (4,))
    shade[..., 3] = np.where(fr.land, (1 - hs) * 0.35, 0)
    ax.imshow(shade)
    ax.set_facecolor(OCEAN_RGB)
    decorate(ax, fr)
    lat_ticks(ax, fr)
    cax = fig.add_axes([0.93, 0.1, 0.015, 0.75])
    fig.colorbar(im, cax=cax, label=unit)
    fig.suptitle(title, fontsize=17, y=0.985)
    fig.savefig(path)
    plt.close(fig)


# --------------------------------------------------------------------- gifs
def _fig_to_pil(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def save_gif(frames, path, ms=120, colors=192):
    """Animated GIF with ONE palette shared by every frame, so legends and
    unchanged areas stay pixel-identical instead of flickering."""
    w, h = frames[0].size
    pick = frames[:: max(1, len(frames) // 12)]
    sample = Image.new("RGB", (w, h * len(pick)))
    for i, f in enumerate(pick):
        sample.paste(f.convert("RGB"), (0, i * h))
    palette = sample.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = [f.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=ms, loop=0, optimize=False)


def _wind_grid(fr, spacing_km=110):
    g = fr.r.grid
    step = max(1, int(round(spacing_km / g.cell_km)))
    sl = (slice(g.pad, g.pad + int(fr.H / g.f) + 1, step), slice(g.pad, g.pad + int(fr.W / g.f) + 1, step))
    ii, jj = np.mgrid[sl]
    X = (jj - g.pad + 0.5) * g.f - 0.5
    Y = (ii - g.pad + 0.5) * g.f - 0.5
    ok = (X >= 0) & (X < fr.W) & (Y >= 0) & (Y < fr.H)
    return sl, X, Y, ok


def season_gif(fr: FullRes, path, var="T", stride=1, scale=0.42, ms=110):
    r = fr.r
    frames = []
    sl, X, Y, ok = _wind_grid(fr)
    H, W = fr.H, fr.W
    hs = hillshade(fr.elev)
    if var == "T":
        cmap, vmin, vmax, unit = "turbo", -25, 40, "°C"
    else:
        cmap, vmin, vmax, unit = "YlGnBu", 0, 12, "mm / day"
    hdr = 1.15                                   # header strip height (inches)
    map_h = H * scale / 100
    mf = map_h / (map_h + hdr)                   # fraction of the figure used by the map
    for k in range(0, r.nt, stride):
        day = r.days[k]
        fig = plt.figure(figsize=(W * scale / 100, map_h + hdr), dpi=100)
        ax = fig.add_axes([0, 0, 1, mf])
        if var == "T":
            f = fr.temperature(r.Tsl[k])
            ax.imshow(f, cmap=cmap, vmin=vmin, vmax=vmax)
            sea = np.zeros((H, W, 4))
            sea[~fr.land] = (1, 1, 1, 0.35)
            ax.imshow(sea)
        else:
            f = np.maximum(fr.up(r.P[k]), 0)
            img = plt.get_cmap(cmap)(np.clip((f - vmin) / (vmax - vmin), 0, 1))
            img[~fr.land] = (*OCEAN_RGB, 1)
            sea = ~fr.land
            img[sea, :3] = img[sea, :3] * 0.0 + plt.get_cmap(cmap)(np.clip(f[sea] / vmax, 0, 1))[:, :3] * 0.5 + 0.5 * OCEAN_RGB
            snow = fr.up(r.snow[k]) if r.snow is not None else None
            if snow is not None:
                sn = np.clip(snow / 40.0, 0, 1) * fr.land
                img[..., :3] = img[..., :3] * (1 - sn[..., None]) + sn[..., None]
            ax.imshow(img)
        shade = np.zeros(hs.shape + (4,))
        shade[..., 3] = np.where(fr.land, (1 - hs) * 0.3, 0)
        ax.imshow(shade)
        u = r.u[k][sl]
        v = r.v[k][sl]
        ax.quiver(X[ok], Y[ok], u[ok], -v[ok], color="k", alpha=0.55, scale=220, width=0.0016,
                  headwidth=4)
        decorate(ax, fr, rivers=False, labels=False)
        m, d, _ = cal.month_of_day(int(day))
        tax = fig.add_axes([0, mf, 1, 1 - mf])
        tax.set_xlim(0, 1)
        tax.set_ylim(0, 1)
        tax.axis("off")
        name = "Temperature & surface wind" if var == "T" else "Precipitation, snow cover & wind"
        # line 1: date (left) and what is shown (right)
        tax.text(0.012, 0.80, cal.date_label(day), fontsize=13, va="center", weight="bold")
        tax.text(0.988, 0.80, name, fontsize=10.5, va="center", ha="right")
        # line 2: season (left), unit + colour scale (right)
        tax.text(0.012, 0.47, m.season.capitalize(), fontsize=10.5, va="center", style="italic",
                 color="#444")
        tax.text(0.585, 0.47, unit, fontsize=9, va="center", ha="right", color="#444")
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin, vmax))
        cax = fig.add_axes([0.60, mf + (1 - mf) * 0.36, 0.385, (1 - mf) * 0.16])
        cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
        cb.ax.tick_params(labelsize=7, pad=1, length=2)
        # line 3: year progress
        tax.add_patch(plt.Rectangle((0.012, 0.06), 0.976, 0.07, color="#ddd"))
        tax.add_patch(plt.Rectangle((0.012, 0.06), 0.976 * day / cal.YEAR_DAYS, 0.07, color="#555"))
        frames.append(_fig_to_pil(fig))
        plt.close(fig)
    save_gif(frames, path, ms=ms, colors=128)


def koppen_frames_gif(items, path, ms=900, scale=0.5):
    """items: list of (FullRes, caption) -> animated Koppen maps with one fixed
    legend (every class that appears in any frame, same place every frame)."""
    frames = []
    classes = [fr.koppen() for fr, _ in items]
    present = [c for c in CODES
               if any(CODES.index(c) in set(np.unique(k[fr.land]).tolist())
                      for k, (fr, _) in zip(classes, items))]
    leg_w = 2.6                                   # inches for the legend column
    for (fr, caption), k in zip(items, classes):
        rgb = shaded_rgb(rgb_image(k).astype(float) / 255.0, fr, 0.35)
        H, W = fr.H, fr.W
        map_w, map_h = W * scale / 100, H * scale / 100
        fig = plt.figure(figsize=(map_w + leg_w, map_h + 0.7), dpi=100)
        ax = fig.add_axes([0, 0, map_w / (map_w + leg_w), map_h / (map_h + 0.7)])
        ax.imshow(rgb, interpolation="nearest")
        tgt = target_fullres()
        for cid, col in TARGET_DRAW_COLORS.items():
            ax.contour(tgt == cid, levels=[0.5], colors=[col], linewidths=1.3)
        decorate(ax, fr, rivers=False, labels=False)
        fig.text(0.01, 0.97, caption, fontsize=12, va="top", weight="bold")
        lax = fig.add_axes([map_w / (map_w + leg_w), 0, leg_w / (map_w + leg_w), map_h / (map_h + 0.7)])
        lax.axis("off")
        handles = [Patch(color=np.array(COLORS[c]) / 255, label=f"{c}  {DESCRIPTIONS[c]}") for c in present]
        handles.append(Patch(facecolor="none", edgecolor="#555", label="outlines: your zones"))
        lax.legend(handles=handles, loc="center left", fontsize=6.6, frameon=False,
                   handlelength=1.2, borderaxespad=0.3, labelspacing=0.35)
        frames.append(_fig_to_pil(fig))
        plt.close(fig)
    save_gif(frames, path, ms=ms)


# --------------------------------------------------------------------- charts
def climograph_panel(ax, fr: FullRes, x, y, name):
    """Local-calendar climograph (10 months + holy days) at a source pixel."""
    r = fr.r
    g = r.grid
    cy, cx = y / g.f - 0.5 + g.pad, x / g.f - 0.5 + g.pad
    iy, ix = int(round(cy)), int(round(cx))
    if not g.land[iy, ix]:
        (iy, ix) = (fr._fill[0][iy, ix], fr._fill[1][iy, ix])
    elev = fr.elev[int(y), int(x)]
    T = r.Tsl[:, iy, ix] - r.params.lapse_rate * elev / 1000.0
    P = r.P[:, iy, ix]
    groups = cal.month_slices(r.nt)
    Tm = np.array([T[gi].mean() for gi in groups])
    Tmax = np.array([T[gi].max() for gi in groups])
    Tmin = np.array([T[gi].min() for gi in groups])
    Pm = np.array([P[gi].sum() * cal.YEAR_DAYS / r.nt for gi in groups])
    names = [m.short for m in cal.MONTHS] + [cal.HOLY.short]
    xs = np.arange(len(names))
    widths = [1.0] * 10 + [0.43]
    ax2 = ax.twinx()
    ax2.bar(xs, Pm, width=np.array(widths) * 0.8, color="#3b7dd8", alpha=0.75)
    ax.fill_between(xs, Tmin, Tmax, color="#e4572e", alpha=0.18, lw=0)
    ax.plot(xs, Tm, color="#e4572e", lw=2.2, marker="o", ms=3)
    ax.axhline(0, color="k", lw=0.5, alpha=0.4)
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)
    ax.set_ylim(-25, 40)
    ax2.set_ylim(0, max(250, Pm.max() * 1.15))
    ax.set_xticks(xs)
    ax.set_xticklabels(names, fontsize=7, rotation=90)
    ax.tick_params(axis="y", labelsize=7, colors="#c0392b")
    ax2.tick_params(axis="y", labelsize=7, colors="#2c5aa0")
    k = fr.koppen()[int(y), int(x)]
    code = CODES[k] if k >= 0 else "?"
    ax.set_title(f"{name}  ·  {code}\n{T.mean():.0f}°C · {Pm.sum():.0f} mm · {elev:.0f} m",
                 fontsize=9)
    from .analogs import model_bins, top_analogs

    T12, P12 = model_bins(T, P, r.days, r.params.winter_solstice_day, r.params.year_days)
    an = top_analogs(T12, P12, 3)
    ax.text(0.5, -0.36, "feels like: " + ", ".join(a["name"] for a in an),
            transform=ax.transAxes, ha="center", va="top", fontsize=7.5, style="italic",
            color="#333")


def climographs(fr: FullRes, names, path, ncols=6):
    import unicodedata

    def norm(t):
        t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().casefold()
        return "".join(ch for ch in t if ch.isalnum()).replace("l", "i")

    places = {norm(p["name"]): p for p in load_places()}
    sel = [places[norm(n)] for n in names if norm(n) in places]
    nrows = int(np.ceil(len(sel) / ncols))
    fig, axs = plt.subplots(nrows, ncols, figsize=(3.3 * ncols, 3.5 * nrows), dpi=100)
    for ax, pl in zip(np.ravel(axs), sel):
        climograph_panel(ax, fr, pl["x"], pl["y"], pl["name"])
    for ax in np.ravel(axs)[len(sel):]:
        ax.axis("off")
    from .analogs import reference_source

    fig.suptitle("Climographs in the local calendar  (line: mean temp °C, band: weekly range, "
                 "bars: precipitation mm per month)", fontsize=12)
    fig.text(0.5, 0.003, f"'feels like' = closest real cities by seasonal temperature and "
             f"rainfall curves ({reference_source()}, seasons aligned to the solstice)",
             ha="center", fontsize=8, color="#555")
    fig.tight_layout(rect=(0, 0.015, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def monthly_atlas(fr: FullRes, path, var="T"):
    r = fr.r
    groups = cal.month_slices(r.nt)
    fig, axs = plt.subplots(4, 3, figsize=(24, 15), dpi=80)
    if var == "T":
        cmap, vmin, vmax, unit = "turbo", -25, 40, "°C"
    else:
        cmap, vmin, vmax, unit = "YlGnBu", 0, 300, "mm / month (35 days)"
    for ax, (i, gi) in zip(axs.flat, enumerate(groups)):
        name = (cal.MONTHS + [cal.HOLY])[i]
        if var == "T":
            f = fr.temperature(r.Tsl[gi].mean(0))
        else:
            f = np.maximum(fr.up(r.P[gi].mean(0)), 0) * 35.0
        ax.imshow(np.ma.masked_where(~fr.land, f), cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_facecolor(OCEAN_RGB)
        decorate(ax, fr, rivers=False, labels=False)
        ax.set_title(f"{name.name}  ({name.season})", fontsize=13)
    axs.flat[-1].axis("off")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin, vmax))
    fig.colorbar(sm, ax=axs.flat[-1], orientation="horizontal", fraction=0.4, label=unit)
    fig.suptitle(("Mean temperature" if var == "T" else "Precipitation") + " by local month",
                 fontsize=20)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def insolation_chart(params, path):
    from .astronomy import insolation_table

    lats = np.linspace(0, 90, 181)
    days = np.arange(cal.YEAR_DAYS) + 0.5
    Q = insolation_table(params, lats, days)
    fig, ax = plt.subplots(figsize=(11, 5), dpi=100)
    im = ax.contourf(days, lats, Q.T, levels=np.arange(0, 560, 20), cmap="inferno")
    fig.colorbar(im, label="daily mean sunlight at top of atmosphere (W/m²)")
    lat0, half = params.lat_center, params.map_height_mi * 1.609344 / 111.195 / 2
    ax.axhspan(lat0 - half, lat0 + half, color="w", alpha=0.25)
    ax.text(5, lat0, "  the map", color="w", va="center", fontsize=11, weight="bold")
    starts = [i * cal.MONTH_DAYS for i in range(10)] + [350]
    ax.set_xticks([s + 17.5 for s in starts[:10]] + [357.5])
    ax.set_xticklabels([m.name.replace(" ", "\n") for m in cal.MONTHS] + ["Holy\nDays"], fontsize=7)
    for s in starts[1:]:
        ax.axvline(s, color="w", lw=0.4, alpha=0.5)
    ax.set_ylabel("latitude (°N)")
    ax.set_title(f"Sunlight through the local year (axial tilt {params.tilt:.1f}°)")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def context_map(result, path, title=None):
    """The whole simulated domain: the map plus the generated surroundings,
    each coloured by its (coarse) Koppen class, sea shaded by mean SST."""
    r = result
    g = r.grid
    st = monthly_stats(r.T, r.P, r.days, r.params.year_days,
                       summer_solstice=r.params.winter_solstice_day + r.params.year_days / 2)
    k = classify(st["Tm"], st["Pm"], st["summer"])
    rgb = rgb_image(k).astype(float) / 255.0
    sst = r.Tsl.mean(0)
    cm = plt.get_cmap("Blues_r")
    sea = cm(np.clip((sst + 5) / 40.0, 0, 1) * 0.55 + 0.35)[..., :3]
    img = np.where(g.land[..., None], rgb, sea)
    img = np.where(g.inmap[..., None], img, img * 0.82 + 0.18 * 0.9)
    fig, ax = plt.subplots(figsize=(14, 14 * g.ny / g.nx + 0.6), dpi=100)
    ax.imshow(img, interpolation="nearest")
    ax.contour(g.land, levels=[0.5], colors="#333", linewidths=0.5)
    y0, x0 = g.pad - 0.5, g.pad - 0.5
    h, w = g.inmap.sum(0).max(), g.inmap.sum(1).max()
    ax.add_patch(plt.Rectangle((x0, y0), w, h, fill=False, ec="red", lw=1.8))
    ax.text(x0 + 4, y0 + 6, "your map", color="red", fontsize=11, weight="bold", va="top")
    # wind arrows (annual mean) for orientation
    step = max(1, int(round(220 / g.cell_km)))
    yy, xx = np.mgrid[step // 2:g.ny:step, step // 2:g.nx:step]
    ax.quiver(xx, yy, r.u.mean(0)[yy, xx], -r.v.mean(0)[yy, xx], color="k", alpha=0.45,
              scale=120, width=0.0018)
    for lat in range(int(g.lat.min()) + 1, int(g.lat.max()) + 1):
        if lat % 5 == 0:
            yrow = np.interp(lat, g.lat[::-1, 0], np.arange(g.ny)[::-1])
            ax.axhline(yrow, color="k", lw=0.4, alpha=0.4, ls=":")
            ax.text(g.nx - 2, yrow - 1, f"{lat}°N", ha="right", fontsize=8, alpha=0.7)
    present = set(CODES[i] for i in np.unique(k[g.land]) if i >= 0)
    koppen_legend(ax, present, loc="lower left", fontsize=6.5, ncol=2)
    ax.set_axis_off()
    ax.set_title(title or "The map in its (unknown, procedurally generated) surroundings — "
                 "Köppen on land, mean sea temperature offshore, mean surface wind", fontsize=11)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)

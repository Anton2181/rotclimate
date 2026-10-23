"""Maps of the old-core term: where the settlement model puts people with and
without it, against HYDE 3.3 (200 CE), the Han AD 2 census and Roman towns.

    python3 -I scripts/plot_population_cores.py --earth output/land_people/earth/earth.npz \
        --hyde data/cache/hyde33/popc_ce_200.tif --shp data/cache/han_ad2/shp/ResearchArea \
        --xlsx data/cache/hanson2016/cities.xlsx --out output/population_cores

Writes cores_vs_hyde.png (densities and log ratios to HYDE at 1 degree) and
han_roman.png (Han commanderies and Roman town density against the model).
Every model field is scaled to HYDE's total over the window (patterns only).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, LogNorm, TwoSlopeNorm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from han_census_check import commanderies, used  # noqa: E402
from harvest_earth_hyde import earth_stages  # noqa: E402
from hyde_compare import blocks, hyde_at  # noqa: E402
from population_cores import CORE_SETS, core_term, travel_distance  # noqa: E402

SURFACE, INK, INK2, LAND0 = "#fcfcfb", "#0b0b0b", "#52514e", "#e7e6e2"
SEQ = LinearSegmentedColormap.from_list("blue", ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"])
DIV = LinearSegmentedColormap.from_list("div", ["#184f95", "#3987e5", "#9ec5f4", "#f0efec", "#f2a3a2", "#e34948", "#a82a2a"])
plt.rcParams.update({"font.size": 9, "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.edgecolor": "#c3c2b7", "figure.facecolor": SURFACE,
                     "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--earth", required=True); ap.add_argument("--hyde", required=True)
    ap.add_argument("--shp", required=True); ap.add_argument("--xlsx", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    z = np.load(a.earth)
    lat, lon, land = z["lat"], z["lon"], z["land"]
    km2, stages = earth_stages(z)
    base = np.nan_to_num(stages["+ malaria (settlement base)"])
    cores = CORE_SETS["cradles + Rome"]
    cored = base * core_term(travel_distance(z, cores, 2.0, 1.0, 1.0), 800)
    H = blocks(hyde_at(a.hyde, lat, lon) * land)
    A = blocks(km2 * land); L = blocks(land.astype(float))
    ok = (L >= 72) & (H > 0)
    fields = {}
    for name, f in (("settlement base", base), ("× old cores", cored)):
        M = blocks(f * km2 * land)
        fields[name] = M * H[ok].sum() / M[ok].sum()
    blat = lat[:A.shape[0] * 12].reshape(-1, 12).mean(1); blon = lon[:A.shape[1] * 12].reshape(-1, 12).mean(1)
    ext = [blon[0] - 0.5, blon[-1] + 0.5, blat[-1] - 0.5, blat[0] + 0.5]

    def dens(M):
        d = np.where(ok, M / np.maximum(A, 1e-9), np.nan)
        return np.clip(d, 0.05, None)

    def panel(ax, img, norm, cmap, title):
        ax.imshow(np.where(L >= 72, 0, np.nan), extent=ext, cmap=LinearSegmentedColormap.from_list("l", [LAND0, LAND0]))
        im = ax.imshow(img, extent=ext, norm=norm, cmap=cmap, interpolation="nearest")
        ax.set_title(title, loc="left", fontsize=10, color=INK)
        ax.set_xlim(-12, 125); ax.set_ylim(0, 56); ax.set_aspect(1.25)
        ax.tick_params(labelsize=7, length=2)
        for nm, (la, lo) in cores.items():
            ax.plot(lo, la, marker="o", ms=5, mfc="none", mec=INK, mew=1.2)
            ax.annotate(nm, (lo, la), xytext=(3, 3), textcoords="offset points", fontsize=7, color=INK)
        return im

    fig, axs = plt.subplots(2, 2, figsize=(13, 7.4), constrained_layout=True)
    dn = LogNorm(0.1, 300)
    panel(axs[0, 0], dens(H), dn, SEQ, "HYDE 3.3, 200 CE (people per km², 1° blocks)")
    im = panel(axs[0, 1], dens(fields["× old cores"]), dn, SEQ,
               "Settlement model × old cores (cradles + Rome, travel cost, L 800 km)")
    fig.colorbar(im, ax=axs[0, :], shrink=0.8, label="people per km² (each map scaled to HYDE's total)")
    rn = TwoSlopeNorm(0, -1.5, 1.5)
    for ax, name, label in ((axs[1, 0], "settlement base", "Settlement model alone ÷ HYDE"),
                            (axs[1, 1], "× old cores", "With old cores ÷ HYDE")):
        r = np.where(ok, np.log10((fields[name] / np.maximum(A, 1e-9) + 1) / (H / np.maximum(A, 1e-9) + 1)), np.nan)
        im2 = panel(ax, np.clip(r, -1.5, 1.5), rn, DIV, f"{label} (log10; red = model too full)")
    cb = fig.colorbar(im2, ax=axs[1, :], shrink=0.8, label="log10 (model + 1) / (HYDE + 1)")
    cb.set_ticks([-1.5, -1, -0.5, 0, 0.5, 1, 1.5]); cb.set_ticklabels(["÷30", "÷10", "÷3", "1", "×3", "×10", "×30"])
    fig.suptitle("Where people lived around 200 CE: environment alone, and with distance from the oldest cores",
                 x=0.01, ha="left", fontsize=12, color=INK)
    fig.savefig(out / "cores_vs_hyde.png", dpi=110)
    plt.close(fig)

    # Han commanderies and Roman towns
    from roman_cities_check import towns
    rows = used(commanderies(a.shp, lat, lon, km2))
    obs = np.array([x["pop"] for x in rows]); area = np.array([x["area_km2"] for x in rows])
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.6), constrained_layout=True)
    for ax, (name, f) in zip(axs[:2], (("Settlement model alone", base), ("× old cores (Central Plain core)", cored))):
        m = np.array([float((f[i, j] * km2[i, j] * land[i, j]).sum()) for i, j in (x["idx"] for x in rows)])
        m = m * obs.sum() / m.sum()
        ax.loglog(obs / area, m / area, "o", ms=5, mfc="#3987e5", mec=SURFACE, mew=0.8, alpha=0.9)
        ax.plot([0.3, 500], [0.3, 500], color=INK2, lw=1, ls="--")
        from scipy.stats import spearmanr
        rho = spearmanr(m / area, obs / area).statistic
        ax.set_title(f"Han AD 2, 98 commanderies: {name}\nrank correlation {rho:.2f}", loc="left", fontsize=10)
        ax.set_xlabel("census people per km²"); ax.set_ylabel("model people per km²")
        ax.set_xlim(0.3, 500); ax.set_ylim(0.3, 500)
    ax = axs[2]
    win = (lon >= -10) & (lon <= 45); wlat = (lat >= 28) & (lat <= 56)
    sub = (cored * land)[np.ix_(wlat, win)]
    vals = sub[land[np.ix_(wlat, win)] & (sub > 0)]
    lo_, hi_ = np.percentile(vals, [5, 99.5])
    ax.imshow(np.where(land[np.ix_(wlat, win)], np.clip(sub, lo_, None), np.nan),
              extent=[lon[win][0], lon[win][-1], lat[wlat][-1], lat[wlat][0]], norm=LogNorm(lo_, hi_),
              cmap=LinearSegmentedColormap.from_list("pale", ["#f0efec", "#cde2fb", "#86b6ef", "#3987e5", "#256abf"]))
    T = towns(a.xlsx)
    ax.scatter([t["lon"] for t in T], [t["lat"] for t in T], s=[max(2, min(40, t["area_ha"] / 6)) for t in T],
               c="#e34948", edgecolors=SURFACE, linewidths=0.4, alpha=0.85)
    ax.set_xlim(-10, 45); ax.set_ylim(28, 56); ax.set_aspect(1.25)
    ax.set_title("Roman towns of AD 150 (Hanson 2016, red; size = area)\nover the model with old cores (blue)",
                 loc="left", fontsize=10)
    ax.tick_params(labelsize=7, length=2)
    fig.savefig(out / "han_roman.png", dpi=110)
    plt.close(fig)
    print("wrote", out / "cores_vs_hyde.png", out / "han_roman.png")


if __name__ == "__main__":
    main()

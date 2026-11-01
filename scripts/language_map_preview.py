"""Language areas from below on the fantasy map: layer 2c's language density, one draw of territories, and the polities (layer 4 preview).

Language density on farmland is layer 2c's C1 (refitted on all Earth blocks;
calibration/language_areas_20261101/plan_2c.json) from the map's corrected
climate, elevation and crop rules. On land where no crop roots (s < 0.05) it
is FORGE density / 3,000 people (layer 1b's split size; illustrative, layer 1
was not adopted). Territories are one random draw: seeds placed with that
density, each land cell joined to the seed it reaches first on foot (Tobler,
with sea crossings at three times flat-land time). The polities are the drawn
de jure claims, used only at the end.

    python -I scripts/language_map_preview.py atlases/earth_fit OUT_DIR [--seed 0]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.sparse import coo_matrix  # noqa: E402
from scipy.sparse.csgraph import dijkstra  # noqa: E402

from figure_lifeways import load as load_foraging  # noqa: E402

SUMMARY_2C = ROOT / "output/language_areas_20261101/layer2c/summary.json"
CROP_KEYS = ("kcal_wheat", "kcal_barley", "kcal_millet", "kcal_rice", "kcal_dates")
SRC_W = 4401.0
BLOCK_KM = 2 * 111.195           # a 2 deg block, north-south
SEA_FACTOR = 3.0


def packet(data: Path, name: str, meta_name: str | None = None, sub="corrected"):
    base = data / sub if (data / sub / f"{name}.bin").exists() else data
    meta = json.loads((base / (meta_name or f"{name}.json")).read_text())
    blob = (base / f"{name}.bin").read_bytes()
    out = {}
    for k, s in meta["arrays"].items():
        n = int(np.prod(s["shape"]))
        a = np.frombuffer(blob, dtype=s["dtype"], count=n, offset=s.get("offset_bytes", s.get("offset", 0))).reshape(s["shape"])
        v = a.astype(float) * s.get("scale", 1.0) + s.get("offset", 0.0) if "scale" in s else a.astype(float)
        if "nodata" in s:
            v = np.where(a == s["nodata"], np.nan, v)
        out[k] = v
    return out, meta


def window_stats(v, land, ny, nx):
    """Mean and standard deviation of v over land within an ny x nx window."""
    m = land.astype(float)
    x = np.where(land, np.nan_to_num(v), 0.0)
    cnt = ndi.uniform_filter(m, (ny, nx), mode="constant")
    s1 = ndi.uniform_filter(x, (ny, nx), mode="constant")
    s2 = ndi.uniform_filter(x * x, (ny, nx), mode="constant")
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = s1 / cnt
        sd = np.sqrt(np.maximum(s2 / cnt - mean ** 2, 0))
    return mean, sd


def travel_graph(elev, land, cell_km):
    h, w = land.shape
    idx = np.arange(h * w).reshape(h, w)
    flat = 6.0 * np.exp(-3.5 * 0.05)
    rows, cols, cost = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        ys = np.arange(0, h - dy); xa = np.arange(max(0, -dx), w - max(0, dx))
        a = idx[np.ix_(ys, xa)]; b = idx[np.ix_(ys + dy, xa + dx)]
        dist = cell_km * np.hypot(dy, dx)
        ea, eb = elev[np.ix_(ys, xa)], elev[np.ix_(ys + dy, xa + dx)]
        both = land[np.ix_(ys, xa)] & land[np.ix_(ys + dy, xa + dx)]
        slope = (eb - ea) / 1000.0 / dist
        sea = SEA_FACTOR * dist / flat
        t_ab = np.where(both, dist / (6.0 * np.exp(-3.5 * np.abs(slope + 0.05))), sea)
        t_ba = np.where(both, dist / (6.0 * np.exp(-3.5 * np.abs(-slope + 0.05))), sea)
        rows += [a.ravel(), b.ravel()]; cols += [b.ravel(), a.ravel()]; cost += [t_ab.ravel(), t_ba.ravel()]
    return coo_matrix((np.concatenate(cost), (np.concatenate(rows), np.concatenate(cols))), shape=(h * w, h * w)).tocsr()


def polity_raster(atlas: Path, shape, land):
    from matplotlib.path import Path as MPath
    h, w = shape
    claims = json.loads((atlas / "data/vectors/dejure_claims.geojson").read_text())["features"]
    sc = w / SRC_W
    yy, xx = np.mgrid[0:h, 0:w]
    pts = np.column_stack([xx.ravel() + 0.5, yy.ravel() + 0.5])
    lab = -np.ones(h * w, int); names, colours, rings = [], [], []
    for i, ft in enumerate(claims):
        geom = ft["geometry"]; polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        names.append(ft["properties"]["polity"]); colours.append(ft["properties"].get("colour", "#000"))
        for poly in polys:
            ring = np.array(poly[0]) * sc; rings.append(ring)
            inside = MPath(ring).contains_points(pts)
            lab[inside & (lab < 0)] = i
    lab = lab.reshape(h, w)
    # slivers of unclaimed cells between adjoining claims or along their
    # coasts (drawing gaps, not frontier land) join the nearest claim
    comp, n = ndi.label((lab < 0) & land)
    sizes = ndi.sum(np.ones_like(comp), comp, index=np.arange(1, n + 1))
    small = np.isin(comp, 1 + np.flatnonzero(sizes < 600))
    _, (iy, ix) = ndi.distance_transform_edt(lab < 0, return_indices=True)  # nearest claimed cell
    lab = np.where(small, lab[iy, ix], lab)
    return lab, names, colours, rings


def compute(atlas: Path, seed: int = 0, draws: int = 20):
    """Language density, one draw of territories, the edge frequency over more
    draws and the polity comparison, from an atlas's corrected climate (or its
    raw one when it has none)."""
    data = atlas / "data"
    A = json.loads((data / "atlas.json").read_text())
    sub = "corrected" if (data / "corrected" / "atlas.bin").exists() else ""
    blob = (data / sub / "atlas.bin").read_bytes()

    def arr(k):
        s = A["arrays"][k]; n = int(np.prod(s["shape"]))
        return np.frombuffer(blob, dtype=s["dtype"], count=n, offset=s["offset"]).reshape(s["shape"])
    cls = arr("cls"); land = cls != 255
    elev = arr("elev").astype(float)
    h, w = land.shape
    T = np.kron(arr("T12").astype(float).mean(0) / 10.0, np.ones((4, 4)))[:h, :w]
    P = np.kron(arr("P12").astype(float).sum(0), np.ones((4, 4)))[:h, :w]
    H, _ = packet(data, "harvest")
    summ = json.loads(SUMMARY_2C.read_text()); C1 = summ["models"]["C1"]
    best = np.nanmax(np.stack([np.nan_to_num(H[k]) for k in CROP_KEYS]), 0) * np.nan_to_num(H["arable"])
    s = np.clip(best / summ["s_ref_kcal"], 0, 1)
    npp = np.nan_to_num(H["npp"])
    cell_km = A["mi_per_px"] * 1.609344 * (A["width"] / w)
    lat = A["lat_center"] + ((h / 2) - (np.arange(h) + 0.5)) * cell_km / A["km_per_deg"]
    coslat = np.cos(np.radians(lat))[:, None]
    ny = int(round(BLOCK_KM / cell_km)); nx = int(round(BLOCK_KM * np.cos(np.radians(A["lat_center"])) / cell_km))
    Tm, _ = window_stats(T, land, ny, nx); Pm, _ = window_stats(P, land, ny, nx); Nm, _ = window_stats(npp, land, ny, nx)
    _, Esd = window_stats(elev, land, ny, nx); Sm, Ssd = window_stats(s, land, ny, nx)
    X = dict(T=Tm, logP=np.log10(np.maximum(Pm, 1.0)), logNPP=np.log10(np.maximum(Nm, 1.0)), rug=np.log10(1.0 + Esd), s_std=Ssd, s_mean=Sm)
    y = C1["coef_all"]["intercept"] + sum(C1["coef_all"][k] * (X[k] - C1["mu"][k]) / C1["sd"][k] for k in C1["mu"])
    block_km2 = BLOCK_KM ** 2 * coslat
    farm = land & (s >= 0.05) & (Sm >= 0.05)
    dens_farm = np.expm1(y) / block_km2                 # languages per km2
    F = load_foraging(data, sub)
    fd = np.kron(np.nan_to_num(F["density_people_km2"]), np.ones((4, 4)))[:h, :w]
    dens = np.where(farm, dens_farm, np.where(land, fd / 3000.0, 0.0))
    area = cell_km ** 2
    expected = float((dens * area)[land].sum()); exp_farm = float((dens * area)[farm].sum())
    G = travel_graph(elev, land, cell_km)

    def draw(seed):
        rng = np.random.default_rng(seed)
        seeds = np.flatnonzero((rng.random(h * w) < (dens * area).ravel()) & land.ravel())
        dist, _, src = dijkstra(G, directed=True, indices=seeds, min_only=True, return_predecessors=True)
        owner = -np.ones(h * w, int)
        pos = {c: i for i, c in enumerate(seeds)}
        owner[np.isfinite(dist)] = [pos[c] for c in src[np.isfinite(dist)]]
        return np.where(land.ravel(), owner, -1).reshape(h, w), len(seeds)

    # only edges between two land cells (coasts would count for both)
    def edges(lab):
        e = np.zeros_like(land)
        dx = (lab[:, 1:] != lab[:, :-1]) & land[:, 1:] & land[:, :-1]
        dy = (lab[1:, :] != lab[:-1, :]) & land[1:, :] & land[:-1, :]
        e[:, 1:] |= dx; e[:, :-1] |= dx; e[1:, :] |= dy; e[:-1, :] |= dy
        return e
    owner, n_drawn = draw(seed)
    freq = np.zeros((h, w)); counts = []
    for k in range(draws):
        o, nk = draw(1000 + k); counts.append(nk)
        freq += ndi.binary_dilation(edges(o), iterations=2)
    freq /= draws
    pol, names, colours, rings = polity_raster(atlas, (h, w), land)
    edge_p = edges(np.where(land, pol, -2))
    rows = []
    for i, nm in enumerate(names):
        cells = (pol == i) & land
        if not cells.any():
            continue
        langs, cnt = np.unique(owner[cells], return_counts=True)
        share = cnt / cnt.sum()
        rows.append(dict(polity=nm, land_km2=float(cells.sum() * area), expected_languages=float((dens * area)[cells].sum()),
                         drawn_languages_any=int(len(langs)), largest_language_share=float(share.max()),
                         effective_languages=float(1.0 / np.sum(share ** 2)), farmland_share=float(farm[cells].mean())))
    unclaimed = land & (pol < 0)
    summary = dict(source=str(SUMMARY_2C.relative_to(ROOT)), climate=sub or "raw", seed=seed, draws=draws, cell_km=cell_km, block_cells=[ny, nx],
                   expected_languages=expected, expected_farmland_languages=exp_farm,
                   drawn_languages_mean=float(np.mean(counts)), farmland_share=float(farm[land].mean()),
                   unclaimed_land_share=float(unclaimed.sum() / land.sum()),
                   unclaimed_expected_languages=float((dens * area)[unclaimed].sum()),
                   language_edge_frequency_on_polity_borders=float(freq[edge_p].mean()),
                   language_edge_frequency_on_land=float(freq[land].mean()),
                   polities=sorted(rows, key=lambda r: -r["expected_languages"]))
    return dict(land=land, farm=farm, dens=dens, owner=owner, freq=freq, pol=pol, edge_p=edge_p, rows=rows, y=y,
                summary=summary, meta=A)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("atlas", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--draws", type=int, default=20)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    R = compute(a.atlas, a.seed, a.draws)
    land, farm, dens, owner, freq, pol, edge_p, rows, y, summary = (R[k] for k in
        ("land", "farm", "dens", "owner", "freq", "pol", "edge_p", "rows", "y", "summary"))
    (a.out / "fantasy_languages.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    np.savez_compressed(a.out / "fantasy_languages.npz", dens=dens.astype(np.float32), owner=owner.astype(np.int32),
                        farm=farm, pol=pol.astype(np.int16), y=y.astype(np.float32), edge_freq=freq.astype(np.float32))
    figure(a.out / "fantasy_languages.png", land, farm, dens, owner, pol, edge_p, freq, rows, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "polities"}, indent=1))
    for r in summary["polities"]:
        print(f"  {r['polity']:22s} land {r['land_km2']:9.0f} km2  expected {r['expected_languages']:5.1f}  "
              f"largest {r['largest_language_share']:.2f}  effective {r['effective_languages']:.1f}  farmland {r['farmland_share']:.2f}")


def figure(path, land, farm, dens, owner, pol, edge_p, freq, rows, summ):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    h, w = land.shape
    sea = np.array([0.84, 0.89, 0.94])
    border = ndi.binary_dilation(edge_p)
    hatch = land & (pol < 0) & ((np.add.outer(np.arange(h), np.arange(w)) % 10) == 0)
    fig, axs = plt.subplots(3, 1, figsize=(13, 19), constrained_layout=True)
    ax = axs[0]
    ax.imshow(np.where(land, np.nan, 1.0), cmap=matplotlib.colors.ListedColormap([sea]), interpolation="nearest")
    im = ax.imshow(np.where(land, dens * 1e4, np.nan), cmap="magma_r", norm=LogNorm(0.05, 20), interpolation="nearest")
    ax.contour(farm.astype(float), levels=[0.5], colors="#2a6f2a", linewidths=0.8)
    fig.colorbar(im, ax=ax, shrink=0.7, label="languages per 10,000 km²")
    ax.set_title("1. Predicted language density. On farmland (inside the green line): layer 2c, from terrain and land-quality variation\n"
                 "(Earth held-out R² 0.34). Elsewhere: FORGE density / 3,000 people (illustrative). "
                 f"Expected {summ['expected_languages']:.0f} languages, {summ['expected_farmland_languages']:.0f} on farmland.", fontsize=10)
    ax = axs[1]
    n = owner.max() + 1
    pal = np.random.default_rng(7).random((n, 3)) * 0.55 + 0.42
    img = np.ones((h, w, 3)) * sea
    img[land & (owner >= 0)] = pal[owner[land & (owner >= 0)]]
    img[hatch] = 0.35
    img[border] = 0.05
    ax.imshow(img, interpolation="nearest")
    top = sorted(rows, key=lambda r: -r["land_km2"])[:4]
    txt = "; ".join(f"{r['polity']} ~{r['expected_languages']:.0f}" for r in top)
    ax.set_title("2. One draw of language territories (on-foot catchments of seeds placed at that density).\n"
                 f"Black: de jure polity borders; hatched: unclaimed land. Expected languages: {txt}.", fontsize=10)
    ax = axs[2]
    img = np.ones((h, w, 3)) * sea
    cm = plt.get_cmap("Greys")
    img[land] = cm(0.05 + 0.8 * np.clip(freq[land] / max(np.percentile(freq[land], 99), 1e-9), 0, 1))[:, :3]
    img[border] = np.array([0.80, 0.10, 0.12])
    ax.imshow(img, interpolation="nearest")
    ax.set_title(f"3. Where language boundaries are likely (share of {summ['draws']} draws with a language edge within ~7 km; dark = often),\n"
                 f"with the polity borders in red. Along polity borders the share is {summ['language_edge_frequency_on_polity_borders']:.2f}, "
                 f"against {summ['language_edge_frequency_on_land']:.2f} over all land.", fontsize=10)
    for ax in axs:
        ax.set_xlim(0, w); ax.set_ylim(h, 0); ax.set_xticks([]); ax.set_yticks([])
    fig.savefig(path, dpi=80)


if __name__ == "__main__":
    main()

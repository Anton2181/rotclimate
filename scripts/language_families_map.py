"""Language families on the fantasy map from the owner's farming hearth(s) (provisional).

Farming spreads from each hearth at layer 2's Earth rate (1.0 km a year by
distance; terrain by Tobler, sea crossings as easy as flat land, as every
Earth fit chose). The farming family covers the farmland; land where no crop
roots keeps its forager languages. Branches (illustrative): the groups that
left the spreading front at a given time, the front cut into arcs of about
600 km. Hearths and settings: calibration/language_areas_20261101/fantasy_hearths.json.

    python -I scripts/language_families_map.py atlases/earth_fit output/language_areas_20261101/families
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
from scipy.sparse.csgraph import dijkstra  # noqa: E402

from language_map_preview import compute, travel_graph  # noqa: E402

HEARTHS = ROOT / "calibration/language_areas_20261101/fantasy_hearths.json"
FLAT = 6.0 * np.exp(-3.5 * 0.05)


def arcs(cells, xy, arc_km, cell_km, seed=0):
    """Cut a set of front cells into contiguous groups of about arc_km (k-means on position)."""
    from sklearn.cluster import KMeans
    if len(cells) == 0:
        return np.zeros(0, int)
    k = max(1, int(round(len(cells) * cell_km / arc_km)))
    k = min(k, len(cells))
    return KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(xy)


def families(atlas: Path, R=None, config=HEARTHS):
    cfg = json.loads(Path(config).read_text())
    R = R or compute(atlas)
    land, farm, owner = R["land"], R["farm"], R["owner"]
    meta = R["meta"]
    h, w = land.shape
    cell_km = meta["mi_per_px"] * 1.609344 * (meta["width"] / w)
    blob = (atlas / "data" / "atlas.bin").read_bytes()
    s = meta["arrays"]["elev"]
    elev = np.frombuffer(blob, dtype=s["dtype"], count=int(np.prod(s["shape"])), offset=s["offset"]).reshape(s["shape"]).astype(float)
    G = travel_graph(elev, land, cell_km, sea_factor=1.0)
    src = [int(hh["row"]) * w + int(hh["col"]) for hh in cfg["hearths"]]
    dist, pred, which = dijkstra(G, directed=True, indices=src, min_only=True, return_predecessors=True)
    years = dist * FLAT / cfg["spread"]["km_per_year"]
    T1, T2, arc_km = cfg["branches"]["primary_years"], cfg["branches"]["secondary_years"], cfg["branches"]["arc_km"]
    order = np.argsort(years)
    a1 = np.arange(h * w); a2 = np.arange(h * w)
    for c in order:
        p = pred[c]
        if p < 0:
            continue
        a1[c] = c if years[c] <= T1 else (a1[p] if years[p] > T1 else p)
        a2[c] = c if years[c] <= T2 else (a2[p] if years[p] > T2 else p)
    fy, fx = np.divmod(np.arange(h * w), w)
    farm_f = farm.ravel()
    # primary branches: arcs of the T1 front; cells inside T1 are the homeland branch (0)
    beyond1 = farm_f & (years > T1)
    front1 = np.unique(a1[beyond1])
    lab1 = arcs(front1, np.column_stack([fx[front1], fy[front1]]) * cell_km, arc_km, cell_km)
    map1 = dict(zip(front1, lab1 + 1))
    b1 = np.zeros(h * w, int)
    b1[beyond1] = [map1[x] for x in a1[beyond1]]
    # sub-branches: arcs of the T2 front within each primary branch
    beyond2 = farm_f & (years > T2)
    b2 = np.zeros(h * w, int)
    for pb in np.unique(b1[beyond2]):
        m = beyond2 & (b1 == pb)
        f2 = np.unique(a2[m])
        lab2 = arcs(f2, np.column_stack([fx[f2], fy[f2]]) * cell_km, arc_km, cell_km)
        map2 = dict(zip(f2, lab2 + 1))
        b2[m] = [map2[x] for x in a2[m]]
    b1 = b1.reshape(h, w); b2 = b2.reshape(h, w); years = years.reshape(h, w)
    # each language territory takes the branch of most of its cells; mostly non-farm territories stay forager languages
    langs = {}
    for lg in np.unique(owner[land & (owner >= 0)]):
        m = owner == lg
        fshare = float(farm[m].mean())
        if fshare < 0.5:
            langs[int(lg)] = dict(family="forager", branch=None)
            continue
        vb1, cb1 = np.unique(b1[m & farm], return_counts=True); top1 = int(vb1[cb1.argmax()])
        sub = b2[m & farm & (b1 == top1)]
        vb2, cb2 = np.unique(sub, return_counts=True); top2 = int(vb2[cb2.argmax()]) if len(sub) else 0
        langs[int(lg)] = dict(family="farming", branch=top1, sub=top2, arrival=float(np.median(years[m & farm])))
    fam = -np.ones((h, w), int)      # -1 sea, 0 forager, 1000 + branch*100 + sub for the farming family
    for lg, d in langs.items():
        m = owner == lg
        fam[m] = 0 if d["family"] == "forager" else 1000 + d["branch"] * 100 + d["sub"]
    pol = R["pol"]
    names = [f["properties"]["polity"] for f in json.loads((atlas / "data/vectors/dejure_claims.geojson").read_text())["features"]]
    per_polity = []
    for i, nm in enumerate(names):
        cells = (pol == i) & land
        if not cells.any():
            continue
        # a language counts for a polity when at least a quarter of its territory lies inside it
        ls = [langs[int(x)] for x in np.unique(owner[cells & (owner >= 0)])
              if (cells & (owner == x)).sum() >= 0.25 * (owner == x).sum()]
        primaries = sorted({d["branch"] for d in ls if d["family"] == "farming"})
        subs = sorted({(d["branch"], d["sub"]) for d in ls if d["family"] == "farming"})
        per_polity.append(dict(polity=nm, languages=len(ls), primary_branches=len(primaries), sub_branches=len(subs),
                               forager_languages=sum(d["family"] == "forager" for d in ls),
                               median_arrival_years=float(np.median(years[cells & farm])) if (cells & farm).any() else None))
    n_farm = sum(d["family"] == "farming" for d in langs.values())
    summary = dict(config=str(Path(config).relative_to(ROOT)), status=cfg["status"], hearths=cfg["hearths"],
                   km_per_year=cfg["spread"]["km_per_year"], primary_years=T1, secondary_years=T2, arc_km=arc_km,
                   languages=len(langs), farming_family_languages=n_farm, forager_languages=len(langs) - n_farm,
                   primary_branches=int(b1.max()) + 1, sub_branches=int(len({(d['branch'], d['sub']) for d in langs.values() if d['family'] == 'farming'})),
                   farmland_filled_years=float(np.nanpercentile(years[farm], 99)),
                   polities=sorted(per_polity, key=lambda r: -r["languages"]))
    return dict(years=years, b1=b1, b2=b2, fam=fam, langs=langs, summary=summary, R=R)


def palette(n_primary):
    import colorsys
    base = []
    for i in range(n_primary):
        hue = (0.03 + i / max(n_primary, 1)) % 1.0
        base.append(colorsys.hls_to_rgb(hue, 0.55, 0.55))
    return base


def render(F, edge_lines=True):
    """RGB image of the families on the language territories, with arrival contours and polity borders."""
    import colorsys
    R = F["R"]; land, owner, pol, edge_p = R["land"], R["owner"], R["pol"], R["edge_p"]
    fam, years = F["fam"], F["years"]
    h, w = land.shape
    sea = np.array([214, 227, 240]) / 255.0
    rgb = np.ones((h, w, 3)) * sea
    n1 = int(F["b1"].max()) + 1
    base = palette(n1)
    for code in np.unique(fam[fam > 0]):
        b, sub = divmod(int(code) - 1000, 100)
        hh, ll, ss = colorsys.rgb_to_hls(*base[b])
        ll = 0.42 + 0.16 * ((sub * 0.61803) % 1.0)          # sub-branches: lighter / darker shades of their branch
        rgb[fam == code] = colorsys.hls_to_rgb(hh, ll, ss)
    rgb[fam == 0] = [0.80, 0.80, 0.78]
    hatch = (fam == 0) & ((np.add.outer(np.arange(h), np.arange(w)) % 8) == 0)
    rgb[hatch] = [0.55, 0.55, 0.52]
    if edge_lines:
        e = np.zeros_like(land)
        e[:, 1:] |= (owner[:, 1:] != owner[:, :-1]) & land[:, 1:] & land[:, :-1]
        e[1:, :] |= (owner[1:, :] != owner[:-1, :]) & land[1:, :] & land[:-1, :]
        rgb[e] = rgb[e] * 0.72
        # arrival contours every 500 years
        lev = np.floor(np.nan_to_num(years, nan=0) / 500.0)
        c = np.zeros_like(land)
        c[:, 1:] |= lev[:, 1:] != lev[:, :-1]; c[1:, :] |= lev[1:, :] != lev[:-1, :]
        rgb[c & land] = [1.0, 1.0, 1.0]
        rgb[ndi.binary_dilation(edge_p)] = [0.05, 0.05, 0.05]
    return rgb


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("atlas", type=Path); ap.add_argument("out", type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    F = families(a.atlas)
    S = F["summary"]
    (a.out / "families.json").write_text(json.dumps(S, indent=1, ensure_ascii=False))
    np.savez_compressed(a.out / "families.npz", years=F["years"].astype(np.float32), b1=F["b1"].astype(np.int16),
                        b2=F["b2"].astype(np.int16), fam=F["fam"].astype(np.int16))
    rgb = render(F)
    land = F["R"]["land"]
    fig, axs = plt.subplots(2, 1, figsize=(13, 13.2), constrained_layout=True)
    ax = axs[0]
    yrs = np.where(land, F["years"], np.nan)
    im = ax.imshow(yrs, cmap="YlOrBr", vmin=0, vmax=np.nanpercentile(yrs, 99), interpolation="nearest")
    ax.imshow(np.where(land, np.nan, 1.0), cmap=matplotlib.colors.ListedColormap([[0.84, 0.89, 0.94]]), interpolation="nearest")
    cs = ax.contour(yrs, levels=np.arange(500, 4001, 500), colors="#4a2a10", linewidths=0.6)
    ax.clabel(cs, fmt="%d", fontsize=7)
    for hh in S["hearths"]:
        ax.plot(hh["col"], hh["row"], marker="*", ms=20, mfc="#c22f2f", mec="white", mew=1.2)
    fig.colorbar(im, ax=ax, shrink=0.7, label="years after farming began at the hearth")
    ax.set_title(f"Farming spreading from the west-coast hearth (provisional, owner's choice) at the Earth rate of {S['km_per_year']:.1f} km a year:\n"
                 f"farmland filled after about {S['farmland_filled_years']:,.0f} years. Contours every 500 years.", fontsize=10)
    ax = axs[1]
    ax.imshow(rgb, interpolation="nearest")
    for hh in S["hearths"]:
        ax.plot(hh["col"], hh["row"], marker="*", ms=18, mfc="#c22f2f", mec="white", mew=1.2)
    ax.set_title(f"One farming family of {S['farming_family_languages']} languages: {S['primary_branches']} branches (colours, the hearth's homeland included), "
                 f"{S['sub_branches']} sub-branches (shades); grey hatched: {S['forager_languages']} forager languages.\n"
                 f"Black: de jure borders; white lines: farming's arrival every 500 years.", fontsize=9.5)
    for ax in axs:
        ax.set_xticks([]); ax.set_yticks([])
    fig.savefig(a.out / "families.png", dpi=85)
    print(json.dumps({k: v for k, v in S.items() if k != "polities"}, indent=1, ensure_ascii=False))
    for p in S["polities"][:8]:
        print("  ", p)


if __name__ == "__main__":
    main()

"""Run the production model on real regions and score it against WorldClim.

    python -I scripts/earth_benchmark.py --params output/overnight_mediterranean/selected_params.json \
        --regions california iberia --cell-km 28 --out output/earth_benchmark/anchor

Uses Earth's tilt, spin and calendar with the physics constants of --params
(see rotclimate/earth.py). Prints one line per region and writes
<out>/summary.json and <out>/maps.png.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402

from rotclimate import earth  # noqa: E402
from rotclimate.config import Params  # noqa: E402


def load_params(path):
    d = json.loads(Path(path).read_text())
    d = d.get("params", d)
    tmp = Path(path)
    return Params.from_json(tmp) if "params" not in json.loads(tmp.read_text()) else Params(**{
        k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items() if k in Params.__dataclass_fields__})


def maps(results, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from rotclimate.koppen import classify, monthly_stats
    from rotclimate.render import rgb_image

    n = len(results)
    fig, axs = plt.subplots(n, 4, figsize=(17, 4.2 * n), squeeze=False)
    for row, (case, res) in zip(axs, results):
        g = case.grid
        p = res.params
        st = monthly_stats(res.T, res.P, res.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
        ko = classify(np.nan_to_num(case.obs_T), np.nan_to_num(case.obs_P), st["summer"])
        ks = classify(st["Tm"], st["Pm"], st["summer"])
        sea = np.array([0.84, 0.89, 0.94])
        for ax, k, title in ((row[0], ko, "observed Köppen (WorldClim)"), (row[1], ks, "simulated Köppen")):
            img = rgb_image(k).astype(float) / 255.0
            img[~g.land] = sea
            ax.imshow(img, interpolation="nearest")
            ax.contour(g.inmap.astype(float), levels=[0.5], colors="k", linewidths=0.8)
            ax.set_title(f"{case.name}: {title}", fontsize=10)
        vmax = np.nanpercentile(np.nan_to_num(case.obs_P).sum(0)[g.land], 98)
        for ax, P, title in ((row[2], np.nan_to_num(case.obs_P).sum(0), "observed rain (mm/yr)"),
                             (row[3], st["Pm"].sum(0), "simulated rain (mm/yr)")):
            im = ax.imshow(np.where(g.land, P, np.nan), cmap="YlGnBu", vmin=0, vmax=vmax, interpolation="nearest")
            ax.contour(g.inmap.astype(float), levels=[0.5], colors="k", linewidths=0.8)
            ax.set_title(title, fontsize=10)
            fig.colorbar(im, ax=ax, shrink=0.7)
        for ax in row:
            ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(out / "maps.png", dpi=90)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", required=True)
    ap.add_argument("--regions", nargs="+", default=list(earth.REGIONS))
    ap.add_argument("--cell-km", type=float, default=28.0)
    ap.add_argument("--steps", type=int, default=25)
    ap.add_argument("--set", default="{}", help="json of parameter overrides")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    base = load_params(a.params).replace(**json.loads(a.set))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, results = [], []
    for name in a.regions:
        t = time.time()
        case = earth.region_case(name, a.cell_km)
        res = earth.run_case(base, case, steps=a.steps)
        r = earth.compare(res, case)
        r["seconds"] = round(time.time() - t, 1)
        rows.append(r)
        results.append((case, res))
        print(earth.summary_line(r), f"[{r['seconds']}s]", flush=True)
    (out / "summary.json").write_text(json.dumps(dict(params=a.params, overrides=json.loads(a.set),
                                                      cell_km=a.cell_km, steps=a.steps, regions=rows), indent=1))
    maps(results, out)


if __name__ == "__main__":
    main()

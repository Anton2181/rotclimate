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
            ax.set_title(f"{case.name}{' (mirrored)' if earth.REGIONS[case.name]['lat0'] < 0 else ''}: {title}",
                         fontsize=10)
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


def climographs(results, out):
    """One row per region: observed (dashed) and simulated (solid) monthly
    temperature and rain at the region's stations."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tables = [(case, earth.station_table(res, case)) for case, res in results]
    ncol = max(len(t) for _, t in tables)
    fig, axs = plt.subplots(len(tables), ncol, figsize=(2.6 * ncol, 2.3 * len(tables)), squeeze=False)
    months = np.arange(12)
    for row, (case, table) in zip(axs, tables):
        mirrored = earth.REGIONS[case.name]["lat0"] < 0
        order = np.roll(months, -6) if mirrored else months        # show calendar months Jan..Dec
        for ax, (name, st) in zip(row, table.items()):
            ax.bar(months, np.array(st["obs_P"])[order], width=0.8, color="#9ecae1", label="obs rain")
            ax.bar(months, np.array(st["sim_P"])[order], width=0.4, color="#08519c", label="sim rain")
            ax.set_ylim(0, max(150, 1.1 * max(max(st["obs_P"]), max(st["sim_P"]))))
            ax.tick_params(labelsize=6)
            t = ax.twinx()
            t.plot(months, np.array(st["obs_T"])[order], "--", color="#cb181d", lw=1.2)
            t.plot(months, np.array(st["sim_T"])[order], "-", color="#cb181d", lw=1.6)
            t.set_ylim(-15, 35)
            t.tick_params(labelsize=6)
            ax.set_xticks(months, list("JFMAMJJASOND"), fontsize=6)
            ax.set_title(f"{name}: obs {st['obs_koppen']}, sim {st['sim_koppen']}\n"
                         f"{sum(st['obs_P']):.0f} / {sum(st['sim_P']):.0f} mm, "
                         f"{np.mean(st['obs_T']):.1f} / {np.mean(st['sim_T']):.1f} C", fontsize=7)
        for ax in row[len(table):]:
            ax.set_axis_off()
    fig.suptitle("Observed (light bars, dashed) vs simulated (dark bars, solid): rain mm/month, temperature C",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "climographs.png", dpi=90)
    plt.close(fig)
    return {case.name: table for case, table in tables}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", required=True)
    ap.add_argument("--regions", nargs="+", default=list(earth.REGIONS))
    ap.add_argument("--cell-km", type=float, default=28.0)
    ap.add_argument("--steps", type=int, default=25)
    ap.add_argument("--set", default="{}", help="json of parameter overrides")
    ap.add_argument("--pad-km", type=float, default=1100.0, help="land and sea modelled around each region")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    base = load_params(a.params).replace(**json.loads(a.set))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, results = [], []
    for name in a.regions:
        t = time.time()
        case = earth.region_case(name, a.cell_km, pad_km=a.pad_km)
        res = earth.run_case(base, case, steps=a.steps)
        r = earth.compare(res, case)
        r["seconds"] = round(time.time() - t, 1)
        rows.append(r)
        results.append((case, res))
        print(earth.summary_line(r), f"[{r['seconds']}s]", flush=True)
    maps(results, out)
    stations = climographs(results, out)
    (out / "summary.json").write_text(json.dumps(dict(params=a.params, overrides=json.loads(a.set),
                                                      cell_km=a.cell_km, pad_km=a.pad_km, steps=a.steps, regions=rows,
                                                      stations=stations), indent=1))
    d = [r["climate_distance"] for r in rows]
    ref = {k: np.mean([r["reference_distances"][k] for r in rows]) for k in rows[0]["reference_distances"]}
    print(f"mean climate distance {np.mean(d):.3f} over {len(d)} regions (references from the observations: "
          f"region mean {ref['region_mean']:.3f}, latitude band + height {ref['latitude_band_and_height']:.3f})")


if __name__ == "__main__":
    main()

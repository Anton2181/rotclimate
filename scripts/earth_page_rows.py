"""Region rows of the Earth test page (reports/earth_page/index.html) from two
nine-region benchmark summaries: the "before" physics and the current Earth
reference. Prints the JavaScript array the page's table and chart read.

    python -I scripts/earth_page_rows.py --before output/earth_benchmark/<before>/summary.json \
        --after output/earth_benchmark/<reference>/summary.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

NAMES = {"california": "California", "iberia": "Iberia", "southeast_us": "South-east US", "levant": "Levant",
         "central_asia": "Central Asia", "east_china": "East China", "chile": "Chile", "cape": "Western Cape",
         "sw_australia": "SW Australia"}
HELD = {"chile", "cape", "sw_australia"}


def rows(path):
    return {r["region"]: r for r in json.loads(Path(path).read_text())["regions"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    a = ap.parse_args()
    before, after = rows(a.before), rows(a.after)
    out = []
    for key, name in NAMES.items():
        r = after[key]
        ref = r["reference_distances"]
        k = r["koppen_full_model"]
        cs = "–" if k.get("cs_retained") is None else f"{k['cs_retained']:.0%} / {k['cs_to_arid']:.0%}"
        bias = r["temperature"]["bias_C"]
        out.append(f'  ["{name}", {before[key]["climate_distance"]:.2f}, {r["climate_distance"]:.2f}, '
                   f'{ref["region_mean"]:.2f}, {ref["latitude_band_and_height"]:.2f}, '
                   f'"{"+" if bias >= 0 else "−"}{abs(bias):.1f} °C", '
                   f'"{r["rain"]["sim_mean_annual_mm"]:.0f} / {r["rain"]["obs_mean_annual_mm"]:.0f}", '
                   f'"{k["exact"]:.0%}", "{cs}", {"true" if key in HELD else "false"}],')
    print("const regions = [\n" + "\n".join(out) + "\n];")
    for label, rs in (("before", before), ("after", after)):
        d = [rs[k]["climate_distance"] for k in NAMES]
        print(f"// {label}: nine-region mean {sum(d) / len(d):.3f}, training {sum(d[:6]) / 6:.3f}")


if __name__ == "__main__":
    main()

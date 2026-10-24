"""Population scenarios and the political reach they imply, side by side.

    python3 -I scripts/control_scenarios.py --atlas atlases/free_fit --out output/control/scenarios_free_fit

Political reach (polity/fields.py) depends on where people live: one
unmarked town per ~40,000 people, minor roads between towns, and faster
going off the roads where the countryside is busy. This reruns it for:

- the Harvest occupation levels (frontier, central, settled core: fixed
  shares of the local food support, settlement_base);
- the central total placed four ways by the Population lab's allocator
  (population/models.py): dispersed (= central), rural (water and gentle
  ground), markets (walking time to named places; the lab's default) and
  dispersed without malaria;
- the central share around the lore heartlands (settlement_cored).

Writes summary.json (land and people within 1 and 2 days of a road or town,
towns, tracks, and per polity: people inside the drawn border, people and
land it holds de facto), polities.csv, and two figures.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from polity.fields import compute  # noqa: E402
from population.export import decode_harvest  # noqa: E402
from population.models import allocate  # noqa: E402


def lab_fields(data: Path):
    meta = json.loads((data / "population.json").read_text()); blob = (data / "population.bin").read_bytes()
    out = {}
    for k, s in meta["arrays"].items():
        dt = np.dtype("<u2" if s["dtype"] == "uint16" else "<f4")
        out[k] = np.frombuffer(blob, dtype=dt, count=int(np.prod(s["shape"])), offset=s["offset"]).reshape(s["shape"]).astype(float)
    return out


def scenarios(data: Path):
    hm, hf = decode_harvest(data)
    share = hm["occupation"]["scenarios"]
    lab = lab_fields(data)
    area = lab["area"]
    base = np.maximum(hf["settlement_base"], 0)
    central_total = float((base * share["central"] * area).sum())

    def placed(capacity, weight):
        people, _ = allocate(capacity * area, weight, central_total)
        return np.divide(people, area, out=np.zeros(area.shape), where=area > 0)
    return {
        "frontier": ("Frontier occupation", base * share["frontier"]),
        "central": ("Central occupation (dispersed)", base * share["central"]),
        "core": ("Settled-core occupation", base * share["core"]),
        "rural": ("Central total, water and terrain", placed(base, lab["rural"])),
        "markets": ("Central total, market access", placed(base, lab["attraction"])),
        "no_malaria": ("Central total, no malaria", placed(np.maximum(hf["settlement_no_malaria"], 0), np.ones(area.shape))),
        "cored": ("Central share, lore heartlands", np.maximum(hf["settlement_cored"], 0) * share["central"]),
    }, area


def summarise(r, area):
    f, land = r["fields"], r["land"]
    people = r["density"] * area
    days = f["days_open"]
    best, held, contested = f["polity_best"], r["held"], r["contested"]
    out = dict(people_M=float(people[land].sum() / 1e6),
               unmarked_towns=int(len(r["suggested"])),
               track_km=float(r["tracks"].sum() * r["cell_km"]),
               land_within_1_day=float((days[land] <= 1).mean()), land_within_2_days=float((days[land] <= 2).mean()),
               people_within_1_day=float(people[land & (days <= 1)].sum() / people[land].sum()),
               people_within_2_days=float(people[land & (days <= 2)].sum() / people[land].sum()),
               mean_control=float(r["control_open"][land].mean()),
               people_weighted_control=float((r["control_open"] * people)[land].sum() / people[land].sum()),
               winter_land_within_1_day=float((f["days_winter"][land] <= 1).mean()),
               held_land=float(held.sum() / land.sum()), contested_land=float(contested.sum() / land.sum()),
               polities={})
    for k, name in enumerate(r["polity_names"]):
        own = np.isin(r["polity_ids"], r["groups"][name]) & land
        mine = held & (best == k)
        out["polities"][name] = dict(
            drawn_km2=float(area[own].sum()), people_in_border_M=float(people[own].sum() / 1e6),
            held_km2=float(area[mine].sum()), people_held_M=float(people[mine].sum() / 1e6),
            held_outside_border_km2=float(area[mine & ~own].sum()),
            border_people_within_1_day=float(people[own & (days <= 1)].sum() / max(people[own].sum(), 1e-9)),
            contested_km2=float(area[r["contested"] & (best == k)].sum()))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--atlas", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", nargs="*", help="scenario keys to run (default all)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    cases, area = scenarios(a.atlas / "data")
    keys = a.only or list(cases)
    results, maps = {}, {}
    for key in keys:
        label, density = cases[key]
        r = compute(a.atlas, density=density)
        results[key] = dict(label=label, **summarise(r, area))
        maps[key] = dict(density=r["density"].astype(np.float32), control=r["control_open"].astype(np.float32),
                         best=r["fields"]["polity_best"].astype(np.int16), held=r["held"], land=r["land"],
                         towns=np.array([(t["row"], t["col"]) for t in r["towns"] if t["kind"] == "unmarked town"]),
                         tracks=r["tracks"])
        s = results[key]
        print(f"{key:11s} {s['people_M']:6.1f} M | towns {s['unmarked_towns']:5d} tracks {s['track_km']:7.0f} km | "
              f"land <=1 d {s['land_within_1_day']:.0%} <=2 d {s['land_within_2_days']:.0%} | people <=1 d "
              f"{s['people_within_1_day']:.0%} | held {s['held_land']:.0%} contested {s['contested_land']:.1%}", flush=True)
        names, rgb = r["polity_names"], r["polity_rgb"]
    (a.out / "summary.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
    with (a.out / "polities.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "polity", "drawn_km2", "people_in_border_M", "held_km2", "people_held_M",
                    "held_outside_border_km2", "border_people_within_1_day", "contested_km2"])
        for key, s in results.items():
            for name, v in s["polities"].items():
                w.writerow([key, name] + [round(v[c], 4) for c in ("drawn_km2", "people_in_border_M", "held_km2", "people_held_M",
                                                                     "held_outside_border_km2", "border_people_within_1_day", "contested_km2")])
    np.savez_compressed(a.out / "maps.npz", **{f"{k}_{n}": v for k, m in maps.items() for n, v in m.items()},
                        names=np.array(names), rgb=np.array([rgb[n] for n in names]))
    print("wrote", a.out)


if __name__ == "__main__":
    main()

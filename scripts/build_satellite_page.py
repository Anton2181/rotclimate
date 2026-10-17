"""Assemble the satellite viewer's files: the two season renders and the
place names (positions from data/places.csv, town or city from the Ravages
sheet's TownsCities tab).

    python -I scripts/build_satellite_page.py output/satellite satellite
"""
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(src, dst):
    src, dst = Path(src), Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for season in ("summer", "winter"):
        shutil.copyfile(src / f"satellite_{season}.webp", dst / f"{season}.webp")
    meta = json.loads((src / "satellite.json").read_text())
    kinds = {}
    rav = ROOT / "ravages" / "data.json"
    if rav.exists():
        for h, name, kind, prov in json.loads(rav.read_text())["towns"]:
            kinds[int(h)] = kind
    places = []
    for r in csv.DictReader((ROOT / "data" / "places.csv").open()):
        kind = kinds.get(int(r["hex"]), r["kind"]) if r.get("hex") else r["kind"]
        places.append(dict(name=r["name"], x=round(float(r["x"]) / 2000 * meta["width"], 1),
                           y=round(float(r["y"]) / 2000 * meta["width"], 1), kind=kind,
                           major=any(k in str(kind).lower() for k in ("city", "capital"))))
    params = json.loads(Path(ROOT / meta["params"]).read_text())
    params = params.get("params", params)
    out = dict(width=meta["width"], height=meta["height"], seasons=meta["seasons"], places=places,
               world=dict(lat=round(params["lat_center"], 1), tilt=round(params["tilt"], 1),
                          bearing=round(params["north_bearing"], 1), retrograde=bool(params["retrograde"])),
               downsample=meta["downsample"])
    (dst / "meta.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{dst}: {len(places)} places, {sum(p['major'] for p in places)} cities")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

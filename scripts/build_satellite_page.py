"""Assemble the satellite viewer's files: for each season an overview at the
drawing's resolution and the full render cut into tiles (loaded only when the
viewer zooms in), and the place names (positions from data/places.csv, town
or city from the Ravages sheet's TownsCities tab).

    python -I scripts/build_satellite_page.py output/satellite satellite
"""
import csv
import json
from PIL import Image
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(src, dst):
    src, dst = Path(src), Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    meta = json.loads((src / "satellite.json").read_text())
    k = meta.get("scale", 1)
    W1, H1 = meta["width"] // k, meta["height"] // k
    cols, rows = (4, 2) if k > 1 else (1, 1)
    tw, th = -(-meta["width"] // cols), -(-meta["height"] // rows)
    (dst / "tiles").mkdir(exist_ok=True)
    for season in ("summer", "winter"):
        im = Image.open(src / f"satellite_{season}.webp")
        im.resize((W1, H1), Image.LANCZOS).save(dst / f"{season}.webp", quality=88, method=4)
        if k > 1:
            for r in range(rows):
                for c in range(cols):
                    im.crop((c * tw, r * th, min((c + 1) * tw, im.width), min((r + 1) * th, im.height))) \
                        .save(dst / "tiles" / f"{season}_{r}_{c}.webp", quality=86, method=4)
    kinds = {}
    rav = ROOT / "ravages" / "data.json"
    if rav.exists():
        for h, name, kind, prov in json.loads(rav.read_text())["towns"]:
            kinds[int(h)] = kind
    places = []
    for r in csv.DictReader((ROOT / "data" / "places.csv").open()):
        kind = kinds.get(int(r["hex"]), r["kind"]) if r.get("hex") else r["kind"]
        places.append(dict(name=r["name"], x=round(float(r["x"]) / 2000 * W1, 1),
                           y=round(float(r["y"]) / 2000 * W1, 1), kind=kind,
                           major=any(k in str(kind).lower() for k in ("city", "capital"))))
    params = json.loads(Path(ROOT / meta["params"]).read_text())
    params = params.get("params", params)
    out = dict(width=W1, height=H1, seasons=meta["seasons"], places=places,
               tiles=dict(scale=k, cols=cols, rows=rows, w=tw, h=th) if k > 1 else None,
               world=dict(lat=round(params["lat_center"], 1), tilt=round(params["tilt"], 1),
                          bearing=round(params["north_bearing"], 1), retrograde=bool(params["retrograde"])),
               downsample=meta["downsample"])
    (dst / "meta.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{dst}: {len(places)} places, {sum(p['major'] for p in places)} cities")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

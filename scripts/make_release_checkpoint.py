"""Turn a confirmed 3-seed climate run into the verified simulation checkpoint scripts/build_atlas_variant.py accepts,
so a release does not repeat a simulation that was just made (as for r44: output/r44_terrain_world/candidate_001.pkl).

The identity is computed exactly as build_atlas_variant does; the run's parameters must equal the release parameters.

    .venv/bin/python -I scripts/make_release_checkpoint.py RESULT.pkl PARAMS.json OUT.pkl [--seeds 1,2,3] [--downsample 8]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result"); ap.add_argument("params"); ap.add_argument("out")
    ap.add_argument("--seeds", default="1,2,3"); ap.add_argument("--downsample", type=int, default=8)
    a = ap.parse_args()
    from build_atlas_variant import load
    p = load(Path(a.params)).replace(downsample=a.downsample)
    with open(a.result, "rb") as f:
        r = pickle.load(f)
    r = r["result"] if isinstance(r, dict) else r
    if json.loads(json.dumps(asdict(r.params))) != json.loads(json.dumps(asdict(p))):
        diff = sorted(k for k, v in asdict(p).items() if asdict(r.params).get(k) != v)
        raise SystemExit(f"run parameters differ from the release parameters: {diff}")
    seeds = [int(x) for x in a.seeds.split(",") if x.strip()]
    identity = dict(params=json.loads(json.dumps(asdict(p))), seeds=seeds, sources={
        f.name: hashlib.sha256(f.read_bytes()).hexdigest()
        for f in (ROOT / "rotclimate").glob("*.py")
        if f.name not in {"atlas.py", "render.py", "biomes.py", "climate_fields.py"}})
    identity["map_inputs"] = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                              for f in (ROOT / "data/source").iterdir() if f.is_file()}
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(dict(identity=identity, result=r), f)
    print("wrote", out)


if __name__ == "__main__":
    main()

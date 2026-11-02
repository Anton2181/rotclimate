"""Label a staged atlas only after its shared parameters match the release."""
from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from earth_benchmark import load_params
from rotclimate.joint import SHARED_FIELDS


def tag(atlas, params, profile, report):
    if not re.fullmatch(r'r\d+', profile) or not re.fullmatch(r'reports/[A-Za-z0-9_]+\.md', report):
        raise ValueError('Invalid release label or report path')
    world, raw = load_params(atlas / 'params.json'), load_params(params)
    if any(getattr(world, k) != getattr(raw, k) for k in SHARED_FIELDS):
        raise ValueError('Atlas shared physics differs from the requested release')
    path = atlas / 'data/atlas.json'; meta = json.loads(path.read_text())
    meta.update(physics_profile=profile, physics_report=report)
    path.write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('atlas', type=Path)
    ap.add_argument('--params', type=Path, required=True); ap.add_argument('--profile', required=True)
    ap.add_argument('--report', required=True); a = ap.parse_args()
    tag(a.atlas, a.params, a.profile, a.report)


if __name__ == '__main__': main()

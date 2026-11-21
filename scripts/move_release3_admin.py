"""Move administration and hierarchy publications built in place on the release-3/4 towns under data/release3/{admin,hierarchy}
(the layout of the r44 release-3 downstream publication, reports/SETTLEMENT_DOWNSTREAM_20261113.md), rewriting the manifests'
file paths. Run after publish_imperial_access.py / publish_administrative_hierarchy.py under run_on_release3.py; afterwards
restore the published in-place files with git checkout.

    move_release3_admin.py
"""
import json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; DATA = ROOT / 'atlases/earth_fit/data'
SETS = {'admin': ('administration', 'administrative_access.json'), 'hierarchy': ('hierarchy_', 'administrative_hierarchy.json')}


def rewrite(x, files, prefix):
    if isinstance(x, dict): return {k: rewrite(v, files, prefix) for k, v in x.items()}
    if isinstance(x, list): return [rewrite(v, files, prefix) for v in x]
    return prefix + x if isinstance(x, str) and x in files else x


if __name__ == '__main__':
    for name, (stem, manifest) in SETS.items():
        target = DATA / 'release3' / name; shutil.rmtree(target, ignore_errors=True)
        files = sorted(str(p.relative_to(DATA)) for d in (DATA, DATA / 'corrected') for p in d.glob(stem + '*') if p.is_file())
        for f in files:
            (target / f).parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(DATA / f, target / f)
        m = rewrite(json.loads((DATA / manifest).read_text()), set(files), f'release3/{name}/')
        (target / manifest).write_text(json.dumps(m, ensure_ascii=False))
        print(name, len(files), 'files')

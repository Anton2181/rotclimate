"""Fresh producer runs of every cohort-protected case; results and fields must be byte identical."""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import build_settlement_cohort_forwarding as builder
from settlement_locations_earth import sha, write


def main():
    plan = json.loads(builder.PLAN.read_text())['scenarios']; out = builder.OUT; fresh = out / 'fresh'
    shutil.rmtree(fresh, ignore_errors=True); files = {}
    for mode in plan['climate_modes']:
        for days in plan['range_days_each_way']:
            for rule in plan['rules']:
                key = builder.run(mode, days, rule, fresh)['key']
                for name in ('results.json', 'fields.npz'):
                    if (fresh / key / name).read_bytes() != (out / key / name).read_bytes():
                        raise ValueError(f'Fresh {key}/{name} differs from the reviewed file')
                    files[f'{key}/{name}'] = sha(out / key / name)
    shutil.rmtree(fresh, ignore_errors=True)
    write(out / 'replay.json', dict(status='passed', byte_exact_files=files))
    print('Fresh cohort-protected replay byte exact:', len(files), 'files')


if __name__ == '__main__':main()

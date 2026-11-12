"""Fresh producer runs of every market-hierarchy case; results and fields must be byte identical."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import build_settlement_hierarchy as two_day
import build_settlement_market_range as market
from settlement_locations_earth import sha, write


def main(family):
    out = two_day.OUT if family == 'hierarchy' else market.OUT; plan = json.loads((two_day.PLAN if family == 'hierarchy' else market.PLAN).read_text())['scenarios']
    fresh = out / 'fresh'; shutil.rmtree(fresh, ignore_errors=True); files = {}
    for mode in plan['climate_modes']:
        for share in plan['forward_share']:
            if family == 'hierarchy':keys = [two_day.run(mode, share, fresh)['key']]
            else:keys = [market.run(mode, days, share, fresh)['key'] for days in plan['range_days_each_way']]
            for key in keys:
                for name in ('results.json', 'fields.npz'):
                    if (fresh / key / name).read_bytes() != (out / key / name).read_bytes():
                        raise ValueError(f'Fresh {key}/{name} differs from the reviewed file')
                    files[f'{key}/{name}'] = sha(out / key / name)
    shutil.rmtree(fresh, ignore_errors=True)
    write(out / 'replay.json', dict(status='passed', family=family, byte_exact_files=files))
    print('Fresh', family, 'replay byte exact:', len(files), 'files')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--family', choices=('hierarchy', 'market'), required=True)
    main(p.parse_args().family)

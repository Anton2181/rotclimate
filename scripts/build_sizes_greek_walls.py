"""Step 2 of calibration/sizes_greek_walls_20261114: rebuild release-3 fantasy sizes with the refitted size model."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import build_settlement_release3 as B

B.EARTH = ROOT / 'output/sizes_greek_walls_20261114'; OUT = ROOT / 'output/sizes_greek_walls_20261114/release3'
if __name__ == '__main__':
    r = B.run(OUT)
    for m, c in r['climates'].items():
        print(m, c['placement']['moved'], {k: (round(v['total']), round(v['largest']), v['local_cereal']['fully_supported_sites'], v['people_ledger']['unmet_shortfall']) for k, v in c['residents'].items()}, c['area_quantiles_ha'])

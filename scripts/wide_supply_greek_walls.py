"""Step 3 of calibration/sizes_greek_walls_20261114: wide grain supply on the refitted sizes at the with-Egypt Earth share."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import build_wide_supply_release3 as B

E = json.loads((ROOT / 'output/greek_walls_20261114/results.json').read_text())['variants']['greece']['decision']['e95_all_at_L_used']
B.R3 = ROOT / 'output/sizes_greek_walls_20261114/release3'; B.EARTH = ROOT / 'output/greek_walls_20261114/results.json'
LOW = json.loads((ROOT / 'output/supply_low_reading_20261114/results.json').read_text())['low_e95']
B.EXTRACTION = (E, 0.10, LOW);   # LOW: the flat-reading Earth share (calibration/supply_low_reading_20261114)
 B.HEADLINE = f'central_x{int(round(E * 100)):02d}'
OUT = ROOT / 'output/sizes_greek_walls_20261114/supply'
if __name__ == '__main__':
    r = B.run(OUT)
    for m, c in r['climates'].items():
        s = c['scenarios'][B.HEADLINE]; print(m, B.HEADLINE, 'fed %.3f self %d imports %d short %d' % (s['fed_share_of_residents'], s['self_sufficient_towns'], s['fed_with_imports_towns'], s['short_towns']))

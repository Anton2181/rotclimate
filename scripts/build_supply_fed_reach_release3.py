"""Staffing for the control rule from supply-fed calibrated residents (downstream plan, amendment A1)."""
import gzip, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write

SRC = ROOT / 'output/settlement_fertility_release3_20261113'; R3 = ROOT / 'output/settlement_release3_20261113'
SUP = ROOT / 'output/settlement_wide_supply_20261113'; OUT = ROOT / 'output/settlement_supplyfed_release3_20261113'
THRESHOLD, STAFF, KEY = 150.0, 100.0, 'central_x33'

if __name__ == '__main__':
    review = json.loads((SUP / 'review.json').read_text())
    if review['status'] != 'passed' or review['results_sha256'] != sha(SUP / 'results.json'):
        raise ValueError('Reviewed supply plan required')
    summary = {}
    for mode in ('raw', 'corrected'):
        model = json.loads(gzip.decompress((SRC / f'earth_fit_{mode}/settled_reach.json.gz').read_bytes()))
        sites = json.loads((R3 / f'placed_{mode}_sites.json').read_text())['sites']
        if [s['node'] for s in model['sites']] != [s['node'] for s in sites]:
            raise ValueError('Chain packet is not on the release-3 towns')
        res = np.load(R3 / f'placed_{mode}_fields.npz')['residents_central']; fed = res * np.load(SUP / f'supply_{mode}.npz')[KEY + '_fed_share']
        case = next(c for c in model['cases'] if c['id'] == 'joint365'); before = np.array(case['institutional_active'], bool)
        affiliated = np.array([s['actor_index'] >= 0 for s in model['sites']]); active = affiliated & (fed >= THRESHOLD)
        case['institutional_active'] = active.tolist(); case['institutional_people'] = np.where(active, STAFF, 0.).tolist()
        case['civilian_people'] = (fed - np.where(active, STAFF, 0.)).tolist(); case['community_viable'] = (fed >= 50.).tolist()
        case['staffing_basis'] = 'supply-fed calibrated residents, one third marketed (downstream plan amendment A1)'
        for s, r in zip(model['sites'], res):
            s['civilian_request_people'] = float(r)
        target = OUT / f'earth_fit_{mode}'; target.mkdir(parents=True, exist_ok=True)
        (target / 'settled_reach.json.gz').write_bytes(gzip.compress(json.dumps(model, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode(), mtime=0))
        summary[mode] = dict(sites=len(sites), affiliated=int(affiliated.sum()), staffed_before=int(before.sum()), staffed_now=int(active.sum()),
            newly_staffed=int((active & ~before).sum()), no_longer_staffed=int((before & ~active).sum()),
            fed_residents=float(fed.sum()), packet_sha256=sha(target / 'settled_reach.json.gz'))
    write(OUT / 'staffing.json', dict(status='supply_fed_staffing_for_control_rule', threshold_people=THRESHOLD, supply_scenario=KEY,
        supply_results_sha256=sha(SUP / 'results.json'), producer_sha256=sha(__file__), climates=summary))
    print(summary)

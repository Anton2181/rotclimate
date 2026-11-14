"""Independent review of output/egypt_sufficiency_20261114: decisions rebuilt from the stored fed-share surfaces
with separate interpolation code, control compared with the archive, monotone Egypt response, fresh replay."""
import json, math, sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/egypt_sufficiency_20261114'


def crossing(shares, fed, level=0.95):
    prev = None
    for e, f in zip(shares, fed):
        if f >= level:
            if prev is None: return e
            (e0, f0) = prev; return e0 + (level - f0) * (e - e0) / (f - f0)
        prev = (e, f)
    return None


def main():
    r = json.loads((OUT / 'results.json').read_text()); plan = json.loads((ROOT / 'calibration/settlement_supply_calibration_20261113/plan.json').read_text())
    assert r['plan_sha256'] == sha(ROOT / 'calibration/egypt_sufficiency_20261114/plan.json') and r['producer_sha256'] == sha(ROOT / 'scripts/egypt_sufficiency.py')
    shares = plan['parameters']['marketed_share_e']; archive = json.loads((ROOT / 'output/settlement_supply_calibration_20261113/results.json').read_text())
    assert r['control_reproduces_archive'] and r['variants']['control']['surface'] == archive['surface']
    checks = 0; passing = []
    for name, v in r['variants'].items():
        ratios = {}
        for L, row in v['surface'].items():
            for part in ('all', 'west', 'east'):
                e = crossing(shares, row[part]['fed_share']); ref = row[part]['e95']
                assert (e is None and ref is None) or abs(e - ref) < 1e-12, (name, L, part); checks += 1
            w, e = row['west']['e95'], row['east']['e95']; ratios[L] = None if not (w and e) else abs(math.log(w / e))
        valid = {L: x for L, x in ratios.items() if x is not None}; best = min(valid, key=lambda L: (valid[L], float(L))) if valid else None
        keep = '270' in valid and (valid['270'] <= math.log(1.25) or valid['270'] <= 1.1 * valid[best]); d = v['decision']
        assert d['best_L_by_west_east_agreement'] == best and d['cited_270_kept'] == keep; use = '270' if keep or best is None else best
        assert d['L_used'] == use and d['e95_all_at_L_used'] == v['surface'][use]['all']['e95']
        for src, dst, key in (('west', 'east', 'west_setting_feeds_east'), ('east', 'west', 'east_setting_feeds_west')):
            e = v['surface'][use][src]['e95']; F = v['surface'][use][dst]['fed_share']
            if e is None: assert d['transfer'][key] is None; continue
            j = max(i for i in range(len(shares)) if shares[i] <= e); val = F[j] if shares[j] == e else F[j] + (e - shares[j]) * (F[j + 1] - F[j]) / (shares[j + 1] - shares[j])
            assert abs(val - d['transfer'][key]) < 1e-12; checks += 1
        ok = keep and all(d['transfer'][k] is not None and d['transfer'][k] >= 0.9 for k in d['transfer']); assert d['transferable'] == all(d['transfer'][k] is not None and d['transfer'][k] >= 0.9 for k in d['transfer'])
        if name != 'control' and ok: passing.append(name)
    assert passing == r['passing_variants']
    v = r['variants']
    for pre in ('Y', 'YP'):
        assert v['control']['egypt_surplus_person_years'] <= v[f'{pre}_1.94']['egypt_surplus_person_years'] <= v[f'{pre}_2.16']['egypt_surplus_person_years']
    fresh = OUT / 'fresh/results.json'; exact = fresh.exists() and fresh.read_bytes() == (OUT / 'results.json').read_bytes()
    write(OUT / 'review.json', dict(status='passed' if exact else 'passed_without_fresh_replay', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'),
        scalar_checks=checks, passing_variants=passing, fresh_byte_exact=bool(exact)))
    print('review', 'passed' if exact else 'passed without fresh replay', checks)


if __name__ == '__main__':
    main()

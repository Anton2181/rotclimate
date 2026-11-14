"""Egypt people-sufficiency sensitivity (calibration/egypt_people_sufficiency_20261114/plan.json).
Reuses the reviewed egypt_sufficiency machinery; Egypt proper's people field scaled to a historical total T."""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import egypt_sufficiency as ES
from settlement_locations_earth import sha, write

S = ES.S; PLAN = ROOT / 'calibration/egypt_people_sufficiency_20261114/plan.json'; OUT = ROOT / 'output/egypt_people_sufficiency_20261114'
VARIANTS = [('control', None, 1.0), ('T4.5_y1', 4.5e6, 1.0), ('T5.0_y1', 5.0e6, 1.0), ('T4.5_y2.16', 4.5e6, 2.16), ('T5.0_y2.16', 5.0e6, 2.16)]
STATE = dict(y=1.0)


def proper(lat, lon):
    return (lon >= 29.0) & (lat <= 32.0) & (lon <= 32.6)


def main(out):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    out.mkdir(parents=True, exist_ok=True); ES.memoise(); fields = S.earth_fields
    def scaled(lat, lon):
        a, b, c, d = fields(lat, lon); f = np.where(proper(lat, lon), STATE['y'], 1.0); return a * f, b * f, c, d
    S.earth_fields = scaled
    plan = json.loads(S.PLAN.read_text()); shares = plan['parameters']['marketed_share_e']; limits = plan['parameters']['haul_limit_L_road_km']
    archive = json.loads(ES.ARCHIVE.read_text()); rows = {}
    for name, T, y in VARIANTS:
        x = dict(np.load(S.PILOT.POOL)); STATE['y'] = y; m = proper(x['lat'], x['lon']) & x['land']; cell = float(x['cell_km']) ** 2
        before = float((x['density'][m] * cell).sum()); factor = 1.0 if T is None else T / before
        if T is not None: x['density'] = np.where(m, x['density'] * factor, x['density'])
        a, meta = S.prepare(x); fed = S.fed_surface(a, shares, limits); west = a['lon'] <= np.median(a['lon'])
        table, decision = S.decide(shares, limits, fed, a['residents'], west)
        pc = m.ravel()[a['nodes']]; i270 = limits.index(270)
        rows[name] = dict(total_people_target=T, yield_factor=y, people_factor=factor, egypt_proper_people_before=before, decision=decision, surface=table,
            egypt_proper_city_fed_share_at_270={str(e): float(fed[i270, j][pc].sum() / a['residents'][pc].sum()) for j, e in enumerate(shares)},
            egypt_proper_residents=float(a['residents'][pc].sum()), egypt_proper_surplus_person_years=float(a['surplus'][m.ravel()].sum()))
        print(name, json.dumps(decision), flush=True)
    control_exact = rows['control']['surface'] == archive['surface'] and rows['control']['decision'] == archive['decision']
    passing = [n for n, r in rows.items() if n != 'control' and r['decision']['cited_270_kept'] and r['decision']['transferable']]
    write(out / 'results.json', dict(status='egypt_people_sufficiency_sensitivity', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), machinery_sha256=sha(ROOT / 'scripts/egypt_sufficiency.py'),
        calibration_producer_sha256=sha(ROOT / 'scripts/settlement_supply_calibration.py'), control_reproduces_archive=bool(control_exact), variants=rows, passing_variants=passing))
    return control_exact, passing


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=OUT); print(main(ap.parse_args().out))

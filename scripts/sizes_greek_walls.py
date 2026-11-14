"""Step 1 of calibration/sizes_greek_walls_20261114: refit the release-2 size model with Greek wall circuits read as inhabited area."""
import csv, io, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import settlement_release2_earth as R
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/sizes_greek_walls_20261114/plan.json'; OUT = ROOT / 'output/sizes_greek_walls_20261114'
BASE = ROOT / 'output/settlement_release2_20261113/results.json'; GREEK = {'Achaea', 'Macedonia', 'Epirus'}


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    out.mkdir(parents=True, exist_ok=True)
    basis = {r['Primary Key']: r['Estimate Basis'] for r in csv.DictReader(io.StringIO((R.CACHE / 'areas.csv').read_bytes().decode('utf-8-sig')))}
    rows, counts, areas = R.cohort()
    base = json.loads(BASE.read_text())
    control = R.evaluate([r for r in rows if r['area'] not in (20.0, 30.0)], 'primary_without_20_30_ha')
    assert control == base['sizes']['primary'], 'uncorrected refit does not reproduce the archived size results'
    primary = [dict(r) for r in rows if r['area'] not in (20.0, 30.0)]; changed = []
    for r in primary:
        if r['province'] in GREEK and basis.get(r['key'], '').startswith('Walls'):
            share = 1 / 3 if r['area'] >= 100 else 1 / 2; changed.append(dict(key=r['key'], province=r['province'], walled_ha=r['area'], share=share)); r['area'] *= share
    corrected = R.evaluate(primary, 'primary_without_20_30_ha_greek_walls_inhabited')
    result = dict(base); result['sizes'] = dict(primary=corrected, uncorrected_primary=base['sizes']['primary'])
    result.update(status='release2_sizes_refit_greek_walls', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)), base_results_sha256=sha(BASE),
                  greek_wall_rows_changed=changed, control_reproduces_archive=True)
    write(out / 'results.json', result)
    m0, m1 = corrected['models']['M1'], control['models']['M1']
    print('selected', corrected['selected'], 'gate', corrected['gate']['passed'], 'KS %.3f ratio %.3f' % (corrected['gate']['mean_ks'], corrected['gate']['mean_total_area_ratio']))
    print('M1 before', [round(c, 4) for c in m1['full_coefficients']], round(m1['heldout_sigma'], 3), 'after', [round(c, 4) for c in m0['full_coefficients']], round(m0['heldout_sigma'], 3), 'rows changed', len(changed), 'of', len(primary))
    print('range before', control['area_range_ha'], 'after', corrected['area_range_ha'])


if __name__ == '__main__':
    main()

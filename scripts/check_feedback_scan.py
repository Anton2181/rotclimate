"""Execute the committed64-interval robustness check without replacing maps."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from prepare_settlement_feedback import OUT
from settlement_locations_earth import sha, write
from polity.settlement_feedback import FeedbackInputs, CerealFeedback
from build_settlement_feedback import audit_positive
from review_settlement_feedback import production, harvest_series, inventory, cycle, close

PLAN = ROOT / 'calibration/settlement_feedback_20261112/scan_check.json'


def run(out):
    declaration = json.loads(PLAN.read_text())
    committed = subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT)
    if committed != PLAN.read_bytes():raise ValueError('Commit the finer-scan declaration first')
    out.mkdir(parents=True, exist_ok=True); rows = []; fields = {}
    preserve = {p: h for key, names in declaration['reference_sha256'].items()
                for name, h in names.items() for p in [str((OUT/key/name).relative_to(ROOT))]}
    publication = ROOT/'atlases/earth_fit/data/settlement_feedback.json'
    preserve[str(publication.relative_to(ROOT))] = sha(publication)
    for path, digest in preserve.items():
        if sha(ROOT/path) != digest:raise ValueError('Frozen original changed: ' + path)
    for key in declaration['targets']:
        old = json.loads((OUT/key/'results.json').read_text()); before = dict(np.load(OUT/key/'fields.npz'))
        x = dict(np.load(OUT/f'{old["climate"]}_inputs.npz')); local = x['local_index']; ids=x['owner']; n=len(x['nodes'])
        inputs=FeedbackInputs(x['people'][local],ids,x['potential_kcal'][local],x['boundaries'][local],
            x['listed_hours'][local],x['reaping_hours'][local],x['access'],x['civilian_request'],x['affiliated'],
            np.bincount(ids,weights=x['potential_kcal'][local],minlength=n))
        model=CerealFeedback(inputs,transfer_fraction=.075,hours_worker_year=old['hours_worker_year'])
        result=model.solve(scan_intervals=declaration['scan_intervals'],refinements=declaration['refinements'])
        scan_feasible=np.stack([r['feasible'] for r in result['scan']])
        scan_source=np.stack([r['source_supported'] for r in result['scan']])
        scan_unmet=np.stack([r['destination_unmet'] for r in result['scan']])
        np.testing.assert_array_equal(scan_feasible[::2],before['scan_feasible'])
        np.testing.assert_array_equal(scan_source[::2],before['scan_source_supported'])
        np.testing.assert_array_equal(scan_unmet[::2],before['scan_destination_unmet'])
        # Independent final production and monthly inventories; the physical
        # model is unchanged and the original33control points are exact.
        produced,retained,annual,peak=production(inputs.potential_kcal,inputs.listed_hours,
            inputs.reaping_hours,result['rural'],old['hours_worker_year'])
        close(produced,result['work'].produced_kcal)
        assert np.all(result['work'].annual_hours_used<=annual+1e-7)
        assert np.all(result['work'].reaping_hours_used<=peak+1e-7)
        supply=harvest_series(produced,inputs.boundaries)
        need=np.broadcast_to(result['rural']*2500*365/12,supply.shape)
        rural=inventory(supply,need,need.sum(0),result['rural_food'].year.initial_stock);cycle(rural)
        close(rural['unmet'],result['rural_food'].year.unmet)
        town_need=np.broadcast_to(result['total']*2500*365/12,result['flow']['arrivals'].shape)
        town=inventory(result['flow']['arrivals'],town_need,result['total']*2500*90,result['town_food'].initial_stock);cycle(town)
        close(town['unmet'],result['town_food'].unmet)
        gate=audit_positive(model,result)
        if gate['status']!='passed':raise ValueError('Finer scan failed the same positive source-food gate')
        delta=result['total']-before['total']
        resolution=before['upper']/(32*2**24)+1e-6
        assert np.all(delta>=-resolution)
        row=dict(key=key,old_town_people=float(before['total'].sum()),fine_town_people=float(result['total'].sum()),
            difference_people=float(delta.sum()),maximum_site_difference_people=float(abs(delta).max()),
            sites_changed_over_one_person=int(np.sum(abs(delta)>1)),
            old_active_sources=int(before['active'].sum()),fine_active_sources=int(result['active'].sum()),
            source_flags_changed=int(np.sum(before['active']!=result['active'])),
            exact_overlap_points=33,source_gate=gate,independent_final_work_and_food=True)
        rows.append(row)
        for name,value in dict(total=result['total'],old_total=before['total'],active=result['active'],
            selected_fraction=result['selected_fraction'],scan_feasible=scan_feasible,scan_source=scan_source,
            scan_destination_unmet=scan_unmet).items():fields[key+'__'+name]=value
        print(key,'finer scan delta',row['difference_people'],'people;',row['source_flags_changed'],'source flags changed',flush=True)
    for path,digest in preserve.items():
        if sha(ROOT/path)!=digest:raise ValueError('Original scenario/map changed during numerical check')
    np.savez_compressed(out/'fields.npz',**fields)
    producers=[Path(__file__),ROOT/'polity/settlement_feedback.py',ROOT/'scripts/build_settlement_feedback.py',
               ROOT/'scripts/review_settlement_feedback.py',ROOT/'polity/settlement_residents.py']
    write(out/'results.json',dict(status='declared_finer_scan_robustness',plan_sha256=sha(PLAN),
        fields_sha256=sha(out/'fields.npz'),rows=rows,total_exact_overlap_points=132,
        producers={str(p.relative_to(ROOT)):sha(p) for p in producers},originals_sha256=preserve,
        original_optional_maps_unchanged=True,empirical_accuracy_or_global_optimum_claimed=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT/'scan_check')
    run(p.parse_args().out)

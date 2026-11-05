"""Replay published benchmark scores independently of the fitting functions."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    data=ROOT/'atlases/earth_evidence/data';prepared=json.loads(gzip.decompress((data/'reaping_cases.json.gz').read_bytes()));cases=prepared['cases'];selection=json.loads((data/'selection.json').read_text());evaluation=json.loads((data/'evaluation_original.json').read_text());restricted_result=json.loads((data/'evaluation.json').read_text());panel=json.loads((data/'panel_audit.json').read_text());ledger=json.loads((data/'ledger.json').read_text())
    assert hashlib.sha256(gzip.decompress((data/'reaping_cases.json.gz').read_bytes())).hexdigest()==selection['prepared_sha256']
    assert prepared['identity']==selection['identity']==evaluation['identity']
    train=[c for c in cases if c['split']=='training'];test=[c for c in cases if c['split']=='evaluation']
    overlap={c['household_id'] for c in train}&{c['household_id'] for c in test}
    assert len(overlap)==panel['leaking_households']==5
    tainted=set(panel['affected_district_label_ids']);restricted=[c for c in test if c['district_id'] not in tainted]
    assert [c['case_id'] for c in restricted]==panel['restricted_case_ids']
    for key in ['case_id','household_id','village_id','district_id']:assert not {c[key] for c in train}&{c[key] for c in restricted},key
    assert selection['training_case_ids']==[c['case_id'] for c in train]
    for group,summary in [(train,selection),(test,evaluation),(restricted,restricted_result)]:
        for scale,key in [(1.,'baseline'),(selection['scale'],'candidate')]:
            districts=defaultdict(list)
            for c in group:
                assert c['hectares']>0 and c['human_reaping_hours']>0 and c['household_members']>0
                assert abs(c['family_reaping_hours']+c['hired_reaping_hours']+c['exchange_reaping_hours']-c['human_reaping_hours'])<1e-7
                assert abs(c['baseline_hours']-c['hectares']*{'WHEAT':48,'BARLEY':32}[c['crop']])<1e-7
                districts[c['district_id']].append(math.log10(scale*c['baseline_hours']/c['human_reaping_hours']))
            absolute=sum(sum(abs(v) for v in values)/len(values) for values in districts.values())/len(districts)
            factor_two=sum(sum(abs(v)<=math.log10(2) for v in values)/len(values) for values in districts.values())/len(districts)
            expected=summary[('training_'+key) if group is train else key]
            assert math.isclose(absolute,expected['equal_district_abs_log10_error'],rel_tol=1e-12)
            assert math.isclose(factor_two,expected['equal_district_within_factor_two'],rel_tol=1e-12)
    assert all(not c['strict_recorded_input_subgroup'] for c in cases)
    assert not evaluation['ancient_default_adoption'] and not evaluation['production_atlas_changed']
    assert evaluation['evaluation_pool_now_spent']
    assert not panel['prospective_qualification'] and not restricted_result['prospective_qualification']
    for r in ledger['parameters']:
        if r['source']=='data/settlement_labour_model.json':assert r['status']=='scenario'
    out=dict(status='passed',training_cases=len(train),evaluation_cases=len(test),original_overlapping_households=len(overlap),original_full_evaluation_invalidated=True,restricted_cases=len(restricted),restricted_household_village_district_overlap=False,metrics_replayed=True,prospective_qualification=False,modern_comparator_only=True,strict_input_analogues=0)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))


if __name__=='__main__':main()

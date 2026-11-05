"""Invalidate the full v1 split; retain an explicitly post-audit diagnostic.

No coefficient is refitted. All records of every affected district label are
excluded from the restricted evaluation, not only overlapping households.
"""
from pathlib import Path
import argparse
from collections import defaultdict
import hashlib
import gzip
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    from harvest.panel_validation import panel_leakage,require_independent_panels
    from harvest.earth_reaping import metrics
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=ROOT/'output/earth_components_20261105/reaping');a=ap.parse_args()
    cache=ROOT/'data/cache/vdsa_8224522/prepared_reaping.json';raw=cache.read_bytes() if cache.exists() else gzip.decompress((ROOT/'atlases/earth_evidence/data/reaping_cases.json.gz').read_bytes());data=json.loads(raw);cases=data['cases'];selection=json.loads((a.out/'selection.json').read_text());original=json.loads((a.out/'evaluation.json').read_text())
    assert hashlib.sha256(raw).hexdigest()==selection['prepared_sha256']
    crossing=panel_leakage(cases);tainted={c['district_id'] for v in crossing.values() for c in v};train=[c for c in cases if c['split']=='training'];test=[c for c in cases if c['split']=='evaluation'];kept=[c for c in test if c['district_id'] not in tainted]
    require_independent_panels(train+kept)
    result=dict(status='full_v1_evaluation_invalidated',original_evaluation_sha256=hashlib.sha256((a.out/'evaluation.json').read_bytes()).hexdigest(),selection_sha256=hashlib.sha256((a.out/'selection.json').read_bytes()).hexdigest(),prepared_sha256=selection['prepared_sha256'],producer_snapshot_commit='5ddb6d20',leaking_households=len(crossing),leaking_training_cases=sum(c['household_id'] in crossing for c in train),leaking_evaluation_cases=sum(c['household_id'] in crossing for c in test),affected_district_label_ids=sorted(tainted),cause='Raw source state labels MAHARASHTRA / MAHARASTRA split the same Akola district across folds. Detected by independent household-ID replay, not outcome-based exclusion.',original_cases=len(test),restricted_cases=len(kept),removed_evaluation_cases=len(test)-len(kept),restricted_districts=len({c['district_id'] for c in kept}),restricted_case_ids=[c['case_id'] for c in kept],baseline=metrics(kept,1),candidate=metrics(kept,selection['scale']),scale_refitted=False,prospective_qualification=False,ancient_default_adoption=False,restricted_interpretation='Post-audit diagnostic with the whole affected district removed. Remaining districts have no training household overlap. This is not a new untouched or fully prospective validation.',original_numeric_qualification=original['qualified_for_modern_comparator'])
    (a.out/'panel_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['restricted_case_ids','baseline','candidate']},indent=2));print('Restricted errors',result['baseline']['equal_district_abs_log10_error'],result['candidate']['equal_district_abs_log10_error'])


if __name__=='__main__':main()

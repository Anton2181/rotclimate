"""Compile conditional housing references; never fill missing dates or city sizes."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.settlement_size_evidence import HousingSample
from settlement_locations_earth import sha,write

SOURCE=ROOT/'data/source/roman_housing_2023'
OUT=ROOT/'output/settlement_size_evidence_20261112'
PLAN=ROOT/'calibration/settlement_size_evidence_20261112'


def main(out):
    for name in ('plan.json','source_access_amendment.json'):
        p=PLAN/name
        if subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)!=p.read_bytes():
            raise ValueError('Commit source preparation declarations first')
    metadata=json.loads((SOURCE/'source.json').read_text())
    with (SOURCE/'table2.csv').open() as f:source=list(csv.DictReader(f))
    if len(source)!=50 or len({r['city_key'] for r in source})!=50:raise ValueError('Expected all50 unique source keys')
    rows=[];blockers=Counter()
    for r in source:
        phase=metadata['chronology'].get(r['city_key'],{})
        x=HousingSample(r['city_key'],int(r['properties']),float(r['sample_area_ha']),float(r['site_area_ha']),
            metadata['citation'],excluded_years=(150,) if phase.get('target_AD150')=='outside_reported_phase' else ())
        reasons=x.blockers(150);blockers.update(reasons)
        references={str(h):x.reference(h) for h in metadata['household_assumptions']['sensitivity_persons']}
        rows.append(dict(r,properties=x.properties,sample_area_ha=x.sample_area_ha,site_area_ha=x.site_area_ha,
            sample_phase=phase.get('description',metadata['all_other_chronology']),
            sample_fraction=x.sample_area_ha/x.site_area_ha,
            reference_scenarios=references,AD150_blockers=list(reasons),AD150_size_fit_eligible=not reasons,
            identity_kind='author_supplied_catalogue_key_not_independently_joined'))
    fractions=np.array([r['sample_fraction'] for r in rows]);counts=np.array([r['properties'] for r in rows])
    summary=dict(source_rows=len(rows),unique_city_keys=len(rows),Britannia_rows=sum(r['province']=='Britannia' for r in rows),
        properties_observed_sum=int(counts.sum()),sample_fraction_min=float(fractions.min()),
        sample_fraction_median=float(np.median(fractions)),sample_fraction_max=float(fractions.max()),
        samples_below_one_percent=int((fractions<.01).sum()),samples_below_ten_percent=int((fractions<.1).sum()),
        samples_whole_stated_extent=int((fractions==1).sum()),AD150_eligible=sum(r['AD150_size_fit_eligible'] for r in rows),
        blocker_counts=dict(blockers),reference_people_at5_min=min(r['reference_scenarios']['5']['people'] for r in rows),
        reference_people_at5_max=max(r['reference_scenarios']['5']['people'] for r in rows))
    out.mkdir(parents=True,exist_ok=True)
    sources=[SOURCE/'source.json',SOURCE/'table2.csv',PLAN/'plan.json',PLAN/'source_access_amendment.json',
        Path(__file__),ROOT/'polity/settlement_size_evidence.py']
    write(out/'results.json',dict(status='housing_preparation_not_size_calibration',adopt=False,summary=summary,rows=rows,
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},
        original52_case_source_recovered=False,catalogue_join_certified=False,
        household_sensitivity_is_confidence_interval=False,fantasy_models_scored=False,
        notes='Sample counts,areas and all3household scenarios retained. ZeroAD150eligible references is a measurement/date gate,not zerohistorical inhabitants.'))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT)
    main(p.parse_args().out)

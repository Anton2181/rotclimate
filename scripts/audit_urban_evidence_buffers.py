"""Read-only evidence contracts and original baseline storage-path diagnostics."""
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/urban_evidence_buffers_20261116'
TIMING=ROOT/'output/urban_calendar_sensitivity_20261116'
MONTHLY=ROOT/'output/urban_earth_monthly_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_evidence_buffer_audit.json'
KCAL=912500.


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def total(value):return math.fsum(np.asarray(value).ravel())


def table(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    expected={};protected={}
    for folder,status in [(TIMING,'passed_four_exact_energy_timing_recipes_with_fixed_grain_work_and_population'),
                          (MONTHLY,'passed_fixed_request_Earth_monthly_food_portability_pilot')]:
        q=read(folder/'qualification.json');assert q['status']==status
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in q[key].items():
                p=str(prefix/name);assert p not in expected or expected[p]==digest,p;expected[p]=digest
        protected.update(q['protected_sha256'])
    for name,digest in expected.items():assert sha(name)==digest,name
    OUT.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'results.json').exists(),'Use a fresh isolated OUT for completed-audit replay'
    facts=[
        dict(id='legacy_calendar',source='reports/CROP_CALENDARS_20261103.md',locator='Opening and integration contract',
             quote='A calendar chosen this way is not an observed harvest date;',
             evidence='Original best-window/tie mechanism; climate-bin crop feasibility',
             can_establish='Exact model energy/window identity and attainable alternatives',
             cannot_establish='Observed planting/harvest dates,ancient cultivar practice or independent date/yield validation',
             integration_gate='Keep window alternatives explicit; do not adopt the most favorable meal recipe'),
        dict(id='observed_modern_calendars',source='reports/OBSERVED_CROP_CALENDARS_20261103.md',locator='What this establishes',
             quote='Passing the duration envelope is only necessary:',
             evidence='Already exposed modern regional calendars; qualifiers and exclusions retained',
             can_establish='Duration-envelope and coarse cold-exposure diagnostics',
             cannot_establish='Ancient pointwise dates,a predicted harvest-date error or yield validation',
             integration_gate='A separately declared cultivar/date comparison is needed; no raw records read here'),
        dict(id='conditional_cereal_clock',source='reports/CEREAL_DEVELOPMENT_20261103.md',locator='Complete results and integration status',
             quote='The actual trained chilling candidate performs worse',
             evidence='Physiological maturity conditional on supplied sowing; evaluated country groups already scored',
             can_establish='Limited conditional-duration comparison; heat-only28.56d vs threshold51.99d evaluation error',
             cannot_establish='Endogenous sowing,harvest operations,water/yield coupling or an untouched validation pool',
             integration_gate='Trained chilling68.06d and2/29nonmaturity failures do not pass adoption; preserve the negative result'),
        dict(id='fao_stage_examples',source='reports/CROP_STAGE_20261114.md',locator='Source findings/Table11',
             quote='No row establishes an ancient Nile barley calendar.',
             evidence='Published conditional stage durations/Kcb coefficients with planting and region labels',
             can_establish='Supplied-stage coefficient curves and exact component integrals',
             cannot_establish='Universal Nile barley dates,unadjusted local ET or measured root transpiration',
             integration_gate='Local phenology,climatic adjustment,diffusion/root-uptake and yield contracts remain separate'),
        dict(id='reserve_algebra',source='reports/CALENDAR_STORAGE_20261103.md',locator='Literature and mathematical scope',
             quote='Neither source supplies a universal 200 AD granary capacity or storage-loss coefficient.',
             evidence='Zero-loss perfectly repeating uniform-demand storage scenario and checked algebra',
             can_establish='Conditional minimum reserve mathematics in days of specified demand',
             cannot_establish='Historical granary capacity,loss rate,food-risk probability or actual supported people',
             integration_gate='Historical capacity/loss evidence or explicitly labelled robustness scenarios needed'),
        dict(id='current_food_scenario',source='reports/URBAN_EARTH_MONTHLY_20261116.md',locator='The actual trial and independent checks',
             quote='The annual→monthly comparison does not identify the causal effect of storage loss or calendar timing alone.',
             evidence='Fixed requests;365d source/export,90d town,5%stock loss and one-bin legs',
             can_establish='Original-tolerance physical stock,route and grain accounting at specified assumptions',
             cannot_establish='Empirical calibration of those assumptions,actual occupancy or demographic equilibrium',
             integration_gate='Isolate uncertain mechanisms before any fit/adoption; exact accounting is not empirical validation')
    ]
    sources={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__)),str(PLAN.relative_to(ROOT)):sha(PLAN),
             str((TIMING/'qualification.json').relative_to(ROOT)):sha(TIMING/'qualification.json'),
             str((MONTHLY/'qualification.json').relative_to(ROOT)):sha(MONTHLY/'qualification.json')}
    for row in facts:
        path=ROOT/row['source'];text=' '.join(path.read_text().split())
        assert row['quote'] in text,(row['id'],row['quote'])
        sources[row['source']]=sha(path)
    for name in ['calibration/crop_calendar_observations_20261103/plan.json','calibration/cereal_phenology_20261103/plan.json',
                 'calibration/crop_stage_20261114/plan.json','scripts/land_people.py','harvest/phenology.py',
                 'harvest/food_stocks.py','polity/earth_fixed_food.py','polity/seasonal_settlement_network.py']:
        sources[name]=sha(ROOT/name)
    buffers=[]
    for reading in ['central','low']:
        path=MONTHLY/'cases'/reading/'fields.npz';sources[str(path.relative_to(ROOT))]=sha(path);c=dict(np.load(path))
        rural_need=c['rural']*KCAL;town_need=c['request']*KCAL
        groups=[
            ('rural','rural_food',c['harvest'],np.broadcast_to(rural_need/12,c['harvest'].shape),rural_need),
            ('commercial_export','export_food',c['marketed'],c['dispatch'],c['marketed'].sum(0)),
            ('town','town_food',c['arrivals'],np.broadcast_to(town_need/12,c['arrivals'].shape),c['request']*2500*90)
        ]
        for label,prefix,supply,demand,capacity in groups:
            initial=c[prefix+'__stock_path'][0]
            available=c[prefix+'__stock_path'][:-1]+supply
            retained=np.minimum(available-np.minimum(available,demand),capacity)
            peak=np.maximum(initial,retained.max(0))
            np.testing.assert_array_equal(peak,c[prefix+'__peak_stock'])
            simultaneous=max(total(initial),max(total(row) for row in retained))
            independent=total(peak);assert simultaneous<=independent+1e-12*max(1,independent)
            valid=capacity>0;fractions=np.divide(peak,capacity,out=np.zeros_like(capacity),where=valid)
            row=dict(reading=reading,store_class=label,positive_capacity_inventories=int(valid.sum()),
                capacity_grain_person_years=total(capacity)/KCAL,
                simultaneous_peak_grain_person_years=simultaneous/KCAL,
                sum_of_individual_peaks_grain_person_years=independent/KCAL,
                median_individual_peak_fraction=float(np.median(fractions[valid])),
                spoilage_grain_person_years=total(c[prefix+'__spoiled'])/KCAL,
                hypothetical_quarter_capacity_exceeded_count='',actually_exporting_origins='',
                exporting_origin_quarter_threshold_count='',departing_grain_share_from_flagged_origins='')
            if label=='commercial_export':
                quarter=capacity*90/365;flag=valid&(peak>quarter);exporting=c['departures'].sum(0)>0
                row.update(hypothetical_quarter_capacity_exceeded_count=int(flag.sum()),
                    actually_exporting_origins=int(exporting.sum()),exporting_origin_quarter_threshold_count=int((flag&exporting).sum()),
                    departing_grain_share_from_flagged_origins=total(c['departures'][:,flag])/total(c['departures']))
            buffers.append(row)
    table(OUT/'evidence_contracts.csv',facts);table(OUT/'buffer_usage.csv',buffers)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    result=dict(status='completed_read_only_existing_evidence_and_baseline_buffer_audit',
        sources_sha256=sources,protected_sha256=protected,
        files_sha256={name:sha(OUT/name) for name in ['evidence_contracts.csv','buffer_usage.csv']},
        evidence_contracts=facts,buffer_diagnostics=buffers,individual_peaks_reconstructed_bit_exact=True,
        simultaneous_peaks_are_not_sums_of_individual_peaks=True,raw_observation_records_read=False,
        per_record_geographic_intersection=False,phenology_rescored=False,food_kernel_reruns=0,
        hypothetical_threshold_is_not_a_meal_forecast=True,new_fit=False,new_validation_claim=False,adopt=False)
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],flush=True)
    for row in buffers:print(json.dumps(row),flush=True)


if __name__=='__main__':main()

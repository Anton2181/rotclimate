"""Source-only selection and extent-basis audit; no new size fit or scores."""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT/'data/cache/roman_city_source_recovery_20261113'
OUT = ROOT/'output/urban_development_evidence_20261116'
PLAN = ROOT/'calibration/urban_diagnosis_20261116/development_evidence.json'
SCREEN = ROOT/'output/urban_concentration_20261116'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def aggregate(records):
    n = len(records)
    counts = lambda key: dict(sorted(Counter(r[key] for r in records).items()))
    a = [r['area'] for r in records]
    return dict(records=n,estimate_basis=counts('basis'),provinces=counts('province'),
                old_province_hash_fold={str(k):sum(hashlib.sha256(r['province'].encode()).digest()[0]%4==k for r in records) for k in range(4)},
                raw_area_bins={'below10':sum(v<10 for v in a),'10_through20':sum(10<=v<=20 for v in a),
                               'above20_through40':sum(20<v<=40 for v in a),'above40_through200':sum(40<v<=200 for v in a),'above200':sum(v>200 for v in a)})


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT) == PLAN.read_bytes()
    old = json.loads((SCREEN/'results.json').read_text());review = json.loads((SCREEN/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(SCREEN/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_concentration_screen.py')
    for name,digest in {**old['producers'],**old['protected_sha256']}.items(): assert sha(ROOT/name)==digest,name
    for name,digest in old['files_sha256'].items():assert sha(SCREEN/name)==digest,name
    metadata = json.loads((CACHE/'initial_schema.json').read_text())
    for entry in metadata['tables']:assert sha(CACHE/entry['file'])==entry['sha256']
    cities = list(csv.DictReader(io.StringIO((CACHE/'cities.csv').read_bytes().decode('cp1252'))))
    areas = list(csv.DictReader(io.StringIO((CACHE/'areas.csv').read_bytes().decode('utf-8-sig'))))
    assert len({r['Primary Key'] for r in cities})==len(cities)
    assert len({r['Primary Key'] for r in areas})==len(areas)
    city = {r['Primary Key']:r for r in cities}; area = {r['Primary Key']:r for r in areas}
    selected = [r for r in cities if float(r['Start Date'])<=150 and (r['End Date'].strip().upper()=='NULL' or float(r['End Date'])>=150)]
    joined = [];invalid=0
    for c in selected:
        if c['Primary Key'] not in area:continue
        a = area[c['Primary Key']]
        try: v=float(a['Area'])
        except ValueError:invalid+=1;continue
        if not (v>0 and v<float('inf')):invalid+=1;continue
        joined.append(dict(province=c['Province'],basis=a['Estimate Basis'],area=v))
    excluded = [r for r in joined if r['area'] in (20.,30.)]
    retained = [r for r in joined if r['area'] not in (20.,30.)]
    cohorts = {'catalogue_AD150_joined_positive_areas':aggregate(joined),'catalogue_AD150_without_exact20_30':aggregate(retained),'catalogue_AD150_exact20_30_excluded':aggregate(excluded)}
    rows=[]
    for name,cohort in cohorts.items():
        for group in ['estimate_basis','provinces','old_province_hash_fold','raw_area_bins']:
            for label,count in cohort[group].items(): rows.append(dict(cohort=name,group=group,label=label,count=count))
    observations_path = ROOT/'output/urban_diagnosis_20261116/observations.json'
    obs = json.loads(observations_path.read_text())
    surveys = {p:{key:obs[p]['3'][key] for key in ['selected_source_records','town_records','source_defined_town_threshold_ha','area_observation','survey_proxy_is_independent_coverage']} for p in ['floodplains','mexico']}
    release_path = ROOT/'output/settlement_release4_20261116/earth_results.json'
    release = json.loads(release_path.read_text())
    actual = {key:release['sizes']['primary'][key] for key in ['cohort','n','provinces','fold_sizes','fold_provinces','area_range_ha']}
    protected = dict(old['protected_sha256'])
    protected.update(old['producers'])
    for name in ['results.json','model.npz','cases.csv','review.json']:protected[str((SCREEN/name).relative_to(ROOT))]=sha(SCREEN/name)
    paths = [Path(__file__),PLAN,CACHE/'initial_schema.json',CACHE/'cities.csv',CACHE/'areas.csv',release_path,observations_path]
    out.mkdir(parents=True,exist_ok=True)
    with (out/'aggregates.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['cohort','group','label','count']);writer.writeheader();writer.writerows(rows)
    result=dict(status='source_selection_audit_no_fit',
                accounting=dict(source_cities=len(cities),source_areas=len(areas),unmatched_area_keys=len(set(area)-set(city)),
                                all_cities_without_area=sum(k not in area for k in city),catalogue_AD150_cities=len(selected),
                                catalogue_AD150_without_area=sum(r['Primary Key'] not in area for r in selected),invalid_or_nonpositive_selected_areas=invalid),
                area_table_fields=list(areas[0]),area_date_certified_by_table=False,
                cohorts=cohorts,actual_release4_training_metadata=actual,survey_cohorts=surveys,
                sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=protected,
                files_sha256={'aggregates.csv':sha(out/'aggregates.csv')},fit_performed=False,new_scores=False,new_blind_test=False,adopt=False,climate_changed=False,
                limits='Source-only Roman cohorts precede geographic/allowed-land/H/finite-core filtering and Greek wall-area corrections in the existing training pipeline. Raw extents are not all certified inhabited areas at AD150. Town selection and area availability differ from archaeological all-site cohorts. No town identities or source coordinates exported.')
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(accounting=result['accounting'],source_cohort_sizes={k:v['records'] for k,v in cohorts.items()},area_table_fields=result['area_table_fields']),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)

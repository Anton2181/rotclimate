"""Recount source eligibility with a separate table reader and scalar loops."""
import csv
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/urban_development_evidence_20261116'
CACHE = ROOT/'data/cache/roman_city_source_recovery_20261113'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name,encoding):
    with (CACHE/name).open(encoding=encoding,newline='') as f:
        table = list(csv.reader(f))
    return table[0],table[1:]


def main():
    r = json.loads((OUT/'results.json').read_text())
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    ch,cities=read('cities.csv','cp1252');ah,areas=read('areas.csv','utf-8-sig')
    assert ch.count('Primary Key')==1 and ah==['Primary Key','Area','Estimate Basis']
    ci={k:i for i,k in enumerate(ch)};catalogue={c[ci['Primary Key']]:c for c in cities};extents={a[0]:a for a in areas}
    assert len(catalogue)==len(cities)==1388 and len(extents)==len(areas)==885
    selected={}
    for key,c in catalogue.items():
        begin=float(c[ci['Start Date']]);end=c[ci['End Date']].strip().upper()
        if begin<=150 and (end=='NULL' or float(end)>=150):selected[key]=c
    records=[];invalid=0
    for key,c in selected.items():
        if key not in extents:continue
        raw=extents[key]
        try:a=float(raw[1])
        except ValueError:invalid+=1;continue
        if not math.isfinite(a) or a<=0:invalid+=1;continue
        records.append((c[ci['Province']],raw[2],a))
    accounting=dict(source_cities=len(cities),source_areas=len(areas),unmatched_area_keys=len(extents.keys()-catalogue.keys()),
                    all_cities_without_area=len(catalogue.keys()-extents.keys()),catalogue_AD150_cities=len(selected),
                    catalogue_AD150_without_area=len(selected.keys()-extents.keys()),invalid_or_nonpositive_selected_areas=invalid)
    assert r['accounting']==accounting
    expected={}
    for label,subset in [('catalogue_AD150_joined_positive_areas',records),
                         ('catalogue_AD150_without_exact20_30',[x for x in records if x[2]!=20 and x[2]!=30]),
                         ('catalogue_AD150_exact20_30_excluded',[x for x in records if x[2]==20 or x[2]==30])]:
        basis=defaultdict(int);provinces=defaultdict(int);folds={str(k):0 for k in range(4)}
        bins={k:0 for k in ['below10','10_through20','above20_through40','above40_through200','above200']}
        for province,description,a in subset:
            basis[description]+=1;provinces[province]+=1
            folds[str(int(hashlib.sha256(province.encode('utf-8')).hexdigest()[:2],16)%4)]+=1
            edge=next((edge for edge in [10,20,40,200] if (a<edge if edge==10 else a<=edge)),None)
            bins[{10:'below10',20:'10_through20',40:'above20_through40',200:'above40_through200',None:'above200'}[edge]]+=1
        expected[label]=dict(records=len(subset),estimate_basis=dict(basis),provinces=dict(provinces),old_province_hash_fold=folds,raw_area_bins=bins)
        for counts in [basis,provinces,folds,bins]:assert sum(counts.values())==len(subset)
    assert r['cohorts']==expected
    assert r['area_table_fields']==ah and r['area_date_certified_by_table'] is False
    actual=json.loads((ROOT/'output/settlement_release4_20261116/earth_results.json').read_text())['sizes']['primary']
    assert r['actual_release4_training_metadata']=={k:actual[k] for k in ['cohort','n','provinces','fold_sizes','fold_provinces','area_range_ha']}
    assert sum(actual['fold_sizes'])==actual['n']==664 and sum(actual['fold_provinces'])==actual['provinces']
    observations=json.loads((ROOT/'output/urban_diagnosis_20261116/observations.json').read_text())
    for pool,n,t in [('floodplains',820,119),('mexico',221,27)]:
        assert r['survey_cohorts'][pool]=={k:observations[pool]['3'][k] for k in ['selected_source_records','town_records','source_defined_town_threshold_ha','area_observation','survey_proxy_is_independent_coverage']}
        assert r['survey_cohorts'][pool]['selected_source_records']==n and r['survey_cohorts'][pool]['town_records']==t
    with (OUT/'aggregates.csv').open() as f:rows=list(csv.DictReader(f))
    cells={}
    for row in rows:
        key=row['cohort'],row['group'],row['label'];assert key not in cells;cells[key]=int(row['count'])
    expected_cells={(name,group,label):value for name,c in expected.items() for group in ['estimate_basis','provinces','old_province_hash_fold','raw_area_bins'] for label,value in c[group].items()}
    assert cells==expected_cells
    for flag in ['fit_performed','new_scores','new_blind_test','adopt','climate_changed']:assert r[flag] is False
    fresh={}
    for name in ['results.json','aggregates.csv']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes();fresh[name]=sha(OUT/name)
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
                method='No producer import. Independent csv.reader joins, date eligibility, scalar basis/province/area bins and hexadecimal province folds. Complete accounting and all aggregate CSV cells; existing training and survey metadata independently read.',
                source_cities=len(cities),source_areas=len(areas),aggregate_cells=len(cells),fresh_byte_exact=fresh,fit_performed=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Reviewed {len(cities)} cities / {len(areas)} area records, {len(cells)} aggregates and two exact fresh files; no fit')


if __name__=='__main__':main()

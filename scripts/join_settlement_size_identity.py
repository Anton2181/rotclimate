"""Join housing samples to the pinned city catalogue by author key; audit, never fill."""
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

import numpy as np
import openpyxl
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.settlement_place_groups import place_groups
from settlement_locations_earth import sha,write

PLAN=ROOT/'calibration/settlement_size_identity_20261112/plan.json'
AMENDMENT=PLAN.with_name('key_format_amendment.json')
KEY=re.compile(r'Hanson2016_([1-9][0-9]*)')
WORKBOOK=ROOT/'data/cache/hanson2016/cities.xlsx'
SOURCE=ROOT/'data/source/roman_housing_2023'
PARENT=ROOT/'output/settlement_size_evidence_20261112/results.json'
OUT=ROOT/'output/settlement_size_identity_20261112'
SEED=20261112;SHUFFLES=20000
CLASSES=('below_1_percent','1_to_below_10_percent','10_to_below_100_percent','whole_stated_extent')


def number(v):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and np.isfinite(v)


def normal(text):
    text=unicodedata.normalize('NFKD',str(text))
    return re.sub(r'[^a-z0-9]','',''.join(c for c in text if not unicodedata.combining(c)).casefold())


def agreement(a,b):
    if a==b:return 'exact'
    return 'equal_after_normalisation' if normal(a)==normal(b) else 'different'


def fraction_class(f):
    if f==1:return CLASSES[3]
    return CLASSES[0] if f<.01 else CLASSES[1] if f<.1 else CLASSES[2]


def association(x,y):
    """Spearman with the declared fixed-seed two-sided permutation description."""
    rho=float(spearmanr(x,y).statistic)
    # Average ranks so ties are treated exactly as in the reported statistic.
    def ranks(v):
        v=np.asarray(v,float);order=np.argsort(v,kind='stable');r=np.empty(len(v))
        i=0
        while i<len(v):
            j=i
            while j+1<len(v) and v[order[j+1]]==v[order[i]]:j+=1
            r[order[i:j+1]]=(i+j)/2+1;i=j+1
        return r
    rx,ry=ranks(x),ranks(y);rng=np.random.default_rng(SEED);hits=0
    cx=rx-rx.mean();denominator=np.sqrt((cx**2).sum()*((ry-ry.mean())**2).sum())
    for _ in range(SHUFFLES):
        p=rng.permutation(ry)
        if abs(float((cx*(p-p.mean())).sum()/denominator))>=abs(rho)-1e-12:hits+=1
    return dict(n=len(x),spearman_rho=rho,permutation_p_two_sided=(hits+1)/(SHUFFLES+1))


def main(out):
    for p in (PLAN,AMENDMENT):
        if subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)!=p.read_bytes():
            raise ValueError('Commit the join declaration and key-format amendment first')
    plan=json.loads(PLAN.read_text())
    if sha(WORKBOOK)!=plan['source_recovery']['pinned_workbook']['sha256']:raise ValueError('Workbook is not the pinned source')
    wb=openpyxl.load_workbook(WORKBOOK,read_only=True,data_only=True)
    try:city_rows=list(wb['Cities'].values);area_rows=list(wb['Areas'].values)
    finally:wb.close()
    cities=[dict(zip(city_rows[0],v)) for v in city_rows[1:] if v[0]]
    areas=defaultdict(list)
    for row in area_rows[1:]:
        if row[0]:areas[row[0]].append(row)

    def cohort(c):
        return number(c['Start Date']) and c['Start Date']<=150 and (not number(c['End Date']) or c['End Date']>=150)

    def positive(c):
        v=areas[c['Primary Key']]
        return len(v)==1 and number(v[0][1]) and v[0][1]>0
    selected=[c for c in cities if cohort(c)]
    gate=dict(cities=len(cities),cities_single_positive_area=sum(map(positive,cities)),
        cities_without_area_record=sum(not areas[c['Primary Key']] for c in cities),AD150_cohort=len(selected),
        AD150_single_positive_area=sum(map(positive,selected)),
        AD150_without_area_record=sum(not areas[c['Primary Key']] for c in selected))
    expected=dict(cities=1388,cities_single_positive_area=885,cities_without_area_record=503,AD150_cohort=1354,
        AD150_single_positive_area=862,AD150_without_area_record=492)
    if gate!=expected:raise ValueError('Recovered workbook fails the declared consistency gate: '+json.dumps(gate))

    # Declared key format: Table 2 integer k is exactly catalogue key Hanson2016_k.
    for label,keys in (('Cities',[c['Primary Key'] for c in cities]),('Areas',list(areas))):
        matches=[KEY.fullmatch(k) if isinstance(k,str) else None for k in keys]
        if not all(matches) or len({int(m.group(1)) for m in matches})!=len(keys):
            raise ValueError(label+' keys do not follow the declared unique Hanson2016_<integer> format')
    by_key=defaultdict(list)
    for c in cities:by_key[c['Primary Key']].append(c)
    with (SOURCE/'table2.csv').open() as f:table=list(csv.DictReader(f))
    parent=json.loads(PARENT.read_text());parent_rows={r['city_key']:r for r in parent['rows']}
    if len(table)!=50 or set(parent_rows)!={r['city_key'] for r in table}:raise ValueError('Expected the 50 reviewed housing rows')
    # The legacy loader fills missing areas with the median of the same Barrington
    # rank inside its coordinate-requiring cohort; record that exposure, not the fill.
    rows=[];counts=Counter()
    for r in table:
        key='Hanson2016_%d'%int(r['city_key']);found=by_key.get(key,[]);p=parent_rows[r['city_key']]
        density=p['properties']/p['sample_area_ha']
        row=dict(city_key=r['city_key'],table_name=r['ancient_name'],table_province=r['province'],
            table_site_area_ha=p['site_area_ha'],sample_area_ha=p['sample_area_ha'],properties=p['properties'],
            sample_fraction=p['sample_fraction'],sample_fraction_class=fraction_class(p['sample_fraction']),
            properties_per_sampled_ha=density,AD150_blockers=p['AD150_blockers'],catalogue_rows=len(found))
        if len(found)!=1:
            row.update(identity_status='unjoined');counts['unjoined']+=1;rows.append(row);continue
        c=found[0];records=areas[key];start,end=c['Start Date'],c['End Date']
        row.update(identity_status='catalogue_key_joined',catalogue_primary_key=key,catalogue_ancient_toponym=c['Ancient Toponym'],
            catalogue_province=c['Province'],barrington_rank=None if c['Barrington Atlas Rank'] is None else str(c['Barrington Atlas Rank']),
            name_agreement=agreement(r['ancient_name'],c['Ancient Toponym']),
            province_agreement=agreement(r['province'],c['Province']),
            catalogue_start=start,catalogue_end=end,area_records=len(records))
        counts['name_'+row['name_agreement']]+=1;counts['province_'+row['province_agreement']]+=1
        if number(start) and number(end) and start<=150<=end:date='covers'
        elif (number(start) and start>150) or (number(end) and end<150):date='excludes'
        else:date='open_or_nonnumeric'
        row['catalogue_AD150']=date;counts['catalogue_AD150_'+date]+=1
        row['catalogue_dates_are_sample_phase']=False
        if not records:state='catalogue_missing'
        elif len(records)>1:state='catalogue_ambiguous'
        elif not number(records[0][1]) or records[0][1]<=0:state='catalogue_nonnumeric_or_nonpositive'
        else:
            value=Decimal(str(records[0][1]));stated=Decimal(r['site_area_ha'])
            half=Decimal(5).scaleb(stated.as_tuple().exponent-1)
            state='equal' if abs(value-stated)<=half else 'different'
            row.update(catalogue_area_ha=records[0][1],table_over_catalogue_area=float(stated/value))
        if records and len(records)==1:row['catalogue_estimate_basis']=records[0][2]
        row['area_agreement']=state;counts['area_'+state]+=1
        located=number(c['Longitude (X)']) and number(c['Latitude (Y)'])
        row['exposure']=dict(count_audit_AD150_cohort=bool(cohort(c)),legacy_placement_loader_AD150=bool(cohort(c) and located),
            legacy_loader_area='catalogue_area' if positive(c) else 'rank_median_fill',
            note='Exposed Roman development evidence; never a blind or transfer pool.')
        counts['exposed_count_cohort']+=bool(cohort(c));counts['exposed_placement_loader']+=bool(cohort(c) and located)
        row['_point']=(c['Longitude (X)'],c['Latitude (Y)']) if located else None
        row['_normal_name']=normal(c['Ancient Toponym']);counts['joined']+=1;rows.append(row)
    duplicates=[]
    for label,field in (('identical_catalogue_coordinates','_point'),('identical_normalised_toponym','_normal_name')):
        groups=defaultdict(list)
        for r in rows:
            if r.get(field):groups[r[field]].append(r['city_key'])
        duplicates+=[dict(kind=label,city_keys=v) for v in groups.values() if len(v)>1]
    for r in rows:r.pop('_point',None);r.pop('_normal_name',None)
    identities={r['city_key']:r['catalogue_primary_key'] for r in rows if r['identity_status']=='catalogue_key_joined'}
    grouped=place_groups([r['city_key'] for r in rows],identities)

    density=np.array([r['properties_per_sampled_ha'] for r in rows]);fraction=np.array([r['sample_fraction'] for r in rows])
    site=np.array([r['table_site_area_ha'] for r in rows]);sample=np.array([r['sample_area_ha'] for r in rows])
    britain=np.array([r['table_province']=='Britannia' for r in rows]);whole=fraction==1
    classes={}
    for name in CLASSES:
        keep=np.array([r['sample_fraction_class']==name for r in rows])
        classes[name]=dict(rows=int(keep.sum()),median_properties_per_sampled_ha=float(np.median(density[keep])),
            min_properties_per_sampled_ha=float(density[keep].min()),max_properties_per_sampled_ha=float(density[keep].max()))
    associations={}
    for label,keep in (('all_rows',np.ones(len(rows),bool)),('excluding_whole_extent_samples',~whole),
            ('Britannia',britain),('other_provinces',~britain)):
        associations[label]={name:association(values[keep],density[keep]) for name,values in
            (('density_vs_sampled_fraction',fraction),('density_vs_stated_site_area',site),('density_vs_investigated_area',sample))}
    summary=dict(housing_rows=len(rows),joined_by_author_key=counts['joined'],unjoined=counts['unjoined'],
        name_agreement={k:counts['name_'+k] for k in ('exact','equal_after_normalisation','different')},
        province_agreement={k:counts['province_'+k] for k in ('exact','equal_after_normalisation','different')},
        area_agreement={k[5:]:v for k,v in sorted(counts.items()) if k.startswith('area_')},
        catalogue_AD150={k[16:]:v for k,v in sorted(counts.items()) if k.startswith('catalogue_AD150_')},
        exposed_in_count_audit_AD150_cohort=counts['exposed_count_cohort'],
        exposed_in_legacy_placement_loader=counts['exposed_placement_loader'],
        duplicate_place_groups=len(duplicates),place_groups=len(grouped),
        AD150_eligible=sum(not r['AD150_blockers'] for r in rows),
        density_median_properties_per_sampled_ha=float(np.median(density)))
    out.mkdir(parents=True,exist_ok=True)
    sources=[PLAN,AMENDMENT,PARENT,SOURCE/'table2.csv',SOURCE/'source.json',Path(__file__),ROOT/'polity/settlement_place_groups.py']
    write(out/'results.json',dict(status='identity_and_sampling_audit_not_size_calibration',adopt=False,
        workbook_sha256=sha(WORKBOOK),recovery_consistency_gate=dict(passed=True,counts=gate),summary=summary,
        sampling_classes=classes,associations=associations,permutation=dict(seed=SEED,shuffles=SHUFFLES),
        duplicate_places=duplicates,place_groups=grouped,rows=rows,
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},
        catalogue_dates_certify_sample_phase=False,equal_area_certifies_contemporaneous_extent=False,
        fantasy_models_scored=False,original52_case_source_recovered=False,
        notes='Author keys joined exactly; names, provinces, areas and dates compared without correction. Catalogue occupation intervals and area equality change no AD150 gate. Associations describe this selected sample only.'))
    print(json.dumps(summary,indent=2));print(json.dumps(associations['all_rows'],indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT)
    main(p.parse_args().out)

"""Compare town-size inequality: conditional Roman references versus coupled allocator scenarios."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import openpyxl

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.settlement_size_shape import BASIS_GROUPS,basis_group,date_blockers,refused,relative_sizes,shape_metrics
from settlement_locations_earth import sha,write

PLAN=ROOT/'calibration/settlement_size_shape_20261112/plan.json'
WORKBOOK=ROOT/'data/cache/hanson2016/cities.xlsx'
IDENTITY=ROOT/'output/settlement_size_identity_20261112/results.json'
FEEDBACK=ROOT/'output/settlement_feedback_20261112'
OUT=ROOT/'output/settlement_size_shape_20261112'
YEAR=150;EXPONENTS=(0.0,0.2,0.5);TAILS=(1.0,0.5,0.25);SEED=20261112;RESAMPLES=2000
METRICS=('gini','share_largest_1_percent','share_largest_10_percent','log10_sd','largest_over_median','rank_size_slope_top100')
PINNED='5b9fc0195c3b5f2df71d6380174974215280cafd3bf5fa463fbf96969b549b6c'


def number(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and np.isfinite(v)


def tail_key(t):return {1.0:'all_places',0.5:'largest_50_percent',0.25:'largest_25_percent'}[t]


def exponent_key(g):return 'density_exponent_%g'%g


def roman_case(area,draws):
    """Point metrics and the declared resampling range for one set of places."""
    out={}
    for g in EXPONENTS:
        sizes=relative_sizes(area,g);out[exponent_key(g)]={}
        for t in TAILS:
            point=shape_metrics(sizes,t);boot={m:np.empty(RESAMPLES) for m in METRICS}
            for i,index in enumerate(draws):
                sample=shape_metrics(sizes[index],t)
                for m in METRICS:boot[m][i]=sample[m]
            point['resampling_range_2.5_97.5']={m:[float(v) for v in np.percentile(boot[m],[2.5,97.5])] for m in METRICS}
            out[exponent_key(g)][tail_key(t)]=point
    return out


def main(out):
    if subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)!=PLAN.read_bytes():
        raise ValueError('Commit the comparison declaration first')
    if sha(WORKBOOK)!=PINNED:raise ValueError('Workbook is not the pinned source')
    wb=openpyxl.load_workbook(WORKBOOK,read_only=True,data_only=True)
    try:city_rows=list(wb['Cities'].values);area_rows=list(wb['Areas'].values)
    finally:wb.close()
    cities=[dict(zip(city_rows[0],v)) for v in city_rows[1:] if v[0]];areas=defaultdict(list)
    for row in area_rows[1:]:
        if row[0]:areas[row[0]].append(row)
    cohort=[c for c in cities if not refused(YEAR,c['Start Date'],c['End Date'])]
    measured=[c for c in cohort if len(areas[c['Primary Key']])==1 and number(areas[c['Primary Key']][0][1]) and areas[c['Primary Key']][0][1]>0]
    if (len(cities),len(cohort),len(measured))!=(1388,1354,862):
        raise ValueError('Cohort differs from the declared 1388/1354/862')
    flags=Counter(b for c in cities for b in date_blockers(YEAR,c['Start Date'],c['End Date']))
    identity=json.loads(IDENTITY.read_text());by_key={c['Primary Key']:c for c in cities}
    ended=sorted(r['table_name'] for r in identity['rows'] if refused(YEAR,by_key[r['catalogue_primary_key']]['Start Date'],by_key[r['catalogue_primary_key']]['End Date']))
    if ended!=['Cassope','Herculaneum','Morgantina','Pompeii']:raise ValueError('Date gate does not refuse the four ended housing places')
    area=np.array([float(areas[c['Primary Key']][0][1]) for c in measured])
    group=np.array([basis_group(areas[c['Primary Key']][0][2]) for c in measured])
    default=np.isin(area,(20.,30.))
    sets={'all_measured':np.ones(len(area),bool)}
    for name in BASIS_GROUPS:
        if (group==name).sum()>=30:sets['basis_'+name]=group==name
    sets['excluding_other_or_unspecified']=group!='other_or_unspecified'
    sets['excluding_exact_20_or_30_ha']=~default
    roman={}
    for name,keep in sets.items():
        subset=area[keep];draws=np.random.default_rng(SEED).integers(0,subset.size,(RESAMPLES,subset.size))
        roman[name]=dict(places=int(subset.size),area_ha_min=float(subset.min()),area_ha_median=float(np.median(subset)),
            area_ha_max=float(subset.max()),scenarios=roman_case(subset,draws))
    measured_keys={c['Primary Key'] for c in measured}
    censoring={}
    for c in cohort:
        rank='unrecorded' if c['Barrington Atlas Rank'] is None else str(c['Barrington Atlas Rank'])
        row=censoring.setdefault(rank,dict(measured=0,unmeasured=0))
        row['measured' if c['Primary Key'] in measured_keys else 'unmeasured']+=1
    censoring=dict(sorted(censoring.items()))

    feedback=json.loads((FEEDBACK/'results.json').read_text());allocator={};requests={}
    for row in feedback['rows']:
        fields=FEEDBACK/row['key']/'fields.npz'
        if sha(fields)!=row['fields_sha256']:raise ValueError('Changed scenario fields: '+row['key'])
        with np.load(fields) as z:quantities=dict(town_total=z['total'],civilian_only=z['civilian'],frozen_rural_reference_total=z['frozen_total'])
        allocator[row['key']]=dict(climate=row['climate'],hours_worker_year=row['hours_worker_year'],transfer_fraction=row['transfer_fraction'],
            town_people=float(quantities['town_total'].sum()),
            quantities={q:{tail_key(t):shape_metrics(v,t) for t in TAILS} for q,v in quantities.items()})
    for climate in ('raw','corrected'):
        with np.load(FEEDBACK/(climate+'_inputs.npz')) as z:
            requests[climate]={tail_key(t):shape_metrics(z['civilian_request'],t) for t in TAILS}

    band={};verdicts={}
    for t in TAILS:
        band[tail_key(t)]={m:[min(roman[s]['scenarios'][exponent_key(g)][tail_key(t)][m] for s in sets for g in EXPONENTS),
                              max(roman[s]['scenarios'][exponent_key(g)][tail_key(t)][m] for s in sets for g in EXPONENTS)] for m in METRICS}
    for key in ('raw_h600_f0.075','corrected_h600_f0.075'):
        verdicts[key]={}
        for t in TAILS:
            verdicts[key][tail_key(t)]={}
            for m in ('gini','log10_sd'):
                value=allocator[key]['quantities']['town_total'][tail_key(t)][m];low,high=band[tail_key(t)][m]
                state='within_reference_band' if low<=value<=high else 'more_equal_than_every_reference' if value<low else 'more_unequal_than_every_reference'
                verdicts[key][tail_key(t)][m]=dict(allocator=value,reference_band=[low,high],state=state,
                    ratio_to_nearest_band_edge=1.0 if state=='within_reference_band' else float(value/(low if value<low else high)))
    states={v[t][m]['state'] for v in verdicts.values() for t in v for m in v[t]}
    supported=states=={'within_reference_band'}
    conclusion='shape_supported_within_reference_band' if supported else \
        'allocator_more_equal_than_every_reference' if states=={'more_equal_than_every_reference'} else \
        'allocator_more_unequal_than_every_reference' if states=={'more_unequal_than_every_reference'} else 'mixed_not_supported'

    samples=identity['rows'];x=np.log10([r['table_site_area_ha'] for r in samples]);y=np.log10([r['properties_per_sampled_ha'] for r in samples])
    slope=float(((x-x.mean())*(y-y.mean())).sum()/((x-x.mean())**2).sum())
    out.mkdir(parents=True,exist_ok=True)
    sources=[PLAN,IDENTITY,FEEDBACK/'results.json',Path(__file__),ROOT/'polity/settlement_size_shape.py']
    write(out/'results.json',dict(status='size_shape_development_diagnostic_not_calibration',adopt=False,comparison_year=YEAR,
        workbook_sha256=sha(WORKBOOK),cohort=dict(cities=len(cities),AD150_cohort=len(cohort),measured=len(measured),
            unmeasured_not_filled=len(cohort)-len(measured),date_flags_all_cities=dict(sorted(flags.items())),
            cohort_with_end_unrecorded=sum('catalogue_end_unrecorded' in date_blockers(YEAR,c['Start Date'],c['End Date']) for c in cohort),
            ended_housing_places_refused=ended),
        basis_groups={name:int((group==name).sum()) for name in BASIS_GROUPS},exact_20_or_30_ha=int(default.sum()),
        barrington_rank_censoring=censoring,density_exponents=list(EXPONENTS),tails=[tail_key(t) for t in TAILS],
        resampling=dict(seed=SEED,resamples=RESAMPLES,meaning='sensitivity to which places are listed; not a confidence interval for historical truth'),
        roman=roman,allocator=allocator,civilian_requests_before_finite_budget=requests,reference_band=band,
        support=dict(rule='Gini and log10 sd within the band at all three tail levels for both 600 h 7.5% cases',verdicts=verdicts,
            shape_supported=supported,conclusion=conclusion),
        housing_sample_context=dict(samples=len(samples),log_density_on_log_site_area_slope=slope,
            note='50 exposed, selected, mixed-period samples; context only, defines no scenario'),
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},
        absolute_sizes_compared=False,fantasy_parameters_fitted=False,
        notes='Relative sizes only. Catalogue areas are exposed conditional references with mixed extent bases; 492 cohort places are unmeasured and not filled. Allocator towns are generated hypotheses.'))
    print(conclusion);print(json.dumps(verdicts,indent=1))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT)
    main(p.parse_args().out)

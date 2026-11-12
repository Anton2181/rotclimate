"""Independent review of the size-shape comparison: raw XML cohort and separate metric routines."""
from collections import defaultdict
from fractions import Fraction
import json
import math
from pathlib import Path
import statistics
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from review_settlement_size_identity import sheets
from settlement_locations_earth import sha,write

OUT=ROOT/'output/settlement_size_shape_20261112';FEEDBACK=ROOT/'output/settlement_feedback_20261112'
METRICS=('gini','share_largest_1_percent','share_largest_10_percent','log10_sd','largest_over_median','rank_size_slope_top100')
TAILS={'all_places':Fraction(1),'largest_50_percent':Fraction(1,2),'largest_25_percent':Fraction(1,4)}


def numeric(v):return isinstance(v,Fraction)


def keep_largest(values,tail):
    ordered=sorted((float(v) for v in values if v>0),reverse=True)
    return ordered[:math.ceil(tail*len(ordered))]


def lorenz_gini(x):
    """Gini from the Lorenz curve by trapezoids; not the producer's rank formula."""
    ascending=np.sort(np.asarray(x,float));curve=np.concatenate([[0.],np.cumsum(ascending)/ascending.sum()])
    return float(1-((curve[1:]+curve[:-1])/len(ascending)).sum())


def pairwise_gini(x):
    a=np.asarray(x,float);return float(np.abs(a[:,None]-a[None,:]).sum()/(2*len(a)**2*a.mean()))


def metrics(values,tail,exact=False):
    x=keep_largest(values,tail);n=len(x);total=math.fsum(x);top=x[:100]
    slope=float(np.polyfit(np.log10(np.arange(1,len(top)+1)),np.log10(top),1)[0]) if len(top)>1 else float('nan')
    return dict(places=n,gini=pairwise_gini(x) if exact else lorenz_gini(x),
        share_largest_1_percent=math.fsum(x[:math.ceil(n/100)])/total,share_largest_10_percent=math.fsum(x[:math.ceil(n/10)])/total,
        log10_sd=statistics.pstdev([math.log10(v) for v in x]),largest_over_median=x[0]/statistics.median(x),
        rank_size_slope_top100=slope)


def same(reported,own,tolerance=1e-9):
    assert reported['places']==own['places']
    for m in METRICS:
        a,b=reported[m],own[m]
        assert (math.isnan(a) and math.isnan(b)) or abs(a-b)<=tolerance*max(1,abs(a),abs(b)),(m,a,b)


def group_of(text):
    words=('' if text is None else str(text)).strip().lower()
    for name,prefixes in (('walls',('walls','ramparts')),('inhabited_area',('inhabited area',)),('urban_grid',('urban grid',))):
        if any(words[:len(p)]==p for p in prefixes):return name
    return 'other_or_unspecified'


def main():
    result=json.loads((OUT/'results.json').read_text());workbook=ROOT/'data/cache/hanson2016/cities.xlsx'
    assert sha(workbook)==result['workbook_sha256']=='5b9fc0195c3b5f2df71d6380174974215280cafd3bf5fa463fbf96969b549b6c'
    for path,digest in result['sources_sha256'].items():assert sha(ROOT/path)==digest,path
    book=sheets(workbook);head=book['Cities'][0]
    cities=[dict(zip(head,row+[None]*(len(head)-len(row)))) for row in book['Cities'][1:] if row and row[0]]
    areas=defaultdict(list)
    for row in book['Areas'][1:]:
        if row and row[0]:areas[row[0]].append(row+[None]*(3-len(row)))
    cohort=[c for c in cities if numeric(c['Start Date']) and c['Start Date']<=150 and not (numeric(c['End Date']) and c['End Date']<150)]
    measured=[c for c in cohort if len(areas[c['Primary Key']])==1 and numeric(areas[c['Primary Key']][0][1]) and areas[c['Primary Key']][0][1]>0]
    k=result['cohort'];assert (k['cities'],k['AD150_cohort'],k['measured'],k['unmeasured_not_filled'])==(len(cities),len(cohort),len(measured),len(cohort)-len(measured))==(1388,1354,862,492)
    flags=dict(catalogue_end_unrecorded=sum(not numeric(c['End Date']) for c in cities),
        place_ended_before_year=sum(numeric(c['End Date']) and c['End Date']<150 for c in cities),
        place_not_yet_founded=sum(numeric(c['Start Date']) and c['Start Date']>150 for c in cities))
    assert all(numeric(c['Start Date']) for c in cities) and k['date_flags_all_cities']==flags
    assert k['cohort_with_end_unrecorded']==sum(not numeric(c['End Date']) for c in cohort)
    assert k['ended_housing_places_refused']==['Cassope','Herculaneum','Morgantina','Pompeii']
    area=[float(areas[c['Primary Key']][0][1]) for c in measured];group=[group_of(areas[c['Primary Key']][0][2]) for c in measured]
    counts={g:group.count(g) for g in ('walls','inhabited_area','urban_grid','other_or_unspecified')}
    assert result['basis_groups']==counts and result['exact_20_or_30_ha']==sum(a in (20,30) for a in area)
    ranks={}
    ids={c['Primary Key'] for c in measured}
    for c in cohort:
        row=ranks.setdefault('unrecorded' if c['Barrington Atlas Rank'] is None else str(c['Barrington Atlas Rank']),dict(measured=0,unmeasured=0))
        row['measured' if c['Primary Key'] in ids else 'unmeasured']+=1
    assert result['barrington_rank_censoring']==dict(sorted(ranks.items()))
    sets={'all_measured':[True]*len(area)}
    for g,n in counts.items():
        if n>=30:sets['basis_'+g]=[x==g for x in group]
    sets['excluding_other_or_unspecified']=[x!='other_or_unspecified' for x in group]
    sets['excluding_exact_20_or_30_ha']=[a not in (20,30) for a in area]
    assert set(result['roman'])==set(sets) and result['density_exponents']==[0.0,0.2,0.5]
    assert result['resampling']['seed']==20261112 and result['resampling']['resamples']==2000
    points=0;ranges=0;extremes={t:{m:[math.inf,-math.inf] for m in METRICS} for t in TAILS}
    for name,keep in sets.items():
        subset=np.array([a for a,use in zip(area,keep) if use]);reported=result['roman'][name]
        assert reported['places']==len(subset) and reported['area_ha_median']==statistics.median(subset.tolist())
        assert (reported['area_ha_min'],reported['area_ha_max'])==(subset.min(),subset.max())
        draws=np.random.default_rng(20261112).integers(0,len(subset),(2000,len(subset)))
        for g in (0.0,0.2,0.5):
            sizes=np.exp((1+g)*np.log(subset));block=reported['scenarios']['density_exponent_%g'%g]
            for label,tail in TAILS.items():
                own=metrics(sizes,tail,exact=True);same(block[label],own,1e-8);points+=1
                for m in METRICS:
                    extremes[label][m][0]=min(extremes[label][m][0],block[label][m]);extremes[label][m][1]=max(extremes[label][m][1],block[label][m])
                boot={m:[] for m in METRICS}
                for index in draws:
                    sample=metrics(sizes[index],tail)
                    for m in METRICS:boot[m].append(sample[m])
                for m in METRICS:
                    low,high=np.percentile(boot[m],[2.5,97.5]);a,b=block[label]['resampling_range_2.5_97.5'][m]
                    assert abs(a-low)<=1e-8*max(1,abs(low)) and abs(b-high)<=1e-8*max(1,abs(high)),(name,g,label,m);ranges+=1
    assert result['reference_band']=={t:{m:v for m,v in ms.items()} for t,ms in extremes.items()}
    feedback=json.loads((FEEDBACK/'results.json').read_text());cases=0
    assert set(result['allocator'])=={r['key'] for r in feedback['rows']} and len(feedback['rows'])==8
    for row in feedback['rows']:
        assert sha(FEEDBACK/row['key']/'fields.npz')==row['fields_sha256']
        with np.load(FEEDBACK/row['key']/'fields.npz') as z:
            arrays=dict(town_total=z['total'],civilian_only=z['civilian'],frozen_rural_reference_total=z['frozen_total'])
            assert np.allclose(z['total'],z['civilian']+z['staff'])
        reported=result['allocator'][row['key']]
        assert abs(reported['town_people']-row['town_people'])<=1e-6 and reported['quantities']['town_total']['all_places']['places']==row['positive_sites']
        for q,values in arrays.items():
            for label,tail in TAILS.items():same(reported['quantities'][q][label],metrics(values,tail,exact=True),1e-8);cases+=1
    for climate in ('raw','corrected'):
        with np.load(FEEDBACK/(climate+'_inputs.npz')) as z:
            for label,tail in TAILS.items():
                same(result['civilian_requests_before_finite_budget'][climate][label],metrics(z['civilian_request'],tail,exact=True),1e-8);cases+=1
    states=set()
    for key in ('raw_h600_f0.075','corrected_h600_f0.075'):
        for label in TAILS:
            for m in ('gini','log10_sd'):
                v=result['support']['verdicts'][key][label][m];value=result['allocator'][key]['quantities']['town_total'][label][m]
                low,high=extremes[label][m];state='within_reference_band' if low<=value<=high else 'more_equal_than_every_reference' if value<low else 'more_unequal_than_every_reference'
                assert v['allocator']==value and v['reference_band']==[low,high] and v['state']==state;states.add(state)
                assert abs(v['ratio_to_nearest_band_edge']-(1 if state=='within_reference_band' else value/(low if value<low else high)))<1e-12
    conclusion='shape_supported_within_reference_band' if states=={'within_reference_band'} else \
        'allocator_more_equal_than_every_reference' if states=={'more_equal_than_every_reference'} else \
        'allocator_more_unequal_than_every_reference' if states=={'more_unequal_than_every_reference'} else 'mixed_not_supported'
    assert result['support']['conclusion']==conclusion and result['support']['shape_supported']==(states=={'within_reference_band'})
    assert result['adopt'] is False and result['absolute_sizes_compared'] is False and result['fantasy_parameters_fitted'] is False
    identity=json.loads((ROOT/'output/settlement_size_identity_20261112/results.json').read_text())
    slope=np.polyfit([math.log10(r['table_site_area_ha']) for r in identity['rows']],[math.log10(r['properties_per_sampled_ha']) for r in identity['rows']],1)[0]
    assert abs(result['housing_sample_context']['log_density_on_log_site_area_slope']-slope)<1e-10
    write(OUT/'review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),workbook_sha256=sha(workbook),
        reviewer_sha256=sha(Path(__file__)),raw_xml_cohort_rebuilt=True,roman_point_metric_sets_checked=points,
        roman_resampling_ranges_checked=ranges,allocator_and_request_metric_sets_checked=cases,
        gini_methods='pairwise mean absolute difference for point values; Lorenz trapezoids for resamples; producer uses the rank formula',
        reference_band_and_support_rule_recomputed=True,conclusion=conclusion,
        reviewer_scope='Independent cohort, grouping, metrics, resampling ranges and support rule. Not a certification of catalogue areas, extent bases or dates, and not an absolute-size check.'))
    print('Reviewed %d Roman point sets, %d resampling ranges and %d allocator sets; conclusion %s.'%(points,ranges,cases,conclusion))


if __name__=='__main__':main()

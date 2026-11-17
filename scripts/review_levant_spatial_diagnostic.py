"""Independent grid assignment, support intersections and scalar conditional scores."""
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from pyproj import CRS,Transformer
from shapely import box,segmentize,from_wkb
from shapely.ops import transform
import sqlite3

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/levant_spatial_diagnostic_20261117';SOURCE=ROOT/'output/roman_regional_sources_20261117'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):return json.loads(p.read_text())
def table(p):
    with p.open() as f:return list(csv.DictReader(f))


def close(a,b):
    assert math.isclose(float(a),float(b),rel_tol=2e-12,abs_tol=2e-12),(a,b)


def projected(lon,lat):
    p,l,p0=math.radians(lat),math.radians(lon-17),math.radians(40)
    c=math.acos(max(-1,min(1,math.sin(p0)*math.sin(p)+math.cos(p0)*math.cos(p)*math.cos(l))))
    k=c/math.sin(c) if c>1e-12 else 1.
    return 6371*k*math.cos(p)*math.sin(l),6371*k*(math.cos(p0)*math.sin(p)-math.sin(p0)*math.cos(p)*math.cos(l))


def main():
    assert not (OUT/'review.json').exists(),'Preserve independent diagnostic review'
    r=read(OUT/'results.json')
    for n,d in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/n)==d,n
    for n,d in r['files_sha256'].items():assert sha(OUT/n)==d,n
    for n in ['results.json',*r['files_sha256']]:assert (OUT/n).read_bytes()==(OUT/'fresh'/n).read_bytes(),n
    with np.load(SOURCE/'observations.npz') as z:obs=dict(z)
    with np.load(OUT/'model_support.npz') as z:data=dict(z)
    with np.load(ROOT/'output/settlement_locations_20261110/rome_inputs.npz') as z:land=z['land'];density=z['density']
    counts={};maxarea=0.
    for i,(lon,lat) in enumerate(zip(obs['lon'],obs['lat'])):
        x,y=projected(float(lon),float(lat));col=round(x/9+299.5);row=round(199.5-y/9)
        assert data['observation_row'][i]==row and data['observation_column'][i]==col
        valid=0<=row<400 and 0<=col<600 and bool(land[row,col]);assert data['observation_retained'][i]==valid
        if valid:
            key=int(obs['source_code'][i]),row,col;counts[key]=counts.get(key,0)+1
    c=sqlite3.connect('file:'+str((SOURCE/'source/dataset/dataset.gpkg').resolve())+'?mode=ro',uri=True)
    polygons={}
    projection=CRS.from_proj4('+proj=aeqd +lat_0=40 +lon_0=17 +R=6371000 +units=m +no_defs');t=Transformer.from_crs(32636,projection,always_xy=True)
    for reference,blob in c.execute('select reference,geom from archaeo_survey_areas where reference is not null'):
        envelope=(blob[3]>>1)&7;g=from_wkb(blob[8+[0,32,48,48,64][envelope]:]);assert reference not in polygons
        polygons[reference]=transform(t.transform,segmentize(g,1000))
    c.close();cells=table(OUT/'cells.csv');assert len(cells)==r['source_model_cell_pairs']==93
    for i,row in enumerate(cells):
        source=int(row['source_code']);rr=int(row['row']);cc=int(row['column']);assert land[rr,cc]
        assert r['source_names'][source]==row['reference']
        left=(cc-300)*9000;top=(200-rr)*9000;expected=polygons[row['reference']].intersection(box(left,top-9000,left+9000,top)).area/1e6
        close(row['model_area_sqkm'],expected);maxarea=max(maxarea,abs(float(row['model_area_sqkm'])-expected))
        assert int(row['site_count'])==counts.get((source,rr,cc),0)
        assert data['count'][i]==int(row['site_count']) and data['row'][i]==rr and data['column'][i]==cc and data['source_code'][i]==source
        assert float(row['legacy_weight'])==float(density[rr,cc])==data['legacy_weight'][i]
        assert float(row['refreshed_weight'])==data['refreshed_weight'][i]
    expected_scores={};score_cells=0
    for code,name in enumerate(r['source_names']):
        idx=np.flatnonzero(data['source_code']==code).tolist();area=[float(data['area_sqkm'][i]) for i in idx];n=[int(data['count'][i]) for i in idx]
        totalarea=math.fsum(area);totaln=sum(n)
        assert totaln>0
        for label in ['uniform','legacy','refreshed']:
            weights=[1. if label=='uniform' else float(data[label+'_weight'][i]) for i in idx]
            norm=math.fsum(a*w for a,w in zip(area,weights));p=[a*w/norm for a,w in zip(area,weights)]
            assert norm>0 and not any(count>0 and weight==0 for count,weight in zip(n,weights))
            for i,v in zip(idx,p):close(data[label+'_probability'][i],v)
            close(math.fsum(data[label+'_probability'][idx]),1)
            ll=math.fsum(count*(math.log(a)+math.log(w)-math.log(norm)) for a,w,count in zip(area,weights,n) if count)
            gain=math.fsum(count*(math.log(w)-math.log(norm/totalarea)) for w,count in zip(weights,n) if count)/totaln
            concordance=[]
            for weight,count in zip(weights,n):
                lower=math.fsum(a for a,w in zip(area,weights) if w<weight);equal=math.fsum(a for a,w in zip(area,weights) if w==weight)
                concordance.append(count*(lower+.5*equal))
            auc=math.fsum(concordance)/(totaln*totalarea)
            expected_scores[name,label]=dict(site_n=totaln,log_likelihood=ll,mean_log_gain=gain,presence_background_auc=auc,zero_weight_occupied_cells=0)
    for row in table(OUT/'scores.csv'):
        expected=expected_scores[row['reference'],row['model']]
        assert row['normalization_valid']=='True'
        for k,v in expected.items():close(row[k],v);score_cells+=1
    for row in table(OUT/'summary.csv'):
        values=[expected_scores[name,row['model']] for name in r['source_names']];ns=[v['site_n'] for v in values]
        close(row['equal_source_mean_log_gain'],math.fsum(v['mean_log_gain'] for v in values)/8)
        close(row['pooled_site_mean_log_gain'],math.fsum(v['mean_log_gain']*n for v,n in zip(values,ns))/sum(ns))
        close(row['equal_source_presence_background_auc'],math.fsum(v['presence_background_auc'] for v in values)/8)
        assert int(row['retained_site_n'])==sum(ns)==565
    for row in table(OUT/'support.csv'):
        code=r['source_names'].index(row['reference']);idx=np.flatnonzero(data['source_code']==code)
        assert int(row['model_land_cells'])==len(idx)
        assert int(row['occupied_model_cells'])==sum(data['count'][idx]>0)
        assert int(row['retained_sites'])==sum(data['count'][idx])
        close(row['model_land_area_sqkm'],math.fsum(data['area_sqkm'][idx]))
    assert r['distinct_model_cells']==len(set(zip(data['row'],data['column'])))==55
    assert r['recipe_all_centre_H_control_exact'] and r['recipe_total_people_control_exact']
    assert r['off_grid_sites']==r['off_land_sites']==0
    assert r['uniform_within_source_detection_assumed_not_qualified'] and r['site_intensity_population_link_assumed_not_qualified']
    for flag in ['new_fit','new_blind_test','new_validation_claim','actual_population_allocated','main_atlas_changed','adopt']:assert r[flag] is False
    result=dict(status='passed_independent_projection_support_counts_probabilities_and_conditional_scores',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
        observation_grid_assignments_checked=565,source_model_cell_pairs_checked=len(cells),conditional_score_values_checked=score_cells,
        maximum_model_intersection_area_difference_sqkm=maxarea,distinct_model_cells=55,all_sources_retained=True,
        comparison_scope='Conditional within-source presence/background diagnostic; no census, uniform detection or population-link qualification.',
        probability_and_likelihood_review='Scalar compensated sums; intensity-ratio gain formula and sorted-background concordance, separate from producer vector formula.',
        source_polygon_projection_and_GE0S_intersection_reused=True,canonical_density_recipe_replay_not_independently_rederived=True,
        fresh_outputs_byte_exact=True,new_fit=False,new_validation_claim=False,main_atlas_changed=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()

"""Independent source, spatial-matching and metric checks of frozen transfer."""
import argparse
import collections
import csv
import io
import json
from pathlib import Path
import re
import sys
import zipfile

import numpy as np
from pyproj import Proj

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha, write
from settlement_vidarbha_transfer import DEFAULT_OUT, CONFIG, METHODS, CACHE, numeric_digest


def distance(lat,lon,a,b):
    lat,lon,a,b=np.radians(lat),np.radians(lon),np.radians(a),np.radians(b)
    return 6371*2*np.arctan2(np.sqrt(np.clip(np.sin((lat-a)/2)**2+np.cos(lat)*np.cos(a)*np.sin((lon-b)/2)**2,0,1)),
                           np.sqrt(np.clip(1-(np.sin((lat-a)/2)**2+np.cos(lat)*np.cos(a)*np.sin((lon-b)/2)**2),0,1)))


def equal(a,b):
    if a is None or b is None:assert a is None and b is None
    else:assert np.isclose(a,b,rtol=1e-12,atol=1e-12),(a,b)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=DEFAULT_OUT);a=p.parse_args();out=a.out
    result=json.loads((out/'results.json').read_text());methods=json.loads(METHODS.read_text())
    assert result['plan_sha256']==sha(CONFIG/'plan.json') and result['methods_sha256']==sha(METHODS)
    assert result['producer_sha256']==sha(ROOT/'scripts/settlement_vidarbha_transfer.py')
    for path,digest in {**result['parent_artifacts'],**result['input_sources']}.items():assert sha(ROOT/path)==digest
    prep=json.loads((ROOT/'output/vidarbha_survey_20261111/preparation.json').read_text())
    norm=lambda s:re.sub('[^a-z0-9]','',s.lower())
    tables={}
    with zipfile.ZipFile(CACHE/'Vidarbha_2016Survey_SiteRecords.zip') as z:
        for kind in ['AllSites','Settlements']:
            body=z.read(prep['archive_members'][kind]['path']);spec=prep['tables'][kind]
            reader=csv.DictReader(io.StringIO(body.decode(spec['format']['encoding']),newline=''))
            tables[kind]=[{norm(k):v.strip() for k,v in r.items() if k and k.strip()} for r in reader if any(r.values())]
    byid=collections.defaultdict(list)
    for r in tables['AllSites']:byid[r['sitecode']].append(r)
    rows=[]
    for r in tables['Settlements']:
        assert len(byid[r['sitecode']])==1
        rows.append(byid[r['sitecode']][0])
    assert len(rows)==134 and all(r['sitetype'].lower()=='settlement' for r in rows)
    lat=np.array([float(r['north']) for r in rows]);lon=np.array([float(r['east']) for r in rows])
    zones=np.array([r['surveyzone'] for r in rows]);phase=np.array([r['ehs'].lower() for r in rows])
    included=np.zeros(len(rows),bool)
    for zone,f in methods['frames'].items():included|=(zones==zone)&(distance(lat,lon,f['latitude'],f['longitude'])<=13)
    projection=Proj(proj='aeqd',lat_0=20.8,lon_0=78.5,R=6371000,units='km')
    x,y=projection(lon,lat)
    offset_spec={'central':(0,0)}
    for axis in ['x','y']:
        for offset in [-3.,-1.,1.,3.]:offset_spec[f'{axis}{offset:+g}km']=(offset if axis=='x' else 0,offset if axis=='y' else 0)
    metric_cases=match_cases=constraint_cases=0
    for grid, g in result['grids'].items():
        cell=int(grid);inputs=out/f'inputs_{cell}km.npz';model=out/f'model_{cell}km.npz'
        assert numeric_digest(inputs)==result['inputs'][grid]['numeric_sha256']
        assert numeric_digest(model)==g['model_numeric_sha256']
        with np.load(inputs) as z:inp=dict(z)
        with np.load(model) as z:mod=dict(z)
        ny,nx=inp['land'].shape
        private=CACHE/f'transfer_matches_{cell}km.json';assert sha(private)==g['private_matches_sha256']
        matches=json.loads(private.read_text());assert matches['site_ids']==[r['sitecode'] for r in rows]
        assert matches['zones']==zones.tolist() and matches['phase']==phase.tolist() and matches['source_inside']==included.tolist()
        assert g['exclusions']['original_points_inside_assigned_frame']==int(included.sum())
        assert g['exclusions']['original_points_outside_assigned_frame']==int((~included).sum())
        assert g['exclusions']['unknown_zone_records']==sum(z not in methods['frames'] for z in zones)
        assert g['exclusions']['phase_records']==dict(collections.Counter(phase))
        la,lo=np.radians(inp['lat'].ravel()),np.radians(inp['lon'].ravel())
        # Direct full-grid dot products, independent of the producer's KD tree.
        vectors=np.array([np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)]).T
        recovered={}
        for offset,(dx,dy) in offset_spec.items():
            olon,olat=projection(x+dx,y+dy,inverse=True);al,bl=np.radians(olat),np.radians(olon)
            points=np.array([np.cos(al)*np.cos(bl),np.cos(al)*np.sin(bl),np.sin(al)]).T
            # Bounded batches avoid a full nrecords x ncells distance allocation.
            ids=np.concatenate([np.argmax(points[i:i+8]@vectors.T,axis=1) for i in range(0,len(rows),8)])
            window=(np.abs(x+dx)<=nx*cell/2)&(np.abs(y+dy)<=ny*cell/2)
            land=inp['land'].ravel()[ids]
            m=matches['offsets'][offset]
            assert ids.tolist()==m['cells'] and window.tolist()==m['in_window'] and land.tolist()==m['land']
            assert g['exclusions']['by_offset'][offset]==dict(outside_window=int((~window).sum()),nonland=int((~land).sum()))
            recovered[offset]=(ids,window&land);match_cases+=len(ids)
        assert len(g['constraints'])==12
        for name,c in g['constraints'].items():
            towns=mod['towns_'+name];ids=towns[:,0]*nx+towns[:,1]
            assert c['placed']==len(ids) and c['requested']==g['natural_production_count']
            assert c['count_met']==(len(ids)==c['requested'])
            assert c['unique']==(len(set(ids))==len(ids))
            assert c['all_eligible']==bool(mod['eligible'].ravel()[ids].all())
            delta=towns[:,None,:]-towns[None,:,:];dist=np.sqrt((delta**2).sum(2))*cell
            i,j=np.triu_indices(len(ids),1)
            equal(c['minimum_separation_km'],float(dist[i,j].min()))
            if name.startswith('fixed'):threshold=np.full(len(i),18.)
            elif name.startswith('production'):
                from scipy.ndimage import gaussian_filter
                smooth=gaussian_filter(np.where(inp['land'],inp['density'],0),1.)
                # Frozen legacy constants, independent direct sequential exclusion.
                radius=1.6*np.minimum(np.sqrt(40000/14.1*(14.1/np.maximum(smooth.ravel()[ids],1e-9))**.7/np.pi),60.)
                threshold=radius[i]
            else:
                weights=mod['score']*mod['eligible']
                if name.startswith('lead'):weights=weights*inp['history450']
                intensity=c['requested']*weights/weights.sum()/cell**2
                radius=np.minimum(.35/np.sqrt(np.maximum(intensity.ravel()[ids],np.finfo(float).tiny)),45.)
                threshold=.5*(radius[i]+radius[j])
            assert c['spacing_pass']==bool(np.all(dist[i,j]>threshold));constraint_cases+=1
        assert len(g['metrics'])==81
        for r in g['metrics']:
            membership=included.copy()
            if r['cohort']=='EH-S_yes':membership&=phase=='yes'
            elif r['cohort']=='possible_phase':membership&=np.isin(phase,['yes','?',''])
            else:assert r['cohort']=='whole_record'
            ids,valid=recovered[r['offset']];selected=membership&valid&(zones==r['zone']);cells=np.unique(ids[selected])
            f=methods['frames'][r['zone']]
            background=inp['land']&(distance(inp['lat'],inp['lon'],f['latitude'],f['longitude'])<=13)
            assert r['included_records']==int(selected.sum()) and r['distinct_cells']==len(cells)
            assert r['background_land_cells']==int(background.sum())
            assert r['matched_cell_centres_outside_frame']==int((~background.ravel()[cells]).sum())
            equal(r['eligible_fraction'],float(mod['eligible'].ravel()[cells].mean()) if len(cells) else None)
            for name,m in r['opportunity'].items():
                field=mod[name];v=field.ravel()[cells];b=field[background]
                percentiles=np.array([(np.sum(b<s)+.5*np.sum(b==s))/len(b) for s in v])
                equal(m['mean_percentile'],float(percentiles.mean()) if len(v) else None)
                equal(m['median_percentile'],float(np.median(percentiles)) if len(v) else None)
                equal(m['relative_mean_score_lift'],float(v.mean()/b.mean()) if len(v) and b.mean()>0 else None)
                metric_cases+=3
            points=np.column_stack(np.divmod(cells,nx))
            for name,values in r['captures'].items():
                towns=mod['towns_'+name]
                nearest=np.sqrt(((points[:,None,:]-towns[None,:,:])**2).sum(2)).min(1)*cell if len(cells) and len(towns) else np.full(len(cells),np.inf)
                for radius,value in values.items():equal(value,float(np.mean(nearest<=int(radius))) if len(cells) else None);metric_cases+=1
    primary=[r for r in result['grids']['3']['metrics'] if r['cohort']=='EH-S_yes' and r['offset']=='central']
    guard=result['guard'];support=sum(r['distinct_cells'] for r in primary)>=30 and sum(r['distinct_cells']>=8 for r in primary)>=2
    rank_delta=float(np.mean([r['opportunity']['lead_L450']['mean_percentile']-r['opportunity']['fixed_L800']['mean_percentile'] for r in primary]))
    capture_delta=float(np.mean([r['captures'][f'lead_L450_seed{s}']['10'] for r in primary for s in [1,7,19,43,97]])-np.mean([r['captures']['fixed_L800_seed1']['10'] for r in primary]))
    constraints=all(v[k] for g in result['grids'].values() for v in g['constraints'].values() for k in ['count_met','unique','all_eligible','spacing_pass'])
    equal(guard['rank_delta'],rank_delta);equal(guard['capture_delta'],capture_delta)
    assert guard['support_qualified']==support and guard['all24_constraints_pass']==constraints
    assert guard['diagnostic_guard_pass']==bool(support and rank_delta>=-.05 and capture_delta>=-.10 and constraints)
    assert result['adopt'] is False and guard['adopt'] is False
    write(out/'review.json',dict(status='passed',source_result_sha256=sha(out/'results.json'),reviewer_sha256=sha(Path(__file__)),
        independent_source_joins=134,full_grid_matches_checked=match_cases,scalar_metric_checks=metric_cases,
        placements_checked=constraint_cases,parent_hashes_unchanged=True,raw_coordinates_redistributed=False,
        guard_reconstructed=True,review_pass_does_not_mean_model_pass=True))
    print('Independent review passed:',match_cases,'matches',metric_cases,'metrics',constraint_cases,'placements',flush=True)


if __name__=='__main__':main()

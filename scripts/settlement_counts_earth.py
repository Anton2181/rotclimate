"""Declared role-specific Earth count fits and direct resident-size support audit."""
import argparse
import collections
import json
from pathlib import Path
import sys

import numpy as np
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from polity.settlement_counts import count_exposure,fit_scale,poisson_deviance
from polity.population_coverage import population_coverage,require_population_coverage

CONFIG=ROOT/'calibration/settlement_counts_20261111';ORIGINAL=ROOT/'output/settlement_locations_20261110'
OUT=ROOT/'output/settlement_counts_20261111';BETAS=[0.,.5,.7,1.,1.5]


def numeric(value):
    try:x=float(value)
    except (ValueError,TypeError):return None
    return x if np.isfinite(x) else None


def source_support():
    import openpyxl
    import shapefile
    book=ROOT/'data/cache/hanson2016/cities.xlsx'
    wb=openpyxl.load_workbook(book,read_only=True,data_only=True)
    try:
        def records(sheet):
            it=wb[sheet].iter_rows(values_only=True);head=next(it)
            return [dict(zip(head,r)) for r in it if r[0] is not None]
        cities=records('Cities');areas=records('Areas')
    finally:
        wb.close()
    byid=collections.defaultdict(list)
    for r in areas:byid[r['Primary Key']].append(r)
    def area_summary(selected):
        joins=collections.Counter();states=collections.Counter();basis=collections.Counter();candidates=0
        for r in selected:
            a=byid[r['Primary Key']];joins[str(len(a))]+=1
            if not a:states['missing_area_record']+=1;continue
            if len(a)>1:states['ambiguous_area_records']+=1;continue
            v=numeric(a[0]['Area']);basis[str(a[0]['Estimate Basis'])]+=1
            if v is None:states['nonnumeric_or_nonfinite']+=1
            elif v<=0:states['nonpositive']+=1
            else:
                states['positive_numeric']+=1
                if v in [20.,30.]:states['exact20_or30ha_candidate']+=1
                else:candidates+=1
        return dict(city_records=len(selected),area_join_multiplicities=dict(joins),area_states=dict(states),
            positive_nondefault_value_candidates=candidates,raw_estimate_basis_counts=dict(basis),
            nondefault_does_not_certify_measured=True)
    dates=collections.Counter();selected=[]
    for r in cities:
        s,e=numeric(r['Start Date']),numeric(r['End Date'])
        if s is None:dates['missing_or_invalid_start']+=1;continue
        if e is not None and e<s:dates['reversed_interval']+=1
        if s<=150 and (e is None or e>=150):
            selected.append(r);dates['AD150_operational_selection']+=1
            dates['selected_missing_or_invalid_end']+=int(e is None)
        else:dates['outside_AD150']+=1
    roman=dict(source_sha256=sha(book),all_cities=area_summary(cities),AD150=area_summary(selected),
        area_records=len(areas),area_unique_IDs=len(byid),city_unique_IDs=len(set(r['Primary Key'] for r in cities)),
        orphan_area_records=sum(r['Primary Key'] not in {c['Primary Key'] for c in cities} for r in areas),date_states=dict(dates),
        old_reader_imputes_missing_area_by_rank_median=True,no_direct_resident_observations=True,
        semantics='Archaeological/estimated extent,not direct people. Preserve Estimate Basis;20/30ha candidates conservative value flags,not a proof allotherareas measured or contemporaneous.')
    points=ROOT/'data/cache/han_ad2/shp/CountyPointsWithPopulation'
    reader=shapefile.Reader(str(points),encoding='utf-8');years=collections.defaultdict(list)
    for r in reader.iterRecords():years[r['YEAR']].append(r.as_dict())
    han={}
    for year,rows in years.items():
        state=collections.Counter();pop=[]
        for r in rows:
            v=numeric(r['CountyPOP'])
            if v is None:state['nonnumeric_or_nonfinite']+=1
            elif v<0:state['negative']+=1
            elif v==0:state['zero']+=1
            else:state['positive']+=1;pop.append(v)
        han[year]=dict(records=len(rows),unique_county_IDs=len(set(r['CountyID'] for r in rows)),
            source_type_counts=dict(collections.Counter(r['TYPE'] for r in rows)),county_population_states=dict(state),
            adjustment_flag_counts=dict(collections.Counter(str(r['Adjusted_o']) for r in rows)),
            directly_recorded_flag_counts=dict(collections.Counter(str(r['DirectReco']) for r in rows)),
            positive_county_population_sum=float(sum(pop)),no_town_resident_labels=True)
    return dict(roman=roman,han=han,han_source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(points.parent.glob(points.name+'.*'))},
        units_guard='Han CountyPOP is district population;Roman Areas are extent estimates. Neither can silently become measured town residents. No area-to-people conversion or median filling performed.')


def source_cells(pool,x):
    """Recover original record multiplicity with the original matching semantics."""
    from polity import earth as E
    import polity_earth_check as P
    if pool=='han':
        observations=E.han_seats()
    else:
        import openpyxl
        wb=openpyxl.load_workbook(ROOT/'data/cache/hanson2016/cities.xlsx',read_only=True,data_only=True)
        try:
            it=wb['Cities'].iter_rows(values_only=True);head=next(it);observations=[]
            for values in it:
                r=dict(zip(head,values));s,e=numeric(r['Start Date']),numeric(r['End Date'])
                lat,lon=numeric(r['Latitude (Y)']),numeric(r['Longitude (X)'])
                if s is not None and s<=150 and (e is None or e>=150) and lat is not None and lon is not None:
                    observations.append(dict(lat=lat,lon=lon))
        finally:wb.close()
    g=dict(x,**{k:v for k,v in P.WINDOWS[pool].items() if k!='cell_km'})
    lat=np.array([r['lat'] for r in observations]);lon=np.array([r['lon'] for r in observations])
    row,col,ok=P.snap(g,lat,lon)
    ids=row*x['land'].shape[1]+col
    assert np.array_equal(np.unique(ids[ok]),x['real']), 'Recovered source cells differ from frozen archive'
    rawrow,rawcol,inside=E.to_cells(g,lat,lon)
    before=x['land'][np.clip(rawrow,0,x['land'].shape[0]-1),np.clip(rawcol,0,x['land'].shape[1]-1)]
    allowed=x['allowed'].ravel()[ids]&x['land'].ravel()[ids]
    return ids[ok&allowed],dict(original_records=len(observations),inside_window_records=int(ok.sum()),
        allowed_source_records=int((ok&allowed).sum()),distinct_allowed_cells=len(np.unique(ids[ok&allowed])),
        outside_window_records=int((~ok).sum()),inside_but_not_allowed_records=int((ok&~allowed).sum()),
        legacy_nearest_land_rescued_inside_records=int((ok&~before).sum()),
        recovered_unique_set_equals_frozen_real=True,matching='Inherited legacy nearest-land snap;not the full-grid Vidarbha rule')


def aggregate(x,towns,nominal_km,record_cells,covered,domain):
    cell=float(x['cell_km']);b=round(nominal_km/cell);land=x['allowed']&x['land'];h,w=land.shape
    if domain=='covered_only':
        land=land&covered
        require_population_coverage(covered,land)
    else:assert domain=='full_frozen'
    yy,xx=np.indices(land.shape);nbx=(w+b-1)//b;nby=(h+b-1)//b
    ids=(yy//b)*nbx+xx//b;n=nbx*nby
    area=np.bincount(ids.ravel(),weights=land.ravel()*cell**2,minlength=n)
    pop=np.bincount(ids.ravel(),weights=(np.where(land,x['density'],0)*cell**2).ravel(),minlength=n)
    real=np.asarray(record_cells,int);real=real[land.ravel()[real]]
    count=np.bincount(ids.ravel()[real],minlength=n)
    unique=np.bincount(ids.ravel()[np.unique(real)],minlength=n)
    predicted=np.asarray(towns,int);nodes=predicted[:,0]*w+predicted[:,1]
    nodes=nodes[land.ravel()[nodes]]
    baseline=np.bincount(ids.ravel()[nodes],minlength=n)
    y0=(np.arange(n)//nbx)*b;x0=(np.arange(n)%nbx)*b
    midy=(y0+np.minimum(y0+b,h)-1)/2;midx=(x0+np.minimum(x0+b,w)-1)/2
    fold=2*(midy>=h/2)+(midx>=w/2)
    keep=area>0
    return {k:v[keep] for k,v in dict(area=area,population=pop,record_count=count,distinct_cell_count=unique,
        baseline_count=baseline,fold=fold.astype(int),block_id=np.arange(n),
        centre_x_km=(midx-(w-1)/2)*cell,centre_y_km=((h-1)/2-midy)*cell).items()},dict(
        nominal_block_km=nominal_km,actual_block_km=b*cell,allowed_source_records=len(real),
        distinct_source_cells=len(np.unique(real)),source_records_in_zero_land_blocks=int(count[~keep].sum()),
        baseline_sites=len(nodes),land_blocks=int(keep.sum()))


def metrics(y,mu,area):
    observed=float(y.sum());predicted=float(mu.sum());dev=poisson_deviance(y,mu)
    moved=.5*float(np.abs(y/observed-mu/predicted).sum()) if observed>0 and predicted>0 else None
    rank=float(spearmanr(y,mu).statistic) if len(y)>1 and np.ptp(y)>0 and np.ptp(mu)>0 else None
    return dict(source_records=observed,predicted_count=predicted,land_km2=float(area.sum()),blocks=len(y),
        deviance=dev,deviance_per_source_record=dev/observed if observed>0 else None,
        deviance_per_10000km2=dev/area.sum()*10000,
        total_count_relative_error=abs(predicted-observed)/observed if observed>0 else None,
        count_mass_to_relocate_after_normalization=moved,count_rank=rank,
        positive_observation_zero_prediction_blocks=int(((y>0)&(mu==0)).sum()))


def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,list):return [clean(v) for v in value]
    if isinstance(value,float) and not np.isfinite(value):return 'infinite' if value>0 else 'invalid'
    return value


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT);a=p.parse_args();out=a.out;out.mkdir(parents=True,exist_ok=True)
    original=json.loads((ORIGINAL/'results.json').read_text())
    assert sha(ORIGINAL/'positions.npz')==original['positions_sha256']
    support=source_support();blocks={};metadata={};saved={};matching={};coverage={};sources={str((ORIGINAL/'results.json').relative_to(ROOT)):sha(ORIGINAL/'results.json')}
    global_path=ROOT/'output/land_people/earth/earth.npz'
    with np.load(global_path) as z:source_lat,source_lon=z['lat'],z['lon']
    sources[str(global_path.relative_to(ROOT))]=sha(global_path)
    with np.load(ORIGINAL/'positions.npz') as positions:
        for pool in ['han','rome']:
            path=ORIGINAL/f'{pool}_inputs.npz';assert sha(path)==original['pools'][pool]['input_sha256']
            sources[str(path.relative_to(ROOT))]=sha(path)
            with np.load(path) as z:x=dict(z)
            record_cells,matching[pool]=source_cells(pool,x)
            covered=population_coverage(x['lat'],x['lon'],source_lat,source_lon);land=x['land']&x['allowed']
            coverage[pool]=dict(required_land_cells=int(land.sum()),covered_land_cells=int((land&covered).sum()),
                missing_land_cells=int((land&~covered).sum()),missing_land_km2=float((land&~covered).sum()*float(x['cell_km'])**2),
                allowed_source_records=len(record_cells),source_records_outside_coverage=int((~covered.ravel()[record_cells]).sum()),
                distinct_source_cells_outside_coverage=len(np.unique(record_cells[~covered.ravel()[record_cells]])),
                full_domain_qualified=bool(covered[land].all()))
            for domain in ['full_frozen','covered_only']:
                for nominal in [100,300]:
                    key=f'{domain}_{pool}_{nominal}km';b,m=aggregate(x,positions[f'{pool}__baseline'],nominal,record_cells,covered,domain)
                    blocks[key]=b;metadata[key]=m
                    for field,values in b.items():saved[key+'__'+field]=values
    rows=[];predictions={}
    for domain in ['full_frozen','covered_only']:
      for nominal in [100,300]:
        for target in ['record_count','distinct_cell_count']:
            for pool in ['han','rome']:
                key=f'{domain}_{pool}_{nominal}km';b=blocks[key];y=b[target]
                rows.append(dict(domain=domain,pool=pool,nominal_km=nominal,target=target,model='archived_production_descriptive',beta=None,
                    folds={str(f):metrics(y[b['fold']==f],b['baseline_count'][b['fold']==f],b['area'][b['fold']==f]) for f in range(4)},
                    total=metrics(y,b['baseline_count'],b['area'])))
            for beta in BETAS:
                for scope in ['role_specific','shared_scale_control']:
                    for pool in ['han','rome']:
                        key=f'{domain}_{pool}_{nominal}km';b=blocks[key];exposure=count_exposure(b['area'],b['population'],beta)
                        mu=np.zeros(len(exposure));folds={};scales={}
                        for f in range(4):
                            train=[];counts=[]
                            for other in ([pool] if scope=='role_specific' else ['han','rome']):
                                o=blocks[f'{domain}_{other}_{nominal}km'];mask=o['fold']!=f
                                train.append(count_exposure(o['area'],o['population'],beta)[mask]);counts.append(o[target][mask])
                            scale=fit_scale(np.concatenate(train),np.concatenate(counts));scales[str(f)]=scale
                            held=b['fold']==f;mu[held]=exposure[held]*(scale if scale is not None else 0.)
                            folds[str(f)]=dict(metrics(b[target][held],mu[held],b['area'][held]),training_scale_identified=scale is not None,
                                training_count=int(np.concatenate(counts).sum()),training_exposure=float(np.concatenate(train).sum()))
                        model=f'{scope}_beta{beta:g}';label=f'{key}__{target}__{model}';predictions[label]=mu
                        row=dict(domain=domain,pool=pool,nominal_km=nominal,target=target,model=model,beta=beta,scale_scope=scope,
                            training_scales=scales,folds=folds,total=metrics(b[target],mu,b['area']))
                        rows.append(row)
                        if nominal==100 and target=='record_count':print(domain,pool,model,'deviance/record',row['total']['deviance_per_source_record'],flush=True)
    ranking={}
    for domain in ['full_frozen','covered_only']:
        values=[]
        for beta in BETAS:
            model=f'role_specific_beta{beta:g}';selected=[r for r in rows if r['domain']==domain and r['nominal_km']==100 and r['target']=='record_count' and r['model']==model]
            values.append(dict(beta=beta,equal_pool_deviance_per_source_record=float(np.mean([r['total']['deviance_per_source_record'] for r in selected])),
                pool_deviance_per_source_record={r['pool']:r['total']['deviance_per_source_record'] for r in selected}))
        values.sort(key=lambda r:r['equal_pool_deviance_per_source_record']);ranking[domain]=values
    np.savez_compressed(out/'blocks.npz',**saved);np.savez_compressed(out/'predictions.npz',**predictions)
    result=dict(status='full_domain_coverage_failure_restricted_development_only',adopt=False,plan_sha256=sha(CONFIG/'plan.json'),producer_sha256=sha(Path(__file__)),
        module_sha256=sha(ROOT/'polity/settlement_counts.py'),parent_artifacts=sources,positions_sha256=sha(ORIGINAL/'positions.npz'),
        correction_sha256=sha(CONFIG/'multiplicity_correction.json'),
        coverage_plan_sha256=sha(CONFIG/'coverage_domain.json'),coverage_module_sha256=sha(ROOT/'polity/population_coverage.py'),
        matching_sources={p:sha(ROOT/p) for p in ['polity/earth.py','rotclimate/earth.py','scripts/polity_earth_check.py']},
        source_support=support,source_matching=matching,population_coverage=coverage,blocks=metadata,rows=rows,ranking=ranking,
        blocks_sha256=sha(out/'blocks.npz'),predictions_sha256=sha(out/'predictions.npz'),
        chosen_for_production=None,urban_resident_labels_manufactured=False,ledger_or_physics_changed=False,
        limitations='Development on exposed saved pools;spatially withheld quadrants for training scales,not fresh source validation. Role-specific administrative/urban catalogue counts,not complete village census. Fitted count is not resident population or a licensed government institution. Zero-support losses retained. No model population rescaling or placement change.')
    for path,digest in sources.items():assert sha(ROOT/path)==digest
    write(out/'results.json',clean(result));print('Count ranking',clean(ranking),flush=True)
    print('Roman area support',support['roman']['AD150']['area_states'],flush=True)


if __name__=='__main__':main()

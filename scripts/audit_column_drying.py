"""Verify and diagnose archived monthly column drying; never integrate climate."""
from dataclasses import asdict
from pathlib import Path
import argparse
import importlib.metadata
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from benchmark_local import DEV12_SPECS
from earth_benchmark import load_params
from local_benchmark_protocol import case_hash, file_hash, freeze, identity, write_json
from rotclimate import earth, joint

SOURCE_TERMS = ('evaporation', 'advection', 'diffusion', 'storm_exchange',
                'column_drying', 'convergence_import')
DISJOINT_TERMS = ('evaporation', 'advection', 'diffusion', 'storm_exchange',
                  'other_column_drying', 'monsoon_drying', 'convergence_import')
COLORS = ['#73a466', '#457fac', '#a5c3d8', '#a98ab8', '#c18c63', '#dfb990', '#c7bd54']


def check_source_closure(fields, mask, *, atol_mm_month=2e-4, rtol=5e-6):
    """Check the saved signed equation and disjoint drying, not climate skill."""
    mask = np.asarray(mask)
    if mask.dtype != np.dtype(bool) or mask.ndim != 2 or not mask.any():
        raise ValueError('Need a nonempty two-dimensional boolean diagnostic mask')
    if not np.isfinite(atol_mm_month) or not np.isfinite(rtol) or min(atol_mm_month, rtol) < 0:
        raise ValueError('Need finite nonnegative closure tolerances')
    values = {}
    for key in (*SOURCE_TERMS, 'monsoon_drying', 'simulated', 'observed', 'residual'):
        if key not in fields:
            raise ValueError('Missing saved equation field: '+key)
        value = np.asarray(fields[key], float)
        if value.shape != (12, *mask.shape) or not np.isfinite(value[:, mask]).all():
            raise ValueError('Invalid saved monthly equation field: '+key)
        values[key] = value[:, mask]
    for key in ('simulated', 'observed'):
        if (values[key] < 0).any():
            raise ValueError('Negative saved rain: '+key)
    drying_tolerance = atol_mm_month + rtol*(np.abs(values['column_drying'])+np.abs(values['monsoon_drying']))
    if ((values['column_drying'] > drying_tolerance).any()
            or (values['monsoon_drying'] > drying_tolerance).any()
            or (values['column_drying']-values['monsoon_drying'] > drying_tolerance).any()):
        raise ValueError('Drying signs or monsoon-subset identity are invalid')
    reconstructed = sum(values[k] for k in SOURCE_TERMS)-values['simulated']
    error = np.abs(reconstructed-values['residual'])
    magnitude = sum(np.abs(values[k]) for k in (*SOURCE_TERMS, 'simulated', 'residual'))
    tolerance = atol_mm_month+rtol*magnitude
    scaled = np.divide(error, tolerance, out=np.zeros_like(error), where=tolerance > 0)
    if (error > tolerance).any():
        raise ValueError('Saved source terms do not reconstruct the saved residual')
    return dict(status='passed', maximum_error_mm_model_month=float(error.max()),
        maximum_tolerance_fraction=float(scaled.max()), atol_mm_model_month=atol_mm_month,
        rtol_sum_absolute_terms=rtol, cells=int(mask.sum()), months=12,
        monsoon_is_subset=True)


def check_layer_water(total, layers, *, atol_mm=2e-5, rtol=2e-6):
    """Check monthly full-grid water arrays before cropping or averaging."""
    total, layers = np.asarray(total, float), np.asarray(layers, float)
    if (total.ndim != 3 or total.shape[0] != 12 or layers.shape != (12, 2, *total.shape[1:])
            or not np.isfinite(total).all() or not np.isfinite(layers).all()
            or (total < 0).any() or (layers < 0).any()
            or not np.isfinite(atol_mm) or not np.isfinite(rtol) or min(atol_mm, rtol) < 0):
        raise ValueError('Need finite nonnegative monthly total and two-layer water')
    error = np.abs(layers.sum(1)-total)
    tolerance = atol_mm+rtol*np.maximum(total, layers.sum(1))
    if (error > tolerance).any():
        raise ValueError('Monthly layer water does not sum to the saved column')
    return dict(status='passed', maximum_error_mm=float(error.max()), atol_mm=atol_mm, rtol=rtol)


def effective_sink_rates(drying_mm_month, water_mm, month_days):
    """Water-weighted loss rate/day and reciprocal days; zero loss -> inf tau.

    The input drying is signed (nonpositive). This ratio of saved monthly
    quantities is not a reconstruction of instantaneous prescribed coefficients.
    Zero water with zero loss leaves both quantities undefined (NaN).
    """
    drying, water = np.asarray(drying_mm_month, float), np.asarray(water_mm, float)
    duration = np.asarray(month_days, float)
    if (drying.shape != water.shape or not np.isfinite(drying).all() or not np.isfinite(water).all()
            or (drying > 0).any() or (water < 0).any()
            or not np.isfinite(duration).all() or (duration <= 0).any()):
        raise ValueError('Need matching signed drying, nonnegative water and positive durations')
    if duration.ndim == 1:
        if water.ndim == 0 or len(duration) != water.shape[0]:
            raise ValueError('Month durations must match the leading monthly axis')
        duration = duration.reshape((len(duration),)+(1,)*(water.ndim-1))
    elif duration.ndim != 0:
        raise ValueError('Need a scalar duration or a vector on the leading monthly axis')
    duration = np.broadcast_to(duration, water.shape)
    if ((water == 0) & (drying < 0)).any():
        raise ValueError('Positive drying loss cannot have zero saved water')
    rate = np.divide(-drying, duration*water, out=np.full_like(water, np.nan), where=water > 0)
    tau = np.divide(1., rate, out=np.full_like(rate, np.inf), where=rate > 0)
    tau = np.where(np.isnan(rate), np.nan, tau)
    return rate, tau


def nullable(values):
    """JSON representation: undefined/infinite reciprocal timescales are null."""
    array = np.asarray(values)
    return np.where(np.isfinite(array), array, None).tolist()


def summarize(fields, mask, month_days, water=None):
    """Equal-cell bin means; preserve all twelve original equal model months."""
    count = int(mask.sum())
    if not count:
        return dict(cells=0, monthly=None, annual=None, water=None)
    keys = (*SOURCE_TERMS, 'monsoon_drying', 'simulated', 'observed', 'residual', 'absolute_residual')
    monthly = {key:np.asarray(fields[key], float)[:, mask].mean(1) for key in keys}
    monthly['other_column_drying'] = monthly['column_drying']-monthly['monsoon_drying']
    annual = {key:float(value.sum()) for key,value in monthly.items()}
    loss = -annual['column_drying']; rain = annual['simulated']
    annual['drying_to_rain'] = loss/rain if rain > 0 else None
    annual['drying_fraction_of_rain_plus_drying'] = loss/(rain+loss) if rain+loss > 0 else None
    result = dict(cells=count, monthly={key:value.tolist() for key,value in monthly.items()}, annual=annual)
    if water is None:
        result['water'] = dict(available=False, reason='This historical profile did not save column/layer water')
    else:
        mean_water = water[:, mask].mean(1)
        rates, times = effective_sink_rates(monthly['column_drying'], mean_water, month_days)
        integrated_water = float((mean_water*month_days).sum())
        annual_rate = loss/integrated_water if integrated_water > 0 else None
        result['water'] = dict(available=True, monthly_mean_column_mm=mean_water.tolist(),
            monthly_effective_sink_rate_per_day=nullable(rates), monthly_effective_timescale_days=nullable(times),
            annual_effective_sink_rate_per_day=annual_rate,
            annual_effective_timescale_days=1/annual_rate if annual_rate is not None and annual_rate > 0 else None,
            rate_definition='Ratio of mean loss to mean water; a water-weighted monthly/annual coefficient')
    return result


def verify_parent(plan):
    """Validate all inputs and exact case geometry without running a climate."""
    parent = ROOT/plan['parent']
    protocol_path, review_path = parent/'protocol.json', parent/'review.json'
    protocol = json.loads(protocol_path.read_text()); review = json.loads(review_path.read_text())
    parent_id = identity(protocol); original = protocol['plan']
    if (review.get('complete') is not True or review.get('all_per_step_checks_passed') is not True
            or review.get('identity') != parent_id or review.get('physics_or_atlas_adoption') is not False
            or list(original['profiles']) != plan['profiles'] or original['regions'] != plan['regions']):
        raise ValueError('Need the complete unchanged six-profile seven-region parent')
    sources = [protocol_path, review_path, parent/'progress.json', DEV12_SPECS]
    for name, sha in protocol['sources'].items():
        path = ROOT/name
        if file_hash(path) != sha:
            raise ValueError('Changed parent scientific source: '+name)
        sources.append(path)
    progress = json.loads((parent/'progress.json').read_text())
    if progress.get('complete') is not True or len(progress.get('records', [])) != len(plan['profiles'])*len(plan['regions']):
        raise ValueError('Incomplete parent progress archive')
    progress_rows = {(r['name'],r['region']):r for r in progress['records']}
    if len(progress_rows) != len(progress['records']):
        raise ValueError('Repeated parent row identity')
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    cases = {region:earth.region_case(region, float(original['cell_km'])) for region in plan['regions']}
    rows = {}; geometry = {}
    for name in plan['profiles']:
        rows[name] = {}
        for region in plan['regions']:
            path = parent/name/(region+'.json'); arrays = path.with_suffix('.npz')
            row = json.loads(path.read_text()); case = cases[region]; g = case.grid; sl = g.map_slice()
            derived = case_hash(case, observed_sea=True)
            if (row.get('identity') != parent_id or row.get('case_identity') != derived
                    or row.get('name') != name or row.get('region') != region or row.get('status') != 'passed'
                    or row.get('numerics', {}).get('all_checks_passed') is not True
                    or row.get('updates') != original['profiles'][name]
                    or row.get('numerical_updates', {}) != original.get('profile_numerics', {}).get(name, {})
                    or row != progress_rows.get((name,region)) or file_hash(arrays) != row.get('arrays_sha256')):
                raise ValueError('Changed or failed parent row/arrays: '+str(path.relative_to(ROOT)))
            theta = joint.update_block(load_params(ROOT/original['physics']), 'physics', row['updates'])
            theta = joint.update_block(theta, 'numerics', row['numerical_updates'])
            params = earth.earth_params(joint.earth_profile(theta), case)
            if json.loads(json.dumps(asdict(params))) != row['params']:
                raise ValueError('Changed parent physical/numerical parameters')
            if region in original.get('extra_circulation_regions', []):
                extra = path.with_name(region+'_extra.npz')
                if file_hash(extra) != row.get('extra_circulation_arrays_sha256'):
                    raise ValueError('Changed parent native companion')
                sources.append(extra)
            full_mask = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
            with np.load(arrays, allow_pickle=False) as saved:
                if (not np.array_equal(saved['valid'], full_mask[sl])
                        or not np.array_equal(saved['elev'], g.elev[sl])
                        or not np.array_equal(saved['observed'], case.obs_P[(slice(None),)+sl], equal_nan=True)
                        or row['rain']['scored_land_cells'] != int(full_mask.sum())):
                    raise ValueError('Changed cropped/full scoring geometry: '+region)
                pair = (saved['valid'].copy(), saved['elev'].copy(), saved['observed'].copy())
                if region in geometry and any(not np.array_equal(a,b,equal_nan=True) for a,b in zip(pair,geometry[region])):
                    raise ValueError('Unpaired diagnostic geometry: '+region)
                geometry[region] = pair
                has_water = {'layer_water','column_water'} <= set(saved.files)
                if has_water != (name in plan['water_profiles']):
                    raise ValueError('Changed declared water availability')
            rows[name][region] = row; sources.extend([path, arrays])
    return protocol, review, cases, rows, sources


def plots(plan, results, paired, out):
    labels = dict(reference='r39', wind_control='Moist', environment_600='6.0', environment_650='6.5',
                  transport_control='Fixed q', column_control='Moist original winds')
    pretty = dict(evaporation='Surface E', advection='Advection', diffusion='Diffusion', storm_exchange='Storms',
                  other_column_drying='Other drying', monsoon_drying='Monsoon drying', convergence_import='Legacy import')
    names = plan['display_profiles']; regions = plan['regions']
    fig, axes = plt.subplots(2,4,figsize=(17,9.3))
    for ax,region in zip(axes.flat,regions):
        x = np.arange(len(names)); pos = np.zeros(len(names)); neg = pos.copy()
        for key,color in zip(DISJOINT_TERMS,COLORS):
            values = np.array([results[n][region]['bins']['all_land']['annual'][key] for n in names])
            ax.bar(x,np.maximum(values,0),bottom=pos,color=color,label=pretty[key])
            ax.bar(x,np.minimum(values,0),bottom=neg,color=color)
            pos += np.maximum(values,0); neg += np.minimum(values,0)
        rain = [results[n][region]['bins']['all_land']['annual']['simulated'] for n in names]
        observed = results[names[0]][region]['bins']['all_land']['annual']['observed']
        ax.plot(x,rain,'D',color='#202020',markersize=4,label='Simulated rain')
        ax.axhline(observed,color='#202020',ls='--',lw=1,label='Observed rain')
        ax.axhline(0,color='#777',lw=.5); ax.grid(axis='y',alpha=.13)
        ax.set(xticks=x,xticklabels=[labels[n] for n in names],title=region.replace('_',' ').title(),ylabel='Signed mm / model year')
    axes.flat[-1].axis('off')
    handles,legend=axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].legend(handles,legend,loc='center',frameon=False,fontsize=11)
    fig.suptitle('Actual archived water equations: supplies, exports and explicit column drying',fontsize=17)
    fig.supxlabel('Original cropped land masks and equal model months; East Australia crop omits some full-score cells.\n'
        'Monsoon is a subset of total drying and is stacked only once. r39 concentration advection is not conservative flux.\n'
        'These are equation terms, not causal shares or a sink-off rainfall prediction.',fontsize=10)
    fig.tight_layout(rect=[0,.085,1,.96]); first=out/'column_drying_budgets.png';fig.savefig(first,dpi=145);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(16,7.5),gridspec_kw={'width_ratios':[1.4,1]})
    delta=np.array([[paired[r]['bins']['all_land']['annual'][k] for k in DISJOINT_TERMS] for r in regions])
    span=max(1.,float(np.abs(delta).max()))
    picture=axes[0].imshow(delta,cmap='RdBu_r',vmin=-span,vmax=span,aspect='auto')
    axes[0].set(yticks=np.arange(len(regions)),yticklabels=[r.replace('_',' ').title() for r in regions],
        xticks=np.arange(len(DISJOINT_TERMS)),xticklabels=[pretty[k].replace(' ','\n') for k in DISJOINT_TERMS],
        title='6.0 K/km minus moist: same 7.5 m/s winds')
    for i in range(len(regions)):
        for j in range(len(DISJOINT_TERMS)):
            axes[0].text(j,i,f'{delta[i,j]:+.0f}',ha='center',va='center',fontsize=9,
                color='white' if abs(delta[i,j])>.65*span else '#151515')
    fig.colorbar(picture,ax=axes[0],label='Signed annual term difference (mm / model year)',shrink=.8)
    for index,name in enumerate(plan['profiles']):
        values=[results[name][r]['bins']['all_land']['annual']['drying_to_rain'] for r in regions]
        axes[1].plot(values,np.arange(len(regions))+(index-2.5)*.09,'o',markersize=5,label=labels[name])
    axes[1].set(yticks=np.arange(len(regions)),yticklabels=[r.replace('_',' ').title() for r in regions],
        xlabel='Annual positive column drying / simulated rain',title='A removal burden, not a predicted rain change')
    axes[1].invert_yaxis();axes[1].grid(axis='x',alpha=.15);axes[1].legend(fontsize=9,loc='best')
    fig.suptitle('What changed in the saved equations?',fontsize=17)
    fig.supxlabel('Identical cropped cells; all six profiles retained. Internal donor exchange is not saved and cannot be inferred here.\n'
        'A signed difference is not physical attribution or evidence that the drying closure is duplicated.',fontsize=10)
    fig.tight_layout(rect=[0,.07,1,.95]);second=out/'column_drying_changes.png';fig.savefig(second,dpi=145);plt.close(fig)
    return [first,second]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=ROOT/'calibration/column_drying_20261027/plan.json')
    parser.add_argument('--out',type=Path,default=ROOT/'output/column_drying_20261027')
    args=parser.parse_args();out=args.out.resolve();plan_path=args.plan.resolve()
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise SystemExit('Preserve the existing audit directory; choose a fresh output')
    phase='parent-verification'
    try:
        plan=json.loads(plan_path.read_text())
        if (plan.get('climate_integrations')!=0 or plan.get('physics_or_atlas_adoption') is not False
                or plan['source_terms']!=list(SOURCE_TERMS) or plan['display_disjoint_terms']!=list(DISJOINT_TERMS)):
            raise ValueError('Changed audit scope or equation design')
        protocol,parent_review,cases,rows,sources=verify_parent(plan)
        sources.extend([Path(__file__).resolve(),plan_path])
        for module in tuple(sys.modules.values()):
            filename=getattr(module,'__file__',None)
            if filename:
                local=Path(filename).resolve()
                if (local.is_relative_to(ROOT) and '.venv' not in local.relative_to(ROOT).parts and local.suffix=='.py'):
                    sources.append(local)
        phase='freeze'
        run_id=freeze(out/'protocol.json',dict(plan=plan,
            sources={str(p.relative_to(ROOT)):file_hash(p) for p in dict.fromkeys(sources)},
            parent_identity=identity(protocol),
            packages={name:importlib.metadata.version(name) for name in ('numpy','scipy','matplotlib')}))
        phase='diagnosis';results={};derived_arrays={};limits=plan['numerical_limits']
        for name in plan['profiles']:
            results[name]={}
            for region in plan['regions']:
                row=rows[name][region];g=cases[region].grid;sl=g.map_slice()
                path=ROOT/plan['parent']/name/(region+'.npz')
                with np.load(path,allow_pickle=False) as saved:
                    fields={k:saved[k].copy() for k in saved.files}
                mask=fields['valid'];elev=fields['elev'];duration=row['params']['year_days']/12.
                cert=check_source_closure(fields,mask,atol_mm_month=limits['closure_atol_mm_model_month'],
                    rtol=limits['closure_rtol_sum_abs'])
                absolute=np.asarray(fields['absolute_residual'])
                if absolute.shape!=(12,*mask.shape) or not np.isfinite(absolute[:,mask]).all() or (absolute[:,mask]<0).any():
                    raise ValueError('Invalid saved absolute residual')
                water=None;water_check=None
                if name in plan['water_profiles']:
                    water_check=check_layer_water(fields['column_water'],fields['layer_water'],
                        atol_mm=limits['layer_sum_atol_mm'],rtol=limits['layer_sum_rtol'])
                    if fields['column_water'].shape!=(12,g.ny,g.nx):
                        raise ValueError('Saved water is not on the verified full case grid')
                    water=fields['column_water'][(slice(None),)+sl]
                    rate,tau=effective_sink_rates(fields['column_drying'][:,mask],water[:,mask],duration)
                    prefix=name+'_'+region+'_'
                    derived_arrays[prefix+'column_water_mm']=water[:,mask]
                    derived_arrays[prefix+'effective_rate_per_day']=rate
                    derived_arrays[prefix+'effective_timescale_days']=tau
                    derived_arrays[prefix+'valid_flat_indices']=np.flatnonzero(mask)
                bins=dict(all_land=mask,lowland=mask&(elev<1000),upland=mask&(elev>=1000))
                results[name][region]=dict(closure=cert,layer_water_check=water_check,
                    geometry=dict(cropped_shape=list(mask.shape),cropped_diagnostic_cells=int(mask.sum()),
                        full_original_scoring_cells=row['rain']['scored_land_cells'],
                        cropped_omits_scoring_cells=row['rain']['scored_land_cells']-int(mask.sum()),
                        map_slice=[[s.start,s.stop] for s in sl],case_identity=row['case_identity']),
                    original_full_score_rain=row['rain'],
                    bins={label:summarize(fields,own,duration,water) for label,own in bins.items()})
        paired={};own,base=plan['paired_change']['candidate'],plan['paired_change']['control']
        for region in plan['regions']:
            paired[region]=dict(candidate=own,control=base,bins={})
            for label in plan['bins']:
                a,b=results[own][region]['bins'][label],results[base][region]['bins'][label]
                if a['cells']!=b['cells']:raise ValueError('Changed paired bin mask')
                paired[region]['bins'][label]=dict(cells=a['cells'],monthly=None,annual=None)
                if a['cells']:
                    paired[region]['bins'][label].update(
                        monthly={k:(np.array(a['monthly'][k])-b['monthly'][k]).tolist() for k in a['monthly']},
                        annual={k:a['annual'][k]-b['annual'][k] for k in a['monthly']})
        arrays=out/'monthly_sink_rates.npz'
        with arrays.open('wb') as stream:np.savez_compressed(stream,**derived_arrays)
        phase='figures';pictures=plots(plan,results,paired,out)
        phase='final-source-verification'
        frozen=json.loads((out/'protocol.json').read_text())
        for name,sha in frozen['sources'].items():
            if file_hash(ROOT/name)!=sha:raise ValueError('Frozen audit input changed: '+name)
        review=dict(complete=True,status='passed',identity=run_id,climate_integrations=0,
            physics_or_atlas_adoption=False,parent_identity=identity(protocol),regions=plan['regions'],
            profiles=results,paired_changes=paired,
            protocol_sha256=file_hash(out/'protocol.json'),arrays_sha256=file_hash(arrays),
            images_sha256={p.name:file_hash(p) for p in pictures},
            donor_vertical_overlap=dict(available=False,reason='Branch winds, donor F and step water were not saved'),
            interpretation=plan['decision'],unavailable=plan['unavailable'])
        write_json(out/'review.json',review)
        print(json.dumps(dict(status='passed',identity=run_id,climate_integrations=0,output=str(out)),indent=2))
    except Exception as error:
        write_json(out/'failure.json',dict(status='failed',phase=phase,error=repr(error),
            climate_integrations=0,physics_or_atlas_adoption=False))
        raise


if __name__=='__main__':main()

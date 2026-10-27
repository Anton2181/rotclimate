"""Standalone PNW native thermal/humidity diagnosis; zero climate integrations."""
from pathlib import Path
import argparse
import importlib.metadata
import json
import ssl
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiments import v10_forcing_audit as reader
from rotclimate.column_thermodynamics import (CP,G,RD,TROPOPAUSE_K,
    integrate_saturation_profile,specific_saturation)
from circulation_reference import acquire,column_targets
from earth_calendar import MONTH_DAYS
from local_benchmark_protocol import file_hash,freeze,identity,write_json


def acquire_air(plan,*,fetch=False):
    """Acquire one new small air subset into its own provenance-checked cache."""
    cache=ROOT/plan['air_cache'];cache.mkdir(parents=True,exist_ok=True)
    manifest_path=cache/'downloads.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    box=plan['new_reference_boxes'][plan['region']]
    if box!=[[14,22,92,102]]:raise ValueError('Only the declared PNW reference box is supported')
    y0,y1,x0,x1=box[0]
    base=reader.BASE+'air.mon.1981-2010.ltm.nc'
    query=f'air[0:1:11][0:1:{reader.VARIABLES["air"]-1}][{y0}:1:{y1}][{x0}:1:{x1}]'
    requests=[('air.das',base+'.das',None),('air_pacific_nw_0.ascii',base+'.ascii?'+query,box[0])]
    sources=[manifest_path];payloads={};provenance={}
    for name,url,subset in requests:
        path=cache/name;origin={}
        if path.exists():
            record=manifest.get(name,{})
            if record.get('url')!=url or record.get('sha256')!=file_hash(path):
                raise ValueError('Changed or unrecorded PNW air cache: '+str(path))
            payload=path.read_text()
            origin=record.get('origin',{})
            if origin.get('path'):
                original=ROOT/origin['path'];original_manifest=ROOT/origin['manifest']
                saved=json.loads(original_manifest.read_text()).get(name,{})
                if (saved.get('url')!=url or saved.get('sha256')!=origin.get('sha256')
                        or file_hash(original)!=origin['sha256']):
                    raise ValueError('Changed original reused air metadata')
                sources.extend([original,original_manifest])
        else:
            original_cache=ROOT/plan['metadata_reuse_cache'];original=original_cache/name
            original_manifest=original_cache/'downloads.json'
            if subset is None and original.exists():
                saved=json.loads(original_manifest.read_text()).get(name,{})
                if saved.get('url')!=url or saved.get('sha256')!=file_hash(original):
                    raise ValueError('Invalid original air metadata provenance')
                payload=original.read_text();reader.metadata(payload,'air')
                origin=dict(path=str(original.relative_to(ROOT)),manifest=str(original_manifest.relative_to(ROOT)),
                    sha256=file_hash(original))
                sources.extend([original,original_manifest])
            else:
                if not fetch:raise ValueError('Missing PNW air input; explicitly run with --fetch: '+str(path))
                print('Fetching NOAA PNW reference: '+name,flush=True)
                context=ssl.create_default_context()
                try:
                    import certifi
                    context.load_verify_locations(cafile=certifi.where())
                except ImportError:pass
                request=urllib.request.Request(url,headers={'User-Agent':'rotclimate-pnw-vertical-audit/1.0'})
                with urllib.request.urlopen(request,timeout=45,context=context) as response:
                    binary=response.read(4*1024*1024+1)
                if len(binary)>4*1024*1024:raise ValueError('Oversized NOAA air response')
                payload=binary.decode('utf-8')
            if subset is None:reader.metadata(payload,'air')
            else:reader.validate_subset(reader.parse_ascii(payload,'air'),subset,reader.VARIABLES['air'])
            temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(payload);temporary.replace(path)
            manifest[name]=dict(url=url,sha256=file_hash(path),bytes=path.stat().st_size,origin=origin)
            write_json(manifest_path,manifest)
        # Re-validate cached payloads as strictly as newly acquired responses.
        if subset is None:reader.metadata(payload,'air')
        else:reader.validate_subset(reader.parse_ascii(payload,'air'),subset,reader.VARIABLES['air'])
        sources.append(path);payloads[name]=payload;provenance[str(path.relative_to(ROOT))]=manifest[name]
    units=reader.metadata(payloads['air.das'],'air')
    field=reader.normalize(reader.parse_ascii(payloads['air_pacific_nw_0.ascii'],'air'),'air',units)
    if not np.isfinite(field.values).all():raise ValueError('Nonfinite PNW air reference')
    return field,sources,provenance


def partial_integrals(values,pressure_hpa):
    """Same trapezoidal pressure nodes for actual q and every capacity profile."""
    a=np.asarray(values,float);p=np.asarray(pressure_hpa,float)
    if (a.ndim!=3 or a.shape[:2]!=(12,len(p)) or not np.isfinite(a).all() or (a<0).any()
            or p.ndim!=1 or not np.array_equal(p,[925,850,700,600,500,400,300])):
        raise ValueError('Need finite nonnegative 12 x seven-pressure x native-cell data')
    k=int(np.flatnonzero(p==700)[0])
    integrate=lambda v,levels:np.trapezoid(v[:,::-1],x=levels[::-1]*100,axis=1)/G
    lower=integrate(a[:,:k+1],p[:k+1]);upper=integrate(a[:,k:],p[k:])
    if (lower<=0).any():raise ValueError('Nonpositive lower partial-column humidity/capacity')
    return dict(total_mm=integrate(a,p),lower_mm=lower,upper_mm=upper,
        lower_mean_q=lower*G/22500.,upper_mean_q=upper*G/40000.,
        upper_lower_mean_q_ratio=(upper/40000.)/(lower/22500.))


def summarize_arrays(arrays,area,days):
    """Retain native data and monthly/annual/DJF/JJA area/day means."""
    area=np.asarray(area,float);days=np.asarray(days,float)
    if (area.ndim!=1 or not len(area) or (area<=0).any() or not np.isfinite(area).all()
            or not np.array_equal(days,MONTH_DAYS)):
        raise ValueError('Need positive native areas and exact geographic Gregorian month days')
    def mean(value,months):
        weights=days[months,None]*area[None,:]
        shape=(len(months),)+(1,)*(value.ndim-2)+(len(area),)
        return np.sum(value[months]*weights.reshape(shape),axis=(0,value.ndim-1))/weights.sum()
    native={};monthly={};seasons={season:{} for season in ('annual','DJF','JJA')}
    for key,value in arrays.items():
        value=np.asarray(value,float)
        if value.ndim not in (2,3) or value.shape[0]!=12 or value.shape[-1]!=len(area) or not np.isfinite(value).all():
            raise ValueError('Invalid monthly native diagnostic array: '+key)
        native[key]=value.tolist();monthly[key]=np.average(value,axis=-1,weights=area).tolist()
        for season,months in [('annual',np.arange(12)),('DJF',np.array([11,0,1])),('JJA',np.array([5,6,7]))]:
            seasons[season][key]=mean(value,months).tolist()
    return dict(native=native,monthly=monthly,seasons=seasons)


def diagnose(plan,air,humidity,mask,area,days):
    """Derive all outcomes only after the caller freezes sources and downloads."""
    levels=np.asarray(plan['pressure_hpa'],float)
    ti=[list(air.pressure_hpa).index(p) for p in levels]
    qi=[list(humidity.pressure_hpa).index(p) for p in levels]
    temperature=(air.values[:,ti]+273.15).reshape(12,len(levels),-1)[:,:,mask]
    ratio=humidity.values[:,qi].reshape(12,len(levels),-1)[:,:,mask]
    q=ratio/(1+ratio)  # The constrained reader normalizes q into mixing ratio r.
    pressure=levels[None,:,None]*100
    observed_qsat=specific_saturation(temperature,pressure)
    actual=partial_integrals(q,levels);observed_capacity=partial_integrals(observed_qsat,levels)
    theta=lambda t:t*(plan['potential_temperature_reference_pa']/pressure)**(RD/CP)
    observed=dict(temperature_c=temperature-273.15,potential_temperature_k=theta(temperature),
        dry_theta_increment_per_interval_k=np.diff(theta(temperature),axis=1),
        specific_humidity_kg_kg=q,specific_saturation_kg_kg=observed_qsat,
        specific_humidity_saturation_fraction=q/observed_qsat,
        partial_water_mm=actual['total_mm'],lower_actual_water_mm=actual['lower_mm'],upper_actual_water_mm=actual['upper_mm'],
        upper_lower_mean_actual_q_ratio=actual['upper_lower_mean_q_ratio'],
        partial_saturation_capacity_mm=observed_capacity['total_mm'],
        lower_saturation_capacity_mm=observed_capacity['lower_mm'],upper_saturation_capacity_mm=observed_capacity['upper_mm'],
        upper_lower_mean_saturation_q_ratio=observed_capacity['upper_lower_mean_q_ratio'],
        partial_water_over_saturation_capacity=actual['total_mm']/observed_capacity['total_mm'],
        lower_water_over_saturation_capacity=actual['lower_mm']/observed_capacity['lower_mm'],
        upper_water_over_saturation_capacity=actual['upper_mm']/observed_capacity['upper_mm'])
    data=dict(observed=summarize_arrays(observed,area,days),profiles={})
    raw={'observed_'+key:value for key,value in observed.items()}
    ps=np.full((12,int(mask.sum())),92500.)
    edges=np.broadcast_to(levels[:,None,None]*100,(len(levels),)+ps.shape)
    for profile in plan['profiles']:
        _,interfaces=integrate_saturation_profile(temperature[:,0]-273.15,ps,edges,profile=profile,
            lapse_k_km=plan['lapse_k_km'],steps=plan['profile_integration_steps_per_interval'])
        predicted=np.moveaxis(interfaces,0,1)
        qsat=specific_saturation(predicted,pressure);capacity=partial_integrals(qsat,levels)
        # Exclude the observed anchor; pressure-weight the withheld850-300hPa nodes.
        difference=np.abs(predicted[:,1:]-temperature[:,1:])
        shape_error=np.trapezoid(difference[:,::-1],x=levels[1:][::-1]*100,axis=1)/55000.
        arrays=dict(temperature_c=predicted-273.15,potential_temperature_k=theta(predicted),
            specific_saturation_kg_kg=qsat,partial_saturation_capacity_mm=capacity['total_mm'],
            lower_saturation_capacity_mm=capacity['lower_mm'],upper_saturation_capacity_mm=capacity['upper_mm'],
            upper_lower_mean_saturation_q_ratio=capacity['upper_lower_mean_q_ratio'],
            withheld_850_300_temperature_shape_mae_c=shape_error)
        data['profiles'][profile]=dict(summarize_arrays(arrays,area,days),
            observed_anchor='Native monthly925hPa temperature only; no humidity fit',
            minimum_temperature_k=float(predicted.min()),
            nodes_at_prescribed_temperature_floor=int(np.sum(predicted<=TROPOPAUSE_K)))
        raw.update({profile+'_'+key:value for key,value in arrays.items()})
    return data,raw


def plot_profiles(data,levels,path):
    """One standalone figure; every predeclared temperature profile is retained."""
    observed=data['observed'];profiles=data['profiles'];levels=np.asarray(levels)
    fig,axes=plt.subplots(2,3,figsize=(15.5,9),constrained_layout=True)
    colors=dict(observed='#222222',lapse='#ac7750',moist='#327f94')
    labels=dict(observed='NCEP/NCAR',lapse='Fixed environmental lapse',moist='Saturated moist profile')
    for ax,season in zip(axes[0,:2],['DJF','JJA']):
        ax.plot(observed['seasons'][season]['temperature_c'],levels,color=colors['observed'],lw=2.5,label=labels['observed'])
        for profile,group in profiles.items():
            ax.plot(group['seasons'][season]['temperature_c'],levels,color=colors[profile],lw=1.8,label=labels[profile])
        ax.set(title=season+' · same observed925hPa anchor',xlabel='Temperature (°C)');ax.legend(frameon=False,fontsize=8)
    season_colors=dict(annual='#333333',DJF='#447ca2',JJA='#ba8658')
    for season,color in season_colors.items():
        axes[0,2].plot(observed['seasons'][season]['potential_temperature_k'],levels,color=color,label=season,lw=2)
        axes[1,0].plot(observed['seasons'][season]['specific_humidity_saturation_fraction'],levels,color=color,label=season,lw=2)
    axes[0,2].set(title='Observed dry potential temperature',xlabel='Dry theta (K)')
    axes[1,0].set(title='Observed specific-humidity saturation fraction',xlabel='q / liquid qsat(T,p)')
    axes[0,2].legend(frameon=False,fontsize=8);axes[1,0].legend(frameon=False,fontsize=8)
    for ax in [*axes[0],axes[1,0]]:
        ax.set(yscale='log',ylim=(925,300),ylabel='Pressure (hPa)')
        ax.set_yticks(levels);ax.set_yticklabels(levels.astype(int));ax.grid(alpha=.15)
    monthly=observed['monthly'];ax=axes[1,1]
    ax.plot(monthly['partial_water_mm'],color=colors['observed'],lw=2.5,label='Observed actual water')
    ax.plot(monthly['partial_saturation_capacity_mm'],color='#777777',ls='--',label='Capacity at observed T')
    for profile,group in profiles.items():
        ax.plot(group['monthly']['partial_saturation_capacity_mm'],color=colors[profile],label=profile.title()+' capacity')
    ax.set(xticks=range(12),xticklabels=list('JFMAMJJASOND'),ylabel='Matched925–300hPa water / capacity (mm)',
        title='Actual humidity and saturation capacity differ');ax.legend(frameon=False,fontsize=7);ax.grid(alpha=.15)
    ax=axes[1,2];x=np.arange(3);width=.19
    groups=[('Observed actual q',observed,'upper_lower_mean_actual_q_ratio','#222222'),
            ('qsat at observed T',observed,'upper_lower_mean_saturation_q_ratio','#777777'),
            ('Lapse qsat',profiles['lapse'],'upper_lower_mean_saturation_q_ratio',colors['lapse']),
            ('Moist qsat',profiles['moist'],'upper_lower_mean_saturation_q_ratio',colors['moist'])]
    for offset,(label,group,key,color) in zip(np.arange(4)*width-1.5*width,groups):
        ax.bar(x+offset,[group['seasons'][s][key] for s in season_colors],width=width,color=color,label=label)
    ax.set(xticks=x,xticklabels=['Annual','DJF','JJA'],ylabel='Mean q700–300 / mean q925–700',
        title='Partial actual-q and saturation-q shapes');ax.legend(frameon=False,fontsize=7);ax.grid(axis='y',alpha=.15)
    fig.suptitle('Pacific Northwest · native ocean thermal and humidity structure',fontsize=16)
    fig.supxlabel('Four fixed native ocean footprints; true-area and Gregorian month weights. No climate integration, humidity fit or rainfall selection.\n'
        'NCEP/NCAR1981–2010 is model-assisted.925–300hPa omits the marine layer below925hPa; liquid saturation and dry theta are explicit approximations.',fontsize=9)
    fig.savefig(path,dpi=145);plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=ROOT/'calibration/pnw_vertical_20261027/plan.json')
    parser.add_argument('--out',type=Path,default=ROOT/'output/pnw_vertical_20261027')
    parser.add_argument('--fetch',action='store_true',help='Explicitly acquire the missing small NOAA air subset')
    args=parser.parse_args();path=args.plan.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    protected=['protocol.json','review.json','failure.json','native_profiles.npz','native_profiles.png']
    if any((out/name).exists() for name in protected):
        raise ValueError('Preserve prior PNW vertical output/failure; choose a fresh --out')
    phase='plan';run_identity=None
    try:
        plan=json.loads(path.read_text());physics=ROOT/plan['physics']
        if (plan['climate_integrations']!=0 or plan['physics_or_atlas_adoption'] is not False
                or plan['profiles']!=['lapse','moist'] or plan['native_ocean_cells']!=4
                or plan['lapse_k_km']!=json.loads(physics.read_text())['lapse_rate']):
            raise ValueError('Changed declared no-fit PNW vertical comparison')
        phase='acquisition'
        reference_plan=ROOT/plan['circulation_reference_plan']
        reference,references=acquire(ROOT,json.loads(reference_plan.read_text()))
        air,air_sources,air_provenance=acquire_air(plan,fetch=args.fetch)
        humidity=reference[plan['region'],'shum']
        for variable in ['shum','hgt']:
            field=reference[plan['region'],variable]
            for axis in ['latitude','longitude','time']:
                if not np.array_equal(getattr(air,axis),getattr(field,axis)):
                    raise ValueError('PNW thermal/humidity/geopotential axes differ: '+axis)
        if not np.isfinite(humidity.values).all():raise ValueError('Nonfinite observed PNW humidity')
        for level in plan['pressure_hpa']:
            if level not in air.pressure_hpa or level not in humidity.pressure_hpa:
                raise ValueError('Missing declared shared pressure level')
        phase='archive-verification'
        archive=ROOT/plan['reference_archive'];record_path=ROOT/plan['reference_record']
        archive_protocol=ROOT/plan['reference_protocol']
        record=json.loads(record_path.read_text());prior=json.loads(archive_protocol.read_text())
        if (record.get('status')!='passed' or record.get('numerics',{}).get('all_checks_passed') is not True
                or file_hash(archive)!=record.get('arrays_sha256') or identity(prior)!=record.get('identity')):
            raise ValueError('Unverified independent PNW native archive')
        if record['circulation']['original_month']!=list(range(12)):
            raise ValueError('PNW archive is not in geographic January-December order')
        for name in references:
            if prior['sources'].get(name)!=file_hash(ROOT/name):
                raise ValueError('PNW reference payload differs from its independent audit: '+name)
        with np.load(archive) as saved:
            mask=saved['circulation_mask_ocean'].copy();native_area=saved['circulation_area'].copy()
            archived_targets={key:saved['circulation_reference_'+key].copy() for key in ['925','850','q925_300']}
        count=len(humidity.latitude)*len(humidity.longitude)
        if (mask.dtype!=np.dtype(bool) or mask.shape!=(count,) or native_area.shape!=(count,)
                or int(mask.sum())!=plan['native_ocean_cells'] or not np.isfinite(native_area).all()
                or (native_area[mask]<=0).any()):raise ValueError('Changed fixed native PNW ocean geometry')
        area=native_area[mask];days=MONTH_DAYS.copy()
        footprint=record['circulation']['scores']['q925_300']['ocean']
        if footprint['native_cells']!=int(mask.sum()) or footprint['area_km2']!=float(area.sum()):
            raise ValueError('Archived PNW footprint/area certificate changed')
        sources=[path,Path(__file__),physics,reference_plan,archive,record_path,archive_protocol,
            ROOT/'scripts/circulation_reference.py',ROOT/'scripts/earth_calendar.py',ROOT/'scripts/local_benchmark_protocol.py',
            ROOT/'experiments/v10_forcing_audit.py',ROOT/'experiments/v10_thermodynamics.py',
            ROOT/'data/v10_atmosphere/downloads.json',ROOT/'data/cache/circulation_reference_20261026/downloads.json',
            *air_sources,*[ROOT/name for name in references],
            *list((ROOT/'rotclimate').glob('*.py')),*list((ROOT/'rotclimate_v10').glob('*.py'))]
        run_identity=freeze(out/'protocol.json',dict(plan=plan,
            sources={str(p.relative_to(ROOT)):file_hash(p) for p in dict.fromkeys(sources)},
            references=references,air_references=air_provenance,
            packages={name:importlib.metadata.version(name) for name in ['numpy','scipy','matplotlib']}))
        phase='matched-reference-verification'
        # Numerical reference products are checked only after freezing every input.
        targets,_,_=column_targets({v:reference[plan['region'],v] for v in ['uwnd','vwnd','shum','hgt']})
        for key,value in targets.items():
            if not np.array_equal(value.reshape(12,2,-1),archived_targets[key]):
                raise ValueError('Independent archived pressure-vector target changed: '+key)
        phase='diagnosis'
        data,arrays=diagnose(plan,air,humidity,mask,area,days)
        longitude,latitude=np.meshgrid(humidity.longitude,humidity.latitude)
        geometry=dict(native_flat_indices=np.flatnonzero(mask).tolist(),native_area_km2=area.tolist(),
            native_latitude=latitude.ravel()[mask].tolist(),native_longitude=longitude.ravel()[mask].tolist(),
            native_ocean_cells=int(mask.sum()),total_area_km2=float(area.sum()),month_days=days.tolist(),
            pressure_hpa=plan['pressure_hpa'],pressure_intervals_hpa=list(zip(plan['pressure_hpa'][:-1],plan['pressure_hpa'][1:])))
        arrays.update(native_flat_indices=np.flatnonzero(mask),native_ocean_mask=mask,native_full_area_km2=native_area,
            native_area_km2=area,native_latitude=latitude.ravel()[mask],native_longitude=longitude.ravel()[mask],
            pressure_hpa=np.asarray(plan['pressure_hpa']),month_days=days)
        target=out/'native_profiles.npz'
        with target.with_suffix('.tmp').open('wb') as stream:np.savez_compressed(stream,**arrays)
        target.with_suffix('.tmp').replace(target)
        phase='figure';picture=out/'native_profiles.png';plot_profiles(data,plan['pressure_hpa'],picture)
        # Stop if any fingerprinted input changed during the diagnostic.
        for name,expected in json.loads((out/'protocol.json').read_text())['sources'].items():
            if file_hash(ROOT/name)!=expected:raise ValueError('Frozen source changed during audit: '+name)
        result=dict(complete=True,status='passed',identity=run_identity,geometry=geometry,**data,
            provenance=dict(protocol_sha256=file_hash(out/'protocol.json'),arrays_sha256=file_hash(target),
                air_references=air_provenance,circulation_references=references),
            image_sha256=file_hash(picture),limitations=plan['limitations'],climate_integrations=0,
            physics_or_atlas_adoption=False,selection='Diagnostic only; neither thermal profile nor humidity coefficient selected')
        write_json(out/'review.json',result)
        print(json.dumps(dict(status='passed',identity=run_identity,climate_integrations=0,
            native_ocean_cells=int(mask.sum()),area_km2=float(area.sum()),output=str(out)),indent=2),flush=True)
    except Exception as error:
        failure=dict(complete=False,status='failed',phase=phase,error=repr(error),identity=run_identity,
            plan_sha256=file_hash(path),script_sha256=file_hash(Path(__file__)),climate_integrations=0,
            physics_or_atlas_adoption=False,note='Preserve this output and every cached response; use a fresh output for a corrected study')
        write_json(out/'failure.json',failure)
        raise


if __name__=='__main__':main()

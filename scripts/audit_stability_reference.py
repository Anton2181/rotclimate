"""Cached Earth height/stability audit; no circulation forcing or Earth runs."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate.column_thermodynamics import G,RD,CP
from rotclimate.lapse_reference import lapse_reference,height_at_pressure
from rotclimate.vertical_state import build_vertical_state
from transport_reference import acquire
from local_benchmark_protocol import file_hash,write_json

PRESSURE_PA=np.array([925,850,700,600,500,400,300,250,200,150,100],float)*100
GAMMA=.006
CAP_K=200.


def diagnose_height_column(pressure_pa,height_m):
    """Hypsometric layer-mean Tv and dry-exponent virtual-theta secant N².

    Coarse monthly pressure-layer means are assigned to geometric-mean p and
    height midpoints. This is a stability proxy, not saturated moist stability.
    Nonpositive N² is retained for explicit exclusion, never floored.
    """
    p,z=np.asarray(pressure_pa,float),np.asarray(height_m,float)
    if (p.ndim!=1 or len(p)<3 or z.shape!=p.shape or not np.isfinite(p).all()
            or not np.isfinite(z).all() or np.any(p<=0) or np.any(np.diff(p)>=0)
            or np.any(np.diff(z)<=0)):
        raise ValueError('Need matching ascending finite height and descending positive pressure')
    z=z-z[0];dz=np.diff(z);centers=.5*(z[:-1]+z[1:])
    tv=G*dz/(RD*np.log(p[:-1]/p[1:]))
    theta=tv*(100000/np.sqrt(p[:-1]*p[1:]))**(RD/CP)
    n2=G*np.diff(np.log(theta))/np.diff(centers)
    rho=(-np.diff(p)/G)/dz
    return dict(edges_m=z,centers_m=centers,hypsometric_virtual_temperature_k=tv,
                virtual_potential_temperature_k=theta,stability_s2=n2,density_kg_m3=rho)


def evaluate_column(pressure_pa,height_m):
    d=diagnose_height_column(pressure_pa,height_m)
    p=np.asarray(pressure_pa,float);z=d['edges_m'];rho=d['density_kg_m3'];n2=d['stability_s2']
    # Exact power-law temperature anchor from ONLY the lowest layer thickness.
    ts=GAMMA*(z[1]-z[0])/(-np.expm1(RD*GAMMA/G*np.log(p[1]/p[0])))
    ref=lapse_reference(d['centers_m'],surface_temperature_k=ts,surface_pressure_pa=p[0],
                        lapse_k_m=GAMMA,tropopause_temperature_k=CAP_K)
    nr=G*np.diff(np.log(ref.potential_temperature_k))/np.diff(d['centers_m'])
    constant=build_vertical_state(z,rho,np.full_like(n2,.01**2))
    candidate=build_vertical_state(z,rho,nr)
    valid=bool(np.all(n2>0))
    observed=build_vertical_state(z,rho,n2) if valid else None
    return dict(**{k:v.tolist() for k,v in d.items()},lapse_stability_s2=nr.tolist(),
        conditional_base_temperature_k=float(ts),conditional_100hpa_depth_m=float(height_at_pressure(p[-1],
            surface_temperature_k=ts,surface_pressure_pa=p[0],lapse_k_m=GAMMA,tropopause_temperature_k=CAP_K)),
        valid_stable_proxy=valid,nonpositive_interfaces=np.flatnonzero(n2<=0).tolist(),
        inferred_first_speed_ms=float(observed.phase_speeds_ms[0]) if valid else None,
        constant_first_speed_ms=float(constant.phase_speeds_ms[0]),lapse_first_speed_ms=float(candidate.phase_speeds_ms[0]))


def summarize(cases):
    keep=[c for c in cases if c['valid_stable_proxy']];w=np.array([c['area_day_weight'] for c in keep]);w/=w.sum()
    speed=np.array([c['inferred_first_speed_ms'] for c in keep])
    result=dict(total_cases=len(cases),valid_cases=len(keep),excluded_cases=len(cases)-len(keep),
        valid_area_day_fraction=float(sum(c['area_day_weight'] for c in keep)/sum(c['area_day_weight'] for c in cases)),
        weighted_inferred_first_speed_ms=float(w@speed))
    for key in ['constant','lapse']:
        estimate=np.array([c[key+'_first_speed_ms'] for c in keep]);delta=estimate-speed
        result[key]=dict(weighted_mean_absolute_relative_speed_error=float(w@np.abs(delta/speed)),
            weighted_mean_absolute_speed_error_ms=float(w@np.abs(delta)),weighted_signed_speed_error_ms=float(w@delta))
    result['conditional_depth_relative_bias']=float(w@np.array([
        (c['conditional_100hpa_depth_m']-c['edges_m'][-1])/c['edges_m'][-1] for c in keep]))
    return result


def run(out):
    out.mkdir(parents=True,exist_ok=True)
    plan_path=ROOT/'calibration/transport_diagnosis_20261028/reference_plan.json'
    plan=json.loads(plan_path.read_text());fields,sources=acquire(ROOT,plan,fetch=False)
    heights={k:v for k,v in sources.items() if Path(k).name.startswith('hgt')}
    source_paths=['rotclimate/lapse_reference.py','rotclimate/vertical_state.py','rotclimate/column_thermodynamics.py',
                  'scripts/audit_stability_reference.py','scripts/transport_reference.py','scripts/circulation_reference.py',
                  'experiments/v10_forcing_audit.py',str(plan_path.relative_to(ROOT))]
    groups={};native={}
    for region in plan['regions']:
        field=fields[region,'hgt'];indices=[np.flatnonzero(field.pressure_hpa*100==p).item() for p in PRESSURE_PA]
        mask_path=ROOT/'output/divergent_thermal_20261028/hydro_control'/f'{region}_transport.npz'
        source_paths.append(str(mask_path.relative_to(ROOT)))
        with np.load(mask_path) as record:
            keys=['native_land_mask','native_ocean_mask','native_land_area','native_ocean_area','native_month_order','native_month_days']
            a={k:record[k] for k in keys}
        native[region]=dict(latitude=field.latitude.tolist(),longitude=field.longitude.tolist(),
                            **{k:v.tolist() for k,v in a.items()})
        height=field.values[a['native_month_order']][:,indices].reshape(12,len(PRESSURE_PA),-1)
        for kind in ['land','ocean']:
            mask=a['native_'+kind+'_mask'].astype(bool);cells=np.flatnonzero(mask)
            if not len(cells):continue
            cases=[]
            for month in range(12):
                for cell in cells:
                    result=evaluate_column(PRESSURE_PA,height[month,:,cell])
                    cases.append(dict(month=month+1,native_cell=int(cell),height_geopotential_m=height[month,:,cell].tolist(),
                        area_day_weight=float(a['native_'+kind+'_area'][cell]*a['native_month_days'][month]),**result))
            groups[region+'_'+kind]=dict(region=region,kind=kind,native_cells=len(cells),cases=cases,summary=summarize(cases))
    summary={key:float(np.mean([group['summary'][key]['weighted_mean_absolute_relative_speed_error'] for group in groups.values()]))
             for key in ['constant','lapse']}
    receipt=dict(status='cached_height_stability_diagnostic',actual_earth_integrations=0,
        coupled_climate_connected=False,physics_or_atlas_adoption=False,reference_only=True,
        pressure_edges_pa=PRESSURE_PA.tolist(),configuration=dict(lapse_k_m=GAMMA,isothermal_cap_k=CAP_K,
            constant_buoyancy_frequency_s=.01,base_pressure_pa=92500,top_pressure_pa=10000,
            temperature_anchor='Exact lowest 925-850 hPa thickness under fixed lapse; conditional, not independent prediction',
            stability_operator='g diff(log(theta_virtual_proxy))/diff(layer height centers); same secants for lapse reference',
            geometry='Identical cached height geometry and pressure-mass density for all three modes; rigid 925/100 hPa lids',
            weighting='Within group native overlap area times month days; summary is equal mean of four group errors'),
        scope='Reused sparse development footprints, NCEP 1981-2010 monthly geopotential height; no heldout validation, observed wave speeds, moist stability or rainfall result. Surface pressure is unavailable: cannot verify 925 hPa is above ground in every land cell. No direct winds/humidity used.',
        references=heights,sources={n:file_hash(ROOT/n) for n in source_paths},native=native,groups=groups,
        equal_group_mean_absolute_relative_speed_error=summary,
        excluded_cases=[dict(group=k,month=c['month'],native_cell=c['native_cell'],nonpositive_interfaces=c['nonpositive_interfaces'])
                        for k,v in groups.items() for c in v['cases'] if not c['valid_stable_proxy']])
    fig,axes=plt.subplots(1,2,figsize=(13,5.8),gridspec_kw=dict(width_ratios=[1,1.3]))
    names=list(groups);x=np.arange(len(names));labels=['India\nland (11 cells)','Mexico\nland (1 cell)','Mexico\nocean (1 cell)','Pacific NW\nocean (3 cells)']
    for offset,key,color,label in [(-.18,'constant','#cc7844','Constant N = 0.01/s'),(.18,'lapse','#247d99','6 K/km lapse + 200 K cap')]:
        axes[0].bar(x+offset,[100*groups[n]['summary'][key]['weighted_mean_absolute_relative_speed_error'] for n in names],.36,label=label,color=color)
    axes[0].set_xticks(x,labels,fontsize=9);axes[0].set_ylabel('Mean absolute relative inferred speed error (%)');axes[0].legend(fontsize=8);axes[0].set_title('Same height/density grid; valid stable columns only')
    for name,label,color in zip(names,labels,['#b65c37','#cc9c22','#23976e','#585ba0']):
        group=groups[name];months=np.arange(1,13);curves={k:[] for k in ['observed','constant','lapse']}
        for month in months:
            cases=[c for c in group['cases'] if c['month']==month and c['valid_stable_proxy']]
            w=np.array([c['area_day_weight'] for c in cases]);w/=w.sum()
            for key in curves:
                field='inferred' if key=='observed' else key
                curves[key].append(float(w@np.array([c[field+'_first_speed_ms'] for c in cases])))
        axes[1].plot(months,curves['observed'],color=color,label=label.replace('\n',' '),lw=2)
        axes[1].plot(months,curves['lapse'],color=color,ls='--',lw=1.7)
        axes[1].plot(months,curves['constant'],color=color,ls=':',lw=1.7)
    axes[1].set_xticks([1,3,5,7,9,11],['Jan','Mar','May','Jul','Sep','Nov']);axes[1].set_ylabel('Inferred first rigid-lid mode speed (m/s)')
    axes[1].set_title('Solid: height proxy; dashed: lapse; dotted: constant N');axes[1].legend(fontsize=8,loc='upper left')
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('Earth reference stability: a structural check, not a rainfall calibration',fontsize=14)
    fig.text(.5,.012,'925–100 hPa partial columns • conditional lowest-layer temperature • 3 nonpositive-stability India profiles excluded • reused footprints',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,.94));fig.savefig(out/'stability_reference.png',dpi=155);plt.close(fig)
    receipt['image_sha256']=file_hash(out/'stability_reference.png');write_json(out/'verification.json',receipt)
    print(json.dumps(dict(summary=summary,groups={k:g['summary'] for k,g in groups.items()},excluded=receipt['excluded_cases']),indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);run(ap.parse_args().out.resolve())

"""Diagnose partial-column parcel energy in the coupled controls, without tuning."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate.parcel_stability import diagnose_parcel
from local_benchmark_protocol import file_hash,write_json


def run(out):
    out.mkdir(parents=True,exist_ok=True);parent=ROOT/'output/pressure_moist_20261029'
    r=json.loads((parent/'verification.json').read_text());controls=json.loads((parent/'controls_verification.json').read_text())
    for n,h in r['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed original coupled source: '+n)
    with np.load(parent/'fields.npz') as record:a={k:record[k] for k in record.files}
    with np.load(parent/'controls_fields.npz') as record:b={k:record[k] for k in record.files}
    p=np.sqrt(a['pressure_edges'][:-1]*a['pressure_edges'][1:]);m=a['cell_mass'];core=(m.shape[1]//2,m.shape[2]//2)
    states=dict(conditional_initial=(a['control_temperature'],a['control_vapor']/m),
        conditional_final=(a['75_temperature'],a['75_vapor']/m),stable_initial=(b['column_control_temperature'],b['column_control_vapor']/m),
        stable_final=(b['75_temperature'],b['75_vapor']/m),dry_initial=(b['dry_initial_temperature'],np.zeros_like(m)))
    arrays=dict(model_pressure_pa=p);cases={};profiles={}
    for name,(t,q) in states.items():
        refinement={}
        for step in [.04,.02,.01,.005]:
            result=diagnose_parcel(p,t,q,max_log_pressure_step=step)
            refinement[str(step)]=dict(mean_positive_j_kg=float(result.positive_buoyancy_energy_j_kg.mean()),
                maximum_positive_j_kg=float(result.positive_buoyancy_energy_j_kg.max()),mean_negative_j_kg=float(result.negative_buoyancy_energy_j_kg.mean()),
                maximum_negative_j_kg=float(result.negative_buoyancy_energy_j_kg.max()),sampled_pressure_levels=len(result.pressure_pa))
        virtual=diagnose_parcel(p,t,q,max_log_pressure_step=.005,virtual_temperature=True)
        cases[name]=dict(refinement=refinement,certificate=result.certificate,
            mean_virtual_positive_j_kg=float(virtual.positive_buoyancy_energy_j_kg.mean()),maximum_virtual_positive_j_kg=float(virtual.positive_buoyancy_energy_j_kg.max()),
            lcl_in_column=int(np.count_nonzero(result.parcel.lcl_in_column)))
        fields=dict(environment_temperature=t,environment_vapor_ratio=q,pressure=result.pressure_pa,
            parcel_temperature=result.parcel.temperature_k,parcel_vapor_ratio=result.parcel.vapor_mixing_ratio,
            buoyancy=result.buoyancy_ms2,positive=result.positive_buoyancy_energy_j_kg,negative=result.negative_buoyancy_energy_j_kg,
            lcl_pressure=result.parcel.lifting_condensation_pressure_pa)
        arrays.update({name+'_'+k:v for k,v in fields.items()});profiles[name]=result
    fig,axes=plt.subplots(2,2,figsize=(12,8));names=['conditional_initial','stable_initial','dry_initial'];labels=['Conditional moist','Saturated-stable','Dry control'];colors=['#b85938','#387966','#5d739d']
    axes[0,0].bar(labels,[float(arrays[n+'_positive'].mean()) for n in names],color=colors)
    axes[0,0].set_ylabel('Positive parcel-buoyancy integral (J/kg)');axes[0,0].set_title('Same partial model column, before circulation');axes[0,0].tick_params(axis='x',labelsize=9)
    for name,label,color in zip(names,labels,colors):
        d=profiles[name];axes[0,1].plot(d.buoyancy_ms2[:,core[0],core[1]],d.pressure_pa/100,label=label,color=color)
    axes[0,1].axvline(0,color='#777',lw=.8);axes[0,1].set_ylim(p[0]/100,p[-1]/100);axes[0,1].set_xlabel('Parcel buoyancy (m/s²)');axes[0,1].set_ylabel('Pressure (hPa)');axes[0,1].set_title('Central-column parcels');axes[0,1].legend(fontsize=8)
    d=profiles['conditional_initial'];flank=(0,0);choose=d.pressure_pa>80000
    axes[1,0].plot(d.buoyancy_ms2[choose,flank[0],flank[1]],d.pressure_pa[choose]/100,color='#b85938',label='Unsaturated flank, internal samples')
    axes[1,0].axvline(0,color='#777',lw=.8)
    lcl=arrays['conditional_initial_lcl_pressure'][flank]
    axes[1,0].axhline(lcl/100,color='#5d739d',ls='--',label='Lifting condensation pressure')
    axes[1,0].set_ylim(p[0]/100,800);axes[1,0].set_xlabel('Parcel buoyancy (m/s²)');axes[1,0].set_ylabel('Pressure (hPa)');axes[1,0].set_title('Shallow inhibition hidden by coarse endpoints');axes[1,0].legend(fontsize=8)
    axes[1,1].bar([0,1,3,4],[arrays[n+'_positive'].mean() for n in ['conditional_initial','conditional_final','stable_initial','stable_final']],color=['#b85938','#d79a77','#387966','#8ab4a4'])
    axes[1,1].set_xticks([0,1,3,4],['Conditional\ninitial','Conditional\n6 h','Stable\ninitial','Stable\n6 h'],fontsize=9);axes[1,1].set_ylabel('Mean positive parcel energy (J/kg)');axes[1,1].set_title('Conditional energy remains after the coupled run')
    for ax in axes.flat:ax.grid(alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('Parcel stability identifies the unresolved moist-convection regime',fontsize=14)
    fig.text(.5,.012,'Lowest model-cell parcels • approximately 965–399 hPa only • dry/dilute primary diagnostic • not full-atmosphere CAPE/CIN or convection closure',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(out/'parcel_stability.png',dpi=155);plt.close(fig)
    np.savez_compressed(out/'fields.npz',**arrays)
    sources=['rotclimate/parcel_stability.py','rotclimate/column_thermodynamics.py','rotclimate/moist_enthalpy.py','scripts/audit_parcel_stability.py',
        'output/pressure_moist_20261029/verification.json','output/pressure_moist_20261029/controls_verification.json',
        'output/pressure_moist_20261029/fields.npz','output/pressure_moist_20261029/controls_fields.npz']
    receipt=dict(status='partial_column_parcel_stability_audit',actual_earth_integrations=0,new_coupled_integrations=0,
        physics_or_atlas_adoption=False,cases=cases,configuration=dict(pressure_source='Geometric centers of prior10 pressure cells',
            source='Lowest selected model cell after initial local phase adjustment; no invented surface parcel',
            log_pressure_steps=[.04,.02,.01,.005],primary_virtual_temperature=False,
            environment_interpolation='Log temperature and linear vapor mixing ratio in log pressure',
            parcel='Pseudoadiabatic, actual temperature-dependent gas/liquid enthalpies and saturation derivatives; dry/dilute compression'),
        sources={n:file_hash(ROOT/n) for n in sources},raw_fields_sha256=file_hash(out/'fields.npz'),image_sha256=file_hash(out/'parcel_stability.png'),
        scope='Reused manufactured pressure-coordinate controls, no Earth validation or parameter fitting. Partial-column positive/negative integrals, not full-atmosphere CAPE/CIN. No convection closure or adoption.')
    write_json(out/'verification.json',receipt);print(json.dumps(cases,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);run(ap.parse_args().out.resolve())

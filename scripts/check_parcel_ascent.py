"""Frozen manufactured parcel thermodynamics, with no actual Earth runs."""
from pathlib import Path
import argparse,json,sys
from itertools import product
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiments.parcel_ascent import ascend,specific_from_relative_humidity
from rotclimate.column_thermodynamics import RD,CP
from local_benchmark_protocol import file_hash,freeze,write_json


def run(plan_path,out):
    plan=json.loads(plan_path.read_text());out.mkdir(parents=True,exist_ok=True)
    sources=[plan_path,Path(__file__),ROOT/'experiments/parcel_ascent.py',
        ROOT/'rotclimate/column_thermodynamics.py',ROOT/'scripts/local_benchmark_protocol.py',
        ROOT/plan['parent'],ROOT/'output/independent_water_20261026/verification.json']
    identity=freeze(out/'protocol.json',dict(plan=plan,sources={str(p.relative_to(ROOT)):file_hash(p) for p in sources}))
    rows=[];arrays={}
    for index,(temperature,rh,endpoint) in enumerate(product(plan['temperature_k'],plan['relative_humidity'],plan['endpoint_pressure_pa'])):
        q=float(specific_from_relative_humidity(temperature,plan['surface_pressure_pa'],rh))
        row=dict(temperature_k=temperature,relative_humidity=rh,endpoint_pressure_pa=endpoint,
                 initial_specific_humidity=q,initial_vapor_kg_kg_dry=q/(1-q),resolutions=[],failures=[])
        runs=[]
        for count in plan['steps']:
            result=ascend(temperature,plan['surface_pressure_pa'],q,endpoint,steps=count);runs.append(result)
            key=f'case{index:02d}_steps{count}'
            fields=dict(pressure_pa=result.pressure_pa,temperature_k=result.temperature_k,
                vapor_kg_kg_dry=result.vapor_kg_kg_dry,condensed_kg_kg_dry=result.condensed_kg_kg_dry,
                pressure_work_j_kg_dry=result.pressure_work_j_kg_dry,
                first_law_residual_j_kg_dry=result.first_law_residual_j_kg_dry)
            arrays.update({key+'_'+n:v for n,v in fields.items()})
            water=float(np.max(np.abs(result.vapor_kg_kg_dry+result.condensed_kg_kg_dry-q/(1-q))))
            energy=float(np.max(np.abs(result.first_law_residual_j_kg_dry)))
            if water>plan['water_absolute_tolerance_kg_kg_dry']:row['failures'].append(str(count)+': water equation')
            if energy>plan['maximum_first_law_residual_j_kg_dry']:row['failures'].append(str(count)+': first law')
            if (result.condensed_kg_kg_dry < -plan['water_absolute_tolerance_kg_kg_dry']).any() or (np.diff(result.condensed_kg_kg_dry)<-plan['water_absolute_tolerance_kg_kg_dry']).any():
                row['failures'].append(str(count)+': nonphysical condensation')
            row['resolutions'].append(dict(steps=count,temperature_k=float(result.temperature_k[-1]),
                vapor_kg_kg_dry=float(result.vapor_kg_kg_dry[-1]),condensed_kg_kg_dry=float(result.condensed_kg_kg_dry[-1]),
                lcl_pressure_pa=result.lcl_pressure_pa,maximum_water_residual_kg_kg_dry=water,
                maximum_first_law_residual_j_kg_dry=energy))
        for coarse in runs[:-1]:
            if abs(coarse.temperature_k[-1]-runs[-1].temperature_k[-1])>plan['endpoint_temperature_convergence_k']:
                row['failures'].append('Endpoint temperature quadrature')
            if abs(coarse.condensed_kg_kg_dry[-1]-runs[-1].condensed_kg_kg_dry[-1])>plan['endpoint_condensation_convergence_kg_kg_dry']:
                row['failures'].append('Endpoint condensation quadrature')
        row['passed']=not row['failures'];rows.append(row)
    raw=out/'paths.npz'
    with raw.open('wb') as stream:np.savez_compressed(stream,**arrays)
    fig,axes=plt.subplots(1,3,figsize=(14,6),constrained_layout=True)
    colors=['#426f98','#b7753c','#4b9061']
    for rh,color in zip(plan['relative_humidity'],colors):
        index=next(i for i,r in enumerate(rows) if r['temperature_k']==300 and r['relative_humidity']==rh and r['endpoint_pressure_pa']==30000)
        key=f'case{index:02d}_steps{plan["steps"][-1]}_';pressure=arrays[key+'pressure_pa']/100
        axes[0].plot(arrays[key+'temperature_k']-273.15,pressure,color=color,label=f'Initial RH {rh:.0%}')
        axes[1].plot(arrays[key+'vapor_kg_kg_dry']/rows[index]['initial_vapor_kg_kg_dry']*100,pressure,color=color)
        lcl=rows[index]['resolutions'][-1]['lcl_pressure_pa']
        if lcl is not None:axes[0].plot(300*(lcl/plan['surface_pressure_pa'])**(RD/CP)-273.15,lcl/100,'o',color=color,ms=5)
        for temperature,style in zip(plan['temperature_k'],['--','-']):
            selected=[r for r in rows if r['temperature_k']==temperature and r['relative_humidity']==rh]
            axes[2].plot([r['endpoint_pressure_pa']/100 for r in selected],
                [r['resolutions'][-1]['condensed_kg_kg_dry']*1000 for r in selected],style,marker='o',color=color,
                label=f'{temperature-273.15:.0f}°C, RH {rh:.0%}')
    p=np.linspace(300,1000,100)
    axes[0].plot(300*(p/1000)**(RD/CP)-273.15,p,color='#777',ls=':',label='Dry analytic path')
    for ax in axes[:2]:
        ax.set(ylim=(1000,300),ylabel='Pressure (hPa)');ax.grid(alpha=.15)
        for pressure in [750,500]:ax.axhline(pressure,color='#aaa',lw=.7,ls='--')
    axes[0].set(title='300K parcels · dry to LCL, then moist',xlabel='Parcel temperature (°C)')
    axes[0].legend(frameon=False,fontsize=8)
    axes[1].set(title='Vapor retained by the rising dry-air parcel',xlabel='Remaining vapor / initial vapor (%)',xlim=(0,102))
    axes[2].set(title='All18 declared endpoints · pressure matters',xlabel='Detrainment endpoint pressure (hPa)',
        ylabel='Immediate condensate (g / kg dry air)',xlim=(800,250));axes[2].grid(alpha=.15);axes[2].legend(frameon=False,fontsize=8)
    fig.suptitle('Parcel cooling and condensation · isolated thermodynamics',fontsize=16)
    fig.supxlabel('Constant dry cp and latent heat; exact dry segment and root-located lifting condensation level (dots).\n'
        'Liquid-only pseudoadiabatic approximation, no entrainment/ice/re-evaporation or environmental heat coupling. Zero Earth integrations.',fontsize=9)
    picture=out/'parcel_paths.png';fig.savefig(picture,dpi=145);plt.close(fig)
    final=dict(complete=True,identity=identity,all_checks_passed=all(r['passed'] for r in rows),manufactured_cases=len(rows),
        numerical_paths=len(rows)*len(plan['steps']),climate_integrations=0,physics_or_atlas_adoption=False,
        rows=rows,arrays_sha256=file_hash(raw),images_sha256={picture.name:file_hash(picture)},
        maximum_first_law_residual_j_kg_dry=max(s['maximum_first_law_residual_j_kg_dry'] for r in rows for s in r['resolutions']),
        maximum_water_residual_kg_kg_dry=max(s['maximum_water_residual_kg_kg_dry'] for r in rows for s in r['resolutions']))
    write_json(out/'review.json',final)
    print(json.dumps({k:v for k,v in final.items() if k!='rows'},indent=2))
    if not final['all_checks_passed']:raise SystemExit('Preserve failed manufactured paths; no climate coupling')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=ROOT/'calibration/parcel_ascent_20261026/plan.json')
    parser.add_argument('--out',type=Path,default=ROOT/'output/parcel_ascent_20261026')
    args=parser.parse_args();run(args.plan.resolve(),args.out.resolve())

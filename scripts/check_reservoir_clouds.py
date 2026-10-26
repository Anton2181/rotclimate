"""Frozen layer-capacity condensation experiment; manufactured domain only."""
from pathlib import Path
import json,sys,subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from local_benchmark_protocol import freeze,file_hash,write_json
from earth_benchmark import load_params
from rotclimate.layer_transport import return_branches
from experiments.two_reservoir_transport import VerticalTransport
from experiments.reservoir_clouds import solve_layer_rain


def main():
    path=ROOT/'calibration/reservoir_clouds_20261026/plan.json';plan=json.loads(path.read_text())
    out=ROOT/'output/reservoir_clouds_20261026';out.mkdir(exist_ok=True);parent=ROOT/plan['parent']
    if (out/'review.json').exists():raise ValueError('Preserve completed/failed experiment')
    old=json.loads((parent/'protocol.json').read_text());prior=json.loads((parent/'review.json').read_text())
    for name,digest in old['sources'].items():
        if file_hash(ROOT/name)!=digest:raise ValueError('Changed parent control source: '+name)
    for name,row in prior['records'].items():
        if json.loads((parent/f'{name}.json').read_text())!=row or row['status']!='passed':raise ValueError('Changed parent control result')
    sources=[path,Path(__file__),ROOT/'experiments/reservoir_clouds.py',ROOT/'tests/test_reservoir_clouds.py',parent/'protocol.json',parent/'review.json']
    hashes=dict(old['sources']);hashes.update({str(p.relative_to(ROOT)):file_hash(p) for p in sources})
    identity=freeze(out/'protocol.json',dict(plan=plan,sources=hashes,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))
    n=plan['numerics'];p=load_params(ROOT/plan['physics']).replace(**{k:v for k,v in n.items() if not k.startswith('linear_')})
    shape=tuple(plan['shape']);dx=plan['cell_km']*1000.;x=np.arange(shape[1])*plan['cell_km']
    u=np.tile(plan['lower_wind_amplitude_ms']*np.sin(2*np.pi*x/x[-1]),(shape[0],1));v=np.zeros(shape);mass=np.ones(shape)
    branches,_,_=return_branches(u,v,v,v,plan['capacity_upper_lower_q_ratio']);fractions=np.array([b[0] for b in branches])
    source=np.zeros((2,)+shape);source[0]=plan['source_mm_day']/86400.
    boundary=np.broadcast_to((plan['boundary_column_water_mm']*fractions)[:,None,None],source.shape)
    closure=dict(conv=p.convective_rain,r0=p.convective_rh,evap=p.subcloud_evaporation,T=np.full(shape,plan['prescribed_temperature_C']),fT=np.full(shape,plan['convective_temperature_factor']))
    drying=1/(plan['drying_days']*86400.);rows={};profiles={};center=shape[0]//2
    for name,settings in plan['profiles'].items():
        row=dict(identity=identity,name=name,status='running')
        try:
            days=settings['mixing_days'];rate=0. if days is None else 1/(days*86400.)
            op=VerticalTransport(mass,(u,v),(plan['upper_wind_factor']*u,v),dx,lower_fraction=plan['lower_mass_fraction'],mixing_rate=rate)
            result=solve_layer_rain(op,p,source,plan['saturation_mm'],plan['dynamics'],boundary,fractions,
                instability=plan['instability'],drying=drying,closure=closure)
            W=result.water.sum(0);P=result.layer_rain.sum(0);q=result.water/op.layer_mass;ratio=q[1]/q[0]
            row.update(status='passed',iterations=result.iterations,scaled_residual=result.scaled_residual,
                maximum_absolute_residual_mm_day=result.maximum_absolute_residual_mm_day,
                boundary_supply_cell_mm_day=result.boundary_supply_cell_mm_day,
                integrated_equation_residual_cell_mm_day=float(((source-drying*result.water)*86400.-result.layer_rain)[:,1:-1,1:-1].sum())+result.boundary_supply_cell_mm_day,
                linear_certificate=result.linear_certificate,maximum_column_water_mm=float(W[1:-1,1:-1].max()),
                maximum_rain_mm_day=float(P[1:-1,1:-1].max()),mean_rain_mm_day=float(P[1:-1,1:-1].mean()),
                minimum_upper_lower_q_ratio=float(ratio[1:-1,1:-1].min()),maximum_upper_lower_q_ratio=float(ratio[1:-1,1:-1].max()))
            profiles[name]=dict(x_km=x[1:-1].tolist(),water_mm=W[center,1:-1].tolist(),rain_mm_day=P[center,1:-1].tolist(),
                upper_lower_q_ratio=ratio[center,1:-1].tolist(),lower_rain_mm_day=result.layer_rain[0,center,1:-1].tolist(),upper_rain_mm_day=result.layer_rain[1,center,1:-1].tolist())
        except Exception as error:
            row.update(status='failed',error=str(error));write_json(out/f'{name}.json',row)
            write_json(out/'review.json',dict(complete=False,identity=identity,records={**rows,name:row}));raise
        if any(file_hash(ROOT/k)!=v for k,v in hashes.items()):raise ValueError('Frozen layer-cloud inputs changed')
        rows[name]=row;write_json(out/f'{name}.json',row)
    write_json(out/'review.json',dict(complete=True,identity=identity,scope=plan['publication'],records=rows,profiles=profiles,
        capacity_fractions=fractions.tolist(),verified_parent_review_sha256=file_hash(parent/'review.json'),
        all_numerical_checks_passed=True,climate_integrations=0,physics_or_atlas_adoption=False))
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()

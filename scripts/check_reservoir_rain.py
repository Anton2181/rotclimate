"""Frozen manufactured test of reservoir transport and actual column rain law."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from local_benchmark_protocol import freeze,file_hash,write_json
from earth_benchmark import load_params
from rotclimate.layer_transport import return_branches,LayerFluxSolver
from rotclimate.moisture import solve_moisture
from rotclimate.transport import moisture_terms,flux_budget
from experiments.two_reservoir_transport import VerticalTransport
from experiments.condensing_reservoirs import solve_column_rain


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=ROOT/'calibration/reservoir_rain_20261026/plan.json')
    parser.add_argument('--out',type=Path,default=ROOT/'output/reservoir_rain_20261026')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    plan=json.loads(args.plan.read_text());n=plan['numerics']
    sources=[args.plan.resolve(),ROOT/plan['physics'],Path(__file__),ROOT/'experiments/two_reservoir_transport.py',
        ROOT/'experiments/condensing_reservoirs.py',ROOT/'rotclimate/moisture.py',ROOT/'rotclimate/layer_transport.py',
        ROOT/'rotclimate/transport.py',ROOT/'rotclimate/solver.py']
    hashes={str(p.relative_to(ROOT)):file_hash(p) for p in sources}
    identity=freeze(out/'protocol.json',dict(plan=plan,sources=hashes))
    if (out/'review.json').exists():raise ValueError('Preserve completed/failed experiment; choose a fresh output')
    p=load_params(ROOT/plan['physics']).replace(**{k:v for k,v in n.items() if not k.startswith('linear_')})
    shape=tuple(plan['shape']);dx=plan['cell_km']*1000.;x=np.arange(shape[1])*plan['cell_km']
    u=np.tile(plan['lower_wind_amplitude_ms']*np.sin(2*np.pi*x/x[-1]),(shape[0],1));v=np.zeros(shape)
    mass=np.ones(shape);source=np.zeros((2,)+shape);source[0]=plan['source_mm_day']/86400.
    branches,uq,vq=return_branches(u,v,v,v,plan['boundary_upper_lower_q_ratio'])
    weights=np.array([b[0] for b in branches]);boundary=np.broadcast_to((plan['boundary_column_water_mm']*weights)[:,None,None],source.shape)
    drying=1/(plan['drying_days']*86400.);saturation=np.full(shape,plan['saturation_mm'])
    closure=dict(conv=p.convective_rain,r0=p.convective_rh,evap=p.subcloud_evaporation,
                 T=np.full(shape,plan['prescribed_temperature_C']),fT=np.full(shape,plan['convective_temperature_factor']))
    rows={};profiles={};center=shape[0]//2
    for name,settings in plan['profiles'].items():
        row=dict(identity=identity,name=name,status='running',scope='Manufactured nonlinear moisture test, not an Earth climate integration')
        try:
            if settings['type']=='fixed_ratio':
                solver=LayerFluxSolver(*shape,dx,column_mass=mass);solver.set_layers(branches)
                solver.rtol=n['linear_rtol'];solver.max_iter=n['linear_max_iter'];solver.require_convergence=True;solver.recover=True
                fixed=solve_moisture(solver,p,uq,vq,np.zeros(shape),np.zeros(shape),source.sum(0),saturation,
                    np.full(shape,plan['dynamics']),plan['instability'],boundary.sum(0),boundary.sum(0).copy(),sink=np.full(shape,drying),closure=closure)
                if not fixed.converged:raise ValueError('Fixed-profile nonlinear equation failed')
                W=fixed.water;P=fixed.rain
                terms=moisture_terms(W,uq,vq,dx,p.moisture_diffusion,(source.sum(0)-drying*W)*86400.,P,0.,W,form='flux',layers=branches,mass=mass)
                ledger=flux_budget(W,uq,vq,dx,p.moisture_diffusion,(source.sum(0)-drying*W)*86400.,P,0.,W,layers=branches,mass=mass)
                row.update(iterations=fixed.iterations,scaled_residual=fixed.scaled_residual,
                    maximum_absolute_residual_mm_day=float(np.nanmax(terms['absolute_residual'])),boundary_supply_cell_mm_day=ledger['advection_boundary_supply_cell_mm_day']+ledger['diffusion_boundary_supply_cell_mm_day'],
                    integrated_equation_residual_cell_mm_day=ledger['equation_residual_cell_mm_day'])
                ratio=np.full(shape,settings['upper_lower_q_ratio'])
            else:
                days=settings['mixing_days'];rate=0. if days is None else 1/(days*86400.)
                op=VerticalTransport(mass,(u,v),(plan['upper_wind_factor']*u,v),dx,lower_fraction=plan['lower_mass_fraction'],mixing_rate=rate)
                result=solve_column_rain(op,p,source,saturation,plan['dynamics'],boundary,
                    instability=plan['instability'],drying=drying,closure=closure)
                W=result.water.sum(0);P=result.layer_rain.sum(0);q=result.water/op.layer_mass;ratio=q[1]/q[0]
                row.update(iterations=result.iterations,scaled_residual=result.scaled_residual,
                    maximum_absolute_residual_mm_day=result.maximum_absolute_residual_mm_day,
                    boundary_supply_cell_mm_day=result.boundary_supply_cell_mm_day,
                    integrated_equation_residual_cell_mm_day=float(((source-drying*result.water)*86400.-result.layer_rain)[:,1:-1,1:-1].sum())+result.boundary_supply_cell_mm_day,
                    linear_certificate=result.linear_certificate)
            row.update(status='passed',maximum_column_water_mm=float(W[1:-1,1:-1].max()),maximum_rain_mm_day=float(P[1:-1,1:-1].max()),
                mean_rain_mm_day=float(P[1:-1,1:-1].mean()),minimum_upper_lower_q_ratio=float(ratio[1:-1,1:-1].min()),maximum_upper_lower_q_ratio=float(ratio[1:-1,1:-1].max()))
            if not np.isfinite(row['scaled_residual']) or row['scaled_residual']>p.moisture_residual_tol:raise ValueError('Missing actual nonlinear certificate')
            profiles[name]=dict(x_km=x[1:-1].tolist(),water_mm=W[center,1:-1].tolist(),rain_mm_day=P[center,1:-1].tolist(),upper_lower_q_ratio=ratio[center,1:-1].tolist())
        except Exception as error:
            row.update(status='failed',error=str(error));write_json(out/f'{name}.json',row)
            write_json(out/'review.json',dict(complete=False,identity=identity,records={**rows,name:row},physics_or_atlas_adoption=False));raise
        if any(file_hash(ROOT/k)!=v for k,v in hashes.items()):raise ValueError('Frozen nonlinear inputs changed')
        rows[name]=row;write_json(out/f'{name}.json',row)
    review=dict(complete=True,identity=identity,scope=plan['publication'],records=rows,profiles=profiles,
        all_numerical_checks_passed=True,climate_integrations=0,physics_or_atlas_adoption=False)
    write_json(out/'review.json',review)
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()

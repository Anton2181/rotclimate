"""Small paired backend benchmark; no climate integration or physical retune."""
from pathlib import Path
from time import perf_counter
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from experiments.two_reservoir_transport import VerticalTransport
from experiments.reservoir_block_solver import solve_block
from local_benchmark_protocol import file_hash,freeze,write_json


def case(shape):
    y,x=np.indices(shape);mass=.75+.15*np.sin(x/11)*np.cos(y/13)
    u=6+2*np.sin(x/9);v=1.5*np.cos(y/8)
    op=VerticalTransport(mass,(u,v),(-u/3,-v/3),56000.,mixing_rate=1/(5*86400.))
    source=np.stack([np.full(shape,2e-5),np.full(shape,5e-6)])
    reaction=np.broadcast_to(np.array([1/86400.,1/(3*86400.)])[:,None,None],source.shape)
    return op,source,reaction,4*op.layer_mass


def main():
    out=ROOT/'output/reservoir_blocks_20261026';out.mkdir(exist_ok=True)
    plan=dict(shapes=[[24,30],[48,64],[72,96]],cell_km=56,rtol=1e-9,max_iter=2000,diffusion=60000.,repetitions=2,
        scope='Numerical backend only. Same operator/source/reaction/boundaries, alternating timing order after separate JIT warmup. No climate integrations or whole-season speed claim.')
    sources=[Path(__file__),ROOT/'experiments/two_reservoir_transport.py',ROOT/'experiments/reservoir_block_solver.py',ROOT/'rotclimate/layer_transport.py',ROOT/'rotclimate/transport.py',ROOT/'tests/test_reservoir_block_solver.py']
    identity=freeze(out/'protocol.json',dict(plan=plan,sources={str(p.relative_to(ROOT)):file_hash(p) for p in sources}))
    if (out/'review.json').exists():raise ValueError('Preserve previous backend benchmark')
    op,s,r,b=case((5,7));solve_block(op,s,r,b,diffusion=60000.,rtol=1e-9,max_iter=2000)
    rows=[]
    for shape in plan['shapes']:
        op,s,r,b=case(tuple(shape));times={'sparse':[],'block':[]};certificates=[];differences=[]
        for repetition in range(plan['repetitions']):
            results={}
            for method in (['sparse','block'] if repetition==0 else ['block','sparse']):
                start=perf_counter()
                if method=='sparse':value,c=op.solve(s,r,b,diffusion=60000.)
                else:value,c=solve_block(op,s,r,b,diffusion=60000.,rtol=plan['rtol'],max_iter=plan['max_iter'])
                times[method].append(perf_counter()-start);results[method]=value
                if method=='block':certificates.append(c)
            difference=float(np.max(np.abs(results['sparse']-results['block'])));differences.append(difference)
            if difference>1e-6:raise ValueError('Backend field mismatch exceeds1e-6mm')
            terms,boundary=op.terms(results['block'],diffusion=60000.)
            residual=s[:,1:-1,1:-1]+terms-(r*results['block'])[:,1:-1,1:-1]
            if np.max(np.abs(residual))>1e-10:raise ValueError('Independent face-ledger error')
        row=dict(shape=shape,unknowns=2*int(np.prod(shape)),seconds=times,
            median_sparse_seconds=float(np.median(times['sparse'])),median_block_seconds=float(np.median(times['block'])),
            maximum_field_difference_mm=max(differences),block_certificates=certificates)
        rows.append(row)
    review=dict(complete=True,identity=identity,scope=plan['scope'],records=rows,climate_integrations=0,physics_or_atlas_adoption=False)
    write_json(out/'review.json',review);print(json.dumps(rows,indent=2))


if __name__=='__main__':main()

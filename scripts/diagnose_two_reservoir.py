"""Manufactured two-reservoir transport example; not an Earth climate score."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiments.two_reservoir_transport import VerticalTransport
from rotclimate.layer_transport import LayerFluxSolver,return_branches
from local_benchmark_protocol import file_hash,write_json


def main():
    out=ROOT/'output/two_reservoir_20261026';out.mkdir(exist_ok=True)
    shape=(7,101);dx=20000.;x=np.arange(shape[1])*dx/1000
    lower=np.tile(8*np.sin(2*np.pi*x/x[-1]),(shape[0],1));zero=np.zeros(shape)
    mass=np.ones(shape);upper=-lower/3
    op=VerticalTransport(mass,(lower,zero),(upper,zero),dx,mixing_rate=1/(5*86400.))
    branches,uq,vq=return_branches(lower,zero,zero,zero,.2)
    weights=np.array([b[0] for b in branches])
    source=np.zeros((2,)+shape);source[0]=1/86400.
    reaction=np.broadcast_to(np.array([1/(10*86400.),1/(3*86400.)])[:,None,None],source.shape)
    boundary=np.broadcast_to((14*weights)[:,None,None],source.shape)
    water,certificate=op.solve(source,reaction,boundary)
    terms,supply=op.terms(water)
    residual=source[:,1:-1,1:-1]+terms-(reaction*water)[:,1:-1,1:-1]
    if np.max(np.abs(residual))>1e-15:raise ValueError('Independent reservoir ledger failed')
    no_mix=VerticalTransport(mass,(lower,zero),(upper,zero),dx)
    unmixed,unmixed_certificate=no_mix.solve(source,reaction,boundary)
    fixed=LayerFluxSolver(*shape,dx,column_mass=mass);fixed.set_layers(branches)
    fixed.rtol=1e-11;fixed.max_iter=10000;fixed.require_convergence=True;fixed.recover=True
    sink=(weights[:,None,None]*reaction).sum(0)
    amount=fixed.solve(uq,vq,0.,sink,source.sum(0),boundary.sum(0))
    row=shape[0]//2;interior=slice(1,-1);xx=x[interior]
    dynamic_rain=(reaction*water).sum(0)*86400.;fixed_rain=sink*amount*86400.
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    axes[0,0].plot(x,lower[row],label='Lower air');axes[0,0].plot(x,upper[row],label='Upper return')
    axes[0,0].set(title='Prescribed opposing winds; balanced dry column',ylabel='Eastward wind (m/s)')
    ratio=(water[1]/op.layer_mass[1])/(water[0]/op.layer_mass[0])
    ratio_unmixed=(unmixed[1]/op.layer_mass[1])/(unmixed[0]/op.layer_mass[0])
    axes[0,1].plot(xx,ratio[row,interior],color='#398f8b',label='Separate,5-day mixing')
    axes[0,1].plot(xx,ratio_unmixed[row,interior],color='#b28b41',label='Separate, no mixing')
    axes[0,1].axhline(.2,color='#a25b6d',ls='--',label='Imposed ratio0.2')
    axes[0,1].set(title='Vertical humidity becomes a solved field',ylabel='Upper/lower mixing-ratio ratio')
    axes[1,0].plot(xx,dynamic_rain[row,interior],color='#398f8b',label='Separate,5-day mixing')
    axes[1,0].plot(xx,(reaction*unmixed).sum(0)[row,interior]*86400.,color='#b28b41',label='Separate, no mixing')
    axes[1,0].plot(xx,fixed_rain[row,interior],color='#a25b6d',ls='--',label='Imposed ratio0.2')
    axes[1,0].set(title='Identical simple linear removal rates',ylabel='Linear removal (mm/day)')
    axes[1,1].plot(xx,water.sum(0)[row,interior],color='#398f8b',label='Separate,5-day mixing')
    axes[1,1].plot(xx,unmixed.sum(0)[row,interior],color='#b28b41',label='Separate, no mixing')
    axes[1,1].plot(xx,amount[row,interior],color='#a25b6d',ls='--',label='Imposed ratio0.2')
    axes[1,1].set(title='Water responds to vertical transport',ylabel='Total column water (mm)')
    for ax in axes.ravel():
        ax.set_xlabel('Synthetic domain x (km)');ax.legend(frameon=False,fontsize=9);ax.grid(alpha=.15)
    fig.suptitle('Two-reservoir transport prototype · manufactured example',fontsize=16)
    fig.supxlabel('Same flat synthetic domain,1mm/day lower supply, layer boundary water and linear sinks; vertical mixing separately controlled.\n'
        'Removal times10/3days are illustrative linear sinks, not a cloud model or calibrated rainfall. No observed climate is scored.',fontsize=9)
    image=out/'vertical_transport.png';fig.savefig(image,dpi=145);plt.close(fig)
    values=dict(x_km=xx.tolist(),lower_wind_ms=lower[row,interior].tolist(),upper_wind_ms=upper[row,interior].tolist(),
        solved_upper_lower_q_ratio=ratio[row,interior].tolist(),no_mixing_upper_lower_q_ratio=ratio_unmixed[row,interior].tolist(),
        separate_reservoir_removal_mm_day=dynamic_rain[row,interior].tolist(),
        fixed_ratio_removal_mm_day=fixed_rain[row,interior].tolist(),separate_reservoir_water_mm=water.sum(0)[row,interior].tolist(),
        fixed_ratio_water_mm=amount[row,interior].tolist())
    report=dict(scope='Manufactured linear transport example only; not coupled ClimateModel and no Earth accuracy result',
        shape=shape,cell_km=dx/1000,lower_mass_fraction=.25,vertical_mixing_days=5.,linear_removal_days=[10.,3.],
        strict_solution=certificate,unmixed_solution=unmixed_certificate,boundary_water_mm=(14*weights).tolist(),
        maximum_absolute_local_ledger_residual_mm_day=float(np.max(np.abs(residual)))*86400.,
        total_boundary_water_supply_cell_mm_day=float(supply.sum())*86400.,
        total_source_minus_removal_cell_mm_day=float((source-reaction*water)[:,1:-1,1:-1].sum())*86400.,
        sources_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in [Path(__file__),ROOT/'experiments/two_reservoir_transport.py',ROOT/'rotclimate/layer_transport.py',ROOT/'rotclimate/transport.py',ROOT/'tests/test_vertical_transport.py']},
        image_sha256=file_hash(image),profile=values,
        limitations='No independent temperatures, saturation/cloud microphysics, latent heating, storms or momentum. Dry-layer masses are fixed; vertical air exchange is diagnosed from steady continuity. Coupling to climate and unchanged Earth/world gates remains required.')
    write_json(out/'diagnostic.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['profile','sources_sha256']},indent=2))


if __name__=='__main__':main()

"""Fixed calendar-month regional rainfall trial with explicit wet/dry starts."""
from pathlib import Path
import argparse,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import extended_surface_spinup as daily
import lower_cell_resolution_pilot as grid
from local_benchmark_protocol import write_json,file_hash
from rotclimate.phase_backend import bind_dependencies
from rotclimate.surface_coupling import SurfaceState,checked_surface,receive_precipitation


def prepare(plan,region):
    values=list(grid.prepare(plan,region));base,a,model=values[:3];p=plan['surface']
    # Static refinement files contain the old wet surface. Rebuild either
    # branch from the common original ground T and declared starting store,
    # then return the common actual conversion rain/enthalpy exactly once.
    raw_temperature=a['archived_surface_temperature_c']+273.15+plan['source_lapse_k_m']*a['elevation']
    store=np.where(a['land'],p['land_initial_liquid_kg_m2'],p['ocean_initial_liquid_kg_m2'])
    surface=checked_surface(SurfaceState(raw_temperature,store,p['substrate_capacity_j_m2_k']),model.shape)
    values[4]=receive_precipitation(surface,a['initial_conversion_rain'],a['initial_conversion_rain_enthalpy'])
    base=dict(base,regions={k:dict(v) for k,v in base['regions'].items()},maximum_convective_sweeps=plan['maximum_convective_sweeps'])
    base['regions'][region]['model_day']=plan['calendar']['integration_start_day'];values[0]=base
    return tuple(values)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--preflight',action='store_true');a=p.parse_args()
    run=bind_dependencies(daily.run,prepare=prepare,advance_surface_coupled=grid.SELECTED.surface_coupled,advance_boundary_with_convection=grid.SELECTED.advance_with_convection)
    run(a.plan,a.out,a.preflight)
    if not a.preflight:
        source=a.out/'verification.json';source.rename(a.out/'inherited_driver_receipt.json');r=json.loads((a.out/'inherited_driver_receipt.json').read_text());plan=json.loads(a.plan.read_text())
        r.update(status='calendar_month_regional_rainfall_trial_finished',scope='Fixed fourteen-day prelude then complete declared Gregorian month; daily checkpoints, explicit initial water and fixed simulated monthly lateral state. Prelude is not assumed sufficient to erase initialization. No observed wind/humidity or rainfall forcing, no calibration/adoption.',calendar=plan['calendar'],inherited_driver_receipt_sha256=file_hash(a.out/'inherited_driver_receipt.json'))
        write_json(a.out/'verification.json',r)

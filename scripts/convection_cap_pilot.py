"""Frozen fine-grid 24h controls with increased solver work, unchanged physics."""
from pathlib import Path
import argparse,json,sys,time
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import lower_cell_resolution_pilot as grid
from rotclimate.phase_backend import bind_dependencies


def prepare(plan,region):
    values=list(grid.prepare(plan,region))
    cap=plan['maximum_convective_sweeps']
    if not isinstance(cap,int) or isinstance(cap,bool) or cap<64:raise ValueError('Need an explicit conservative solver work cap')
    values[0]=dict(values[0],maximum_convective_sweeps=cap)
    values[2].research_case_region=region
    return tuple(values)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--preflight',action='store_true');a=p.parse_args()
    timings=[]
    def timed(*args,**kwargs):
        record=dict(region=args[0].research_case_region,dt_s=args[3],completed=False);start=time.perf_counter()
        try:
            result=grid.SELECTED.surface_coupled(*args,**kwargs);record['completed']=True
            closure=result.certificate['dynamics_before_surface_return']['convective_adjustment']
            record.update(convective_sweeps=closure['sweeps'],target_converged=closure['converged'],remaining_target_interfaces=closure['remaining_active_interfaces'])
            return result
        except Exception as error:
            record['error']=repr(error);raise
        finally:
            record['seconds']=time.perf_counter()-start;timings.append(record)
            if len(timings)%24==0:(a.out/'coupled_timings_live.json').write_text(json.dumps(dict(calls=timings,scope='In-flight observations only; future calls are not outcomes.'),indent=2)+'\n')
    selected=replace(grid.SELECTED,surface_coupled=timed)
    run=bind_dependencies(grid.run,prepare=prepare,SELECTED=selected);run(a.plan,a.out,a.preflight)
    if not a.preflight:(a.out/'coupled_timings.json').write_text(json.dumps(dict(calls=timings,scope='All coupled calls, including failed attempts; timing includes certificate extraction, excludes preparation and file I/O. No timing gate or confidence interval.'),indent=2)+'\n')
    if a.preflight:
        result=json.loads(a.out.read_text());plan=json.loads(a.plan.read_text());result['maximum_convective_sweeps']={spec['name']:json.loads((ROOT/spec['plan']).read_text())['maximum_convective_sweeps'] for spec in plan['cases']};a.out.write_text(json.dumps(result,indent=2)+'\n')

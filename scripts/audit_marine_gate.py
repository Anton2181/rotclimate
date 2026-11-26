"""Integration-free audit of e91 geometry using already saved climate fields."""
import ast
import csv
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
from scipy import ndimage as ndi

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from marine_access import production_geometry,backtrace,STATUS,SEA,EXIT,CALM,LIMIT
from local_benchmark_protocol import file_hash,freeze,write_json
from rotclimate.koppen import monthly_weights

PLAN=ROOT/'calibration/marine_gate_audit_20261126/plan.json'
OUT=ROOT/'output/marine_gate_audit_20261126'
PARENT=ROOT/'output/somalia_mechanism_20261126'
TRACE=ROOT/'output/somalia_transport_trace_20261126'
CAPTURE=ROOT/'output/somalia_marine_exchange_trace_20261126'


def assert_actual_geometry(land,g,p,source):
    """Execute only the real e91 pure-geometry AST, never construct/run a model."""
    tree=ast.parse(source.read_text())
    candidates=[n for n in ast.walk(tree) if isinstance(n,ast.If) and
        isinstance(n.test,ast.Compare) and isinstance(n.test.left,ast.Attribute) and
        isinstance(n.test.left.value,ast.Name) and n.test.left.value.id=='p' and n.test.left.attr=='inflow_gain' and
        any(isinstance(a,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='inflow_dir' for t in a.targets) for a in n.body)]
    assert len(candidates)==1
    code=compile(ast.Module(body=candidates,type_ignores=[]),str(source),'exec')
    obj=SimpleNamespace();env=dict(np=np,ndi=ndi,p=SimpleNamespace(**p),g=SimpleNamespace(land=land,cell_km=56.),self=obj)
    exec(code,env)
    for a,b in [(g['normal_east'],obj.inflow_dir[0]),(g['normal_north'],obj.inflow_dir[1]),
                (g['reach'],obj.inflow_reach),(g['nearest_r'],obj.inflow_near[0]),(g['nearest_c'],obj.inflow_near[1])]:
        np.testing.assert_array_equal(a,b)


def main():
    assert not (OUT/'results.json').exists(),'Preserve completed saved-field audit'
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    plan=json.loads(PLAN.read_text());p=json.loads((ROOT/'calibration/local_accuracy_20261023/r58_params.json').read_text())
    source=ROOT/'rotclimate/model.py';paths=[PLAN,Path(__file__),ROOT/'scripts/marine_access.py',
        ROOT/'scripts/local_benchmark_protocol.py',ROOT/'rotclimate/koppen.py',source,
        ROOT/'calibration/local_accuracy_20261023/r58_params.json',CAPTURE/'qualification.json']
    qualification=json.loads((CAPTURE/'qualification.json').read_text())
    for n,h in qualification['sources_sha256'].items():assert file_hash(ROOT/n)==h,n
    for n,h in qualification['files_sha256'].items():assert file_hash(CAPTURE/n)==h,n
    for case in plan['cases']:
        r,v=case['region'],case['variant']
        paths.extend([PARENT/r/v/'fields.npz',TRACE/r/v/'trace.npz',CAPTURE/r/v/'capture.npz'])
    sources={str(path.relative_to(ROOT)):file_hash(path) for path in paths}
    OUT.mkdir(parents=True,exist_ok=True);freeze(OUT/'preparation.json',dict(plan=plan,sources_sha256=sources))
    records=[];summaries=[];horizon=3*p['inflow_km'];cell=56.
    for case in plan['cases']:
        region,variant=case['region'],case['variant']
        with np.load(PARENT/region/variant/'fields.npz') as z:f=dict(z)
        with np.load(TRACE/region/variant/'trace.npz') as z:t=dict(z)
        with np.load(CAPTURE/region/variant/'capture.npz') as z:capture=dict(z)
        land=f['land'];mask=f['mask'];starts=np.column_stack(np.nonzero(mask));ii,jj=starts.T
        np.testing.assert_array_equal(ii,t['rows']);np.testing.assert_array_equal(jj,t['cols'])
        np.testing.assert_array_equal(t['days'],capture['days'])
        geometry=production_geometry(land,cell,p['inflow_km']);assert_actual_geometry(land,geometry,p,source)
        ne,nn=geometry['normal_east'][mask],geometry['normal_north'][mask]
        weights=monthly_weights(t['days'],365.)
        gate_instant=np.clip((t['trace__moisture_u']*ne+t['trace__moisture_v']*nn)/3,0,1)
        gate_mean=weights@gate_instant
        positive=weights@np.maximum(capture['marine'],0)*365/12
        negative=weights@np.minimum(capture['marine'],0)*365/12
        case_rows=[]
        for m in range(12):
            u,v=f['u'][m],f['v'][m];local=np.clip((u[mask]*ne+v[mask]*nn)/3,0,1)
            coarse=backtrace(land,u,v,starts,cell_km=cell,step_km=cell/4,horizon_km=horizon)
            fine=backtrace(land,u,v,starts,cell_km=cell,step_km=cell/8,horizon_km=horizon)
            for k,(r,col) in enumerate(starts):
                row=dict(region=region,variant=variant,month=m+1,row=int(r),col=int(col),
                    lat=float(f['lat'][r,col]),lon=float(f['lon'][r,col]),
                    monthly_surface_u_ms=float(u[r,col]),monthly_surface_v_ms=float(v[r,col]),
                    inward_normal_east=float(ne[k]),inward_normal_north=float(nn[k]),
                    sea_distance_km=float(geometry['distance_km'][r,col]),reach=float(geometry['reach'][r,col]),
                    nearest_index_is_real_sea=bool(geometry['nearest_valid_sea'][r,col]),
                    local_gate_of_monthly_mean=float(local[k]),mean_instantaneous_production_gate=float(gate_mean[m,k]),
                    positive_marine_exchange_mm=float(positive[m,k]),negative_marine_exchange_mm=float(negative[m,k]))
                for label,a in [('quarter_cell',coarse),('eighth_cell',fine)]:
                    row[label+'_status']=STATUS[int(a['status'][k])]
                    row[label+'_distance_km']=float(a['distance_km'][k])
                    row[label+'_sea_row']=int(a['sea_r'][k]);row[label+'_sea_col']=int(a['sea_c'][k])
                case_rows.append(row)
        records.extend(case_rows);n=len(starts)
        summary=dict(region=region,variant=variant,scored_cells=n,cell_month_rows=len(case_rows),
            has_in_domain_sea=geometry['has_sea'],invalid_nearest_sea_indices=int((~geometry['nearest_valid_sea'][mask]).sum()),
            mean_absolute_gate_averaging_difference=float(np.mean([abs(r['local_gate_of_monthly_mean']-r['mean_instantaneous_production_gate']) for r in case_rows])),
            max_absolute_gate_averaging_difference=float(max(abs(r['local_gate_of_monthly_mean']-r['mean_instantaneous_production_gate']) for r in case_rows)),
            step_status_agreement_fraction=float(np.mean([r['quarter_cell_status']==r['eighth_cell_status'] for r in case_rows])),
            positive_marine_annual_mean_mm=float(positive.sum()/n),negative_marine_annual_mean_mm=float(negative.sum()/n),
            paths_by_step={})
        for label in ['quarter_cell','eighth_cell']:
            groups={}
            for status in STATUS.values():
                group=[r for r in case_rows if r[label+'_status']==status]
                groups[status]=dict(cell_months=len(group),positive_local_gate_rows=sum(r['local_gate_of_monthly_mean']>0 for r in group),
                    positive_marine_exchange_annual_mean_mm=sum(r['positive_marine_exchange_mm'] for r in group)/n,
                    negative_marine_exchange_annual_mean_mm=sum(r['negative_marine_exchange_mm'] for r in group)/n)
            summary['paths_by_step'][label]=groups
        summaries.append(summary)
    with (OUT/'cell_months.csv').open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    for n,h in sources.items():assert file_hash(ROOT/n)==h,n
    write_json(OUT/'results.json',dict(status='completed_saved_field_marine_gate_audit',sources_sha256=sources,
        files_sha256={'cell_months.csv':file_hash(OUT/'cell_months.csv')},summaries=summaries,
        path_horizon_km=horizon,path_steps_km=[14.,7.],climate_integrations=0,climate_adopted=False,
        interpretation='Monthly frozen-flow proxy disagreements, not proven physical gate errors or rainfall attribution. Off-domain/calm paths remain unknown.'))
    for r in summaries:print(json.dumps(r),flush=True)


if __name__=='__main__':main()

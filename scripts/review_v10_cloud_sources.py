"""Verify completed passive cloud-source replays; saved data only."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scripts import replay_v10_cloud_sources as run
from rotclimate_v10.earth import atomic_json,sha256


def load_verified(source,prepared=None):
    protocol,inputs,setting,initials,finals,tables=run.prepare() if prepared is None else prepared
    state=json.loads((source/'state.json').read_text())
    if json.loads((source/'manifest.json').read_text())!=protocol or state['status']!='complete':raise ValueError('Need unchanged completed cloud-source replays.')
    if set(state['cases'])!={j['key'] for j in protocol['jobs']}:raise ValueError('Cloud-source case set changed.')
    records={};collectors={};seconds=0.;errors=[]
    for job in protocol['jobs']:
        key=job['key'];folder=source/'cases'/key;row=state['cases'][key]
        run.run.previous.verify_completed(folder,row)
        if json.loads((folder/'config.json').read_text())!={**job,'code_sha256':protocol['code_sha256']}:raise ValueError('Cloud-source config changed.')
        if set(row['evidence_sha256'])!={'year1.json','year1.npz'}:raise ValueError('Cloud-source evidence declaration incomplete.')
        case,p,g,air,c=inputs[job['region']]
        record,collector=run.read_checkpoint(folder,case,g,completed=True)
        if record is None:raise ValueError('Missing source replay final year.')
        run.run.previous.replay.verify_physical(record,finals[key])
        run.run.run.validate_control_record(record,tables[job['region']]['monthly_import_target_mm'])
        errors.append(run.run.run.review.verify_annual(record,initials[key],case))
        b=record[-1]['budget'];ledger=collector.arrays['ledger'].sum(0)
        for actual,expected in ((ledger[0].sum(),b['boundary_import_gross_mm']),(ledger[1].sum(),b['boundary_export_gross_mm']),
            (ledger[2,2],b['ocean_evaporation_mm']),(ledger[2,3],b['land_evaporation_mm']),(ledger[3].sum(),b['rain_mm']),
            (collector.arrays['initial_store'].sum(),initials[key].water.sum(0).mean())):
            if not np.isclose(actual,expected,atol=1e-7,rtol=0):raise ValueError('Source totals disagree with physical water ledger.')
        if collector.arrays['maximum_errors'].max()>1e-9:raise ValueError('Source reconstruction exceeds its declared bound.')
        target=run.run.run.koppen_maps.classify_months(case.domain.temperature_c,case.observed_rain_mm,case.score_mask)
        masks={'domain':np.ones(case.domain.land.shape,bool),'scored_land':case.score_mask,**run.review.groups_for(case,target)}
        computed=collector.summary(masks,run.review.WINTER,run.review.SUMMER)
        computed.update(physical_reproduction_exact=True,source_case=job['source_case'],source_year=job['source_year'],elapsed_seconds=record[-1]['elapsed_seconds'],
            case_config_sha256=sha256(folder/'config.json'),evidence_sha256={name:sha256(folder/name) for name in ('year1.json','year1.npz')})
        if computed!=row:raise ValueError('Source summary differs from reconstructed tagged fields.')
        records[key]=record;collectors[key]=collector;seconds+=record[-1]['elapsed_seconds']
    if run.source_id()!=protocol['code_sha256']:raise ValueError('Cloud-source sources changed during review.')
    return protocol,state,inputs,records,collectors,seconds,errors


def fractions(values):
    values=np.asarray(values,float);total=float(values.sum())
    return dict(zip(run.model.SOURCES,(values/total).tolist())) if total>0 else None


def analyse(source):
    protocol,state,inputs,records,collectors,seconds,errors=load_verified(source)
    contrasts={}
    for region in inputs:
        a,b=(state['cases'][region+'_'+mode] for mode in ('bulk','parcel_lower'));contrasts[region]={}
        for area in a['regions']:
            rows={}
            for season in ('winter','summer'):
                field=season+'_rain_mm_by_source';old=np.array(a['regions'][area][field]);new=np.array(b['regions'][area][field])
                rows[season]={'bulk_mm_by_source':dict(zip(run.model.SOURCES,old.tolist())),
                    'cloud_mm_by_source':dict(zip(run.model.SOURCES,new.tolist())),
                    'bulk_total_mm':float(old.sum()),'cloud_total_mm':float(new.sum()),'cloud_source_fraction':fractions(new),
                    'signed_source_amount_change_mm':dict(zip(run.model.SOURCES,(new-old).tolist())),
                    'note':'Last vapor entry and signed differences of labelled rain. Not molecular ancestry or causal source-removal fractions.'}
            contrasts[region][area]=rows
    data={'source_code_sha256':protocol['code_sha256'],'source_manifest_sha256':sha256(source/'manifest.json'),
        'source_state_sha256':sha256(source/'state.json'),'analysis_script_sha256':sha256(Path(__file__)),
        'sources_verified':True,'exact_replays':len(records),'integration_minutes':seconds/60,
        'maximum_recomputed_physical_errors':{k:max(abs(e[k]) for e in errors) for k in errors[0]},
        'maximum_annual_source_error_mm':max(abs(v) for r in state['cases'].values() for v in r['annual_source_error_mm']),
        'maximum_source_reconstruction_error_mm':max(c.arrays['maximum_errors'].max() for c in collectors.values()),
        'cases':state['cases'],'contrasts':contrasts,'new_climate_integrations':0,'atlas_updated':False,
        'interpretation':'One fixed final synthetic year per case; unknown initial vapor explicitly retained. Winter October–March, summer April–September. Source labels do not establish causal importance of changing soil or circulation.'}
    return data


def markdown(data):
    lines=['# Completed passive cloud-rain source review','',f"Four exact physical replays verified; {data['integration_minutes']:.2f} saved integration minutes. Source stores/rain, annual budgets and monthly boundary inputs agree with physical fields.",'',
        '| Reference-arid land, summer | Rain: bulk → cloud | Boundary share of cloud rain | Ocean evaporation | Land recycling | Initial unknown |',
        '|---|---:|---:|---:|---:|---:|']
    for region,areas in data['contrasts'].items():
        row=areas['reference_arid']['summer'];f=row['cloud_source_fraction']
        lines.append(f'| {region} | {row["bulk_total_mm"]:.2f} → {row["cloud_total_mm"]:.2f} mm | {f["boundary"]:.1%} | {f["ocean_evaporation"]:.1%} | {f["land_recycling"]:.1%} | {f["initial"]:.3%} |')
    lines+=['', 'The misplaced Iberia-domain summer rain is predominantly imported, with a modest direct last-vapor-entry land-recycling share. This deprioritizes soil evaporation as its principal direct water source; it does not establish the causal effect of suppressing recycling.', '',
        'The boundary humidity currently uses one offshore-mean profile on every edge, including continental inflow. Test its spatial distribution against cached native monthly humidity before more amplitude or soil searches. Compare native local humidity with both original and matched-monthly-gross-input controls to separate placement from water amount. No new NOAA requests are needed.', '',
        '![Rainfall sources by month](source_rainfall.png)', '',
        'Labels identify the most recent entry to atmospheric vapor, not soil ancestry. Parcel condensate inherits its ascending donor labels before recipient mixing. Initial vapor remains explicitly unknown; summer is April–September, long after initial atmospheric flushing. Domains include neighboring land and North Africa. Atlas unchanged.']
    return '\n'.join(lines)+'\n'


def plot(data,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors=['#bbbbbb','#4378a7','#55b4c0','#a66f3d'];fig,axes=plt.subplots(2,2,figsize=(12,7.8),constrained_layout=True)
    for i,region in enumerate(('california','iberia')):
        for j,mode in enumerate(('bulk','parcel_lower')):
            ax=axes[i,j];row=data['cases'][region+'_'+mode]['regions']['reference_arid'];a=np.array(row['monthly_rain_mm_by_source']);bottom=np.zeros(12)
            for k,(name,color) in enumerate(zip(run.model.SOURCES,colors)):
                ax.bar(np.arange(1,13),a[:,k],bottom=bottom,color=color,label=name.replace('_',' '));bottom+=a[:,k]
            ax.set(title=region.title()+' · '+('bulk saturation' if mode=='bulk' else 'lower-interface cloud bound'),ylabel='Rain (mm/month)',xticks=np.arange(1,13));ax.grid(axis='y',alpha=.15)
            if i==0 and j==0:ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Rain in reference-arid land: imported moisture dominates the summer increase',fontsize=13)
    for ext in ('png','svg'):fig.savefig(out/('source_rainfall.'+ext),dpi=170,facecolor='#fbfcfc')
    plt.close(fig)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'output/v10_cloud_sources');p.add_argument('--out',type=Path,default=ROOT/'output/v10_cloud_source_review');p.add_argument('--write',action='store_true');a=p.parse_args(argv)
    data=analyse(a.source)
    if a.write:
        out,source=a.out.resolve(),a.source.resolve()
        if out==source or out in source.parents or source in out.parents:raise ValueError('Preserve completed source evidence.')
        atomic_json(a.out/'review.json',data);(a.out/'review.md').write_text(markdown(data));plot(data,a.out)
    print(markdown(data));return 0


if __name__=='__main__':raise SystemExit(main())

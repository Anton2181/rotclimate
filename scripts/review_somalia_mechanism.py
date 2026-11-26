"""Check diagnostic fields/tables and render all months of both controls."""
import argparse
import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json

OUT=ROOT/'output/somalia_mechanism_20261126'
PLAN=ROOT/'calibration/somalia_mechanism_20261126/plan.json'


def main():
    assert not (OUT/'review.json').exists(),'Keep completed diagnostic review'
    result=json.loads((OUT/'results.json').read_text());plan=json.loads(PLAN.read_text())
    for n,h in result['sources_sha256'].items():assert file_hash(ROOT/n)==h,n
    for n,h in result['files_sha256'].items():assert file_hash(OUT/n)==h,n
    rows={(r['region'],r['variant']):r for r in result['rows']}
    assert set(rows)=={(r,v) for r in plan['regions'] for v in plan['variants']}
    table=list(csv.DictReader((OUT/'months.csv').open()));assert len(table)==96
    values_checked=0
    for (region,variant),row in rows.items():
        assert row['overrides']==plan['variants'][variant] and row['numeric_certificate']['all_checks_passed']
        with np.load(OUT/region/variant/'fields.npz') as z:f=dict(z)
        mask=f['mask'];assert mask.any()
        np.testing.assert_allclose(row['annual_rain_mm'],f['P'][:,mask].sum(0).mean(),rtol=1e-14)
        np.testing.assert_allclose(row['annual_temperature_mae_C'],np.abs(f['T'][:,mask]-f['obs_T'][:,mask]).mean(),rtol=1e-14)
        for month in range(12):
            expected={name:float(f[key][month,mask].mean()) for name,key in [
                ('observed_rain_mm','obs_P'),('simulated_rain_mm','P'),('evaporation_mm','E'),
                ('column_water_mm','W'),('surface_u_ms','u'),('surface_v_ms','v')]}
            expected['temperature_bias_C']=float((f['T'][month,mask]-f['obs_T'][month,mask]).mean())
            record=next(r for r in table if r['region']==region and r['variant']==variant and int(r['month'])==month+1)
            for key,value in expected.items():
                np.testing.assert_allclose(float(record[key]),value,rtol=1e-14,atol=1e-14);values_checked+=1
        if variant=='control':
            part='sealed_S18' if region=='s_2n_43e' else 'sealed_U18'
            ref=ROOT/f'output/ppe_20261126/ref58/r58_{part}'
            reference=json.loads((ref/'cases'/f'{region}.json').read_text())
            assert row['case_identity']==reference['case_identity']
            with np.load(ref/'cells'/f'{region}.npz') as old:
                for key,archived in [('T','Ts'),('P','Ps'),('obs_T','To'),('obs_P','Po')]:
                    np.testing.assert_array_equal(f[key][:,mask].astype(np.float32),old[archived])
    for e in result['effects']:
        p={v:rows[e['region'],v]['annual_rain_mm'] for v in plan['variants']}
        np.testing.assert_allclose(e['factorial_interaction_mm'],p['both']-p['no_local_recycling']-p['minimum_turning']+p['control'])
    colors=['#365e77','#ad7646','#548674','#9a6584'];labels=['r58 control','No local recycling','Minimum wind turning','Both interventions']
    fig,axes=plt.subplots(2,3,figsize=(16,8));months=np.arange(1,13)
    for row,region in enumerate(plan['regions']):
        control=rows[region,'control'];obs=[x['observed_rain_mm'] for x in control['all_months']]
        axes[row,0].plot(months,obs,color='#222222',linestyle='--',linewidth=2,label='Observed')
        for variant,color,label in zip(plan['variants'],colors,labels):
            records=rows[region,variant]['all_months']
            for col,key in enumerate(['simulated_rain_mm','evaporation_mm','surface_u_ms']):
                axes[row,col].plot(months,[x[key] for x in records],color=color,label=label,linewidth=1.7)
        for col,title in enumerate(['Rain (mm per model month)','Evaporation (mm per model month)','Surface eastward wind (m/s)']):
            ax=axes[row,col];ax.set(xticks=[1,3,5,7,9,11],xlabel='Production month',title=title)
            ax.grid(alpha=.15)
        axes[row,0].set_ylabel('Somalia · spent S18' if row==0 else 'Sahara control · spent U18')
        axes[row,2].axhline(0,color='#777777',linewidth=.6)
    handles,legends=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,legends,ncol=5,loc='lower center',bbox_to_anchor=(.5,.075),frameon=False)
    fig.suptitle('Somali over-rainfall: fixed recycling and wind-turning ablations',fontsize=16)
    fig.text(.5,.025,'Eight strict numerical integrations on two exposed development regions; no parameter fit or adoption.\n'
             'Coupled counterfactual responses are not a measured moisture-budget decomposition. Surface winds shown; production uses 12 equal model months.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.08,right=.99,top=.89,bottom=.19,hspace=.35,wspace=.23)
    fig.savefig(OUT/'diagnostic.png',dpi=160);plt.close(fig)
    write_json(OUT/'review.json',dict(status='passed_fixed_diagnostic_fields_and_tables',
        results_sha256=file_hash(OUT/'results.json'),reviewer_sha256=file_hash(Path(__file__)),
        exact_reference_controls=2,strict_numerical_cases=8,independent_monthly_values_checked=values_checked,
        all_twelve_months_retained=True,diagnostic_figure_sha256=file_hash(OUT/'diagnostic.png'),
        parameter_fit=False,adoption=False))
    print('Two exact controls;8 numerical certificates;672 monthly scalar values checked; figure rendered.')


def seal():
    assert not (OUT/'qualification.json').exists()
    result=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['results_sha256']==file_hash(OUT/'results.json')
    assert review['reviewer_sha256']==file_hash(Path(__file__))
    assert review['diagnostic_figure_sha256']==file_hash(OUT/'diagnostic.png')
    for n,h in result['sources_sha256'].items():assert file_hash(ROOT/n)==h,n
    for n,h in result['files_sha256'].items():assert file_hash(OUT/n)==h,n
    report=ROOT/'calibration/somalia_mechanism_20261126/findings.md'
    files=[*result['files_sha256'],'preparation.json','results.json','review.json','diagnostic.png']
    write_json(OUT/'qualification.json',dict(status='passed_fixed_Somali_ablation_not_a_climate_adoption',
        sources_sha256={**result['sources_sha256'],str(Path(__file__).relative_to(ROOT)):file_hash(Path(__file__)),
                        str(report.relative_to(ROOT)):file_hash(report)},
        files_sha256={n:file_hash(OUT/n) for n in files},strict_numerical_cases=8,
        exact_reference_controls=2,independent_monthly_values_checked=672,figure_visually_inspected=True,
        coupled_model_responses_not_measured_causal_shares=True,
        parameter_fit=False,climate_adopted=False,atlas_changed=False,sealed_targets_used=False))
    print('Sealed8-case diagnostic and inspected figure; no new climate adopted.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--seal',action='store_true')
    args=parser.parse_args();(seal if args.seal else main)()

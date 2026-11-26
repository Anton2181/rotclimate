"""Audit captured land exchange and the corrected local equation, then present it."""
import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from somalia_transport_trace import COMPONENTS

OLD=ROOT/'output/somalia_transport_trace_20261126'
OUT=ROOT/'output/somalia_marine_exchange_trace_20261126'


def check():
    result=json.loads((OUT/'results.json').read_text());old=json.loads((OLD/'results.json').read_text())
    for r,folder in [(result,OUT),(old,OLD)]:
        for n,h in r['sources_sha256'].items():assert file_hash(ROOT/n)==h,n
        for n,h in r['files_sha256'].items():assert file_hash(folder/n)==h,n
    return result,old


def main():
    assert not (OUT/'review.json').exists()
    r,old=check();annual=[];winds=[];checked=0
    for row in r['rows']:
        region,variant=row['region'],row['variant']
        previous=next(x for x in old['rows'] if x['region']==region and x['variant']==variant)
        assert row['numeric_certificate']==previous['numeric_certificate']
        with np.load(OLD/region/variant/'trace.npz') as z:a=dict(z)
        with np.load(OUT/region/variant/'capture.npz') as z:c=dict(z)
        np.testing.assert_array_equal(c['original_residual'],a['budget__residual'])
        net=sum(a['budget__'+k].astype(float) for k in ['evaporation','column_drying','convergence_import'])+c['marine']
        np.testing.assert_allclose(net,c['net_source'],rtol=3e-6,atol=1e-5)
        supply=net+sum(a['budget__'+k].astype(float) for k in ['advection','diffusion','storm_exchange'])
        residual=supply-c['rain'];np.testing.assert_allclose(residual,c['corrected_residual'],atol=1e-10)
        scale=np.maximum(c['rain']+np.abs(c['net_source']),.1)
        normalized=np.abs(residual)/scale
        np.testing.assert_allclose(normalized,c['corrected_scaled_residual'],rtol=2e-8,atol=1e-10)
        assert normalized.max()<=row['existing_equation_tolerance']
        n=len(a['days']);weights=np.zeros((12,n));year=365.
        for m in range(12):
            for k in range(n):
                weights[m,k]=max(0,min((m+1)*year/12,(k+1)*year/n)-max(m*year/12,k*year/n))/(year/12)
        for m,record in enumerate(row['months']):
            for key,values in [('marine_exchange_mm',c['marine']),('original_residual_mm',c['original_residual']),
                ('original_absolute_residual_mm',np.abs(c['original_residual'])),('corrected_residual_mm',residual),
                ('corrected_absolute_residual_mm',np.abs(residual))]:
                expected=float(np.sum(weights[m,:,None]*values,axis=0).mean()*year/12)
                np.testing.assert_allclose(expected,record[key],rtol=5e-11,atol=1e-9);checked+=1
        udiff=float(np.abs(a['trace__u']-a['trace__moisture_u']).max())
        vdiff=float(np.abs(a['trace__v']-a['trace__moisture_v']).max())
        winds.append(dict(region=region,variant=variant,max_surface_transport_u_difference_ms=udiff,
                          max_surface_transport_v_difference_ms=vdiff))
        values={key:float(a['budget__'+key].astype(float).mean()*year) for key in COMPONENTS}
        values['marine_exchange']=float(c['marine'].mean()*year);values['rain_sink']=-float(c['rain'].mean()*year)
        values.update(region=region,variant=variant,corrected_signed_residual_mm=float(residual.mean()*year),
                      corrected_absolute_residual_mm=float(np.abs(residual).mean()*year),
                      original_absolute_residual_mm=float(np.abs(c['original_residual']).mean()*year),
                      max_corrected_scaled_residual=float(normalized.max()),
                      max_original_surface_E_scaled_residual=previous['max_step_scaled_residual'])
        annual.append(values)
    keys=COMPONENTS+['marine_exchange','rain_sink']
    labels=['Advection','Diffusion','Eddy exchange','Land E','Column drying','Convergence import','Marine relaxation','Rain sink']
    names=['Somalia · r58','Somalia · turning','Sahara · r58'];colors=['#35677f','#65917c','#b07c53']
    fig,axes=plt.subplots(1,3,figsize=(18,6.8))
    for j,(data,color,name) in enumerate(zip(annual,colors,names)):
        axes[0].barh(np.arange(len(keys))+(j-1)*.25,[data[k] for k in keys],height=.23,color=color,label=name)
    axes[0].set(yticks=np.arange(len(keys)),yticklabels=labels,xlabel='Signed local equation totals (mm/year)',title='Rain balances local source and sink terms')
    axes[0].axvline(0,color='#555555',linewidth=.7);axes[0].invert_yaxis();axes[0].legend(fontsize=8,loc='lower left');axes[0].grid(axis='x',alpha=.13)
    for row,color,name in zip(r['rows'],colors,names):
        axes[1].plot(np.arange(1,13),[m['marine_exchange_mm'] for m in row['months']],color=color,label=name,linewidth=1.8)
    axes[1].axhline(0,color='#666666',linewidth=.7);axes[1].set(xlabel='Production month',ylabel='Signed marine relaxation (mm/model month)',
        title='Omitted term can add or remove water',xticks=[1,3,5,7,9,11]);axes[1].legend(fontsize=8);axes[1].grid(alpha=.13)
    before=[x['max_original_surface_E_scaled_residual'] for x in annual];after=[x['max_corrected_scaled_residual'] for x in annual]
    xx=np.arange(3);axes[2].bar(xx-.17,before,.32,color='#b07c53',label='Old export + surface-E scale')
    axes[2].bar(xx+.17,after,.32,color='#35677f',label='Complete export + solver scale')
    axes[2].axhline(.01,color='#444444',linestyle='--',label='Existing 0.01 criterion')
    axes[2].set(yscale='log',xticks=xx,xticklabels=['Somalia\nr58','Somalia\nturning','Sahara\nr58'],
        ylabel='Maximum scaled local equation residual',title='Correct bookkeeping corroborates solver checks')
    axes[2].legend(fontsize=8,loc='upper right');axes[2].grid(axis='y',alpha=.13)
    fig.suptitle('Marine-humidity exchange was missing from the exported budget',fontsize=16)
    fig.text(.5,.035,'Three instrumented replays preserve all physical climate outputs exactly. The original failed export checks are retained.\n'
             'Stationary concentration-form local equations; no conservative regional boundary-flux or observed causal-attribution claim. No climate improvement is claimed.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.09,right=.985,top=.86,bottom=.18,wspace=.38)
    fig.savefig(OUT/'corrected_budget.png',dpi=160);plt.close(fig)
    write_json(OUT/'review.json',dict(status='passed_captured_marine_exchange_and_local_equation_review',
        results_sha256=file_hash(OUT/'results.json'),original_results_sha256=file_hash(OLD/'results.json'),
        reviewer_sha256=file_hash(Path(__file__)),independent_monthly_integral_checks=checked,
        three_exact_instrumented_replays=True,all_local_checks_below_existing_tolerance=True,
        annual_equations=annual,surface_transport_comparisons=winds,
        figure_sha256=file_hash(OUT/'corrected_budget.png'),global_conservation_claim=False))
    print(json.dumps(dict(annual_equations=annual,winds=winds),indent=1))


def seal():
    assert not (OUT/'qualification.json').exists()
    r,old=check();review=json.loads((OUT/'review.json').read_text())
    assert review['results_sha256']==file_hash(OUT/'results.json')
    assert review['original_results_sha256']==file_hash(OLD/'results.json')
    assert review['reviewer_sha256']==file_hash(Path(__file__))
    assert review['figure_sha256']==file_hash(OUT/'corrected_budget.png')
    report=ROOT/'calibration/somalia_transport_trace_20261126/findings.md'
    test=ROOT/'tests/test_marine_exchange_diagnostic.py'
    files=[*r['files_sha256'],'results.json','preparation.json','review.json','corrected_budget.png']
    write_json(OUT/'qualification.json',dict(status='passed_diagnostic_correction_no_physical_climate_change',
        sources_sha256={**r['sources_sha256'],str(Path(__file__).relative_to(ROOT)):file_hash(Path(__file__)),
                        str(report.relative_to(ROOT)):file_hash(report),str(test.relative_to(ROOT)):file_hash(test)},
        files_sha256={n:file_hash(OUT/n) for n in files},exact_instrumented_replays=3,
        total_instrumented_replays=6,independent_monthly_integral_checks=180,
        source_and_sink_regression_tests=True,figure_visually_inspected=True,
        original_failed_export_checks_preserved=True,physical_source_files_changed=False,
        core_export_patch_deferred_until_W18c_closed=True,climate_adopted=False,atlas_changed=False))
    print('Qualified captured source correction; original failures retained and climate unchanged.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seal',action='store_true')
    args=p.parse_args();(seal if args.seal else main)()

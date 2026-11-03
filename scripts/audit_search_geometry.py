"""Describe completed search coverage and cross-start linear predictability.

Retrospective development-data diagnosis, never selection or global-optimum proof.
"""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def leave_start_out(x,y,starts,alpha=.01):
    """An anchored linear response with a fixed ridge, held out by whole start."""
    import numpy as np
    x,y,starts=np.asarray(x,float),np.asarray(y,float),np.asarray(starts)
    if x.ndim!=2 or y.shape!=(len(x),2) or starts.shape!=(len(x),):raise ValueError('Unmatched design')
    if not np.isfinite(x).all() or not np.isfinite(y).all() or alpha<=0:raise ValueError('Invalid design/ridge')
    result=[]
    for start in sorted(set(starts.tolist())):
        train=starts!=start;test=~train
        if train.sum()<x.shape[1] or not test.any():raise ValueError('Insufficient held-start data')
        coefficients=np.linalg.solve(x[train].T@x[train]+alpha*np.eye(x.shape[1]),x[train].T@y[train])
        prediction=x[test]@coefficients
        combined=(prediction-y[test]).mean(1)
        result.append(dict(start=int(start),train=int(train.sum()),test=int(test.sum()),
            predicted_component_changes=prediction.tolist(),actual_component_changes=y[test].tolist(),
            combined_mae=float(np.abs(combined).mean()),combined_rmse=float(np.sqrt(np.mean(combined**2)))))
    return result


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=ROOT/'calibration/r42_multistart_20261102b';campaign=json.loads((folder/'campaign.json').read_text())
    source=ROOT/'output/r42_multistart_20261102b';selected=json.loads((source/'selection.json').read_text())
    plans=[json.loads((ROOT/n).read_text()) for n in campaign['plans']]
    knobs=plans[0]['knobs'];names=[k[0] for k in knobs];bounds=np.asarray([k[1:] for k in knobs],float)
    records=[];hashes={}
    for start in range(1,4):
        path=source/f'chain_{start}/evals.jsonl';rows=[json.loads(s) for s in path.read_text().splitlines()]
        if [r['n'] for r in rows]!=list(range(13)):raise ValueError('Search is incomplete')
        hashes[str(path.relative_to(ROOT))]=file_hash(path)
        if plans[start-1]['knobs']!=knobs:raise ValueError('Bounds differ across starts')
        records.extend(dict(r,start=start) for r in rows)
    controls=[r for r in records if r['n']==0];ref=controls[0]
    if any((r['knobs'],r['T'],r['P'])!=(ref['knobs'],ref['T'],ref['P']) for r in controls):
        raise ValueError('Expected three exact reproduction controls')
    rows=[r for r in records if r['n']>0]
    values=np.asarray([[r['knobs'][k] for k in names] for r in rows]);normal=(values-bounds[:,0])/np.ptp(bounds,axis=1)
    origin=(np.asarray([ref['knobs'][k] for k in names])-bounds[:,0])/np.ptp(bounds,axis=1)
    if ((normal<0)|(normal>1)).any():raise ValueError('Proposal outside declared bounds')
    x=normal-origin;y=np.asarray([[r['T']/ref['T']-1,r['P']/ref['P']-1] for r in rows])
    starts=np.asarray([r['start'] for r in rows]);singular=np.linalg.svd(x,compute_uv=False)
    folds=leave_start_out(x,y,starts)
    winner=selected['finalist'];best=np.asarray([winner['knobs'][k] for k in names]);best=(best-bounds[:,0])/np.ptp(bounds,axis=1)
    fig,axes=plt.subplots(3,3,figsize=(13,9),layout='constrained',sharey=True)
    for j,(ax,name) in enumerate(zip(axes.flat,names)):
        for start,color in zip(range(1,4),['#2868a2','#d97726','#36916d']):
            mask=starts==start;ax.scatter(normal[mask,j],1+y[mask].mean(1),s=24,color=color,alpha=.85,label=f'Start {start}')
        ax.scatter([best[j]],[winner['S']],marker='*',s=130,color='#a12b37',zorder=4,label='Adopted r43')
        ax.axhline(1,color='#555',lw=.7);ax.set_xlim(0,1);ax.set_title(name.replace('_',' '),fontsize=10,loc='left')
        ax.set_xlabel('Fraction of declared parameter range',fontsize=9);ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
        if j%3==0:ax.set_ylabel('Combined error / r42')
    fig.suptitle('Search coverage: 36 proposals across nine dimensions\nEach panel is a projection, not an isolated causal parameter effect',fontsize=14)
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='outside lower center',ncol=4,frameon=False)
    out=ROOT/'output/search_geometry_20261103';out.mkdir(exist_ok=True)
    image=out/'parameter_coverage.png';fig.savefig(image,dpi=135);plt.close(fig)
    report=dict(climate_integrations=0,adoption=False,used_sealed_data=False,
        evaluations=len(records),reproduction_controls=len(controls),proposals=len(rows),dimensions=len(names),
        unique_proposals=len(np.unique(values,axis=0)),rank=int(np.linalg.matrix_rank(x)),singular_values=singular.tolist(),
        condition_number=float(singular[0]/singular[-1]),coverage={name:dict(proposal_min_fraction=float(normal[:,j].min()),
            proposal_max_fraction=float(normal[:,j].max()),winner_fraction=float(best[j])) for j,name in enumerate(names)},
        anchored_ridge_alpha=.01,leave_whole_start_out=folds,winning_development_gain=1-winner['S'],
        inputs_sha256=hashes,selection_sha256=file_hash(source/'selection.json'),
        image_sha256=file_hash(image),observer_sha256=file_hash(Path(__file__)),
        scope='Retrospective design/predictability audit on development data only. Identical reproduction controls are excluded from cross-start error evaluation. Fixed ridge, no hyperparameter selection, no new candidate selection or parameter recommendation. Linear prediction error is not generalization uncertainty and no rank/coverage result proves a local or global minimum.')
    write_json(out/'review.json',report)
    print(json.dumps({k:report[k] for k in ['proposals','dimensions','rank','condition_number','winning_development_gain']}))
    print('Whole-start combined prediction MAE:',[r['combined_mae'] for r in folds])


if __name__=='__main__':main()

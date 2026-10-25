"""Audit target-rule factors on a verified, self-generated atlas checkpoint.

This reads saved climate, checks its input identities, and makes no new fit.
"""
from dataclasses import asdict
from pathlib import Path
import argparse
import hashlib
import json
import pickle
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from earth_benchmark import load_params
from rotclimate.geography import TARGET_CLASSES
from rotclimate.score import evaluate,membership_factors,terrain_slope


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkpoint',required=True,type=Path)
    ap.add_argument('--atlas',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args()
    with a.checkpoint.open('rb') as stream:cached=pickle.load(stream)
    identity=cached['identity'];r=cached['result']
    for name,expected in identity['sources'].items():
        if digest(ROOT/'rotclimate'/name)!=expected:raise ValueError('Changed scientific source: '+name)
    for name,expected in identity['map_inputs'].items():
        if digest(ROOT/'data/source'/name)!=expected:raise ValueError('Changed map source: '+name)
    params=json.loads(json.dumps(asdict(load_params(a.atlas/'params.json'))))
    if params!=identity['params']:raise ValueError('Atlas parameters do not match saved climate')
    if not r.numerics.get('all_checks_passed'):raise ValueError('Unverified climate')
    ev=evaluate(r);g=r.grid
    summary=json.loads((a.atlas/'summary.json').read_text())
    if abs(ev['accuracy']-summary['strict_accuracy'])>1e-12:raise ValueError('Atlas accuracy does not reproduce')
    factors=membership_factors(ev['indices'],slope=terrain_slope(g))
    zones={}
    for cid,key,label,_ in TARGET_CLASSES:
        mask=g.inmap&g.land&(g.target==cid)
        names=list(factors[key]);values=np.array([factors[key][name][mask] for name in names])
        limiting=values.argmin(0)
        zones[key]=dict(label=label,cells=int(mask.sum()),strict_recall=ev['recall'][key],
            mean_membership=ev['per_class'][key],
            climate={name:dict(mean=float(ev['indices'][name][mask].mean()),
                              median=float(np.median(ev['indices'][name][mask])))
                     for name in ['MAT','Tcold','Thot','MAP','aridity','Psdry','Pwwet']},
            factors={name:dict(mean=float(values[i].mean()),median=float(np.median(values[i])),
                               below_half_share=float((values[i]<.5).mean()),
                               lowest_factor_share=float((limiting==i).mean())) for i,name in enumerate(names)})
    a.out.mkdir(parents=True,exist_ok=True)
    record=dict(zones=zones,checkpoint_sha256=digest(a.checkpoint),identity=identity,
        script_sha256=digest(__file__),diagnostic_only=True,
        note='Fixed existing target definitions. Rule-factor means describe saved climate; they are not causal parameter sensitivities. '
             'Strict labels also require compatible Koppen classes and competition among zone rules.')
    (a.out/'diagnosis.json').write_text(json.dumps(record,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    columns=list(dict.fromkeys(name for z in zones.values() for name in z['factors']))
    matrix=np.full((len(zones),len(columns)),np.nan)
    for i,z in enumerate(zones.values()):
        for j,name in enumerate(columns):
            if name in z['factors']:matrix[i,j]=z['factors'][name]['mean']
    fig,ax=plt.subplots(figsize=(12,5.8),constrained_layout=True)
    cmap=plt.get_cmap('RdYlGn').copy();cmap.set_bad('#eeeeee')
    im=ax.imshow(matrix,cmap=cmap,vmin=0,vmax=1,aspect='auto')
    for i,j in zip(*np.nonzero(np.isfinite(matrix))):
        ax.text(j,i,f'{matrix[i,j]:.2f}',ha='center',va='center',fontsize=9,color='#222222')
    ax.set_xticks(np.arange(len(columns)),[n.replace('_',' ') for n in columns],rotation=45,ha='right')
    ax.set_yticks(np.arange(len(zones)),[z['label']+f' · recall {z["strict_recall"]:.0%}' for z in zones.values()])
    ax.set_title('Which existing target requirements does the published Earth fit miss?',pad=15)
    fig.colorbar(im,ax=ax,shrink=.7,label='Mean fuzzy rule factor (0 fails; 1 meets)')
    fig.supxlabel('Verified r38 climate · layouts 1–3 · downsample 8. Grey = requirement not used. Descriptive factors, not causal attribution.',fontsize=9)
    fig.savefig(a.out/'target_factors.png',dpi=150);plt.close(fig)
    for key,z in zones.items():
        weakest=min(z['factors'],key=lambda n:z['factors'][n]['mean'])
        print(key,weakest,round(z['factors'][weakest]['mean'],3),flush=True)


if __name__=='__main__':main()

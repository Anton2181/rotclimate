"""Read signed water equations for clearly declared post-search comparisons."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_column_drying import check_source_closure,DISJOINT_TERMS,COLORS
from local_benchmark_protocol import file_hash,write_json


def diagnose(out):
    protocol=json.loads((out/'protocol.json').read_text());p=protocol['plan'];progress=json.loads((out/'progress.json').read_text());review=json.loads((out/'review.json').read_text())
    if not progress['complete'] or not review['complete']:raise ValueError('Need completed search')
    valid={n:s for n,s in review['scores'].items() if s.get('physical_admissible')}
    if not valid:raise ValueError('No admissible candidate')
    selected=dict(best_objective=min(valid,key=lambda n:(valid[n]['objective'],n)),
        best_mean_climate=min(valid,key=lambda n:(valid[n]['mean_combined_ratio'],n)),
        best_native=min(valid,key=lambda n:(valid[n]['native_squared_regret'],n)))
    names=list(dict.fromkeys(['reference','environment_control',*selected.values()]));records={(r['name'],r['region']):r for r in progress['records']}
    result={};raw_hashes={}
    for name in names:
        result[name]={}
        for region in p['regions']:
            row=records[name,region];path=out/name/(region+'.npz')
            if row['status']!='passed' or file_hash(path)!=row['arrays_sha256']:raise ValueError('Changed water-budget archive')
            raw_hashes[name+'/'+region]=file_hash(path)
            with np.load(path) as z:
                fields={k:z[k] for k in z.files};mask=fields['valid']
                certificate=check_source_closure(fields,mask)
                annual={key:float(fields[key][:,mask].sum(0).mean()) for key in ['evaporation','advection','diffusion','storm_exchange','column_drying','monsoon_drying','convergence_import','simulated','observed','residual']}
                annual['other_column_drying']=annual['column_drying']-annual['monsoon_drying']
                result[name][region]=dict(cropped_cells=int(mask.sum()),full_scoring_cells=row['rain']['scored_land_cells'],annual_mm=annual,closure=certificate)
    fig,axes=plt.subplots(2,4,figsize=(17,9.5));labels={'reference':'r39','environment_control':'Env. control'}
    for role,n in selected.items():labels[n]=labels.get(n,'')+(' / ' if n in labels else '')+role.replace('best_','')
    pretty=['Surface E','Advection','Diffusion','Storm exchange','Other drying','Monsoon drying','Legacy import']
    for ax,region in zip(axes.flat,p['regions']):
        pos=np.zeros(len(names));neg=pos.copy();x=np.arange(len(names))
        for key,color,label in zip(DISJOINT_TERMS,COLORS,pretty):
            y=np.array([result[n][region]['annual_mm'][key] for n in names]);ax.bar(x,np.maximum(y,0),bottom=pos,color=color,label=label);ax.bar(x,np.minimum(y,0),bottom=neg,color=color);pos+=np.maximum(y,0);neg+=np.minimum(y,0)
        ax.plot(x,[result[n][region]['annual_mm']['simulated'] for n in names],'D',color='#222',ms=4,label='Simulated rain')
        ax.axhline(result['reference'][region]['annual_mm']['observed'],color='#222',ls='--',lw=1,label='Observed rain')
        ax.axhline(0,color='#888',lw=.6);ax.set(xticks=x,xticklabels=[labels[n].replace(' ','\n') for n in names],ylabel='Signed mm/year',title=region.replace('_',' ').title());ax.tick_params(axis='x',labelsize=7)
    axes.flat[-1].axis('off');handles,legend=axes.flat[0].get_legend_handles_labels();axes.flat[-1].legend(handles,legend,loc='center',frameon=False)
    fig.suptitle('Why different objectives select different water balances',fontsize=16)
    fig.supxlabel('Declared post-search selections: objective, average climate error and native-error regret. All raw search outcomes remain available.\nOriginal cropped domains (East Australia347 versus358 full-score cells); equal model months. Monsoon is a subset of drying.\nSigned terms describe model equations, not independent causal shares. r39 concentration advection is not a conservative flux.',fontsize=9)
    fig.tight_layout(rect=[0,.10,1,.95]);picture=out/'water_tradeoffs.png';fig.savefig(picture,dpi=145);plt.close(fig)
    meta=dict(status='passed',selection_rule='Best objective, best mean combined climate ratio, best native regret among admissible completed candidates; diagnostic choices do not change selection or validation',selected=selected,profiles=result,
        raw_arrays_sha256=raw_hashes,protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),script_sha256=file_hash(Path(__file__)),
        helper_sha256=file_hash(ROOT/'scripts/audit_column_drying.py'),image_sha256=file_hash(picture),new_earth_integrations=0,physics_or_atlas_adoption=False)
    write_json(out/'water_tradeoffs.json',meta);print(json.dumps(selected,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);diagnose(ap.parse_args().out.resolve())

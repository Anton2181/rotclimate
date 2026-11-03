"""Render completed conditional-development evidence without selecting models."""
from pathlib import Path
import json
import sys
import shutil

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=ROOT/'output/cereal_phenology_20261103'
    result=json.loads((out/'result.json').read_text());plan_path=ROOT/'calibration/cereal_phenology_20261103/plan.json'
    for name,expected in result['sources_sha256'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Evaluated source changed: '+name)
    if file_hash(plan_path)!=result['plan_sha256'] or file_hash(out/'selection.json')!=result['selection_sha256']:
        raise ValueError('Declaration or selected parameters changed')
    names=['legacy_heat_only','published_heat_only','reference_chilling','selected_global']
    labels=['Existing heat\nthreshold ablation','Published heat\nadaptation','Plus fixed winter\nchilling proxy','Training-selected\nheat/chilling']
    fig,axes=plt.subplots(1,2,figsize=(13,5.1),layout='constrained')
    x=np.arange(4)
    for offset,pool,color,label in [(-.18,'training','#aac4bc','Training: 237 records /62 countries'),
                                   (.18,'evaluation','#397c70','Evaluation: 29 records /16 countries')]:
        values=[result['scores'][n][pool]['country_mean_penalized_error_days'] for n in names]
        axes[0].bar(x+offset,values,width=.36,color=color,label=label)
    axes[0].set(xticks=x,xticklabels=labels,ylabel='Equal-country mean duration error (days)',ylim=(0,120))
    axes[0].legend(frameon=False,fontsize=8)
    idx=np.array([r['evaluation'] for r in result['records']]);observed=np.array([r['growing_days'] for r in result['records']])[idx]
    predicted=np.array(result['predictions']['published_heat_only'])[idx]
    assert np.all(predicted>0)
    axes[1].scatter(observed,predicted,s=35,color='#397c70',alpha=.7)
    axes[1].plot([0,365],[0,365],':',color='#555')
    axes[1].set(xlabel='Observed regional sowing-to-harvest duration (days)',
                ylabel='Modeled maturity duration (days)',title='Published heat adaptation · all29 evaluation records',
                xlim=(0,365),ylim=(0,365))
    for ax in axes:ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.2)
    fig.suptitle('Cereal development: adapted heat requirements help; generic chilling hurts\nObserved sowing prescribed · modern climatology at approximate centroids · no ancient yield/population adoption',fontsize=12)
    image=out/'cereal_development.png';fig.savefig(image,dpi=135);plt.close(fig)
    review=dict(status='completed_conditional_development_check',adoption=False,result=result,
        plan=json.loads(plan_path.read_text()),result_sha256=file_hash(out/'result.json'),figure_sha256=file_hash(image),
        publisher_sha256=file_hash(Path(__file__)),
        interpretation='Published heat adaptation improves this limited country-separated conditional-duration test. Generic chilling is unsupported here; selected winter15days remains worse. Existing-threshold comparator is a thermal ablation, not production atlas date accuracy. Sowing observed; no plant-survival, biomass, water stress or ancient cultivar validation. Photoperiod equation implemented but reference sensitivity disabled as in paper. Evaluation dataset previously inspected diagnostically, not untouched.')
    write_json(out/'review.json',review)
    destination=ROOT/'atlases/economy_lab/data'
    shutil.copyfile(image,destination/image.name);write_json(destination/'cereal_development.json',review)
    print('Prepared verified cereal-development evidence')


if __name__=='__main__':main()

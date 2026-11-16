"""Display every architecture/control fold comparison after independent review."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='urban_population_refresh_20261116'
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_population_refresh_20261116'


def main():
    result=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==hashlib.sha256((OUT/'results.json').read_bytes()).hexdigest()
    fig,axes=plt.subplots(2,2,figsize=(10,6.5),sharex=True,layout='constrained')
    for i,model in enumerate(['M1','M1C']):
        for j,(metric,label) in enumerate([('mae','Mean absolute log-area error'),('nll','Gaussian log-area NLL')]):
            ax=axes[i,j]
            for alternative,color,style,text in [('M0_control','#888','--','Intercept-only control'),('legacy_'+model,'#b86237','-','Legacy H'),('floodplain_base_'+model,'#287a9e','-','Refreshed H, same recipe')]:
                rows=[r for r in result['folds'] if r['alternative']==alternative]
                ax.plot([r['outer'] for r in rows],[r[metric] for r in rows],style,color=color,marker='o',label=text)
            ax.set(title=f'{model} · {label}',xlabel='Held-out province fold',ylabel='Lower is better',xticks=range(4));ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Qualified input refresh: modest predictive gains, weak fold 3 remains\nAll five fixed alternatives; same 153 held-out target records',fontsize=13)
    fig.savefig(OUT/'paired_input_comparison.png',dpi=160)
    svg=OUT/'paired_input_comparison.svg';fig.savefig(svg,metadata={'Date':None});svg.write_text('\n'.join(a.rstrip() for a in svg.read_text().splitlines())+'\n');plt.close(fig)


if __name__=='__main__':main()

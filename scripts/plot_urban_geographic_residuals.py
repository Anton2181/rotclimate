"""Plot every reviewed fold bias/variance decomposition without refitting."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='urban_geographic_residuals_20261116'
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/urban_geographic_residuals_20261116'


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==hashlib.sha256((OUT/'results.json').read_bytes()).hexdigest()
    fig,axes=plt.subplots(2,3,figsize=(11,6.5),sharex=True,sharey=True,layout='constrained')
    for i,cohort in enumerate(['mixed','strict']):
        for j,model in enumerate(['M0','M1','M1C']):
            ax=axes[i,j];rows=[a for a in r['cases'] if a['training_cohort']==cohort and a['model']==model]
            assert [a['outer'] for a in rows]==[0,1,2,3]
            bias=np.array([a['bias_squared'] for a in rows]);variance=np.array([a['centered_residual_mean_square'] for a in rows])
            ax.bar(range(4),bias,color='#c4713b',label='Squared bias')
            ax.bar(range(4),variance,bottom=bias,color='#4989a6',label='Residual variance')
            for a in rows:
                ax.text(a['outer'],a['mse']+.035,f'{a["mean_signed_log_residual"]:+.2f}',ha='center',fontsize=9)
            ax.set(title=f'{cohort.capitalize()} training · {model}',xticks=range(4),xlabel='Held-out province fold',ylim=(0,2.2))
            ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
            if j==0:ax.set_ylabel('Mean squared log-area error')
    axes[0,0].legend(loc='upper left',fontsize=8)
    fig.suptitle('Weak fold 3 has both bias and scatter across all six alternatives\nLabels show mean signed log residual; positive = underprediction',fontsize=13)
    fig.savefig(OUT/'bias_variance.png',dpi=160)
    svg=OUT/'bias_variance.svg';fig.savefig(svg,metadata={'Date':None})
    svg.write_text('\n'.join(a.rstrip() for a in svg.read_text().splitlines())+'\n');plt.close(fig)


if __name__=='__main__':main()

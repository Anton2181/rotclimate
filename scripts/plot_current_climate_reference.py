"""Plot verified current-reference errors; performs no model integration."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json
OUT=ROOT/'output/climate_reference_20261127'


def main():
    assert not (OUT/'error_summary.png').exists()
    review=json.loads((OUT/'review.json').read_text())
    assert review['regions']==review['numerical_certificates']==97
    rows=review['statistics']
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(15,10))
    settings=[(0,0,'temperature_mae_C','Largest temperature errors','Monthly temperature MAE (C)',False),
              (0,1,'rain_loss','Largest rainfall errors','Existing per-cell rain loss',False),
              (1,0,'historical_temperature_mae_change_C','Current source minus historical source','Temperature MAE change (C)',True),
              (1,1,'historical_rain_loss_change','Current source minus historical source','Rain loss change',True)]
    labels={'s_2n_43e':'s_2n_43e (Somalia)','u_21n_21e':'u_21n_21e (Sahara)'}
    for row,col,key,title,unit,signed in settings:
        chosen=sorted(rows,key=lambda r:abs(r[key]) if signed else r[key],reverse=True)[:12][::-1]
        values=[r[key] for r in chosen]
        colors=['#377d8d' if value<=0 or not signed else '#b47552' for value in values]
        ax=axes[row,col]
        ax.barh(np.arange(len(chosen)),values,color=colors)
        ax.set(yticks=np.arange(len(chosen)),yticklabels=[labels.get(r['region'],r['region']) for r in chosen],title=title,xlabel=unit)
        ax.tick_params(axis='y',labelsize=8);ax.grid(axis='x',alpha=.15);ax.axvline(0,color='#999',linewidth=.6)
    fig.suptitle('Verified97-region current-source r58 baseline: remaining errors and source differences')
    fig.text(.5,.028,'Same exposed regions, observations, r58 parameters and strict solver criteria. Historical results preserved.\nThis is calibration infrastructure, not improved global skill or a new adopted atlas. Deltas include real source corrections.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.14,right=.98,top=.91,bottom=.10,hspace=.30,wspace=.55)
    fig.savefig(OUT/'error_summary.png',dpi=160);plt.close(fig)
    write_json(OUT/'figure_review.json',dict(review_sha256=file_hash(OUT/'review.json'),producer_sha256=file_hash(__file__),figure_sha256=file_hash(OUT/'error_summary.png'),integrations=0))


if __name__=='__main__':main()

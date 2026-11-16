"""Show paired H-input changes for every province;not a prediction score."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='urban_population_recipe_20261116'
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_population_recipe_20261116'


def main():
    result=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==hashlib.sha256((OUT/'results.json').read_bytes()).hexdigest()
    fig,ax=plt.subplots(figsize=(10,12),layout='constrained')
    rows=[r for r in result['provinces'] if r['variant']=='floodplain_settlement_base' and r['cohort']=='strict' and r['n']]
    assert len(rows)==40
    for variant,color,label,offset in [('floodplain_settlement_base','#286c9b','Floodplain, same settlement-base recipe',-.15),('floodplain_P2_Frier','#c16b39','Floodplain + P2/Frier recipe',.15)]:
        values=[r for r in result['provinces'] if r['variant']==variant and r['cohort']=='strict' and r['n']]
        med=np.array([r['positive_pair_log_H_change_p50'] for r in values]);lower=np.array([r['positive_pair_log_H_change_p25'] for r in values]);upper=np.array([r['positive_pair_log_H_change_p75'] for r in values])
        ax.errorbar(med,np.arange(len(values))+offset,xerr=[med-lower,upper-med],fmt='o',markersize=3.5,color=color,label=label,capsize=2)
    labels=[f'{r["province_name"]}  (n={r["n"]}{", small" if r["small_sample"] else ""})' for r in rows]
    ax.set(yticks=np.arange(len(rows)),yticklabels=labels,xlabel='Median paired log(H new / H legacy); bars = interquartile range',
           title='Population inputs change local H before any size model is refitted\nAll 40 strict-target provinces; all 153 targets retain positive H')
    ax.tick_params(axis='y',labelsize=8);ax.invert_yaxis();ax.axvline(0,color='#555',linewidth=1);ax.grid(axis='x',alpha=.2);ax.legend(loc='lower right',fontsize=8)
    fig.savefig(OUT/'province_H_changes.png',dpi=160)
    svg=OUT/'province_H_changes.svg';fig.savefig(svg,metadata={'Date':None});svg.write_text('\n'.join(a.rstrip() for a in svg.read_text().splitlines())+'\n');plt.close(fig)


if __name__=='__main__':main()

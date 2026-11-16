"""Show every fold's empirical hierarchy forecast score,with no adoption claim."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='urban_hierarchy_refresh_20261116'
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_hierarchy_refresh_20261116'


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==hashlib.sha256((OUT/'results.json').read_bytes()).hexdigest()
    fig,axes=plt.subplots(1,2,figsize=(10,4.2),layout='constrained')
    for ax,cohort,title in zip(axes,['all','strict'],['All 664 catalogue extents','153 strict inhabited-area targets']):
        for variant,color,label in [('legacy','#b76a38','Legacy H,isolated training'),('refreshed','#287a9e','Refreshed H,isolated training')]:
            rows=[a for a in r['fold_scores'] if a['variant']==variant and a['cohort']==cohort]
            ax.plot([a['outer'] for a in rows],[a['log_area_crps'] for a in rows],marker='o',color=color,label=label)
        ax.set(title=title,xlabel='Held-out province fold',ylabel='Empirical log-area CRPS;lower is better',xticks=range(4));ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle('Joint hierarchy: modest input gains under a common train-only protocol\nFive fixed seeds; no new source validation or map adoption',fontsize=12)
    fig.savefig(OUT/'hierarchy_forecast_comparison.png',dpi=160)
    svg=OUT/'hierarchy_forecast_comparison.svg';fig.savefig(svg,metadata={'Date':None});svg.write_text('\n'.join(a.rstrip() for a in svg.read_text().splitlines())+'\n');plt.close(fig)


if __name__=='__main__':main()

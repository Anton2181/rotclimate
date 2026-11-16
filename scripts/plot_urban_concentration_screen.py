"""Plot all declared primary-grid screen aggregates after independent review."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt'] = 'urban_concentration_20261116'
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/urban_concentration_20261116'


def main():
    result = json.loads((OUT/'results.json').read_text()); review = json.loads((OUT/'review.json').read_text())
    assert review['status'] == 'passed'
    assert review['results_sha256'] == hashlib.sha256((OUT/'results.json').read_bytes()).hexdigest()
    cases = result['cases']; summary = []
    for pool in ['floodplains','mexico']:
        for cell in [3,9]:
            for reading in ['low','central']:
                for family in ['hinterland','rank_control']:
                    for q in [1.,1.25,1.5,2.]:
                        sub = [a for a in cases if (a['pool'],a['cell_km'],a['reading'],a['family'],a['exponent']) == (pool,cell,reading,family,q)]
                        assert len(sub) == 5
                        row = dict(pool=pool,cell_km=cell,reading=reading,family=family,exponent=q,seeds=5)
                        for k in ['interval_ks_lower_bound','paired_interval_hit','paired_mean_log_distance','largest_area_ha','above200','lower_bound_hits','upper_bound_hits']:
                            vals = [a[k] for a in sub]
                            row['mean_'+k] = float(np.mean(vals)) if all(v is not None for v in vals) else None
                        summary.append(row)
    with (OUT/'summary.csv').open('w',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    fig, axes = plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for i,(pool,label) in enumerate([('floodplains','Mesopotamian towns'),('mexico','Mexican small settlements')]):
        for j,(metric,title) in enumerate([('interval_ks_lower_bound','Area CDF gap lower bound'),('paired_mean_log_distance','Paired log distance from source area')]):
            ax = axes[i,j]
            for reading,color in [('low','#2878a8'),('central','#b85b30')]:
                for family,style in [('hinterland','-'),('rank_control','--')]:
                    rows = [r for r in summary if (r['pool'],r['cell_km'],r['reading'],r['family']) == (pool,3,reading,family)]
                    ax.plot([r['exponent'] for r in rows],[r['mean_'+metric] for r in rows],style,color=color,marker='o',label=f'{reading}: {family.replace("_"," ")}')
            ax.set(title=f'{label}\n{title}',xlabel='Redistribution exponent (1 = baseline)',ylabel='Five-seed mean; lower is better',xticks=[1,1.25,1.5,2])
            ax.grid(alpha=.2);ax.set_ylim(bottom=0)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Fixed requested urban population: concentration worsens both comparisons\n3 km primary grid; development evidence, no map adoption',fontsize=13)
    fig.savefig(OUT/'primary_comparison.png',dpi=160)
    svg = OUT/'primary_comparison.svg'
    fig.savefig(svg,metadata={'Date':None})
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)


if __name__ == '__main__': main()

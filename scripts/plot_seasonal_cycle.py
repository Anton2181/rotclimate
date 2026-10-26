"""Show initialization effects and whole-domain annual-repeatability checks."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from local_benchmark_protocol import file_hash,write_json


def main():
    out=ROOT/'output/seasonal_cycle_20261026_verified';path=out/'review.json';review=json.loads(path.read_text())
    if not review['complete'] or not review['all_per_step_checks_passed']:raise ValueError('Need the complete, numerically verified pilot')
    rows=review['records'];names=['north_india','iran_plateau','iberia','r38_atlas','r39_candidate']
    labels=['North India','Iran plateau','Iberia','Published r38 world','r39 research world']
    fields=['temperature','rain','water','soil_water','recycled_rain','snow_water']
    fig,axes=plt.subplots(1,2,figsize=(12,5.2),constrained_layout=True)
    for ax,years in zip(axes,[1,3]):
        matrix=[];map_ok=[]
        for name in names:
            row=next(r for r in rows if r['name']==name and r['extra_years']==years)
            cycle=row['numerics']['annual_cycle'];last=cycle['comparisons'][-1]
            matrix.append([last['fields'][key]['domain_max_abs']/cycle['limits'][key] for key in fields])
            map_ok.append(last['map_land_repeats'])
        matrix=np.array(matrix)
        im=ax.imshow(np.minimum(matrix,2),norm=TwoSlopeNorm(vmin=0,vcenter=1,vmax=2),cmap='RdYlGn_r',aspect='auto')
        for i,j in np.ndindex(matrix.shape):
            ax.text(j,i,f'{matrix[i,j]:.2g}',ha='center',va='center',fontsize=9,color='#222222',
                    bbox=dict(facecolor='white',alpha=.65,edgecolor='none',pad=1))
        ax.set(xticks=np.arange(6),xticklabels=['T','Rain','Vapor','Soil','Rain memory','Snow'],
               yticks=np.arange(5),yticklabels=[label+(' · land passes' if ok else '') for label,ok in zip(labels,map_ok)],
               title=f'{years} extra year'+('s' if years!=1 else '')+' · final two complete cycles')
        ax.tick_params(axis='x',rotation=35)
    fig.colorbar(im,ax=list(axes),shrink=.8,label='Maximum / repeatability limit (>1 fails; colour capped at 2)')
    fig.suptitle('Do the deterministic annual cycles repeat?',fontsize=15)
    fig.supxlabel('All 15 runs passed their per-step solves. Three extra years settle mapped land in all five cases;\n'
                  'North India retains a small soil-water mismatch outside the scored map. These are not climate-error intervals.',fontsize=9)
    fig.savefig(out/'annual_repeatability.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(12,6.8),constrained_layout=True)
    for column,name in enumerate(names[:3]):
        values=[]
        for years in [0,3]:
            with (out/name/f'years_{years}.pkl').open('rb') as stream:
                import pickle
                result=pickle.load(stream)['result']
            from rotclimate.koppen import monthly_stats
            st=monthly_stats(result.T,result.P,result.days,result.params.year_days,
                summer_solstice=result.params.winter_solstice_day+result.params.year_days/2)
            with np.load(ROOT/f'output/constrained_blend_20261025/development/g0.9995_a1/cells/{name}.npz') as old:
                observed=old['Po'].mean(1);i,j=old['i'],old['j']
            values.append(st['Pm'][:,i,j].mean(1))
        ax=axes[0,column];ax.plot(observed,c='#222222',label='Observed');ax.plot(values[0],c='#3b78a5',label='Current primer')
        ax.plot(values[1],c='#d87828',ls='--',label='+3 complete years')
        ax.set(title=labels[column],ylabel='Rain (mm/month)' if column==0 else None)
        if column==0:ax.legend(fontsize=8)
        axes[1,column].bar(np.arange(12),values[1]-values[0],color='#3b78a5')
        axes[1,column].axhline(0,c='#777777',lw=.5)
        axes[1,column].set(ylabel='Change from current (mm/month)' if column==0 else None)
    for ax in axes.flat:
        ax.set_xticks(np.arange(12),list('JFMAMJJASOND'));ax.grid(axis='y',alpha=.15)
    fig.suptitle('Longer spin-up barely changes regional rainfall; the main biases remain',fontsize=14)
    fig.supxlabel('Same r39 physics, planet and forcing. Three reused development regions at 56 km. No calibration or atlas-climate adoption.',fontsize=9)
    fig.savefig(out/'rainfall_initialization.png',dpi=150);plt.close(fig)
    write_json(out/'figures.json',dict(review_sha256=file_hash(path),plotter_sha256=file_hash(Path(__file__)),
        pictures_sha256={name:file_hash(out/name) for name in ['annual_repeatability.png','rainfall_initialization.png']}))


if __name__=='__main__':main()

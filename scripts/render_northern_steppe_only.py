"""Maps, seasonal charts and world/planet table for the sole-steppe experiment."""
import csv
import hashlib
import html
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rotclimate.koppen import CODES,COLORS,DESCRIPTIONS

OUT=ROOT/'output/northern_steppe_only_20261116';VIEW=OUT/'presentation'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    review=json.loads((OUT/'review.json').read_text());assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    comparison=json.loads((OUT/'comparison.json').read_text());protocol=json.loads((ROOT/'calibration/northern_steppe_only_20261116/protocol.json').read_text())
    best=json.loads((OUT/'best_params.json').read_text());base=protocol['base'];VIEW.mkdir(exist_ok=True)
    with np.load(OUT/'preview.npz') as z:a={k:z[k] for k in z.files}
    fig,axes=plt.subplots(2,3,figsize=(18,8.5),layout='constrained',facecolor='#f7f8f4')
    lut=np.array([COLORS[c] for c in CODES])/255.;slices={};classes=set()
    for row,name in enumerate(['baseline','candidate']):
        inmap=a[name+'__inmap'];yy,xx=np.nonzero(inmap);crop=(slice(yy.min(),yy.max()+1),slice(xx.min(),xx.max()+1));slices[name]=crop
        land=a[name+'__land'][crop];target=a[name+'__steppe_mask'][crop]
        for col in range(3):
            ax=axes[row,col];ax.set_facecolor('#d6e4f0');ax.set_xticks([]);ax.set_yticks([])
            for spine in ax.spines.values():spine.set_visible(False)
        t=axes[row,0].imshow(np.ma.array(a[name+'__MAT'][crop],mask=~land),cmap='coolwarm',vmin=-30,vmax=40)
        rain=axes[row,1].imshow(np.ma.array(a[name+'__MAP'][crop],mask=~land),cmap='YlGnBu',norm=LogNorm(10,3000))
        kg=a[name+'__koppen'][crop];rgb=lut[kg];rgb[~land]=[214/255,228/255,240/255];axes[row,2].imshow(rgb)
        classes.update(map(int,np.unique(kg[land])))
        for ax in axes[row]:
            ax.contour(target.astype(float),levels=[.5],colors='white',linewidths=2.5)
            ax.contour(target.astype(float),levels=[.5],colors='#202020',linewidths=.8)
        for ax,title in zip(axes[row],['Mean annual temperature','Annual precipitation','Köppen climate']):
            ax.set_title(('Published baseline' if name=='baseline' else 'Steppe-only fit')+' · '+title,fontsize=11)
    fig.colorbar(t,ax=list(axes[:,0]),fraction=.025,pad=.01,label='°C')
    fig.colorbar(rain,ax=list(axes[:,1]),fraction=.025,pad=.01,label='mm/year (log scale)')
    fig.suptitle('Only the outlined northern cold-dry region entered the fit\nFixed r44 physics recipe · ds16, mean of three surroundings · isolated exploratory world/planet fit',fontsize=15)
    fig.supxlabel('Other painted zones were excluded from selection. Map orientation and surrounding land were free; this is not an adopted atlas.',fontsize=11)
    fig.savefig(VIEW/'climate_comparison.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(13,1.7),layout='constrained');ax.axis('off')
    handles=[Patch(facecolor=lut[i],label=f'{CODES[i]}: {DESCRIPTIONS[CODES[i]]}') for i in sorted(classes)]
    ax.legend(handles=handles,loc='center',ncol=5,frameon=False,fontsize=9)
    fig.savefig(VIEW/'koppen_legend.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.1),layout='constrained');months=np.arange(1,13)
    for name,color in [('baseline','#3b718d'),('candidate','#b65532')]:
        m=comparison['ensemble'][name]
        for ax,field in zip(axes,['monthly_T_median','monthly_P_median']):
            ax.plot(months,m[field],marker='o',label='Baseline' if name=='baseline' else 'Steppe-only fit',color=color)
    for ax,ylabel in zip(axes,['Temperature (°C)','Precipitation (mm/month)']):
        ax.set(xlabel='Diagnostic month (12 equal bins from calendar day 0)',ylabel=ylabel,xticks=months);ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Median climate inside the sole northern target; three-layout mean fields')
    fig.savefig(VIEW/'target_seasonal_cycle.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,3.5),layout='constrained')
    rows=[json.loads(s) for s in (OUT/'evals.jsonl').read_text().splitlines()];rows.sort(key=lambda r:r['eval'])
    scores=[r['score'] for r in rows];ax.plot([r['eval'] for r in rows],scores,'.',color='#6d8e9e',label='Evaluated world')
    ax.plot(np.arange(1,98),np.maximum.accumulate(scores),color='#ad5a38',label='Best so far')
    ax.set(xlabel='Evaluation index (budget 97)',ylabel='Sole-target cold-dry membership',ylim=(0,1.03));ax.legend();ax.grid(alpha=.2)
    fig.savefig(VIEW/'search.png',dpi=160);plt.close(fig)
    units={'lat_center':'degrees N','north_bearing':'degrees clockwise from map top','tilt':'degrees',
           'eccentricity':'dimensionless','perihelion_after_solstice':'days after winter solstice',
           'solar_flux':'Earth flux multiple','greenhouse_wm2':'W/m²','planet_radius':'Earth radii',
           'beyond_continuity_km':'km','beyond_relief_m':'m','retrograde':'boolean',
           'cross_equatorial_transport':'existing model coefficient','ebm_land_scale':'existing EBM land-response factor'}
    parameterrows=[]
    for name,lo,hi in protocol['space']:
        v=best[name];parameterrows.append(dict(parameter=name,baseline=base[name],candidate=v,
            units=units.get(name,'land fraction'),lower_bound=lo,upper_bound=hi,
            within_one_percent_of_bound=False if isinstance(v,bool) else min((v-lo)/(hi-lo),(hi-v)/(hi-lo))<=.01))
    with (VIEW/'parameters.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(parameterrows[0]));w.writeheader();w.writerows(parameterrows)
    table=''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in ['parameter','baseline','candidate','units'])+'</tr>' for r in parameterrows)
    m=comparison['ensemble']['candidate'];b=comparison['ensemble']['baseline']
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Northern-steppe-only experiment</title>
<style>body{{max-width:1400px;margin:32px auto;padding:0 20px;font:16px/1.5 system-ui;color:#24333b;background:#f7f8f4}}img{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:8px;border-bottom:1px solid #ccd3cf;text-align:left}}.scroll{{overflow:auto}}a{{color:#1c6682}}</style>
<h1>Northern-steppe-only experiment</h1><p>Only the outlined painted cold-dry zone entered the loss. All other target zones and global realism/spill penalties had zero weight. This is an exploratory fit, with no atlas adoption.</p>
<p>Fine-grid three-layout target membership: {b['score']:.4f} → {m['score']:.4f}. Cold steppe (BSk): {b['BSk_share']:.1%} → {m['BSk_share']:.1%}; cold desert (BWk): {b['BWk_share']:.1%} → {m['BWk_share']:.1%}.</p>
<img src="climate_comparison.png" alt="Baseline and sole-target candidate temperature, rainfall and Köppen maps, with sole target outlined"><img src="koppen_legend.png" alt="Köppen colour legend">
<p>The existing cold-dry rule rewards cool annual temperature and aridity; it does not demand grassland or exclude desert. World north direction and surrounding land were free. The result is one bounded search outcome, not uniquely identified planetary facts.</p>
<img src="target_seasonal_cycle.png" alt="Monthly temperature and rainfall in the target"><img src="search.png" alt="All 97 sole-target search scores">
<h2>World and planetary parameters</h2><p>Earth day, 365-day year, gravity, terrain and shared physical recipe stayed fixed. Radius uses the existing first-order world scaling. Latitude/orientation, surrounding land, EBM land scale and cross-equatorial transport were among the 19 free knobs. <a href="parameters.csv">Download exact parameter table</a>.</p>
<div class="scroll"><table><thead><tr><th>Parameter</th><th>Baseline</th><th>Candidate</th><th>Units</th></tr></thead><tbody>{table}</tbody></table></div>
<p>97 coarse evaluations; selected candidate checked at ds16 with three surrounding-world layouts. The finer comparison did not reselect the winner. Neither native ds8 qualification nor Earth validation is claimed. <a href="../review.json">Independent numerical review</a></p></html>'''
    (VIEW/'index.html').write_text(page)
    files=['climate_comparison.png','koppen_legend.png','target_seasonal_cycle.png','search.png','parameters.csv','index.html']
    manifest=dict(renderer_sha256=sha(Path(__file__)),preview_sha256=sha(OUT/'preview.npz'),
        comparison_sha256=sha(OUT/'comparison.json'),review_sha256=sha(OUT/'review.json'),
        files_sha256={n:sha(VIEW/n) for n in files},adopt=False)
    (VIEW/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Rendered world/planet experiment maps, seasonal chart, exact parameters and local viewer')


if __name__=='__main__':main()

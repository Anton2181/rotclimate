"""Reviewed seasonal resident-support and cohort comparison maps, fixed town sites."""
import csv
import hashlib
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_candidate_seasonal_20261116';BASE=ROOT/'output/urban_hierarchy_candidate_20261116'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text());replay=json.loads((OUT/'replay.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    assert replay['status']=='passed' and replay['results_sha256']==sha(OUT/'results.json')
    dest=OUT/'presentation';dest.mkdir(exist_ok=True);terrain=np.asarray(Image.open(BASE/'terrain.png').convert('RGB'));h,w=terrain.shape[:2]
    with np.load(OUT/'town_model.npz') as z:a={k:z[k] for k in z.files}
    lookup={c['key']:c for c in r['cases']};payload={};files=[]
    for mode in ['raw','corrected']:
        sites=json.loads((BASE/f'control/placed_{mode}_sites.json').read_text())['sites'];xy=np.array([(s['column']+.5,s['row']+.5) for s in sites])
        for reading in ['central','low']:
            for hours in [600,300]:
                keys=[f'{mode}_{label}_{reading}_h{hours}' for label in ['control','candidate']]
                values=[np.divide(a[k+'__target'],a[k+'__request'],out=np.zeros(len(sites)),where=a[k+'__request']>0) for k in keys]
                fig,axes=plt.subplots(1,3,figsize=(18,5),layout='constrained',facecolor='#f7f8f4')
                for ax in axes:
                    ax.imshow(terrain,extent=(0,w,h,0));ax.set(xlim=(0,w),ylim=(h,0));ax.axis('off')
                for ax,k,v,label in zip(axes[:2],keys,values,['Published-size control','Candidate sizes']):
                    c=lookup[k];dots=ax.scatter(xy[:,0],xy[:,1],s=7,c=v,cmap='RdYlGn',vmin=0,vmax=1,linewidths=.12,edgecolors='#324742')
                    status='Certified frozen allocation' if c['qualified'] else 'UNQUALIFIED trial'
                    ax.set_title(f'{label}\n{c["supported"]:,.0f} / {c["requested"]:,.0f} requested residents\n{status}; {c["active_institutions"]} funded cohorts',fontsize=10)
                change=axes[2].scatter(xy[:,0],xy[:,1],s=7,c=values[1]-values[0],cmap='RdBu',vmin=-.25,vmax=.25,linewidths=.12,edgecolors='#324742')
                axes[2].set_title('Candidate − control fraction retained\nBlue = larger fraction; red = smaller fraction',fontsize=10)
                fig.colorbar(dots,ax=list(axes[:2]),fraction=.026,pad=.015,label='Fraction of requested residents retained')
                fig.colorbar(change,ax=axes[2],fraction=.026,pad=.015,label='Change in fraction (colours clip at ±0.25)',extend='both')
                fig.suptitle(f'{mode.capitalize()} · {"size-dependent request density" if reading=="central" else "100 residents/ha request density"} · {hours} annual field hours/worker\nSeasonal cereal scenario: actual source people/work, repeating stores and transport losses',fontsize=13)
                fig.supxlabel('Fixed recruitment mix, earliest eligible harvest and quarterly travel sampling. Rural deficits remain explicit; no all-world food-feasible or adoption claim.',fontsize=10)
                name=f'{mode}_{reading}_h{hours}.png';fig.savefig(dest/name,dpi=150);plt.close(fig);files.append(name)
                payload[f'{mode}_{reading}_h{hours}']=dict(ids=[s['id'] for s in sites],xy=xy.tolist(),
                    control_fraction=values[0].tolist(),candidate_fraction=values[1].tolist(),
                    control_people=a[keys[0]+'__target'].tolist(),candidate_people=a[keys[1]+'__target'].tolist())
    (dest/'plot_data.json').write_text(json.dumps(payload,separators=(',',':'))+'\n');files.append('plot_data.json')
    summary=[]
    for mode in ['raw','corrected']:
        for reading in ['central','low']:
            old=lookup[f'{mode}_control_{reading}_h600'];new=lookup[f'{mode}_candidate_{reading}_h600']
            summary.append(f'<tr><td>{mode} / {reading}</td><td>{old["supported"]:,.0f}</td><td>{new["supported"]:,.0f}</td><td>{old["active_institutions"]} → {new["active_institutions"]}</td><td>{old["qualified"]} / {new["qualified"]}</td></tr>')
    images=''.join(f'<h2>{html.escape(name[:-4].replace("_"," "))}</h2><img src="{name}" alt="Paired seasonal resident-support map">' for name in files if name.endswith('.png'))
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Seasonal settlement support</title>
<style>body{{max-width:1500px;margin:30px auto;padding:0 20px;background:#f7f8f4;color:#263840;font:16px/1.5 system-ui}}img{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #cbd3cf;padding:8px;text-align:left}}.scroll{{overflow:auto}}a{{color:#17607b}}</style>
<h1>Seasonal settlement support</h1><p>The same fixed towns, original finite people and crop/work inputs, now tested with harvest timing, repeating stores and paid transport loss. Candidate and control use the same assumptions.</p>
<p>A certified frozen allocation passes fresh physical food/work/population checks. It is distinct from numerical fixed-point convergence and from maximum sustainable population. Density readings define the original resident requests; these reduced occupancies do not refit or certify the town footprints. Unsupported rural origins remain visible and do not export their meals. This is a partial cereal scenario; no atlas adoption or complete diet/labour claim.</p>
<div class="scroll"><table><thead><tr><th>600-hour scenario</th><th>Control residents</th><th>Candidate residents</th><th>Funded 100-person cohorts</th><th>Physical certificate, control/candidate</th></tr></thead><tbody>{''.join(summary)}</tbody></table></div>
<p><a href="../towns.csv">Every town/scenario CSV</a> · <a href="../summary.csv">Scenario totals</a> · <a href="../review.json">Independent review</a> · <a href="../replay.json">Fresh-point replay</a></p>
{images}</html>'''
    (dest/'index.html').write_text(page);files.append('index.html')
    manifest=dict(renderer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
        review_sha256=sha(OUT/'review.json'),replay_sha256=sha(OUT/'replay.json'),terrain_sha256=sha(BASE/'terrain.png'),
        files_sha256={n:sha(dest/n) for n in files},adopt=False)
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Rendered eight paired seasonal support comparisons')


if __name__=='__main__':main()

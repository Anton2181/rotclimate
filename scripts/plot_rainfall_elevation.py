"""Descriptive r38 rainfall diagnosis by height; no candidate selection or refit."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    source=ROOT/'output/rain_structure_20261025/reference_recovery/cells/north_india.npz'
    out=ROOT/'output/rain_structure_20261025/elevation_diagnosis';out.mkdir(exist_ok=True)
    bands=[(0,500),(500,1500),(1500,3000),(3000,4500),(4500,10000)]
    records=[]
    with np.load(source) as z:
        for low,high in bands:
            mask=(z['elev']>=low)&(z['elev']<high)
            simulated=z['Ps'][:,mask].astype(float).mean(1)
            observed=z['Po'][:,mask].astype(float).mean(1)
            records.append(dict(low_m=low,high_m=high,cells=int(mask.sum()),
                simulated_monthly_mm=simulated.tolist(),observed_monthly_mm=observed.tolist(),
                simulated_annual_mm=float(simulated.sum()),observed_annual_mm=float(observed.sum())))
    result=dict(region='north_india',cell_km=56,physics='r38',
        diagnostic_only=True,bands=records,
        note='Descriptive development-region analysis after inspecting these bands; no predeclared confirmatory test. '
             'Native scored cells; constant projected cell area. Height covaries with location. '
             'Different elevation groups are not matched causal experiments. No additional climate runs or fitted parameters.',
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
    fig,(ax,season)=plt.subplots(1,2,figsize=(12,4.8),constrained_layout=True)
    x=np.arange(len(bands));width=.36
    ax.bar(x-width/2,[r['observed_annual_mm'] for r in records],width,color='#3672aa',label='WorldClim observed')
    ax.bar(x+width/2,[r['simulated_annual_mm'] for r in records],width,color='#cf7547',label='r38 simulated')
    labels=['0–0.5 km','0.5–1.5 km','1.5–3 km','3–4.5 km','above 4.5 km']
    ax.set_xticks(x,[label+f'\n{r["cells"]} cells' for label,r in zip(labels,records)])
    ax.set_ylabel('Annual rainfall (mm)');ax.set_title('Dry foothills and excessive high-plateau rain')
    ax.legend(frameon=False,fontsize=9);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    months=np.arange(1,13)
    for i,color,label in [(1,'#3b779c','500–1,500 m'),(4,'#a45b48','above 4,500 m')]:
        r=records[i]
        season.plot(months,r['observed_monthly_mm'],color=color,label=label+' · observed',linewidth=2)
        season.plot(months,r['simulated_monthly_mm'],color=color,ls='--',label=label+' · simulated',linewidth=2)
    season.set_xticks(months,list('JFMAMJJASOND'));season.set_ylabel('Monthly rainfall (mm)')
    season.set_title('Opposite rainfall biases across the elevation groups')
    season.grid(alpha=.15);season.legend(frameon=False,fontsize=8)
    fig.suptitle('North India rainfall on the reproduced r38 reference',fontsize=14)
    fig.supxlabel('56 km scored land cells grouped by height. Descriptive diagnosis; elevation and location covary. No new fit.',fontsize=9)
    fig.savefig(out/'rainfall_elevation.png',dpi=140);plt.close(fig)
    print('Saved rainfall elevation diagnosis from the verified r38 cell cache.')


if __name__=='__main__':main()

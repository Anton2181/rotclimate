"""Scientific timing figure from reviewed reconstructed calendars; no food model."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm,ListedColormap
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_earth_calendars_20261116'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    result=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed_original_model_calendar_and_source_partition_review'
    assert review['results_sha256']==sha(OUT/'results.json') and review['calendars_sha256']==sha(OUT/'calendars.npz')
    a=dict(np.load(OUT/'calendars.npz'))
    annual=dict(np.load(ROOT/'output/urban_seasonal_transfer_20261116/wind_1981/prepared/low_central.npz'))
    rows=list(csv.DictReader((OUT/'monthly_energy.csv').open()))
    months=[r['label'] for r in rows];base=np.array([float(r['base_annual_work_limited_person_years']) for r in rows])/1e6
    basin=np.array([float(r['basin_annual_work_limited_person_years']) for r in rows])/1e6
    fig,(left,right)=plt.subplots(1,2,figsize=(14,6),gridspec_kw={'width_ratios':[1.3,1]},layout='constrained')
    lat=annual['lat'].ravel();lon=annual['grid_lon'].ravel();land=annual['land'].ravel();source=a['source_indices']
    left.scatter(lon[land],lat[land],s=1,c='#e5e7e8',rasterized=True)
    valid=a['base_potential_kcal']>0
    colors=ListedColormap(plt.get_cmap('twilight_shifted')(np.linspace(0,1,12,endpoint=False)))
    points=left.scatter(lon[source[valid]],lat[source[valid]],c=a['base_boundary'][valid],s=4,
                        cmap=colors,norm=BoundaryNorm(np.arange(-.5,12.5),12),rasterized=True)
    flood=a['basin_potential_kcal']>0
    left.scatter(lon[source[flood]],lat[source[flood]],s=7,facecolors='none',edgecolors='#15191d',linewidths=.35)
    left.set(xlabel='Longitude (°E)',ylabel='Latitude (°N)',title='Recovered base-cereal harvest boundary')
    left.set_xlim(lon[source].min()-1,lon[source].max()+1);left.set_ylim(lat[source].min()-1,lat[source].max()+1)
    left.set_aspect(1/np.cos(np.deg2rad(38)))
    bar=fig.colorbar(points,ax=left,orientation='horizontal',ticks=np.arange(12),fraction=.06,pad=.08)
    bar.ax.set_xticklabels(months,fontsize=8);bar.set_label('First strict best model season; black rings mark floodplain sources',fontsize=9)
    right.bar(np.arange(12),base,color='#407798',label='Base component')
    right.bar(np.arange(12),basin,bottom=base,color='#d8a64b',label='Floodplain component')
    right.set(xticks=np.arange(12),xticklabels=months,ylabel='Annual-work-limited grain (million person-years)',
              title='Timing assigned to the unchanged annual grain total')
    right.set_ylim(0,float((base+basin).max())*1.12)
    right.legend(frameon=False);right.grid(axis='y',alpha=.2);right.set_axisbelow(True)
    fig.suptitle('Earth source-calendar reconstruction • no seasonal food simulation',fontsize=15)
    fig.supxlabel('Model timing, not observed harvest dates. No revised work, storage loss, rural meals or transport dispatch is simulated here.',fontsize=10)
    fig.savefig(OUT/'timing.png',dpi=160);plt.close(fig)
    receipt=dict(status='rendered_reviewed_model_calendar_timing',producer_sha256=sha(Path(__file__)),
        results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),timing_sha256=sha(OUT/'timing.png'),
        map_base_source_points=int(valid.sum()),basin_ring_sources=int(flood.sum()),
        annual_grain_person_years=float((base+basin).sum()*1e6),seasonal_food_trial=False,adopt=False)
    (OUT/'presentation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['status'],flush=True)


if __name__=='__main__':main()

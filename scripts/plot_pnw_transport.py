"""Correct PNW chart axes from frozen raw arrays; never rerun the climate."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rotclimate import earth
from scripts.circulation_reference import acquire
from scripts.local_benchmark_protocol import file_hash,write_json


def monthly_component(vectors,mask,area,component=0):
    """Twelve true-area component means; preserve the month axis."""
    v=np.asarray(vectors);m=np.asarray(mask);a=np.asarray(area)
    if v.shape!=(12,2,len(a)) or m.shape!=a.shape or not m.any() or (a[m]<=0).any():
        raise ValueError('Need twelve monthly east/north vectors and selected positive native areas')
    return np.average(v[:,:,m],axis=2,weights=a[m])[:,component]


def main():
    out=ROOT/'output/pnw_transport_20261027';review=json.loads((out/'review.json').read_text());protocol=json.loads((out/'protocol.json').read_text());plan=protocol['plan']
    for n,h in protocol['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed scientific source: '+n)
    saved={}
    for n,row in review['rows'].items():
        source=out/(n+'.npz')
        if file_hash(source)!=row['arrays_sha256']:raise ValueError('Changed raw vectors')
        with np.load(source) as z:saved[n]={k:z[k] for k in z.files}
    fields,_=acquire(ROOT,plan);field=fields['pacific_nw','shum'];lon,lat=np.meshgrid(field.longitude-360,field.latitude)
    case=earth.region_case('pacific_nw',plan['cell_km']);g=case.grid
    sample=saved['reference'];valid=sample['circulation_mask_land']|sample['circulation_mask_ocean'];selection=valid.reshape(lon.shape)
    native=sample['circulation_reference_q925_300'];names=['NCEP/NCAR',*plan['profiles']]
    labels=dict(reference='r39',reservoir_control='Previous reservoirs',column_no_mix='Corrected closure')
    fig,axes=plt.subplots(2,4,figsize=(14,8),constrained_layout=True)
    for i,(season,months) in enumerate([('Winter (DJF)',[11,0,1]),('Summer (JJA)',[5,6,7])]):
        days=np.array([31,28,31,30,31,30,31,31,30,31,30,31])[months]
        for ax,n in zip(axes[i],names):
            v=np.average((native if n=='NCEP/NCAR' else saved[n]['circulation_model'])[months],axis=0,weights=days)
            ax.set_facecolor('#f8fbfd')
            ax.contourf(case.lon,g.lat,g.land.astype(float),levels=[.5,1.5],colors=['#dedede'],antialiased=False)
            arrows=ax.quiver(lon[selection],lat[selection],v[0,valid],v[1,valid],angles='uv',scale=70,width=.007,color='#265b8a')
            ax.quiverkey(arrows,.12,.91,10,'10 m/s',labelpos='E',coordinates='axes')
            ax.set(xlim=(-130,-110),ylim=(40,53),xlabel='Longitude (°E)',ylabel='Latitude (°N)',title=season+' · '+labels.get(n,n))
            ax.set_aspect(1/np.cos(np.radians(46)))
    fig.suptitle('Pacific Northwest · matched native partial-column circulation',fontsize=16)
    fig.supxlabel('Four covered ocean footprints; no land footprint passes the conservative terrain mask. Same area aggregation and geographic vectors.\nMonthly q-weighted925–300hPa reference omits transient covariance; modeled vectors are whole-column moisture diagnostics.',fontsize=9)
    first=out/'native_vectors_v2.png';fig.savefig(first,dpi=145);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,5.4),constrained_layout=True)
    colors=['#466d96','#888888','#b16e37'];ocean=sample['circulation_mask_ocean'];area=sample['circulation_area']
    for n,c in zip(plan['profiles'],colors):
        axes[0].plot(monthly_component(saved[n]['circulation_model'],ocean,area),label=labels[n],color=c)
        axes[1].plot(review['rows'][n]['monthly_rain']['simulated'],label=labels[n],color=c)
        humidity=review['rows'][n]['circulation'].get('humidity',{}).get('scores',{}).get('ocean')
        if humidity:axes[2].plot(humidity['monthly_model_q_ratio'],label=labels[n],color=c)
    axes[0].plot(monthly_component(native,ocean,area),label='NCEP/NCAR',color='#222',lw=2.5)
    axes[1].plot(review['rows']['reference']['monthly_rain']['observed'],label='WorldClim',color='#222',lw=2.5)
    humidity=review['rows']['reservoir_control']['circulation']['humidity']['scores']['ocean']
    axes[2].plot(humidity['monthly_reference_q_ratio'],label='NCEP/NCAR',color='#222',lw=2.5)
    axes[0].set(title='Native ocean · eastward moisture wind',ylabel='Eastward speed (m/s)')
    axes[1].set(title='Regional scored land · monthly rainfall',ylabel='Rain (mm / equal model month)')
    axes[2].set(title='Native ocean · partial humidity shape',ylabel='Mean q700–300 / mean q925–700')
    for ax in axes:ax.set(xticks=range(12),xticklabels=list('JFMAMJJASOND'));ax.grid(alpha=.15);ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Pacific Northwest · transport, rainfall and vertical humidity',fontsize=16)
    fig.supxlabel('Three climate reruns reproduce parent rainfall cells and temperature scores; r39 also reproduces archived monthlyT/P.\nCoarse1981–2010 reanalysis and1970–2000 rainfall periods differ. Association is not causal attribution; no fitting or adoption.',fontsize=9)
    second=out/'monthly_diagnostics_v2.png';fig.savefig(second,dpi=145);plt.close(fig)
    write_json(out/'figures.json',dict(status='passed',climate_integrations=0,review_sha256=file_hash(out/'review.json'),
        plotter_sha256=file_hash(Path(__file__)),original_figures_preserved=review['images_sha256'],
        correction='Original monthly plot indexed January east/north instead of the twelve eastward months. Corrected component axis; raw diagnostics and climates unchanged. Map keys moved to avoid title overlap.',
        images_sha256={p.name:file_hash(p) for p in [first,second]}))


if __name__=='__main__':main()

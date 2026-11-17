"""Inspection figure for qualified original routes; no atlas or scenario update."""
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from select_warehouse_routes import OUT,ANNUAL,sha,read,write


def main():
    review=read(OUT/'review.json');assert review['status'].startswith('passed_')
    assert review['results_sha256']==sha(OUT/'results.json')
    assert not (OUT/'map_receipt.json').exists(),'Preserve completed inspection figure'
    routes=read(OUT/'routes.json');restoration=read(OUT/'restoration.json')
    with np.load(ANNUAL/'prepared/low_transport_world.npz') as z:land=z['land'];lat=z['lat'];lon=z['lon']
    flatlat,flatlon=lat.ravel(),lon.ravel()
    colors={'central':'#1264a3','low':'#cc6419'}
    fig,axes=plt.subplots(2,2,figsize=(14,9),sharex=True,sharey=True)
    for q,ax in enumerate(axes.ravel()):
        ax.contourf(lon,lat,land.astype(int),levels=[.5,1.5],colors=['#e4e4db'],zorder=0)
        ax.contour(lon,lat,land.astype(int),levels=[.5],colors=['#a8aaa2'],linewidths=.35,zorder=1)
        inter=[r for r in routes if r['quarter']==q and r['kind']=='intertown']
        central=next(r for r in inter if r['reading']=='central');low=next(r for r in inter if r['reading']=='low')
        same=central['nodes']==low['nodes']
        for r in ([central] if same else inter):
            cells=np.array(r['physical_cells']);color='#6550a1' if same else colors[r['reading']]
            ax.plot(flatlon[cells],flatlat[cells],color=color,lw=1.8,zorder=4,
                ls='-' if r['reading']=='central' else '--')
            ax.scatter(flatlon[[r['origin'],r['destination']]],flatlat[[r['origin'],r['destination']]],
                s=[27,37],marker='o',color=color,edgecolors='white',linewidths=.5,zorder=5)
            ports=r['port_membership'];landings=r['river_landing_membership']
            ax.scatter(flatlon[ports],flatlat[ports],s=36,marker='s',facecolors='none',edgecolors=color,linewidths=1,zorder=6)
            ax.scatter(flatlon[landings],flatlat[landings],s=38,marker='^',facecolors='none',edgecolors=color,linewidths=1,zorder=6)
        source=next(r for r in routes if r['quarter']==q and r['kind']=='source' and r['reading']=='central')
        cells=np.array(source['physical_cells'])
        ax.plot(flatlon[cells],flatlat[cells],color='#258354',lw=3,zorder=7)
        ax.scatter([flatlon[source['origin']]],[flatlat[source['origin']]],marker='+',color='#258354',s=70,zorder=8)
        ax.annotate('Selected source leg (9 road-km)',(flatlon[source['origin']],flatlat[source['origin']]),
            xytext=(-5,12),textcoords='offset points',ha='right',fontsize=7.5,color='#236341')
        costs=f"Central {central['saved_cost']:.2f}; low {low['saved_cost']:.2f} road-km"
        ax.set_title(f'Quarter {q+1} · original month index {q*3}\n{costs}',fontsize=11)
        ax.set_xlim(-6,36);ax.set_ylim(24,46);ax.set_aspect(1/np.cos(np.deg2rad(36)))
        ax.grid(alpha=.16);ax.tick_params(labelsize=8)
    axes[1,0].set_xlabel('Longitude (°E)');axes[1,1].set_xlabel('Longitude (°E)')
    axes[0,0].set_ylabel('Latitude (°N)');axes[1,0].set_ylabel('Latitude (°N)')
    legend=[Line2D([0],[0],color=colors['central'],lw=2,label='Central intertown'),
        Line2D([0],[0],color=colors['low'],lw=2,ls='--',label='Low intertown'),
        Line2D([0],[0],color='#6550a1',lw=2,label='Identical central + low path'),
        Line2D([0],[0],color='#258354',marker='+',lw=2,label='Source leg (both readings)'),
        Line2D([0],[0],marker='s',color='gray',markerfacecolor='none',lw=0,label='Model port membership'),
        Line2D([0],[0],marker='^',color='gray',markerfacecolor='none',lw=0,label='Model river landing membership')]
    fig.legend(handles=legend,loc='lower center',ncol=3,fontsize=8.5,bbox_to_anchor=(.5,.055),frameon=False)
    fig.suptitle('Sixteen original funded route certificates · representative least-cost paths',fontsize=15,y=.98)
    fig.text(.5,.025,'Largest recorded source and intertown leg per quarter/reading; selected before graph replay.\n'
        'Road-km costs are not durations. Symbols are network membership, not authenticated warehouses. No food or atlas update.',
        ha='center',fontsize=9)
    fig.subplots_adjust(top=.89,bottom=.18,hspace=.3,wspace=.15)
    target=OUT/'original_routes.png';fig.savefig(target,dpi=170);plt.close(fig)
    write(OUT/'map_receipt.json',dict(status='inspection_figure_from_independently_checked_original_route_certificates',
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),OUT/'routes.json',OUT/'review.json',
            OUT/'restoration.json',ANNUAL/'prepared/low_transport_world.npz']},figure_sha256=sha(target),
        route_records=16,plot_panels=4,new_graph_calls=0,new_food_calls=0,new_atlas_release=False,adopt=False))
    print('Saved',target,flush=True)


if __name__=='__main__':main()

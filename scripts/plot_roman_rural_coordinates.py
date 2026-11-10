"""Plot aggregate coordinate-hypothesis checks, never raw source locations."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def main():
    audit=json.loads((ROOT/'output/roman_rural_coordinates_20261110/audit.json').read_text())
    fig,ax=plt.subplots(figsize=(10,4.8),facecolor='#f5f5ee')
    ax.set_facecolor('#f5f5ee')
    for y,key,label,color in [(1,'X_easting_Y_northing_metres','X = easting, Y = northing','#227c70'),
                               (0,'X_northing_Y_easting_metres','Axes reversed','#a44738')]:
        row=audit['hypotheses'][key]
        lo,mid,hi=(row[k] for k in ['min_distance_metres','median_distance_metres','max_distance_metres'])
        ax.plot([lo,hi],[y,y],color=color,lw=5,solid_capstyle='round')
        ax.scatter([lo,hi],[y,y],color=color,s=45,zorder=3)
        ax.scatter([mid],[y],marker='D',color=color,s=80,zorder=4)
        ax.text((lo*hi)**.5,y+.18,f'{lo:,.0f}–{hi:,.0f} m; median {mid:,.0f} m',ha='center',color=color,fontsize=11)
    ax.axvline(audit['threshold_metres'],color='#7b7048',ls='--',lw=1.5)
    ax.text(1100,.5,'Declared 1 km check',color='#7b7048',rotation=90,va='center',fontsize=10)
    ax.set_xscale('log');ax.set_xlim(6,1000000);ax.set_ylim(-.4,1.5)
    ax.set_yticks([1,0],['X = easting\nY = northing','X = northing\nY = easting'])
    ax.set_xlabel('Distance from archive point to official heritage reference (metres, log scale)')
    ax.grid(axis='x',alpha=.15)
    ax.spines[['top','right','left']].set_visible(False)
    fig.suptitle('Rural archive coordinate check',x=.04,ha='left',fontsize=18,fontweight='bold')
    fig.text(.04,.88,'Six named sites · all eight official points retained · no fitted offsets',fontsize=11)
    fig.text(.04,.06,'Named-site schema check, not model accuracy or whole-archive survey precision.\nSources: ADS rural Britain (10.5284/1030449), Historic England official list entries.',fontsize=9,color='#555555')
    fig.subplots_adjust(left=.19,right=.97,top=.80,bottom=.22)
    out=ROOT/'reports/figures/roman_rural_coordinates_20261110.png'
    fig.savefig(out,dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    print(out)


if __name__=='__main__':main()

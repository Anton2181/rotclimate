"""Show sample selection and stated-extent agreement for the joined housing samples."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha

SURFACE='#f5f3ed';INK='#1d2a2c';MUTED='#5b6664';GRID='#a7a6a0'
# Two-series palette checked with the dataviz validator against this surface.
BRITAIN='#ad643b';OTHER='#2a78d6'
OFFSETS={'Metapontum':(10,-4),'Celsa':(10,-3),'Cassope':(-10,12),'Cuicul':(18,-18),'Bulla Regia':(12,-14),
    'Emporiae':(16,-20),'Utica':(16,-22)}


def main():
    folder=ROOT/'output/settlement_size_identity_20261112'
    result=json.loads((folder/'results.json').read_text());review=json.loads((folder/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(folder/'results.json')
    rows=result['rows'];s=result['summary'];a=result['associations']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
        'axes.edgecolor':GRID,'xtick.color':MUTED,'ytick.color':MUTED,'axes.labelcolor':MUTED,'text.color':INK})
    fig,(ax,bx)=plt.subplots(1,2,figsize=(13.5,6.4));fig.patch.set_facecolor(SURFACE)
    for axis in (ax,bx):axis.set_facecolor(SURFACE);axis.grid(alpha=.18,color=GRID,lw=.8);axis.set_axisbelow(True)

    fraction=np.array([r['sample_fraction']*100 for r in rows]);density=np.array([r['properties_per_sampled_ha'] for r in rows])
    britain=np.array([r['table_province']=='Britannia' for r in rows])
    for keep,color,marker,label in ((~britain,OTHER,'o','Other provinces (40)'),(britain,BRITAIN,'D','Britannia (10)')):
        ax.scatter(fraction[keep],density[keep],c=color,marker=marker,s=46,edgecolors=SURFACE,linewidths=1.2,label=label,zorder=3)
    bands=(('below_1_percent',.02,1),('1_to_below_10_percent',1,10),('10_to_below_100_percent',10,85),('whole_stated_extent',85,220))
    for name,left,right in bands:
        median=result['sampling_classes'][name]['median_properties_per_sampled_ha'];count=result['sampling_classes'][name]['rows']
        ax.hlines(median,left*1.08,right/1.08,color=INK,lw=2,zorder=2)
        ax.text(np.sqrt(left*right),6.6,f'median {median:.0f}\nn = {count}',ha='center',va='bottom',fontsize=9,color=MUTED)
    for edge in (1,10,85):ax.axvline(edge,color=GRID,lw=1,ls=':')
    ax.set_xscale('log');ax.set_yscale('log');ax.set_xlim(.02,220);ax.set_ylim(6,130)
    ax.set_xticks([.1,1,10,100],['0.1%','1%','10%','100%']);ax.set_yticks([10,20,50,100],['10','20','50','100'])
    ax.set_xlabel('Investigated share of the stated site extent');ax.set_ylabel('Residential properties per investigated hectare')
    every=a['all_rows']['density_vs_sampled_fraction'];partial=a['excluding_whole_extent_samples']['density_vs_sampled_fraction']
    ax.set_title('Smaller samples tend to report denser housing',loc='left',fontsize=12,pad=24)
    ax.text(0,1.02,f"Rank correlation {every['spearman_rho']:+.2f} over all 50; {partial['spearman_rho']:+.2f} without the two whole-extent samples. Bars: class medians.",
            transform=ax.transAxes,fontsize=9,color=MUTED)
    ax.legend(loc='upper right',frameon=False,fontsize=9,handletextpad=.3)

    table=np.array([r['table_site_area_ha'] for r in rows]);catalogue=np.array([r['catalogue_area_ha'] for r in rows])
    differs=np.array([r['area_agreement']=='different' for r in rows])
    bx.plot([4,330],[4,330],color=GRID,lw=1.2,zorder=1)
    bx.scatter(catalogue[~differs],table[~differs],c='#b9bdb6',s=40,edgecolors=SURFACE,linewidths=1.2,zorder=2,
               label=f"Same extent in both ({s['area_agreement']['equal']})")
    bx.scatter(catalogue[differs],table[differs],c=INK,s=52,edgecolors=SURFACE,linewidths=1.2,zorder=3,
               label=f"Different extent ({s['area_agreement']['different']})")
    for r in rows:
        if r['area_agreement']=='different':
            dx,dy=OFFSETS[r['table_name']]
            bx.annotate(f"{r['table_name']}  {r['table_site_area_ha']:g} vs {r['catalogue_area_ha']:g} ha",
                (r['catalogue_area_ha'],r['table_site_area_ha']),xytext=(dx,dy),textcoords='offset points',fontsize=9,color=INK,
                ha='left' if dx>0 else 'right',va='center',
                arrowprops=dict(arrowstyle='-',color=MUTED,lw=.7,shrinkA=0,shrinkB=3))
    bx.set_xscale('log');bx.set_yscale('log');bx.set_xlim(4,330);bx.set_ylim(4,330);bx.set_aspect('equal')
    ticks=[5,10,20,50,100,200];bx.set_xticks(ticks,[str(t) for t in ticks]);bx.set_yticks(ticks,[str(t) for t in ticks])
    bx.set_xlabel('City catalogue area (ha)');bx.set_ylabel('Housing-table site extent (ha)')
    bx.set_title('Seven of 50 samples use a different site extent',loc='left',fontsize=12,pad=24)
    bx.text(0,1.02,'All 50 joined by author key. On the line: same extent in both sources.',
            transform=bx.transAxes,fontsize=9,color=MUTED)
    bx.legend(loc='lower right',frameon=False,fontsize=9,handletextpad=.3)
    d=s['catalogue_AD150']
    fig.suptitle('Housing samples joined to the city catalogue: identity settled, measurement still open',x=.055,ha='left',fontsize=15,y=.975)
    fig.text(.055,.035,f"Catalogue occupation dates: {d['excludes']} places ended before AD 150, {d['covers']} have a dated span covering it, {d['open_or_nonnumeric']} have no recorded end. "
        'These are whole-site spans, not housing phases,\nso no sample yet qualifies as an AD 150 size label. '
        'Sources: Ortman & Hanson (2023), Britannia 54, Table 2, CC BY 4.0; Hanson (2016) Cities Database, OxREP, doi:10.5287/bodleian:eqapevAn8.',
        fontsize=9,color=MUTED,linespacing=1.5)
    fig.subplots_adjust(left=.07,right=.98,top=.83,bottom=.2,wspace=.24)
    path=ROOT/'reports/figures/settlement_size_identity_20261112.png';fig.savefig(path,dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    print(path)


if __name__=='__main__':main()

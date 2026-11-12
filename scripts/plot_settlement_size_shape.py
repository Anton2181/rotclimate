"""Show relative town sizes: conditional Roman references against the coupled allocator."""
from collections import defaultdict
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import openpyxl

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.settlement_size_shape import refused,relative_sizes
from settlement_locations_earth import sha

SURFACE='#f5f3ed';INK='#1d2a2c';MUTED='#5b6664';GRID='#a7a6a0'
ROMAN={0.0:'#86b6ef',0.2:'#2a78d6',0.5:'#104281'};ALLOCATOR='#ad643b'


def main():
    folder=ROOT/'output/settlement_size_shape_20261112'
    result=json.loads((folder/'results.json').read_text());review=json.loads((folder/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(folder/'results.json')
    wb=openpyxl.load_workbook(ROOT/'data/cache/hanson2016/cities.xlsx',read_only=True,data_only=True)
    try:city_rows=list(wb['Cities'].values);area_rows=list(wb['Areas'].values)
    finally:wb.close()
    areas=defaultdict(list)
    for row in area_rows[1:]:
        if row[0]:areas[row[0]].append(row[1])
    area=np.array([float(areas[c[0]][0]) for c in city_rows[1:] if c[0] and not refused(150,c[7],c[8]) and len(areas[c[0]])==1
                   and isinstance(areas[c[0]][0],(int,float)) and areas[c[0]][0]>0])
    assert area.size==result['cohort']['measured']
    with np.load(ROOT/'output/settlement_feedback_20261112/corrected_h600_f0.075/fields.npz') as z:towns=z['total'][z['total']>0]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
        'axes.edgecolor':GRID,'xtick.color':MUTED,'ytick.color':MUTED,'axes.labelcolor':MUTED,'text.color':INK})
    fig,(ax,bx)=plt.subplots(1,2,figsize=(13.5,6.4),gridspec_kw={'width_ratios':[1.15,1]});fig.patch.set_facecolor(SURFACE)
    for axis in (ax,bx):axis.set_facecolor(SURFACE);axis.grid(alpha=.18,color=GRID,lw=.8);axis.set_axisbelow(True)

    def curve(sizes):
        ordered=np.sort(sizes)[::-1];return np.arange(1,ordered.size+1),ordered/np.median(ordered)
    labels={0.0:'Roman areas, constant density',0.2:'Roman areas, density rising slowly with area',0.5:'Roman areas, density rising fast with area'}
    for g,color in ROMAN.items():
        rank,relative=curve(relative_sizes(area,g));ax.plot(rank,relative,color=color,lw=2,zorder=2,label=labels[g])
    rank,relative=curve(towns);ax.plot(rank,relative,color=ALLOCATOR,lw=2.4,zorder=3,label='Allocator towns')
    handles,names=ax.get_legend_handles_labels();order=[2,1,0,3]
    ax.legend([handles[i] for i in order],[names[i] for i in order],loc='lower left',frameon=False,fontsize=9,handlelength=1.6)
    ax.axhline(1,color=GRID,lw=1,ls=':');ax.set_xscale('log');ax.set_yscale('log');ax.set_xlim(.9,1300);ax.set_ylim(.02,700)
    ax.set_xticks([1,10,100,1000],['1','10','100','1,000']);ax.set_yticks([.1,1,10,100],['0.1','1','10','100'])
    ax.set_xlabel('Rank of place, largest first');ax.set_ylabel('Size relative to the median place')
    ax.set_title('Largest town is 8 times the median; Roman references reach 58 to 436',loc='left',fontsize=12,pad=24)
    ax.text(0,1.02,f"{area.size} measured Roman places of AD 150 and {towns.size:,} allocator towns (corrected climate, 600 h, 7.5%).",
            transform=ax.transAxes,fontsize=9,color=MUTED)

    tails=[('all_places','All places'),('largest_50_percent','Largest half'),('largest_25_percent','Largest quarter')]
    for i,(key,label) in enumerate(tails):
        y=len(tails)-1-i;low,high=result['reference_band'][key]['gini']
        bx.plot([low,high],[y,y],color='#cfd6dc',lw=12,solid_capstyle='round',zorder=1)
        for g,color in ROMAN.items():
            bx.scatter(result['roman']['all_measured']['scenarios']['density_exponent_%g'%g][key]['gini'],y,c=color,s=70,edgecolors=SURFACE,linewidths=1.5,zorder=3)
        value=result['allocator']['corrected_h600_f0.075']['quantities']['town_total'][key]['gini']
        bx.scatter(value,y,c=ALLOCATOR,marker='D',s=70,edgecolors=SURFACE,linewidths=1.5,zorder=3)
        bx.text(value,y+.24,f'{value:.2f}',ha='center',fontsize=9,color=INK)
        bx.text(low,y-.3,f'{low:.2f}',ha='center',fontsize=9,color=MUTED);bx.text(high,y-.3,f'{high:.2f}',ha='center',fontsize=9,color=MUTED)
    bx.set_yticks(range(len(tails)),[t[1] for t in tails][::-1]);bx.set_xlim(0,1);bx.set_ylim(-.7,2.75)
    bx.set_xlabel('Gini coefficient of sizes (0 = all equal)');bx.grid(axis='y',alpha=0)
    bx.set_title('Allocator sizes are more equal at every tail level',loc='left',fontsize=12,pad=24)
    bx.text(0,1.02,'Diamond: allocator. Dots: all Roman places. Bar: range over declared sets.',
            transform=bx.transAxes,fontsize=9,color=MUTED)
    fig.suptitle('Town sizes: the allocator has no large centres',x=.055,ha='left',fontsize=15,y=.975)
    fig.text(.055,.025,'Relative sizes only; absolute residents are not compared. Roman sizes are conditional references (area times an assumed density), not censuses.\n'
        '492 cohort places have no area and are left out, not filled. Allocator towns are generated hypotheses.\n'
        'Sources: Hanson (2016) Cities Database, OxREP, doi:10.5287/bodleian:eqapevAn8; coupled scenarios of 12 November 2026.',
        fontsize=9,color=MUTED,linespacing=1.5)
    fig.subplots_adjust(left=.07,right=.98,top=.83,bottom=.22,wspace=.28)
    path=ROOT/'reports/figures/settlement_size_shape_20261112.png';fig.savefig(path,dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    print(path)


if __name__=='__main__':main()

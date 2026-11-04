"""Show storage assumptions and the same wider landscape under all climates."""
from pathlib import Path
import gzip
import json

ROOT=Path(__file__).resolve().parents[1]


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fits=[('free_fit','raw','Free'),('earth_fit','raw','Earth raw'),('earth_fit','corrected','Earth corrected'),('whittaker_fit','raw','Whittaker')];models=[]
    for name,mode,title in fits:
        data=ROOT/'atlases'/name/'data';manifest=json.loads((data/'presence_mobility.json').read_text());p=manifest['packets'][mode]
        models.append((title,json.loads(gzip.decompress((data/p['payload']).read_bytes()))))
    out=ROOT/'output/presence_mobility_scale_20261104';fig,axes=plt.subplots(2,4,figsize=(17,9.5),facecolor='#f8faf9',gridspec_kw={'height_ratios':[1.6,1]})
    for j,(title,m) in enumerate(models):
        e=next(e for e in m['mobility_scales']['regional_dense'] if e['id']=='seasonal_grassland');sparse=next(e for e in m['mobility_scales']['regional_sparse'] if e['id']=='seasonal_grassland')
        c=e['cases'][0];r=c['mobile'];home=e['patches'][e['home']];patches=e['patches'];ground=e['ground_nodes']
        meta=json.loads((ROOT/'atlases/free_fit/data/atlas.json').read_text());km=meta['width']/m['shape'][1]*meta['mi_per_px']*1.609344;cell=m['cell_px']
        point=lambda p:((p['x']-home['x'])/cell*km,(home['y']-p['y'])/cell*km)
        ax=axes[0,j]
        for p in ground:
            x,y=point(p);ax.add_patch(Rectangle((x-km/2,y-km/2),km,km,facecolor='#e6e7de',edgecolor='none'))
        counts=np.bincount(r['locations'],minlength=len(patches))
        for i,p in enumerate(patches):
            x,y=point(p);colour='#2c7c7b' if counts[i]>0 else '#c8c6ac';ax.add_patch(Rectangle((x-km/2,y-km/2),km,km,facecolor=colour,edgecolor='none'))
        xy=np.array([point(ground[i]) for segment in r['segments'] for i in segment]);ax.plot(xy[:,0],xy[:,1],c='white',lw=3);ax.plot(xy[:,0],xy[:,1],c='#243e51',lw=1.2)
        labels={}
        for i in r['locations']:
            if i not in labels:labels[i]=chr(65+len(labels))
        for i,label in labels.items():
            x,y=point(patches[i]);ax.scatter([x],[y],s=95,c='white',edgecolors='#243e51',lw=.6,zorder=4);ax.text(x,y,label,ha='center',va='center',fontsize=7,zorder=5)
        ax.scatter([0],[0],s=145,facecolors='none',edgecolors='#a85668',marker='s',lw=1.3,zorder=6)
        ax.set_aspect('equal');ax.autoscale_view();ax.set_title(title,loc='left',fontsize=12);ax.set(xlabel='km from fixed home',ylabel='km from fixed home');ax.spines[['top','right']].set_visible(False)
        values=[c['best_fixed_base_continuous']['annual_need_met'],sparse['cases'][0]['mobile']['annual_need_met'],r['annual_need_met'],c['resource_upper_bound']['annual_need_met']]
        bar=axes[1,j];bar.bar(range(4),np.array(values)*100,color=['#b49361','#9ab8ae','#337b86','#b7c1cb'])
        for k,v in enumerate(values):bar.text(k,v*100+1,f'{v:.1%}',ha='center',fontsize=8)
        bar.set(xticks=range(4),xticklabels=['Best fixed\nall land','Sparse\ncircuit','More bases\ncircuit','Resource\nbound*'],ylim=(0,110),ylabel='Annual DM need met (%)');bar.tick_params(axis='x',labelsize=8);bar.spines[['top','right']].set_visible(False);bar.grid(axis='y',alpha=.15)
    fig.suptitle('A wider seasonal landscape: mobility gains depend on the climate fit',x=.035,ha='left',fontsize=18,y=.99)
    fig.text(.035,.945,'Same grassland anchor outside named claims · ~74 km radius · same fine-cell grazing area, 100 feed units, seven-day feed pack and two travel-days per bin',fontsize=10)
    fig.subplots_adjust(left=.05,right=.985,top=.885,bottom=.19,wspace=.3,hspace=.43)
    fig.text(.035,.035,'Grey land supplies paths; tan squares are candidate resource patches; green squares are visited. No resources from intervening land are pooled into a base.\n'
        'Best fixed base searches EVERY home-connected fine cell, including bases absent from the movement lattice. *Resource bound ignores travel and is not a feasible route.\n'
        'Water access is unresolved here. All routes are independent, perfect-foresight dry-matter scenarios, not actual camps, animal nutritional adequacy or human population.\n'
        'The regional circuits exceed the stronger fixed-base control in Free and Whittaker climates; this advantage is absent in both Earth climates.',fontsize=9,linespacing=1.5)
    fig.savefig(out/'regional_circuits.png',dpi=155,facecolor=fig.get_facecolor());plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(14,6),facecolor='#f8faf9');keys=['stores90','origin90','origin0','collect1','rural180'];x=np.arange(len(keys))
    for title,m in models:
        by={c['id']:c for c in m['presence']};counts=[sum(s['shortfall_bins']==0 for s in by[k]['sites']) for k in keys]
        axes[0].plot(x,counts,marker='o',label=title,lw=1.5)
    axes[0].set(xticks=x,xticklabels=['365-day\nexport store','90-day\nexport store','No export\nstore','Collect 1%\nof surplus','180-day\nrural store'],ylim=(-5,160),ylabel='Sites fully supplied in all 12 bins /151')
    axes[0].tick_params(axis='x',labelsize=8);axes[0].legend(frameon=False,fontsize=8);axes[0].set_title('One changed assumption at a time',loc='left',fontsize=11)
    m=models[2][1];by={c['id']:c for c in m['presence']};order=np.argsort([s['annual_need_met'] for s in by['origin90']['sites']])
    for key,label,col in [('stores90','365-day origin store','#287877'),('origin90','90-day origin store','#b99b62'),('collect1','Collect 1% of rural overflow','#925965')]:
        axes[1].plot(np.arange(1,152),[by[key]['sites'][i]['annual_need_met']*100 for i in order],label=label,c=col,lw=1.5)
    axes[1].set(xlabel='Sites ordered by the 90-day export-store scenario',ylabel='Declared annual food need met (%)',ylim=(0,105),xlim=(1,151));axes[1].legend(frameon=False,fontsize=8,loc='lower right');axes[1].set_title('Earth corrected · the same 100-person test',loc='left',fontsize=11)
    for ax in axes:ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15)
    fig.suptitle('Permanent food support is sensitive to origin storage and collection',x=.05,ha='left',fontsize=16,y=.98)
    fig.subplots_adjust(left=.07,right=.98,top=.83,bottom=.28,wspace=.24)
    fig.text(.05,.035,'Hold the 100-person ration, 90-day destination store, freight slots, paths and crop response fixed. Baseline rural stores: 365 demand-days; export stores: 365 flow-days; collection: 10%.\n'
        'These are sensitivity scenarios under the SAME fixed dispatch rule, not optimized trade or historically measured storage limits.\n'
        'The cereal-only 180-day rural-store scenario fails the protected rural requirement, so its cells export nothing. Other foods and exchange are omitted.\n'
        'No actual famine, garrison strength, staffing or sovereignty is inferred. All seven earlier provisioning cases and local circuits retain their earlier values.',fontsize=9,linespacing=1.5)
    fig.savefig(out/'origin_storage.png',dpi=155,facecolor=fig.get_facecolor());plt.close(fig)
    print(out/'regional_circuits.png');print(out/'origin_storage.png')


if __name__=='__main__':main()

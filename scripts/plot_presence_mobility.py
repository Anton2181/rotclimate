"""Standalone scientific figures from the actual published scenario packets."""
from pathlib import Path
import gzip
import json

ROOT=Path(__file__).resolve().parents[1]


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Patch
    from matplotlib.colors import BoundaryNorm,ListedColormap
    from PIL import Image
    data=ROOT/'atlases/earth_fit/data';meta=json.loads((data/'atlas.json').read_text());manifest=json.loads((data/'presence_mobility.json').read_text());packet=manifest['packets']['corrected']
    model=json.loads(gzip.decompress((data/packet['payload']).read_bytes()));out=ROOT/'output/presence_mobility_20261104'
    colours=['#914d55','#b47c64','#d2af79','#ced3a4','#83ae98','#287877'];cmap=ListedColormap(colours);norm=BoundaryNorm([0,.25,.5,.75,.9,.999999,1.00001],6)
    cases={c['id']:c for c in model['presence']};fig,axes=plt.subplots(1,2,figsize=(15,6.5),facecolor='#f8faf9',gridspec_kw={'width_ratios':[1.4,1]})
    ax=axes[0];background=np.asarray(Image.open(data/'corrected/presence_people500_freight25.webp')).copy()
    ax.imshow(background);case=cases['people500_freight25'];values=np.array([s['annual_need_met'] for s in case['sites']])
    for unresolved,marker in [(False,'o'),(True,'D')]:
        select=np.array([(s['actor'] is None)==unresolved for s in model['sites']]);xy=np.array([[s['x'],s['y']] for s in model['sites']])[select]
        ax.scatter(xy[:,0],xy[:,1],c=values[select],cmap=cmap,norm=norm,s=24,edgecolors='#293d46',linewidths=.4,marker=marker,
            label='Affiliation unresolved' if unresolved else 'Provisional affiliation linked')
    ax.set_title('500-person test · 25-tonne freight slots per bin\nDots: annual cereal need met; background: worst-bin need met',loc='left',fontsize=11);ax.axis('off')
    ax.legend(loc='upper left',bbox_to_anchor=(0,-.05),fontsize=8,frameon=False)
    axes[1].set_title('The same 151 marked sites under changed budgets',loc='left',fontsize=11)
    order=np.argsort(values)
    for key,label,color,ls in [('stores90','100 people · 5 t/bin','#287877','-'),('people500','500 people · same 5 t/bin','#9f5c5d','--'),
            ('people500_freight25','500 people · 25 t/bin','#38758e','-'),('closure_no_store','100 people · interruption, no store','#bf9c5f',':')]:
        axes[1].plot(np.arange(1,152),[cases[key]['sites'][i]['annual_need_met']*100 for i in order],color=color,label=label,ls=ls,lw=1.7)
    axes[1].set(xlim=(1,151),ylim=(0,105),xlabel='Sites ordered by the 500-person / 25-tonne scenario',ylabel='Declared annual cereal need met (%)')
    axes[1].spines[['top','right']].set_visible(False);axes[1].grid(axis='y',alpha=.15);axes[1].legend(fontsize=8,frameon=False,loc='lower right')
    fig.suptitle('Sustained presence requires food and logistics',fontsize=18,x=.035,ha='left',y=.98)
    fig.text(.035,.9,'Earth-corrected climate · food support at known symbols, including unresolved affiliations · no ownership or garrison-size prediction',fontsize=10)
    fig.subplots_adjust(left=.035,right=.98,top=.78,bottom=.29,wspace=.15)
    fig.text(.035,.04,'Single wheat/barley crop; rural meals protected before collection. Scenario assumptions: 10% of rural overflow collectable; on-farm export stores;\n'
        'explicit freight slots, losses and one-bin delivery delay; destination stores 90 demand-days unless stated. The interruption closes two busy dispatch bins.\n'
        'These are independent scenarios, not actual armies, historical populations or territorial control. Missing communities remain unscored.\n'
        'A small group being easy to feed under these assumptions does not establish institutions or rights to obtain its food.',fontsize=9,linespacing=1.5)
    fig.savefig(out/'food_support.png',dpi=155,facecolor=fig.get_facecolor());plt.close(fig)
    fig,axes=plt.subplots(2,4,figsize=(16,9),facecolor='#f8faf9',gridspec_kw={'height_ratios':[1.6,1]})
    cell_km=meta['mi_per_px']*1.609344*packet['cell_px'];cell=packet['cell_px'];palette=['#e5decd','#afc6ad','#5d9c8e','#285f72']
    for j,e in enumerate(model['mobility']):
        ax=axes[0,j];c=e['cases'][0];r=c['mobile'];patches=e['patches'];home=patches[e['home']]
        coordinate=lambda p:((p['x']-home['x'])/cell*cell_km,(home['y']-p['y'])/cell*cell_km)
        counts=np.bincount(r['locations'],minlength=len(patches))
        for i,p in enumerate(patches):
            x,y=coordinate(p);colour=palette[0 if counts[i]==0 else 1 if counts[i]<=3 else 2 if counts[i]<=8 else 3]
            ax.add_patch(Rectangle((x-cell_km/2,y-cell_km/2),cell_km,cell_km,facecolor=colour,edgecolor='white',linewidth=.3))
        points=np.array([coordinate(patches[i]) for segment in r['segments'] for i in segment])
        ax.plot(points[:,0],points[:,1],c='white',lw=3);ax.plot(points[:,0],points[:,1],c='#203d50',lw=1)
        seen={}
        for i in r['locations']:
            if i not in seen:seen[i]=chr(65+len(seen))
        for i,label in seen.items():
            x,y=coordinate(patches[i]);ax.scatter([x],[y],s=80,c='white',edgecolors='#203d50',linewidths=.6,zorder=5);ax.text(x,y,label,fontsize=7,ha='center',va='center',zorder=6)
        ax.scatter([0],[0],s=135,marker='s',facecolors='none',edgecolors='#9b4e62',lw=1.5,zorder=7)
        ax.autoscale_view();ax.set_aspect('equal');ax.spines[['top','right']].set_visible(False);ax.set(xlabel='km from resource anchor',ylabel='km from resource anchor')
        titles=['Tarani resource landscape','Grassland outside named claims','Mixed resources outside named claims','Tribes of the Neck resource landscape']
        ax.set_title(titles[j],loc='left',fontsize=10)
        vals=[c['stationary']['annual_need_met']*100,r['annual_need_met']*100,c['best_fixed_base_continuous']['annual_need_met']*100]
        axes[1,j].bar(np.arange(3),vals,color=['#b2b5a9','#367c85','#b89768'],width=.7)
        for k,v in enumerate(vals):axes[1,j].text(k,v+1.5,f'{v:.1f}%',ha='center',fontsize=9)
        axes[1,j].set(xticks=range(3),xticklabels=['Fixed\nhome','Closed\ncircuit','Best fixed\nbase*'],ylim=(0,110),ylabel='Annual DM need met (%)')
        axes[1,j].spines[['top','right']].set_visible(False);axes[1,j].grid(axis='y',alpha=.15)
    fig.suptitle('Seasonal movement versus choosing a better base',fontsize=18,x=.04,ha='left',y=.99)
    fig.text(.04,.945,'Earth-corrected climate · four independent resource landscapes · dark patches visited more often · letters locate patches in the seasonal tables',fontsize=10)
    fig.subplots_adjust(left=.05,right=.985,top=.88,bottom=.19,wspace=.3,hspace=.5)
    fig.text(.04,.025,'Each circuit: one unsplit herd of 100 dry-matter reference units; fresh growth used once; 7 demand-days of carried feed; same home and reserve at year end.\n'
        '*Best fixed base permits relocation anywhere in the same landscape and continuous reserves. Here, none of the four circuits beats that stronger control.\n'
        'Water access is unresolved in these plots. A mapped-water filter excludes three fixed homes rather than proving absence of water. No nutrition, actual camps,\n'
        'political organization or human population is predicted. These are small local landscapes, not a test of long-range transhumance across wider seasonal gradients.',fontsize=9,linespacing=1.5)
    fig.savefig(out/'resource_circuits.png',dpi=155,facecolor=fig.get_facecolor());plt.close(fig)
    print(out/'food_support.png');print(out/'resource_circuits.png')


if __name__=='__main__':main()

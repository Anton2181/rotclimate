"""Export worldwide resource maps and fixed geographic feed profiles."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from PIL import Image
    from local_benchmark_protocol import file_hash
    data=ROOT/'atlases/earth_fit/data';manifest=json.loads((data/'pasture.json').read_text());packet=manifest['packets']['corrected']
    views={}
    for layer in packet['layers']:
        for view in layer.get('variants',{}).get('options',[layer]):views[Path(view['file']).stem.removeprefix('pasture_')]=view
    keys=['annual_dm','lean_fraction','reserve_days','water_distance']
    titles=['Annual usable forage · tonnes DM /land km²','Lean-bin new growth · share of mean production',
        'Minimum zero-loss feed reserve · demand-days','Mean distance to mapped rivers/lakes']
    fig,axes=plt.subplots(2,2,figsize=(14,8),facecolor='#f8faf9')
    for ax,key,title in zip(axes.ravel(),keys,titles):
        view=views[key];path=data/view['file']
        if file_hash(path)!=packet['image_sha256'][view['file']]:raise ValueError('Pasture image changed')
        ax.imshow(Image.open(path));ax.axis('off');ax.set_title(title,loc='left',fontsize=11,pad=8)
        for i,p in enumerate(packet['pilots'],1):
            ax.scatter([p['x']],[p['y']],s=50,c='white',edgecolors='#263c46',linewidths=.7)
            ax.text(p['x'],p['y'],str(i),ha='center',va='center',fontsize=7,color='#263c46')
        ax.legend(handles=[Patch(facecolor=v['color'],label=v['label']) for v in view['items'][:6]],
            loc='upper center',bbox_to_anchor=(.5,-.005),ncol=3,fontsize=8,frameon=False,columnspacing=1)
    fig.suptitle('Pasture resources across the whole world',x=.04,ha='left',fontsize=19,y=.985)
    fig.text(.04,.935,'Earth-corrected climate · all land, without a political eligibility mask · numbered cells are fixed geographic examples',fontsize=10)
    fig.subplots_adjust(left=.035,right=.985,bottom=.2,top=.88,hspace=.32,wspace=.04)
    fig.text(.04,.025,'Reserve test: constant demand consumes half annual usable DM; zero loss. Annual/seasonal productivity and forage shares are model assumptions.\n'
        'Water proximity does not establish drinkable supply. These maps do not estimate herds, human population, mobility or political control.\n'
        'Examples: 1 Tarani; 2 grassland outside named claims; 3 mixed resources outside named claims; 4 Tribes of the Neck. Labels do not assign livelihoods.',fontsize=9)
    out=ROOT/'output/pasture_maps_20261104';fig.savefig(out/'world_resources.png',dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,7.5),facecolor='#f8faf9')
    for i,(ax,p) in enumerate(zip(axes.ravel(),packet['pilots']),1):
        annual=p['annual_dm'];supply=np.array([np.nan if v is None else v for v in p['monthly_dm']])
        ax.bar(np.arange(1,13),supply/(annual/12),color='#549b92',width=.8,label='New usable DM /bin mean')
        ax.axhline(.5,c='#9b643d',lw=1.5,ls='--',label='Test demand: half annual production')
        ax.set_title(str(i)+'. '+p['label'],loc='left',fontsize=10)
        ax.set_xticks([1,3,6,9,12]);ax.set_xlabel('Climatological seasonal bin');ax.set_ylabel('× mean new production')
        ax.spines[['top','right']].set_visible(False)
        ax.text(.02,.94,f'Minimum reserve: {p["reserve_days"]:.1f} demand-days\n90-day buffer: {p["shortfall_bins"]:.0f}/12 shortfall bins',
            transform=ax.transAxes,va='top',fontsize=9,bbox=dict(facecolor='white',edgecolor='none',alpha=.85))
    axes[0,0].legend(loc='upper right',fontsize=7)
    fig.suptitle('Different seasonal feed profiles under the same accounting rules',x=.06,ha='left',fontsize=15,y=.98)
    fig.subplots_adjust(left=.07,right=.98,top=.89,bottom=.15,hspace=.48,wspace=.23)
    fig.text(.06,.04,'Fixed resource cells, not ethnographic observations or representative regional averages. No mobility or herd nutrition model.\n'
        'Feed is consumed/stored once; repeating stocks and overflow close the dry-matter ledger. Standing forage and cut fodder are not distinguished.',fontsize=9)
    fig.savefig(out/'seasonal_profiles.png',dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    print(out/'world_resources.png');print(out/'seasonal_profiles.png')


if __name__=='__main__':main()

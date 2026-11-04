"""Make a static, consistently scaled comparison of access source assumptions."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap,BoundaryNorm
    from local_benchmark_protocol import file_hash
    folder=ROOT/'output/imperial_access_20261104/earth_fit_corrected'
    review=json.loads((folder/'review.json').read_text())
    if file_hash(folder/'fields.npz')!=review['arrays_sha256']:raise ValueError('Access grid changed')
    inventory_path=ROOT/'output/administrative_inventory_20261104/review.json'
    if file_hash(inventory_path)!=review['inventory_sha256']:raise ValueError('Inventory changed')
    inventory=json.loads(inventory_path.read_text())
    with np.load(folder/'fields.npz') as grid:
        land=grid['land'];claim=grid['imperial_claim'];values=grid['accessible_months']
    cmap=ListedColormap(['#eee9df','#d8c8b2','#c6b593','#a1b8a3','#69998a','#286f70']);cmap.set_bad('#d6e3f0')
    norm=BoundaryNorm([-.5,.5,3.5,6.5,9.5,11.5,12.5],cmap.N)
    fig,axes=plt.subplots(2,2,figsize=(13,7.5),facecolor='#f8faf9')
    for ax,case,title in zip(axes.ravel(),[0,1,3,5],['Recorded commandery seats','Other marked places included','Proposed towns and tracks included','Imperial forts and legion locations']):
        image=ax.imshow(np.ma.masked_where(~land,values[case]),cmap=cmap,norm=norm,extent=[0,inventory['width'],inventory['height'],0])
        yy=(np.arange(land.shape[0])+.5)*inventory['height']/land.shape[0]
        xx=(np.arange(land.shape[1])+.5)*inventory['width']/land.shape[1]
        ax.contour(xx,yy,claim,levels=[.5],colors=['#614674'],linewidths=.5,alpha=.8)
        if case==0:
            seats=[c for c in inventory['commanderies'] if c['status']=='matched']
            ax.scatter([c['x'] for c in seats],[c['y'] for c in seats],s=5,c='#202b30',edgecolors='white',linewidths=.25)
        s=review['summaries'][review['cases'][case]]
        ax.set_title(title+'\n'+f'{100*s["twelve_month_claim_share"]:.1f}% of claimed land accessible in all 12 bins',fontsize=11,loc='left')
        ax.axis('off')
    fig.suptitle('How source assumptions change imperial access',fontsize=18,x=.05,ha='left',y=.985)
    fig.text(.05,.94,'Earth-corrected climate · within two person-travel days · purple outline: painted imperial claim',fontsize=10)
    fig.subplots_adjust(left=.04,right=.98,bottom=.15,top=.88,wspace=.06,hspace=.23)
    colorbar=fig.colorbar(image,ax=axes,orientation='horizontal',fraction=.035,pad=.035,aspect=55,ticks=[0,2,5,8,10.5,12])
    colorbar.ax.set_xticklabels(['0','1–3','4–6','7–9','10–11','All 12'])
    colorbar.set_label('Accessible climatological seasonal bins')
    fig.text(.05,.035,'Access scenarios, not ownership, allegiance or military strength. Common ports and river landings include proposed-town sites.\n'
        '70/72 seats verified; Kudā and the disputed Thalamâtâs seat excluded. No troop strength inferred from legion founding numbers.',fontsize=9)
    destination=ROOT/'output/imperial_access_20261104/access_comparison.png'
    fig.savefig(destination,dpi=170,facecolor=fig.get_facecolor());plt.close(fig)
    print(destination)


if __name__=='__main__':main()

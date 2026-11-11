"""Plot all central service comparisons and a fixed illustrative driver map."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm,ListedColormap
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/settlement_service_demand_20261111'


def main():
    result=json.loads((OUT/'results.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(14,5.8),facecolor='#f5f5ee')
    names={'potential':'Overlapping potential','allocated':'Allocated potential requests','per_centre':'Requests per expected centre'}
    colors={'potential':'#526f9a','allocated':'#227c70','per_centre':'#ac7027'}
    for ax,subset in zip(axes,['full','strict_nonroadside']):
        rows=result['subsets'][subset]['results'][0]['predictors'];ax.set_facecolor('#f5f5ee')
        for roads,style,label in [('no_roads','--','no roads'),('recorded_roads','-','recorded roads')]:
            for field,color in colors.items():
                ax.plot([.5,1.,2.],[rows[f'{roads}_B{budget:g}_{field}']['AUC'] for budget in [.5,1.,2.]],
                    style+'o',color=color,label=names[field]+', '+label)
        ax.axhline(rows['environment']['AUC'],color='#555555',ls=':',label='Existing suitability')
        ax.axhline(rows['history_L450_intensity']['AUC'],color='#999999',ls='-.',label='Existing history intensity')
        ax.set_ylim(.3,.7);ax.set_xticks([.5,1,2]);ax.grid(alpha=.18)
        ax.spines[['top','right']].set_visible(False);ax.set_xlabel('One-way travel budget (walking-days)')
        ax.set_title('Full recorded context contrast' if subset=='full' else 'Every roadside-tagged record excluded')
    axes[0].set_ylabel('Conditional ranking AUC; no fitting')
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.085),ncol=4,fontsize=8)
    fig.suptitle('Service demand changes the contrast; local checks limit the gain',x=.045,ha='left',fontsize=17,fontweight='bold')
    fig.text(.045,.88,'Central coordinates shown; all nine coordinate scenarios and source strata are exported. No predictor or default selected.',fontsize=10)
    fig.text(.045,.025,'Strict non-roadside per-centre AUC≈0.64–0.65 overall, but only≈0.55–0.56 in 50 km blocks for the 2-day cases.\nPotential requests are not completed services, population, dated AD200 roles or political control.',fontsize=9,color='#555555')
    fig.subplots_adjust(left=.07,right=.98,top=.79,bottom=.28,wspace=.17)
    path=ROOT/'reports/figures/settlement_service_demand_scores_20261111.png';fig.savefig(path,dpi=150,facecolor=fig.get_facecolor());plt.close(fig)

    fields=dict(np.load(OUT/'fields.npz'));x=dict(np.load(ROOT/'output/settlement_locations_20261110/rome_inputs.npz'))
    cell=float(x['cell_km']);core=fields['core_mask'];rr,cc=np.nonzero(core)
    crop=np.s_[max(0,rr.min()-1):min(core.shape[0],rr.max()+2),max(0,cc.min()-1):min(core.shape[1],cc.max()+2)]
    lon,lat=x['lon'][crop],x['lat'][crop];land=x['land'][crop]
    density=np.where(x['allowed']&x['land'],x['density']*cell**2,0)
    panels=[(density,'Fixed reference demand','Reference units per cell'),
        (fields['recorded_roads_B1_allocated'],'Allocated potential requests','Request units per candidate cell'),
        (fields['recorded_roads_B1_per_centre'],'Requests per expected centre','Request units per centre equivalent')]
    fig,axes=plt.subplots(1,3,figsize=(13,6.2),facecolor='#f5f5ee')
    for ax,(values,title,label) in zip(axes,panels):
        ax.set_facecolor('#efeee8');ax.patch.set_hatch('///');ax.patch.set_edgecolor('#cccccc')
        ax.pcolormesh(lon,lat,land.astype(int),cmap=ListedColormap(['#dce8ee','#dddcd3']),shading='nearest',vmin=0,vmax=1)
        values=values[crop];positive=values[(values>0)&land]
        lo,hi=np.percentile(positive,[3,97]);lo=max(lo,1e-12);hi=max(hi,lo*1.01)
        data=np.ma.masked_where((values<=0)|~land,values)
        mesh=ax.pcolormesh(lon,lat,data,norm=LogNorm(lo,hi),cmap='viridis',shading='nearest')
        ax.contour(lon,lat,land.astype(float),levels=[.5],colors='#77766d',linewidths=.45)
        ax.set_xlim(-7,3);ax.set_ylim(49,57);ax.set_aspect(1/np.cos(np.radians(53)))
        ax.set_title(title,fontsize=11);ax.set_xlabel('Longitude');ax.set_ylabel('Latitude')
        bar=fig.colorbar(mesh,ax=ax,shrink=.65,pad=.025,extend='both');bar.ax.tick_params(labelsize=7);bar.set_label(label,fontsize=8)
    fig.suptitle('Potential service demand on the Earth test grid',x=.035,ha='left',fontsize=17,fontweight='bold')
    fig.text(.035,.88,'Fixed illustration: recorded roads, one-way 1 walking-day budget. Each origin apportions its own finite potential requests.',fontsize=10)
    fig.text(.035,.025,'Hatched: outside the original model window. Blue: modelled water. Grey: no displayed reference/candidate value.\nLog colours clipped at 3rd/97th percentiles; these are request drivers, not town sizes, actual population or political control.',fontsize=9,color='#555555')
    fig.subplots_adjust(left=.055,right=.98,top=.8,bottom=.19,wspace=.3)
    path2=ROOT/'reports/figures/settlement_service_demand_maps_20261111.png';fig.savefig(path2,dpi=150,facecolor=fig.get_facecolor(),bbox_inches='tight',pad_inches=.12);plt.close(fig)
    print(path);print(path2)


if __name__=='__main__':main()

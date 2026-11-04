"""Export six comparable coverage diagnostics; never draw inferred ownership."""
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
    from matplotlib.patches import Patch
    from polity.coverage_audit import aggregate_words,seasonal_mask
    from publish_world_coverage import load_fields
    from local_benchmark_protocol import file_hash
    folder=ROOT/'output/world_coverage_20261104/earth_fit_corrected';r=json.loads((folder/'review.json').read_text())
    if file_hash(folder/'coverage.bin.gz')!=r['binary_sha256']:raise ValueError('Coverage arrays changed')
    lookup,words,unknown=load_fields(folder,r);land=lookup>0;n=r['land_cells'];pop=np.array([i.bit_count() for i in range(4096)])
    linked=seasonal_mask(aggregate_words(words[0,:,1]),1);expanded=seasonal_mask(aggregate_words(words[2,:,1]),1)
    outward=seasonal_mask(aggregate_words(words[0,:,0]),1);un=seasonal_mask(unknown[1],1)
    overlap=np.zeros(n,np.uint16)
    for m in range(12):overlap|=(np.sum(((words[2,:,1]>>(2*m))&3)>=2,axis=0)>=2).astype(np.uint16)<<m
    values=[pop[linked],pop[expanded],pop[expanded&~linked],pop[outward&~linked],pop[overlap],pop[un]]
    titles=['Evidence-linked sources · seasonal two-way access','With claim-assigned and generated sources',
        'Additional bins dependent on extra sources','Outward bins without a same-site return · linked sources',
        'Overlapping actor reach · expanded sources','Access from marked sites with unresolved affiliation']
    colours=['#eee9df','#d8c8b2','#c6b593','#a1b8a3','#69998a','#286f70'];labels=['0 bins','1–3','4–6','7–9','10–11','All12']
    cmap=ListedColormap(colours);cmap.set_bad('#d6e3f0');norm=BoundaryNorm([-.5,.5,3.5,6.5,9.5,11.5,12.5],6)
    fig,axes=plt.subplots(3,2,figsize=(14,11),facecolor='#f8faf9')
    for ax,value,title in zip(axes.ravel(),values,titles):
        full=np.full(lookup.shape,np.nan);full[land]=value
        ax.imshow(np.ma.masked_invalid(full),cmap=cmap,norm=norm);ax.axis('off');ax.set_title(title,loc='left',fontsize=10,pad=7)
    fig.suptitle('Worldwide access and its dependence on source evidence',x=.04,y=.985,ha='left',fontsize=18)
    fig.text(.04,.947,'Earth-corrected climate · 2 days per leg · outward and return must use the same site within each fixed seasonal snapshot',fontsize=10)
    fig.subplots_adjust(left=.035,right=.985,top=.91,bottom=.14,hspace=.16,wspace=.04)
    fig.legend(handles=[Patch(facecolor=c,label=l) for c,l in zip(colours,labels)],loc='lower center',bbox_to_anchor=(.5,.08),ncol=6,frameon=False)
    fig.text(.04,.025,'Coverage is from provisional inventories; the qualifying actor/site can differ between seasonal bins. Overlap is not observed conflict.\n'
        'No new sovereignty, military strength or absent-community inference. Shared modelled transport includes generated tracks and landings.\n'
        'Avādāyā Tribes and Tribes of the Neck lack linked-site inventories: their documented-source access is unscored, not zero actual control.',fontsize=9)
    destination=ROOT/'output/world_coverage_20261104/world_coverage.png';fig.savefig(destination,dpi=155,facecolor=fig.get_facecolor());plt.close(fig);print(destination)


if __name__=='__main__':main()

"""Standalone comparison plate from the four published scenario packets."""
from pathlib import Path
import gzip
import json
import sys
ROOT=Path(__file__).resolve().parents[1]


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    data=ROOT/'atlases/earth_fit/data';p=json.loads((data/'settled_reach.json').read_text())['packets']['corrected'];m=json.loads(gzip.decompress((data/p['payload']).read_bytes()))
    cases=['reference','joint365','joint1'];labels=['Food unconstrained','10% collection · year store','1% collection · year store']
    fig,axes=plt.subplots(2,3,figsize=(16,7.3),layout='constrained');fig.patch.set_facecolor('#f1f3ef')
    for col,(case,label) in enumerate(zip(cases,labels)):
        summary=next(s for s in m['summaries'] if s['id']==case)
        for row,key in enumerate(['reach_towns','reach_defacto']):
            option=next(o for o in p['options'][key] if o['value']==case);axes[row,col].imshow(Image.open(data/option['file']));axes[row,col].set_axis_off()
        axes[0,col].set_title(label+'\n'+format(summary['civilian_people']/1e6,'.2f')+' M requested/allocated civilians',fontsize=12)
        axes[1,col].set_title(str(summary['active_sources'])+' affiliated sources · '+format(summary['area_weighted_access_bins'],'.2f')+'/12 access bins',fontsize=11)
    fig.suptitle('Earth-corrected climate: local cereal → settlement allocation → available reach sources',fontsize=17)
    fig.supxlabel('Top: alternative resident scenarios, not census estimates. Bottom: two-way seasonal reach, not sovereignty.\nSame candidates and transport. Other foods, imports, labour and water volumes remain unbalanced.',fontsize=11)
    out=ROOT/'output/settlement_integration_20261104';fig.savefig(out/'settlement_reach_comparison.png',dpi=130);plt.close(fig)
    print(out/'settlement_reach_comparison.png')


if __name__=='__main__':main()

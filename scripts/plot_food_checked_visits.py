"""Show all new task stages and all 48 matched policy food outcomes."""
import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha
OUT=ROOT/'output/continuous_food_visit_calendars_20261112'

def plot():
    r=json.loads((OUT/'results.json').read_text());assert json.loads((OUT/'review.json').read_text())['results_sha256']==sha(OUT/'results.json');keys=[c['key'] for c in r['cases']];labels=[k.replace('corrected','Corr.').replace('raw','Raw').replace('_h',' · ').replace('_crew','h · crew ') for k in keys];figures=[];y=np.arange(8)
    fig,ax=plt.subplots(figsize=(12,7));stages=[('funded','hour_plan','funded_visits','New hour-funded jobs','#b3b4ac'),('policy','baseline','qualified_visits','Collection-first: BOTH gates','#bd8155'),('policy','joint','qualified_visits','Joint order: BOTH gates','#6d9b9e'),('selected','whole_provider_year','qualified_visits','One whole provider-year: BOTH','#3b647b')]
    for j,(stage,policy,field,label,color) in enumerate(stages):
        rows=[next(v for v in r['visit_rows'] if v['key']==k and v['stage']==stage and (stage=='selected' or v['policy']==policy)) for k in keys];values=[v[field] for v in rows];ax.barh(y+(j-1.5)*.19,values,height=.18,label=label,color=color)
        if stage=='selected':
            for i,value in enumerate(values):ax.text(value+500,i+(j-1.5)*.19,f'{value:,}',fontsize=8,va='center')
    ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlabel('Point tasks across 12 bins · alternative scenarios');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True);ax.legend(loc='lower center',bbox_to_anchor=(.5,1.02),ncol=2,fontsize=9,frameon=False);fig.suptitle('New point jobs: full mandatory year AND the selected calendar’s OWN cereal',fontsize=13)
    fig.text(.5,.025,'Each provider uses one complete policy for all bins. Every new baseline BOTH-qualified task identity is retained.\nNo union of individual job successes; conditional residents are unchanged. Points do not establish held blocks or authority.',ha='center',fontsize=9);fig.subplots_adjust(left=.22,right=.98,bottom=.15,top=.83);path=ROOT/'reports/figures/food_checked_visits_tasks_20261112.png';fig.savefig(path,dpi=160);plt.close(fig);figures.append(path)
    fig,axes=plt.subplots(1,2,figsize=(13,7));columns=[(p,a) for p in ('baseline','joint') for a in 'ABC'];rows=[[next(v for v in r['food_rows'] if v['key']==k and v['policy']==p and v['accounting']==a) for p,a in columns] for k in keys]
    for ax,values,title,fmt in [(axes[0],np.array([[v['food_no_shortage'] for v in row] for row in rows]),'Provider food passes · all active retained','d'),(axes[1],np.array([[100*v['unmet']/v['needed'] for v in row] for row in rows]),'Unmet cereal / meals · percent','.4f')]:
        image=ax.imshow(values,aspect='auto',cmap='YlGnBu');ax.set_yticks(y,labels if ax==axes[0] else []);ax.set_xticks(range(6),['Base A','Base B','Base C','Joint A','Joint B','Joint C'],rotation=35,ha='right');ax.set_title(title,fontsize=11)
        middle=(values.max()+values.min())/2
        for i in range(8):
            for j in range(6):ax.text(j,i,format(int(values[i,j]),fmt) if fmt=='d' else format(values[i,j],fmt),ha='center',va='center',fontsize=8,color='white' if values[i,j]>middle else '#222')
    fig.suptitle('All 48 policy food results: omissions and timing are distinct changes',fontsize=12);fig.text(.5,.025,'A: planned cargo, lagged bin starts. B: packed cargo, same starts. C: SAME packed cargo, job returns within the imposed lag.\nSame residents, 90-day stores, 2,500 kcal/day and retention 0.95 once. Food alone does not qualify mandatory work.',ha='center',fontsize=9);fig.subplots_adjust(left=.18,right=.99,bottom=.2,top=.91,wspace=.15);path=ROOT/'reports/figures/food_checked_visits_food_20261112.png';fig.savefig(path,dpi=160);plt.close(fig);figures.append(path);return figures
if __name__=='__main__':
    for p in plot():print(p)

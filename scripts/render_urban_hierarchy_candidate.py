"""Standalone candidate comparison viewer and scientific map exports."""
import base64
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource,TwoSlopeNorm,LinearSegmentedColormap
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/urban_hierarchy_candidate_20261116'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


TEMPLATE='''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Settlement hierarchy candidate</title><link rel="icon" href="data:,"><style>
:root{color-scheme:light;--ink:#202b32;--muted:#53636a;--line:#cbd4d8;--blue:#204f75}*{box-sizing:border-box}body{margin:0;background:#f5f6f3;color:var(--ink);font:15px/1.5 system-ui,sans-serif}main{max-width:1550px;margin:auto;padding:24px}h1{font-size:28px;line-height:1.2;margin:0 0 6px}h2{font-size:18px;margin:0 0 8px}.sub,.note{color:var(--muted);margin:6px 0 16px}.badge{display:inline-block;background:#f1dfba;color:#5b431a;padding:3px 10px;border-radius:20px;font-size:13px;margin-bottom:12px}.controls{display:flex;gap:14px;flex-wrap:wrap;align-items:end;padding:16px;background:white;border:1px solid var(--line);border-radius:8px;margin:18px 0}label{font-size:13px;color:var(--muted);display:grid;gap:4px}button,select,input{font:inherit;padding:7px 10px;border:1px solid #a9b9bf;border-radius:5px;background:white;color:var(--ink)}button{cursor:pointer}button:hover{background:#e7eff2}input[type=range]{padding:7px 0;width:120px}.maps{display:grid;grid-template-columns:1fr 1fr;gap:16px}.panel{background:white;border:1px solid var(--line);border-radius:8px;padding:14px;min-width:0}.summary{font-size:14px;color:var(--muted);min-height:24px}.map{width:100%;aspect-ratio:1000/463;display:block;background:#dceaf0;border:1px solid #c7d0d2;touch-action:none;cursor:grab}.map:active{cursor:grabbing}circle{fill:#264f70;fill-opacity:.68;stroke:#16354b;stroke-width:.25}circle.marked{stroke:#9b6724;stroke-width:.85;fill-opacity:.88}circle.selected{stroke:#f21a51;stroke-width:1.8;fill-opacity:1}circle.dim{opacity:.08}text.townlabel{font-size:7px;paint-order:stroke;stroke:white;stroke-width:2px;stroke-linejoin:round;fill:#262f34;pointer-events:none}.legend{display:flex;gap:18px;align-items:center;flex-wrap:wrap;font-size:13px;color:var(--muted);margin:12px 0}.gradient{display:inline-block;width:120px;height:10px;background:linear-gradient(90deg,#3b71a8,#f4f3e9,#bd4d3e);vertical-align:middle;border:1px solid #ccc}.detail{margin-top:18px;background:white;border:1px solid var(--line);border-radius:8px;padding:16px}table{border-collapse:collapse;width:100%;max-width:650px}th,td{text-align:left;padding:7px 10px;border-bottom:1px solid #e1e6e8}th{font-size:13px;color:var(--muted)}td.num{text-align:right;font-variant-numeric:tabular-nums}.links{display:flex;gap:20px;flex-wrap:wrap;margin:14px 0}a{color:#185b83}#search-status{font-size:13px;color:var(--muted)}@media(max-width:800px){main{padding:14px}.maps{grid-template-columns:1fr}h1{font-size:24px}.controls{gap:10px}.map{min-height:0}}
</style></head><body><main>
<div class="badge">Development preview · not an adopted release</div><h1>Settlement hierarchy candidate</h1>
<p class="sub">Existing map and refreshed Earth fit. Town locations, total population and climate are unchanged.</p>
<div class="controls"><label>Map scenario<select id="mode"><option value="corrected">Corrected climate</option><option value="raw">Raw climate</option></select></label>
<label>Population reading<select id="reading"><option value="central">Size-dependent density</option><option value="low">100 people / ha</option></select></label>
<label>Candidate colours<select id="display"><option value="area">Settlement areas</option><option value="change">Area change</option></select></label>
<label>Find a settlement<input id="search" type="search" placeholder="Name or actor" autocomplete="off"></label>
<label>Zoom <span id="zoom-value">1×</span><input id="zoom" type="range" min="1" max="8" value="1" step="0.1"></label><button id="reset">Reset view</button></div>
<div id="search-status" aria-live="polite"></div><div class="maps"><section class="panel"><h2>Published map</h2><div id="old-summary" class="summary"></div><svg class="map" id="old-map" role="img" aria-label="Published settlement map. Drag to pan;use plus or minus to zoom." tabindex="0"></svg></section>
<section class="panel"><h2>Candidate</h2><div id="new-summary" class="summary"></div><svg class="map" id="new-map" role="img" aria-label="Candidate settlement map. Drag to pan;use plus or minus to zoom." tabindex="0"></svg></section></div>
<div class="legend"><span>Circle size scales with settlement area</span><span>Gold outline: marked place</span><span id="change-legend" hidden>½× <span class="gradient"></span> 2× · white = unchanged;colours saturate at these limits</span></div>
<p class="note">Drag either map or use the zoom control;the views stay aligned. Click a town for its comparison. Large local changes can come from seeded residual reassignment and are not town-level predictions.</p>
<section class="detail" aria-live="polite"><h2 id="town-name">Choose a settlement</h2><p id="town-actor" class="note">Search or click a town to inspect the same location in both maps.</p>
<table id="details" hidden><thead><tr><th>Quantity</th><th>Published</th><th>Candidate</th></tr></thead><tbody>
<tr><td>Modelled area (ha)</td><td class="num" id="old-area"></td><td class="num" id="new-area"></td></tr>
<tr><td>Allocated residents · annual people ledger</td><td class="num" id="old-res"></td><td class="num" id="new-res"></td></tr>
<tr><td>Local cereal ratio · annual check</td><td class="num" id="old-food"></td><td class="num" id="new-food"></td></tr></tbody></table></section>
<p class="note">People are conserved in the annual ledger. Seasonal source food, labour and imported supply remain to be qualified. Climate r44 is retained.</p>
<nav class="links"><a id="candidate-download" href="candidate/placed_corrected_towns.csv" download>Candidate towns CSV</a><a id="control-download" href="control/placed_corrected_towns.csv" download>Published control CSV</a><a href="town_changes.csv" download>Complete changes CSV</a><a href="comparison.csv" download>People and cereal summary</a></nav>
</main><script id="payload" type="application/json">__PAYLOAD__</script><script>
'use strict';const DATA=JSON.parse(document.getElementById('payload').textContent),NS='http://www.w3.org/2000/svg';
const $=id=>document.getElementById(id);let state={mode:'corrected',reading:'central',display:'area',zoom:1,x:0,y:0,selected:null};let circles=[[],[]];
function svgEl(tag,attrs={}){const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);return e;}
function fmt(v,dp=0){return Number(v).toLocaleString('en-GB',{maximumFractionDigits:dp});}function colour(q){const t=Math.max(-1,Math.min(1,Math.log2(q))),a=t<0?[59,113,168]:[189,77,62],f=Math.abs(t);return 'rgb('+a.map((v,i)=>Math.round((1-f)*[244,243,233][i]+f*v)).join(',')+')';}
function updateView(){const box=[state.x,state.y,1000/state.zoom,463/state.zoom].join(' ');$('old-map').setAttribute('viewBox',box);$('new-map').setAttribute('viewBox',box);$('zoom').value=state.zoom;$('zoom-value').textContent=state.zoom.toFixed(1)+'×';}
function select(i){state.selected=i;updateDetail();highlight();}
function highlight(){const term=$('search').value.trim().toLowerCase();let n=0;DATA.modes[state.mode].towns.forEach((t,i)=>{const match=!term||(t.name+' '+t.actor).toLowerCase().includes(term);if(match)n++;circles.forEach(list=>{list[i].classList.toggle('dim',!match);list[i].classList.toggle('selected',state.selected===i);});});$('search-status').textContent=term?n+' matching settlements':DATA.modes[state.mode].towns.length+' fixed locations';}
function updateDetail(){const t=DATA.modes[state.mode].towns[state.selected];$('details').hidden=!t;if(!t){$('town-name').textContent='Choose a settlement';$('town-actor').textContent='Search or click a town to inspect the same location in both maps.';return;}$('town-name').textContent=t.name;$('town-actor').textContent=(t.actor||'Unassigned actor')+' · area '+fmt(t.ratio,2)+'× published';$('old-area').textContent=fmt(t.old_area,2);$('new-area').textContent=fmt(t.new_area,2);$('old-res').textContent=fmt(t['old_res_'+state.reading]);$('new-res').textContent=fmt(t['new_res_'+state.reading]);$('old-food').textContent=fmt(t['old_food_'+state.reading],3)+'×';$('new-food').textContent=fmt(t['new_food_'+state.reading],3)+'×';}
function draw(){const data=DATA.modes[state.mode];circles=[[],[]];['old-map','new-map'].forEach((id,panel)=>{const svg=$(id);svg.replaceChildren();svg.append(svgEl('image',{href:DATA.background,x:0,y:0,width:1000,height:463}));data.towns.forEach((t,i)=>{const area=panel?t.new_area:t.old_area,c=svgEl('circle',{cx:t.x+.5,cy:t.y+.5,r:.65+.2*Math.sqrt(area),'data-index':i,'data-id':t.id,class:t.marked?'marked':'','vector-effect':'non-scaling-stroke'});if(panel&&state.display==='change'){c.style.fill=colour(t.ratio);c.style.fillOpacity='.9';}const title=svgEl('title');title.textContent=t.name+' · '+fmt(t.old_area,2)+' → '+fmt(t.new_area,2)+' ha ('+fmt(t.ratio,2)+'×)';c.append(title);c.addEventListener('click',()=>select(i));svg.append(c);circles[panel].push(c);if(['imperial capital','major imperial city'].includes(t.symbol)){const label=svgEl('text',{x:t.x+4.5,y:t.y-2.5,class:'townlabel'});label.textContent=t.name;svg.append(label);}});});const s=data.summary[state.reading];$('old-summary').textContent=fmt(s.old_res)+' allocated residents · '+fmt(s.old_area)+' ha';$('new-summary').textContent=fmt(s.new_res)+' allocated residents · '+fmt(s.new_area)+' ha';$('change-legend').hidden=state.display!=='change';$('candidate-download').href='candidate/placed_'+state.mode+'_towns.csv';$('control-download').href='control/placed_'+state.mode+'_towns.csv';updateView();updateDetail();highlight();}
for(const id of ['mode','reading','display'])$(id).addEventListener('change',()=>{state[id]=$(id).value;if(id==='mode')state.selected=null;draw();});$('search').addEventListener('input',highlight);$('search').addEventListener('keydown',e=>{if(e.key==='Enter'){const q=$('search').value.trim().toLowerCase(),towns=DATA.modes[state.mode].towns;let i=towns.findIndex(t=>t.name.toLowerCase()===q);if(i<0)i=towns.findIndex(t=>(t.name+' '+t.actor).toLowerCase().includes(q));if(i>=0)select(i);}});
$('zoom').addEventListener('input',()=>{const old=state.zoom;state.zoom=Number($('zoom').value);state.x+=500/old-500/state.zoom;state.y+=231.5/old-231.5/state.zoom;updateView();});$('reset').addEventListener('click',()=>{state.zoom=1;state.x=0;state.y=0;updateView();});
for(const id of ['old-map','new-map']){const svg=$(id);let drag=null;svg.addEventListener('pointerdown',e=>{if(e.target.tagName==='circle')return;drag={x:e.clientX,y:e.clientY};svg.setPointerCapture(e.pointerId);});svg.addEventListener('pointermove',e=>{if(!drag)return;const r=svg.getBoundingClientRect();state.x-=(e.clientX-drag.x)*1000/state.zoom/r.width;state.y-=(e.clientY-drag.y)*463/state.zoom/r.height;drag={x:e.clientX,y:e.clientY};updateView();});svg.addEventListener('pointerup',()=>drag=null);svg.addEventListener('pointercancel',()=>drag=null);svg.addEventListener('wheel',e=>{e.preventDefault();const r=svg.getBoundingClientRect(),px=(e.clientX-r.left)/r.width,py=(e.clientY-r.top)/r.height,old=state.zoom;state.zoom=Math.max(1,Math.min(8,old*Math.exp(-e.deltaY*.002)));state.x+=px*1000*(1/old-1/state.zoom);state.y+=py*463*(1/old-1/state.zoom);updateView();},{passive:false});svg.addEventListener('keydown',e=>{if(['+','=','-','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();if(['+','='].includes(e.key))state.zoom=Math.min(8,state.zoom*1.2);else if(e.key==='-')state.zoom=Math.max(1,state.zoom/1.2);else if(e.key==='ArrowLeft')state.x-=30/state.zoom;else if(e.key==='ArrowRight')state.x+=30/state.zoom;else if(e.key==='ArrowUp')state.y-=30/state.zoom;else state.y+=30/state.zoom;updateView();}});}
draw();
</script></body></html>'''


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_hierarchy_candidate.py')
    with (OUT/'town_changes.csv').open() as f:changes=list(csv.DictReader(f))
    with np.load(OUT/'town_model.npz') as z:compact={k:z[k] for k in z.files}
    admin=ROOT/'atlases/earth_fit/data/administration_grid.npz'
    with np.load(admin) as z:land=z['land'];elev=z['elev'].astype(float)
    palette=LinearSegmentedColormap.from_list('candidate_land',['#dce3cb','#cad5b5','#bfc7a6','#c4b69e','#c5bbac','#eee9df'])
    terrain=LightSource(315,45).shade(np.where(land,elev,0),cmap=palette,vert_exag=.06,dx=3.68,dy=3.68,blend_mode='soft')[:,:,:3]
    terrain=.7*terrain+.3*np.array([.91,.92,.86]);terrain[~land]=[.86,.92,.95]
    road_path=ROOT/'data/source/ravages_v8/roads.png'
    with Image.open(road_path) as im:road_alpha=np.asarray(im.convert('RGBA'))[:,:,3]>0
    roads=np.asarray(Image.fromarray(road_alpha.astype('uint8')*255).resize((1000,463),Image.Resampling.BOX))/255>.05
    terrain[roads & land]=.55*terrain[roads & land]+.45*np.array([.47,.39,.31])
    Image.fromarray((np.clip(terrain,0,1)*255).astype('uint8')).save(OUT/'terrain.png')
    payload=dict(background='data:image/png;base64,'+base64.b64encode((OUT/'terrain.png').read_bytes()).decode(),result_sha256=sha(OUT/'results.json'),modes={})
    for mode in ['raw','corrected']:
        towns=[]
        for i,t in enumerate(x for x in changes if x['mode']==mode):
            row=dict(id=t['id'],name=t['name'],actor=t['actor'],x=int(t['column']),y=int(t['row']),marked=t['marked']=='True',symbol=t['campaign_symbol'],old_area=float(t['legacy_area_ha']),new_area=float(t['candidate_area_ha']),ratio=float(t['area_ratio']))
            for reading in ['central','low']:
                row['old_res_'+reading]=float(t['legacy_residents_'+reading]);row['new_res_'+reading]=float(t['candidate_residents_'+reading]);row['old_food_'+reading]=float(compact[f'{mode}__legacy__local_support_share_{reading}'][i]);row['new_food_'+reading]=float(t['candidate_local_support_'+reading])
            towns.append(row)
        summary={x['reading']:dict(old_res=x['legacy_residents'],new_res=x['candidate_allocated_residents'],old_area=x['legacy_area_ha'],new_area=x['candidate_area_ha']) for x in r['comparison'] if x['mode']==mode}
        payload['modes'][mode]=dict(towns=towns,summary=summary)
        fig,axes=plt.subplots(1,3,figsize=(18,4.3),layout='constrained')
        for ax,kind,title in zip(axes,['old','new','change'],['Published','Candidate','Candidate / published area']):
            ax.imshow(terrain,origin='upper');ax.contour(land,levels=[.5],colors=['#485c61'],linewidths=.25)
            area=np.array([t['new_area'] if kind!='old' else t['old_area'] for t in towns]);color=np.log2([t['ratio'] for t in towns]) if kind=='change' else '#294f70'
            pts=ax.scatter([t['x'] for t in towns],[t['y'] for t in towns],s=3+.11*area,c=color,cmap='RdBu_r' if kind=='change' else None,norm=TwoSlopeNorm(0,-1,1) if kind=='change' else None,alpha=.8,linewidths=.15,edgecolors='#233b45')
            for t in towns:
                if t['symbol'] in ['imperial capital','major imperial city']:ax.annotate(t['name'],(t['x'],t['y']),xytext=(3,3),textcoords='offset points',fontsize=6,bbox=dict(facecolor='white',alpha=.65,edgecolor='none',pad=.5))
            ax.set(title=title,xlim=(0,1000),ylim=(463,0));ax.set_axis_off()
            if kind=='change':
                bar=fig.colorbar(pts,ax=ax,shrink=.65,ticks=[-1,0,1],extend='both');bar.ax.set_yticklabels(['½×','1×','2×'])
        fig.suptitle(f'{mode.capitalize()} map · fixed-site hierarchy candidate · development preview',fontsize=14)
        fig.text(.5,.01,'Circle size scales with modelled area. Total population and locations unchanged. Seasonal source-food/work qualification pending.',ha='center',fontsize=9)
        fig.savefig(OUT/f'comparison_{mode}.png',dpi=170);plt.close(fig)
    (OUT/'viewer_data.json').write_text(json.dumps(payload,separators=(',',':'),allow_nan=False)+'\n')
    text=json.dumps(payload,separators=(',',':'),allow_nan=False).replace('<','\\u003c')
    (OUT/'index.html').write_text(TEMPLATE.replace('__PAYLOAD__',text))
    files=['terrain.png','viewer_data.json','index.html','comparison_raw.png','comparison_corrected.png']
    manifest=dict(status='rendered_from_reviewed_candidate',result_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),renderer_sha256=sha(Path(__file__)),background_source_sha256=sha(admin),painted_roads_source_sha256=sha(road_path),background_scope='Shared fixed terrain and painted roads only;mode-specific derived tracks are not mixed into the background.',files_sha256={name:sha(OUT/name) for name in files},main_atlas_published=False)
    (OUT/'presentation.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Rendered offline synchronized map viewer and raw/corrected comparison PNGs')


if __name__=='__main__':main()

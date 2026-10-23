/* A supplied census is conserved; attraction redistributes it within support. */
(function(root,factory){
  const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.PopulationAtlas=api;
})(typeof globalThis!=='undefined'?globalThis:this,()=>{
  function allocate(capacity,weight,requested){
    if(!Number.isFinite(requested)||requested<0||capacity.length!==weight.length)throw Error('Enter a finite, non-negative population.');
    let ceiling=0,minWeight=Infinity;
    for(let i=0;i<capacity.length;i++){
      if(!Number.isFinite(capacity[i])||capacity[i]<0||!Number.isFinite(weight[i])||weight[i]<0)throw Error('Invalid population support or attraction.');
      if(weight[i]>0&&capacity[i]>0){ceiling+=capacity[i];minWeight=Math.min(minWeight,weight[i]);}
    }
    const target=Math.min(requested,ceiling),people=new Float64Array(capacity.length);
    let lo=0,hi=target>0?1/minWeight:0;
    if(target>0&&target<ceiling)for(let n=0;n<42;n++){
      const mid=(lo+hi)/2;let total=0;
      for(let i=0;i<capacity.length;i++)total+=Math.min(capacity[i],mid*capacity[i]*weight[i]);
      if(total<target)lo=mid;else hi=mid;
    }
    let total=0;
    for(let i=0;i<capacity.length;i++){
      people[i]=target>=ceiling?(weight[i]>0?capacity[i]:0):Math.min(capacity[i],((lo+hi)/2)*capacity[i]*weight[i]);
      total+=people[i];
    }
    return {people,allocated:total,unallocated:Math.max(0,requested-total),capacity:ceiling,requested};
  }
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const num=(v,d=1)=>Number(v).toLocaleString(undefined,{maximumFractionDigits:d});
  const count=v=>v>=1e6?num(v/1e6,3)+' M':num(v,0);
  const readouts=rows=>rows.map(([v,k])=>`<div class="readout"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join('');
  async function load(meta,fresh,onChange,onProvince){
    const response=await fetch(fresh('data/'+meta.population.metadata),{cache:'no-store'});
    if(!response.ok)throw Error('Population metadata could not load.');
    const m=await response.json();if(m.fingerprint!==meta.population.fingerprint)throw Error('Population metadata differs from this atlas.');
    const binary=await fetch(fresh('data/'+meta.population.binary),{cache:'no-store'});
    if(!binary.ok)throw Error('Population data could not load.');
    const buf=await binary.arrayBuffer(),f={};let end=0;
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buf)),v=>v.toString(16).padStart(2,'0')).join('');
    if(digest!==m.binary_sha256)throw Error('Population data belong to a different build. Update the complete atlas folder.');
    for(const [name,a] of Object.entries(m.arrays)){
      const Type={float32:Float32Array,uint16:Uint16Array}[a.dtype],n=a.shape.reduce((x,y)=>x*y,1);
      if(!Type||a.offset%4||a.offset+n*Type.BYTES_PER_ELEMENT>buf.byteLength)throw Error('Incomplete population data.');
      f[name]=new Type(buf,a.offset,n);end=Math.max(end,a.offset+n*Type.BYTES_PER_ELEMENT);
    }
    if(end!==buf.byteLength)throw Error('Population data size differs from its metadata.');
    const initial=new URLSearchParams(location.hash.slice(1));
    const budget=Number(initial.get('population'));
    $('population-budget').value=initial.has('population')&&Number.isFinite(budget)&&budget>=0?budget/1e6:m.default_population/1e6;
    if(['dispersed','rural','markets'].includes(initial.get('pattern')))$('population-pattern').value=initial.get('pattern');
    let result=null,capacity=null,density=null,uniform=null,selection=null,selectedProvince=null,lastKey=null;
    const state=()=>({population:Number($('population-budget').value)*1e6,pattern:$('population-pattern').value});
    function compute(){
      const s=state(),disease=$('disease').value,key=JSON.stringify([s,disease]);
      if(key===lastKey)return;
      const base=f[disease==='absent'?'capacity_absent':'capacity'];capacity=new Float64Array(base.length);
      const weight=s.pattern==='dispersed'?new Float64Array(base.length).fill(1):f[s.pattern==='rural'?'rural':'attraction'];
      let total=0;for(let i=0;i<base.length;i++){capacity[i]=base[i]*f.area[i];total+=capacity[i];}
      result=allocate(capacity,weight,s.population);density=new Float64Array(base.length);uniform=new Float64Array(base.length);
      const fraction=Math.min(s.population/Math.max(total,1e-30),1);
      for(let i=0;i<base.length;i++){density[i]=f.area[i]>0?result.people[i]/f.area[i]:0;uniform[i]=base[i]*fraction;}
      lastKey=key;
      $('population-totals').innerHTML=readouts([[count(s.population),'supplied population'],[count(result.allocated),'allocated within local support'],
        [count(result.unallocated),'not supported / unallocated'],[count(total),'environmental support ceiling']]);
      $('population-balance').textContent=result.unallocated>Math.max(1,s.population*1e-8)
        ?`${count(result.unallocated)} people remain outside the map allocation because the requested total exceeds eligible local support.`
        :'The map conserves the supplied population within numerical rounding. Attraction changes where people live; it does not add people.';
      const rows=Array.from({length:m.provinces.length+1},(_,i)=>({i,name:i?m.provinces[i-1]:'Outside province grid',people:0,area:0,capacity:0}));
      for(let i=0;i<base.length;i++){const r=rows[f.province[i]];r.people+=result.people[i];r.area+=f.area[i];r.capacity+=capacity[i];}
      rows.sort((a,b)=>b.people-a.people);
      $('population-provinces').innerHTML=rows.filter(r=>r.area>0).map(r=>`<tr><th><button type="button" data-name="${esc(r.name)}" aria-pressed="${r.name===selectedProvince}">${esc(r.name)}</button></th><td>${count(r.people)}</td><td>${num(r.people/r.area)}</td><td>${num(r.capacity>0?r.people/r.capacity*100:0)}%</td></tr>`).join('');
      point();
    }
    function point(){
      if(!selection||!result)return;
      const [x,y,name]=selection,xx=Math.max(0,Math.min(m.shape[1]-1,Math.floor(x/meta.width*m.shape[1]))),
        yy=Math.max(0,Math.min(m.shape[0]-1,Math.floor(y/meta.height*m.shape[0]))),i=yy*m.shape[1]+xx;
      $('population-place').textContent=name?`Population near ${name}`:'At the selected place';
      if(!(f.area[i]>0)){$('population-point').textContent='Choose land to inspect population support.';return;}
      const support=capacity[i]/f.area[i],market=f.market[i]>0?m.markets[f.market[i]-1].name:'No overland market';
      $('population-point').innerHTML=readouts([[num(density[i])+' /km²','allocated population'],[num(support)+' /km²','local environmental support'],
        [num(support>0?density[i]/support*100:0)+'%','population pressure'],[num(Math.max(0,support-density[i]))+' /km²','spare food support'],
        [f.travel[i]>=0?num(f.travel[i])+' hours':'No land connection','walking to a named market'],[market,'nearest walking market']]);
    }
    function render(layer){
      compute();const key=layer.id.slice(4),base=f[$('disease').value==='absent'?'capacity_absent':'capacity'];
      const cv=document.createElement('canvas');cv.width=m.shape[1];cv.height=m.shape[0];
      const ctx=cv.getContext('2d'),im=ctx.createImageData(cv.width,cv.height);
      const colors=layer.stops.map(s=>[1,3,5].map(i=>parseInt(s.slice(i,i+2),16)));
      for(let i=0;i<base.length;i++){
        let value=key==='density'?density[i]:key==='pressure'?(base[i]>0?100*density[i]/base[i]:0):
          key==='headroom'?Math.max(0,base[i]-density[i]):key==='shift'?(uniform[i]>0?density[i]/uniform[i]:1):
          key==='travel'?f.travel[i]:f.attraction[i]*100;
        let c;
        if(!f.area[i])c=[214,227,240];
        else if(key==='travel'&&value<0)c=[176,176,176];
        else{
          const scaled=layer.log?(Math.log(Math.max(value,layer.vmin))-Math.log(layer.vmin))/Math.log(layer.vmax/layer.vmin):(value-layer.vmin)/(layer.vmax-layer.vmin);
          const p=Math.max(0,Math.min(1,scaled))*(colors.length-1),j=Math.min(colors.length-2,Math.floor(p));
          c=colors[j].map((v,k)=>Math.round(v+(colors[j+1][k]-v)*(p-j)));
        }
        im.data.set([...c,255],i*4);
      }
      ctx.putImageData(im,0,0);return cv.toDataURL('image/png');
    }
    $('population-budget').addEventListener('change',onChange);$('population-pattern').addEventListener('change',onChange);
    $('population-reset').addEventListener('click',()=>{$('population-budget').value=m.default_population/1e6;$('population-pattern').value='markets';onChange();});
    $('population-provinces').addEventListener('click',e=>{
      const b=e.target.closest('button[data-name]');if(!b)return;
      selectedProvince=selectedProvince===b.dataset.name?null:b.dataset.name;onProvince(selectedProvince);
      for(const button of $('population-provinces').querySelectorAll('button'))button.setAttribute('aria-pressed',button.dataset.name===selectedProvince?'true':'false');
    });
    $('population-clear').addEventListener('click',()=>{selectedProvince=null;onProvince(null);for(const b of $('population-provinces').querySelectorAll('button'))b.setAttribute('aria-pressed','false');});
    $('population-download').addEventListener('click',()=>{
      compute();const s=state(),rows=['province,area_km2,allocated_people,local_support_people'];
      for(let p=0;p<=m.provinces.length;p++){
        let area=0,people=0,support=0;for(let i=0;i<f.area.length;i++)if(f.province[i]===p){area+=f.area[i];people+=result.people[i];support+=capacity[i];}
            if(area)rows.push(['"'+(p?m.provinces[p-1]:'Outside province grid').replace(/"/g,'""')+'"',area,people,support].join(','));
      }
      rows.push(['"TOTAL ALLOCATED"','',result.allocated,''].join(','));rows.push(['"UNALLOCATED"','',result.unallocated,''].join(','));
      const a=document.createElement('a'),url=URL.createObjectURL(new Blob([rows.join('\n')+'\n'],{type:'text/csv;charset=utf-8'}));a.href=url;a.download='population_'+s.population+'_'+s.pattern+'_'+$('disease').value+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    });
    compute();return {render,state,select:(x,y,name)=>{selection=[x,y,name];point();},
      stats:()=>({...result,people:undefined})};
  }
  return {allocate,load};
});

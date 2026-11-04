/* Seasonal source coverage. No sovereignty, military strength or empty-land inference. */
window.CoverageAtlas=(()=>{
  const $=id=>document.getElementById(id),hash=async b=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),x=>x.toString(16).padStart(2,'0')).join('');
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  async function bytes(url){const r=await fetch(url);if(!r.ok)throw Error(`Coverage HTTP ${r.status}`);return r.arrayBuffer();}
  function mask(word,b){let m=0;for(let t=0;t<12;t++)if(((word>>>(2*t))&3)>=3-b)m|=1<<t;return m;}
  const pop=new Uint8Array(4096),gap=new Uint8Array(4096);
  for(let m=0;m<4096;m++){
    let run=0;for(let t=0;t<12;t++)if(m&(1<<t))pop[m]++;
    for(let t=0;t<24;t++){run=m&(1<<(t%12))?0:Math.min(12,run+1);gap[m]=Math.max(gap[m],run);}
  }
  async function extend(meta,fresh,mode){
    if(!document.querySelector('script[data-coverage-enabled]'))return null;
    const manifest=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/coverage.json')))),packet=manifest.packets[mode];
    if(!packet||packet.expected_harvest_fingerprint!==meta.harvest?.fingerprint)throw Error('Coverage climate does not match');
    meta.layers.push(...packet.layers);return {manifest,packet,fresh,mode};
  }
  async function attach(state,harvest,changed,compare){
    const {packet:p,fresh,mode}=state;
    if(!harvest||await hash(harvest.binaryBuffer)!==p.expected_harvest_binary_sha256)throw Error('Coverage food/climate inputs changed');
    const n=p.land_cells,k=p.actors.length;let loading=null,loaded=false,lookup,words,unknown,landGrid,registry,selection=null,active=false,view='coverage',records=[];
    const cache=new Map();
    $('coverage-actor').innerHTML='<option value="all">All represented actors</option>'+p.actors.map((a,i)=>`<option value="${i}">${esc(a.name)}</option>`).join('');
    $('coverage-sources').innerHTML=p.scenario_labels.map((v,i)=>`<option value="${i}">${esc(v)}</option>`).join('');
    $('coverage-budget').innerHTML=p.budgets_days.map((v,i)=>`<option value="${i}">${v} days per leg</option>`).join('');
    const initial=new URLSearchParams(location.hash.slice(1)),actorName=initial.get('coverage_actor');
    const ai=p.actors.findIndex(a=>a.name===actorName);$('coverage-actor').value=ai>=0?String(ai):'all';
    const si=p.scenarios.indexOf(initial.get('coverage_sources'));$('coverage-sources').value=String(si>=0?si:0);
    const bi=p.budgets_days.indexOf(Number(initial.get('coverage_budget')));$('coverage-budget').value=String(bi>=0?bi:1);
    $('coverage-inventory').innerHTML=p.actors.map(a=>`<tr><th scope="row">${esc(a.name)}</th>${a.source_counts.map(c=>`<td>${c}</td>`).join('')}<td>${a.source_counts[0]?'provisional linked sites':'missing affiliated-site inventory'}</td></tr>`).join('');
    $('coverage-grid').href='data/'+p.binary;$('coverage-registry').href='data/'+p.registry;$('coverage-source-csv').href='data/'+p.sources_csv;
    $('coverage-compare').addEventListener('click',compare);$('coverage-open-audit').addEventListener('click',()=>changed(true));
    for(const id of ['coverage-actor','coverage-sources','coverage-budget'])$(id).addEventListener('change',()=>changed());
    function config(){return {s:Number($('coverage-sources').value),a:$('coverage-actor').value==='all'?-1:Number($('coverage-actor').value),b:Number($('coverage-budget').value)};}
    async function load(){
      if(!loading)loading=(async()=>{
        const [compressed,reg]=await Promise.all([bytes(fresh('data/'+p.binary)),bytes(fresh('data/'+p.registry))]);
        if(await hash(compressed)!==p.binary_sha256||await hash(reg)!==p.registry_sha256)throw Error('Coverage data identity changed');
        if(!window.DecompressionStream)throw Error('This browser cannot open compressed coverage grids');
        const raw=await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
        if(raw.byteLength!==p.raw_bytes)throw Error('Coverage grid length changed');
        lookup=new Uint32Array(raw,0,p.shape[0]*p.shape[1]);words=new Uint32Array(raw,p.offsets.words,3*k*2*n);unknown=new Uint32Array(raw,p.offsets.unknown,2*n);
        landGrid=new Uint32Array(n);const seen=new Uint8Array(n);let cells=0;
        for(let i=0;i<lookup.length;i++)if(lookup[i]){
          const j=lookup[i]-1;if(j>=n||seen[j])throw Error('Invalid coverage land index');seen[j]=1;landGrid[j]=i;cells++;
        }
        if(cells!==n)throw Error('Incomplete coverage land index');
        registry=JSON.parse(new TextDecoder().decode(reg));loaded=true;
      })();
      return loading;
    }
    const wordAt=(s,a,d,i)=>words[(((s*k+a)*2+d)*n)+i];
    function masks(s,a,d,b){
      const key=[s,a,d,b].join('/');if(cache.has(key))return cache.get(key);
      const result=new Uint16Array(n),overlap=new Uint16Array(n);
      for(let actor=a<0?0:a;actor<(a<0?k:a+1);actor++)for(let i=0;i<n;i++){
        const m=mask(wordAt(s,actor,d,i),b);overlap[i]|=result[i]&m;result[i]|=m;
      }
      const entry={mask:result,overlap};if(cache.size>=12)cache.delete(cache.keys().next().value);cache.set(key,entry);return entry;
    }
    function point(){
      if(!loaded||!selection)return;
      let [x,y,name]=selection;
      const named=name?registry.records.find(r=>r.name===name&&r.node!==undefined):null;
      const grid=named?named.node:Math.max(0,Math.min(p.shape[0]-1,Math.floor(y/p.cell_px)))*p.shape[1]+Math.max(0,Math.min(p.shape[1]-1,Math.floor(x/p.cell_px)));
      const index=lookup[grid]-1;const {s,a:chosen,b}=config(),a=view==='unknown'?-1:chosen;
      $('coverage-place').textContent=name?`Coverage near ${name}`:'At the selected coverage cell';
      if(index<0){$('coverage-readouts').textContent='Choose land on the travel-analysis grid.';$('coverage-point').textContent='';$('coverage-point-note').textContent='';$('coverage-download').disabled=true;records=[];return;}
      records=[];
      for(let sc=0;sc<3;sc++)for(let actor=0;actor<k;actor++){
        const sources=p.actors[actor].source_counts[sc],out=mask(wordAt(sc,actor,0,index),b),both=mask(wordAt(sc,actor,1,index),b);
        records.push({climate:mode,grid_row:Math.floor(grid/p.shape[1]),grid_column:grid%p.shape[1],source_scenario:p.scenarios[sc],actor:p.actors[actor].name,
          source_nodes:sources,per_leg_days:p.budgets_days[b],status:sources?'conditional_site_access':'missing_source_inventory',
          outward_bins:sources?pop[out]:null,same_site_two_way_bins:sources?pop[both]:null,longest_two_way_gap:sources?gap[both]:null,
          unaffiliated_site_two_way_bins:pop[mask(unknown[n+index],b)],scope:'site-access scenario, not sovereignty, conflict or absent communities'});
      }
      const sc=view==='source_gain'?2:s;const selected=records.slice(sc*k,(sc+1)*k);
      $('coverage-point').innerHTML=selected.map(r=>`<tr><th scope="row">${esc(r.actor)}</th><td>${r.source_nodes}</td><td>${r.outward_bins??'unscored'}</td><td>${r.same_site_two_way_bins??'unscored'}</td><td>${r.longest_two_way_gap??'unscored'}</td></tr>`).join('');
      const missing=a>=0&&(p.actors[a].source_counts[sc]===0||(view==='source_gain'&&p.actors[a].source_counts[0]===0));
      const both=masks(sc,a,1,b).mask[index],out=masks(sc,a,0,b).mask[index];
      const overlap=masks(sc,-1,1,b).overlap[index]&both;
      const rows=missing?[["Unscored","missing source inventory"]]:[[pop[out]+'/12','outward access bins'],[pop[both]+'/12','same-site outward and return bins'],[gap[both],'longest cyclic gap, bins'],[pop[overlap]+'/12','overlapping actor-reach bins']];
      if(!missing&&view==='source_gain')rows.push([pop[both&~masks(0,a,1,b).mask[index]]+'/12','bins added by source hypothesis']);
      if(!missing&&view==='direction_gap')rows.push([pop[out&~both]+'/12','outward access without same-site return']);
      if(view==='unknown')rows.length=0;
      rows.push([pop[mask(unknown[n+index],b)]+'/12','access from unaffiliated marked sites']);
      $('coverage-readouts').innerHTML=rows.map(([v,label])=>`<div class="readout"><div class="v">${esc(v)}</div><div class="k">${esc(label)}</div></div>`).join('');
      $('coverage-point-note').textContent='Readouts describe travel from available site inventories. Unscored actors may have unrecorded communities, camps or institutions. Outward and return access use the same site in each seasonal snapshot.';
      $('coverage-download').disabled=false;
    }
    $('coverage-download').addEventListener('click',()=>{
      if(!records.length)return;const keys=Object.keys(records[0]),q=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
      const csv=[keys,...records.map(r=>keys.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\r\n')+'\r\n';
      window.atlasSave('selected_world_coverage.csv',new Blob([csv],{type:'text/csv;charset=utf-8'}));
    });
    async function render(variant){
      await load();view=variant?.value||'coverage';const {s,a,b}=config(),sc=view==='source_gain'?2:s;
      const noInventory=a>=0&&(p.actors[a].source_counts[sc]===0||(view==='source_gain'&&p.actors[a].source_counts[0]===0));
      const both=masks(sc,a,1,b),values=new Uint8Array(n);let selected=both.mask;
      if(view==='source_gain'){
        const base=masks(0,a,1,b).mask,expanded=masks(2,a,1,b).mask;for(let i=0;i<n;i++)values[i]=pop[expanded[i]&~base[i]];
      }else if(view==='direction_gap'){
        const out=masks(s,a,0,b).mask;for(let i=0;i<n;i++)values[i]=pop[out[i]&~selected[i]];
      }else if(view==='overlap'){
        const over=masks(s,-1,1,b).overlap;for(let i=0;i<n;i++)values[i]=pop[over[i]&selected[i]];
      }else if(view==='unknown')for(let i=0;i<n;i++)values[i]=pop[mask(unknown[n+i],b)];
      else for(let i=0;i<n;i++)values[i]=(view==='isolation'?gap:pop)[selected[i]];
      const colors=view==='isolation'?['#286f70','#8db3a0','#c5c799','#d3b081','#b87c65','#824f58']:
        ['#eee9df','#d8c8b2','#c6b593','#a1b8a3','#69998a','#286f70'];
      const labels=view==='isolation'?['No gap bins','1–2 bins','3–5','6–8','9–11','All 12 bins']:['0 bins','1–3 bins','4–6','7–9','10–11','All 12 bins'];
      const bounds=view==='isolation'?[.5,2.5,5.5,8.5,11.5]:[.5,3.5,6.5,9.5,11.5];
      const canvas=document.createElement('canvas');canvas.width=p.shape[1];canvas.height=p.shape[0];const ctx=canvas.getContext('2d'),im=ctx.createImageData(canvas.width,canvas.height);
      for(let i=0;i<lookup.length;i++){im.data[i*4]=214;im.data[i*4+1]=227;im.data[i*4+2]=240;im.data[i*4+3]=255;}
      const rgb=colors.map(c=>[1,3,5].map(i=>parseInt(c.slice(i,i+2),16)));
      for(let i=0;i<n;i++){
        let code=0;while(code<bounds.length&&values[i]>=bounds[code])code++;
        const c=noInventory&&view!=='unknown'?[183,180,174]:rgb[code],j=landGrid[i]*4;im.data[j]=c[0];im.data[j+1]=c[1];im.data[j+2]=c[2];
      }
      ctx.putImageData(im,0,0);point();
      return {url:canvas.toDataURL('image/png'),items:noInventory&&view!=='unknown'?[{color:'#b7b4ae',label:'Missing inventory; access unscored'}]:colors.map((color,i)=>({color,label:labels[i]})),
        context:(view==='unknown'?'Unaffiliated marked sites':a<0?'All represented actors':p.actors[a].name)+' · '+p.budgets_days[b]+' days per leg · '+(view==='unknown'?'unresolved affiliation':view==='source_gain'?'evidence → generated sources':p.scenario_labels[s])};
    }
    return {render,select:(...v)=>{selection=v;if(active)point();},
      state:()=>{const {s,a,b}=config();return {coverage_actor:a<0?'all':p.actors[a].name,coverage_sources:p.scenarios[s],coverage_budget:p.budgets_days[b]};},
      show:(id,variant)=>{
        active=id==='reach_coverage_audit';view=variant?.value||'coverage';$('coverage-controls').hidden=!active;$('coverage-section').hidden=!active;
        $('coverage-baseline-note').hidden=!['reach_defacto','reach_polities'].includes(id);
        if(active){$('harvest-section').hidden=true;$('coverage-actor-control').hidden=view==='unknown';$('coverage-source-control').hidden=['unknown','source_gain'].includes(view);}
      }};
  }
  return {extend,attach,mask};
})();

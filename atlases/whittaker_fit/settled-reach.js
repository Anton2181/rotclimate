/* One food ledger changes settlement allocation, then available reach sources. */
window.SettledReachAtlas=(()=>{
  const $=id=>document.getElementById(id),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const digest=async b=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),v=>v.toString(16).padStart(2,'0')).join('');
  async function bytes(url){const r=await fetch(url);if(!r.ok)throw Error('Settlement support HTTP '+r.status);return r.arrayBuffer();}
  async function unpack(b){if(!window.DecompressionStream)throw Error('Updated browser needed for optional support ledgers');return new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();}
  async function extend(meta,fresh,mode){
    if(!document.querySelector('script[data-settled-reach-enabled]'))return null;
    const manifest=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/settled_reach.json')))),p=manifest.packets[mode];
    if(!p||p.expected_harvest_fingerprint!==meta.harvest?.fingerprint)throw Error('Settlement support climate mismatch');
    const originals=meta.layers.filter(l=>['reach_towns','reach_defacto'].includes(l.id));
    if(originals.length!==2)throw Error('Missing original settlement/reach modes');
    const changed=originals.map(l=>{const options=l.variants?.options||[{value:'0',label:'Original placement',file:l.file,items:l.items,note:l.note}];
      return {...l,label:l.id==='reach_towns'?'Settlements':'Supply-supported reach',controls:[],variants:{label:'Settlement / supply scenario',default:'joint365',options:[...p.options[l.id],...options.map(o=>({...o,value:'legacy_'+o.value,label:'Legacy · '+o.label,integrated_support:false}))]}};});
    meta.layers=meta.layers.map(l=>changed.find(c=>c.id===l.id)||l);
    return {p,fresh,mode,restore:()=>{meta.layers=meta.layers.map(l=>originals.find(c=>c.id===l.id)||l);}};
  }
  async function attach(state,harvest,changed,choosePlace){
    const {p,fresh,mode}=state;
    if(!harvest||await digest(harvest.binaryBuffer)!==p.expected_harvest_binary_sha256)throw Error('Settlement Harvest identity changed');
    let model=null,lookup=null,catchments=null,masks=null,pending=null,active=false,layer='',variant='joint365',siteId=new URLSearchParams(location.hash.slice(1)).get('settled_site'),selected=null,generation=0,skipInitial=true;
    const fmt=(v,d=0)=>Number(v).toLocaleString(undefined,{maximumFractionDigits:d}),pop=v=>{let n=0;for(;v;v&=v-1)n++;return n;};
    const readouts=rows=>rows.map(([v,k])=>`<div class="readout"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join('');
    function clear(message){$('settled-readouts').textContent='';$('settled-site-note').textContent=message;$('settled-global').textContent='';$('settled-months').textContent='';$('settled-cell').textContent='';$('settled-download').disabled=true;}
    async function load(){
      if(model)return;if(pending)return pending;
      pending=(async()=>{
        const [a,b]=await Promise.all([bytes(fresh('data/'+p.payload)),bytes(fresh('data/'+p.binary))]);
        if(await digest(a)!==p.payload_sha256||await digest(b)!==p.binary_sha256)throw Error('Settlement packet checksum mismatch');
        const [ar,br]=await Promise.all([unpack(a),unpack(b)]),m=JSON.parse(new TextDecoder().decode(ar));
        if(m.climate!==mode||JSON.stringify(m.shape)!==JSON.stringify(p.shape)||br.byteLength!==p.raw_bytes)throw Error('Invalid settlement packet layout');
        const size=p.shape[0]*p.shape[1];lookup=new Uint32Array(br,0,size);catchments=new Uint16Array(br,p.offsets.catchments,size);masks=new Uint16Array(br,p.offsets.masks);
        if(catchments.some(i=>i>m.sites.length)||lookup.some(i=>i>p.land_cells)||masks.some(v=>v>4095))throw Error('Invalid settlement resource indices');
        model=m;$('settled-site').innerHTML=m.sites.map(s=>`<option value="${s.id}">${esc(s.name)} · ${esc(s.actor||'unresolved affiliation')}</option>`).join('');
        if(!m.sites.some(s=>s.id===siteId))siteId=m.sites.find(s=>s.marked)?.id||m.sites[0].id;
        $('settled-site').value=siteId;$('settled-ledgers').href='data/'+p.payload;$('settled-grid').href='data/'+p.binary;
      })().catch(e=>{pending=null;throw e;});return pending;
    }
    function render(){
      if(!active||!model)return;
      const k=model.cases.findIndex(c=>c.id===variant),c=model.cases[k],j=model.sites.findIndex(s=>s.id===siteId),s=model.sites[j],sum=model.summaries[k],reference=model.summaries[0];
      $('settled-global').textContent=`${fmt(sum.viable_communities)} / ${fmt(model.sites.length)} candidate communities meet the declared minimum; ${fmt(sum.active_sources)} / ${fmt(reference.active_sources)} affiliated sources staffed. Modelled two-way access: ${fmt(sum.area_weighted_access_bins,2)} / 12 area-weighted bins (matched reference ${fmt(reference.area_weighted_access_bins,2)}). These are alternative scenarios, not extra census people.`;
      $('settled-readouts').innerHTML=readouts([[fmt(s.civilian_request_people),'reference civilian request'],[c.food_constrained?fmt(c.food_ceiling_people[j]):'Unconstrained','seasonal food ceiling · all residents'],[fmt(c.civilian_people[j]),'allocated civilian scenario'],[fmt(c.institutional_people[j]),'institutional residents · same food pool'],[c.institutional_active[j]?'Available':'Unavailable / unassigned','source for this reach scenario'],[c.community_viable[j]?'Meets minimum':'Below scenario minimum','50 civilian reference people']]);
      $('settled-site-note').textContent=s.name+' · '+(s.actor||'affiliation unresolved')+' · '+s.affiliation_basis+'. '+(s.marked?'Marked place retained as evidence even if local cereal cannot support the scenario. ':'Proposed administrative/market location; this is not a worldwide village or camp generator. ')+
        'The 7.5% civilian request is a scenario, not a validated town-size model. No imports, other foods or labour budget are inferred. A failed grain scenario does not establish abandonment or political collapse.';
      $('settled-months').innerHTML=c.food_constrained?Array.from({length:12},(_,t)=>`<tr><th>${t+1}</th><td>${fmt(c.monthly_arrivals_kcal[j][t]/1e6,2)}</td><td>${fmt(c.monthly_need_kcal[j][t]/1e6,2)}</td><td>${fmt(c.stock_path_kcal[j][t+1]/1e6,2)}</td></tr>`).join(''):'<tr><td colspan="4">Transport-matched counterfactual: food unconstrained; no grain ledger or demographic validation claimed.</td></tr>';
      let index=-1;
      if(selected){const [x,y]=selected,row=Math.floor(y/p.cell_px),col=Math.floor(x/p.cell_px);if(row>=0&&row<p.shape[0]&&col>=0&&col<p.shape[1])index=lookup[row*p.shape[1]+col]-1;}
      $('settled-cell').innerHTML=index>=0?model.actors.map((a,i)=>{const bins=pop(masks[(k*model.actors.length+i)*p.land_cells+index]),v=sum.actors[i];return `<tr><th>${esc(a.name)}</th><td>${v.inventory_scored?fmt(v.active_sources)+' / '+fmt(v.candidate_sources):'Inventory missing'}</td><td>${v.inventory_scored?bins+' / 12':'Unscored'}</td></tr>`;}).join(''):'<tr><td colspan="3">Select land for actor-specific two-way reach. Missing inventories are unscored, not empty territory.</td></tr>';
      $('settled-download').disabled=false;
    }
    $('settled-site').addEventListener('change',()=>{siteId=$('settled-site').value;render();changed();const s=model.sites.find(s=>s.id===siteId);choosePlace?.((s.column+.5)*p.cell_px,(s.row+.5)*p.cell_px,s.name);});
    $('settled-download').addEventListener('click',()=>{
      if(!model||!active)return;const j=model.sites.findIndex(s=>s.id===siteId),s=model.sites[j],rows=[];
      for(const c of model.cases)for(let t=0;t<12;t++)rows.push({climate:mode,site_id:s.id,site:s.name,actor:s.actor,affiliation_basis:s.affiliation_basis,scenario:c.id,seasonal_bin:t+1,civilian_request_people:s.civilian_request_people,food_ceiling_people:c.food_constrained?c.food_ceiling_people[j]:null,civilian_people:c.civilian_people[j],institutional_people:c.institutional_people[j],institutional_active:c.institutional_active[j],arrivals_kcal:c.food_constrained?c.monthly_arrivals_kcal[j][t]:null,need_kcal:c.food_constrained?c.monthly_need_kcal[j][t]:null,end_stock_kcal:c.food_constrained?c.stock_path_kcal[j][t+1]:null,scope:'conditional local cereal settlement/source allocation; not measured population or sovereignty'});
      const keys=Object.keys(rows[0]),q=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
      window.atlasSave('settlement_food_source.csv',new Blob([[keys,...rows.map(r=>keys.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\r\n')+'\r\n'],{type:'text/csv;charset=utf-8'}));
    });
    return {state:()=>({settled_site:siteId||''}),show:(id,v)=>{
      layer=id;variant=v?.value||'joint365';active=['reach_towns','reach_defacto'].includes(id)&&!!v?.integrated_support;const gen=++generation;$('settled-section').hidden=!active;
      if(active){$('harvest-section').hidden=true;clear('Loading the joint settlement and food ledger…');load().then(()=>{if(gen===generation)render();}).catch(e=>{if(gen===generation){clear('Detailed ledger unavailable: '+e.message+'. The precomputed map remains a conditional scenario.');console.error(e);}});}
    },select:(x,y)=>{selected=[x,y];if(skipInitial){skipInitial=false;return;}if(!active||!model)return;const row=Math.floor(y/p.cell_px),col=Math.floor(x/p.cell_px),i=row>=0&&row<p.shape[0]&&col>=0&&col<p.shape[1]?catchments[row*p.shape[1]+col]:0;if(i){siteId=model.sites[i-1].id;$('settled-site').value=siteId;}render();changed();}};
  }
  return {extend,attach};
})();

/* Recorded communication hierarchy; no inferred jurisdiction or ownership. */
window.AdministrativeHierarchy=(()=>{
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const hash=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
  async function bytes(url){const r=await fetch(url);if(!r.ok)throw Error(`Hierarchy HTTP ${r.status}`);return r.arrayBuffer();}
  const sum=xs=>xs.some(x=>x===null)?null:xs.reduce((a,b)=>a+b,0);
  function stats(values,budget){
    const finite=values.filter(v=>v!==null);let mask=0,run=0,longest=0;
    values.forEach((v,i)=>{if(v!==null&&v<=budget)mask|=1<<i;});
    for(let i=0;i<24;i++){run=(mask&(1<<(i%12)))?0:Math.min(12,run+1);longest=Math.max(longest,run);}
    return {best:finite.length?Math.min(...finite):null,worst:finite.length===12?Math.max(...finite):null,
      within:values.filter(v=>v!==null&&v<=budget).length,longest};
  }
  async function extend(meta,fresh,mode){
    if(!document.querySelector('script[data-hierarchy-enabled]'))return null;
    const manifest=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/administrative_hierarchy.json'))));
    const packet=manifest.packets[mode];
    if(!packet||packet.expected_harvest_fingerprint!==meta.harvest?.fingerprint)throw Error('Hierarchy climate does not match');
    if(await hash(await bytes(fresh('data/administrative_inventory.json')))!==manifest.inventory_sha256)throw Error('Hierarchy inventory changed');
    meta.layers.push(...packet.layers);return {manifest,packet,fresh,mode};
  }
  async function attach(state,harvest,changed,choosePlace){
    const {manifest,packet,fresh,mode}=state;
    if(!harvest||await hash(harvest.binaryBuffer)!==packet.expected_harvest_binary_sha256)throw Error('Hierarchy food/climate input changed');
    const raw=await bytes(fresh('data/'+packet.days_file));if(await hash(raw)!==packet.days_sha256)throw Error('Hierarchy travel data changed');
    const payload=JSON.parse(new TextDecoder().decode(raw));const days=payload.days,links=manifest.registry.links;
    if(JSON.stringify(payload.leg_order)!==JSON.stringify(['capital_to_province','province_to_seat','seat_to_province','province_to_capital'])||
       !Array.isArray(days)||days.length!==2||days.some(s=>s.length!==12||s.some(m=>m.length!==links.length||m.some(r=>r.length!==4||r.some(v=>v!==null&&(!Number.isFinite(v)||v<0))))))
      throw Error('Invalid hierarchy travel table');
    $('hierarchy-commandery').innerHTML=links.map(c=>`<option value="${esc(c.commandery_id)}">${esc(c.name)}${c.status==='located'?'':' · unresolved'}</option>`).join('');
    $('hierarchy-budget').innerHTML=manifest.budgets_days.map(v=>`<option value="${v}">${v} days</option>`).join('');
    const initial=new URLSearchParams(location.hash.slice(1));
    if(links.some(c=>c.commandery_id===initial.get('commandery')))$('hierarchy-commandery').value=initial.get('commandery');
    $('hierarchy-budget').value=manifest.budgets_days.includes(Number(initial.get('reply_budget')))?initial.get('reply_budget'):'30';
    let skipInitial=initial.has('commandery'),scenario=0,active=false,records=[];
    const fmt=v=>v===null?'unreachable':v.toFixed(1);
    function render(){
      const i=links.findIndex(c=>c.commandery_id===$('hierarchy-commandery').value),c=links[i];const budget=Number($('hierarchy-budget').value);
      $('hierarchy-place').textContent=c.name+' · '+(c.seat_name||'unresolved seat');
      $('hierarchy-parent').textContent=`Recorded province: ${c.province||'unknown'}; provincial seat: ${c.province_seat||'unresolved'}.`;
      $('hierarchy-selection-note').textContent='Readouts describe this recorded seat, not the territory around a clicked point.';
      $('hierarchy-download').disabled=c.status!=='located';
      if(c.status!=='located'){
        $('hierarchy-readouts').textContent='Seat or provincial assignment unresolved; no travel time or budget score assigned.';
        $('hierarchy-months').textContent='';records=[];return;
      }
      records=[];
      for(let s=0;s<2;s++)for(let m=0;m<12;m++){
        const legs=days[s][m][i];records.push({climate:mode,scenario:packet.scenarios[s],model_month:m+1,commandery_id:c.commandery_id,
          commandery:c.name,province:c.province,province_seat:c.province_seat,capital_to_province:legs[0],province_to_seat:legs[1],
          seat_to_province:legs[2],province_to_capital:legs[3],provincial_reply_days:sum(legs.slice(1,3)),imperial_reply_days:sum(legs),
          reply_budget_days:budget,scope:'same-month travel-only hierarchy scenario, not political control'});
      }
      const current=records.slice(12*scenario,12*(scenario+1));const imperial=stats(current.map(r=>r.imperial_reply_days),budget);
      const local=stats(current.map(r=>r.provincial_reply_days),budget);
      $('hierarchy-readouts').innerHTML=[[fmt(local.worst),'days · longest provincial reply'],[fmt(imperial.worst),'days · longest imperial reply via province'],
        [imperial.within+'/12','bins within selected imperial reply budget'],[imperial.longest,'longest consecutive bins over budget']]
        .map(([v,k])=>`<div class="readout"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join('');
      $('hierarchy-months').innerHTML=Array.from({length:12},(_,m)=>{
        const a=records[m],b=records[m+12];return `<tr><th scope="row">${m+1}</th><td>${fmt(a.province_to_seat)}</td><td>${fmt(a.seat_to_province)}</td><td>${fmt(a.imperial_reply_days)}</td><td>${fmt(b.province_to_seat)}</td><td>${fmt(b.seat_to_province)}</td><td>${fmt(b.imperial_reply_days)}</td></tr>`;
      }).join('');
    }
    $('hierarchy-grid').href='data/'+packet.grid;$('hierarchy-csv').href='data/'+packet.csv;
    for(const id of ['hierarchy-commandery','hierarchy-budget'])$(id).addEventListener('change',()=>{
      render();changed();
      if(id==='hierarchy-commandery'){
        const c=links.find(c=>c.commandery_id===$('hierarchy-commandery').value);
        if(c?.status==='located')choosePlace?.(c.x,c.y,c.seat_name);
      }
    });
    $('hierarchy-download').addEventListener('click',()=>{
      if(!records.length)return;const keys=Object.keys(records[0]),quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
      const csv=[keys,...records.map(r=>keys.map(k=>r[k]))].map(r=>r.map(quote).join(',')).join('\r\n')+'\r\n';
      window.atlasSave('selected_administrative_reply.csv',new Blob([csv],{type:'text/csv;charset=utf-8'}));
    });
    render();
    return {state:()=>({commandery:$('hierarchy-commandery').value,reply_budget:$('hierarchy-budget').value}),
      selectedPlace:()=>{const c=links.find(c=>c.commandery_id===$('hierarchy-commandery').value);return c?.status==='located'?c:null;},
      show:(id,variant)=>{active=id==='hierarchy_links';$('hierarchy-section').hidden=!active;
        if(active){$('harvest-section').hidden=true;scenario=variant?.scenario??0;$('hierarchy-view-note').textContent=variant?.caption||'';render();}},
      select:(x,y,name)=>{
        if(skipInitial){skipInitial=false;return;}if(!active)return;
        const key=s=>String(s??'').normalize('NFKD').replace(/\p{M}/gu,'').trim().toLowerCase();
        const named=links.find(c=>key(c.seat_name)===key(name)||key(c.name)===key(name+' Commandery'));
        if(name&&named){$('hierarchy-commandery').value=named.commandery_id;render();changed();return;}
        const candidates=links.filter(c=>c.status==='located').map(c=>({c,d:Math.hypot(c.x-x,c.y-y)})).sort((a,b)=>a.d-b.d);
        if(candidates[0]?.d<=15){$('hierarchy-commandery').value=candidates[0].c.commandery_id;render();changed();}
        else $('hierarchy-selection-note').textContent='No verified seat near this click. Use the commandery selector; the readouts still describe the selected seat.';
      }};
  }
  return {extend,attach,stats};
})();

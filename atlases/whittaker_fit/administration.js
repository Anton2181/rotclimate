/* Administrative inventory and isolated access scenarios, not inferred allegiance. */
window.AdministrativeAtlas=(()=>{
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const hash=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
  async function bytes(url){const r=await fetch(url);if(!r.ok)throw Error(`Administration HTTP ${r.status}`);return r.arrayBuffer();}
  async function extend(meta,fresh,mode){
    if(!document.querySelector('script[data-administration-enabled]'))return null;
    const manifest=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/administrative_access.json'))));
    const packet=manifest.packets[mode];
    if(!packet || packet.expected_harvest_fingerprint!==meta.harvest?.fingerprint)throw Error('Administrative access climate does not match');
    const inventoryBytes=await bytes(fresh('data/'+manifest.inventory));
    if(await hash(inventoryBytes)!==manifest.inventory_sha256)throw Error('Administrative inventory changed');
    meta.layers.push(...packet.layers);
    return {manifest,packet,mode,inventory:JSON.parse(new TextDecoder().decode(inventoryBytes)),fresh};
  }
  function metrics(mask){
    let months=0,run=0,longest=0;
    for(let i=0;i<12;i++)if(mask&(1<<i))months++;
    for(let i=0;i<24;i++){run=(mask&(1<<(i%12)))?0:Math.min(12,run+1);longest=Math.max(longest,run);}
    return {months,longest};
  }
  async function attach(state,harvest){
    const {manifest,packet,mode,inventory,fresh}=state;
    if(!harvest || await hash(harvest.binaryBuffer)!==packet.expected_harvest_binary_sha256)
      throw Error('Administrative access does not match the loaded food/population inputs');
    const buffer=await bytes(fresh('data/'+packet.binary));
    const cells=packet.shape[0]*packet.shape[1];
    if(buffer.byteLength!==cells*15 || await hash(buffer)!==packet.binary_sha256)throw Error('Administrative access grid changed or is incomplete');
    const masks=new Uint16Array(buffer,0,6*cells);
    const annual=new Uint8Array(buffer,packet.fields.annual_flags.offset,cells);
    const proposals=new Uint8Array(buffer,packet.fields.proposal_recurrence.offset,cells);
    const land=new Uint8Array(buffer,packet.fields.land.offset,cells);
    let selection=null,records=null,activeCase=0;
    $('administration-inventory-note').textContent=`${manifest.matched_centres} of ${manifest.listed_centres} commandery centres have confirmed marker positions. Remaining centres are unresolved or inexact and excluded from the recorded-centre scenario.`;
    $('administration-grid').href='data/'+packet.grid;
    $('administration-centres').href='data/'+manifest.centres_csv;
    $('administration-inventory').href='data/'+manifest.inventory;
    $('administration-scenarios').innerHTML=packet.cases.map((c,i)=>{
      const s=packet.summaries[c];return `<tr><th scope="row">${esc(packet.case_labels[i])}</th><td>${packet.source_counts[c]}</td><td>${s.mean_months_in_claim.toFixed(2)}</td><td>${(100*s.twelve_month_claim_share).toFixed(1)}%</td></tr>`;
    }).join('');
    $('administration-unresolved').textContent=inventory.commanderies.filter(c=>c.status!=='matched').map(c=>
      c.name+': '+(c.discrepancies?.join(' ')||(c.status==='name_matched_position_unverified'?
        'named sheet location without a verified map symbol; excluded from the seat-source scenario.':'location unresolved.'))).join(' ');
    function point(){
      if(!selection)return;
      const [x,y,name]=selection;
      const row=Math.max(0,Math.min(packet.shape[0]-1,Math.floor(y/packet.cell_px)));
      const col=Math.max(0,Math.min(packet.shape[1]-1,Math.floor(x/packet.cell_px)));const index=row*packet.shape[1]+col;
      $('administration-place').textContent=name?`Access near ${name}`:'At the selected place';
      if(!land[index]){
        $('administration-readouts').textContent='Choose land on the access-analysis grid.';
        $('administration-point').textContent='';$('administration-download').disabled=true;records=null;return;
      }
      records=packet.cases.map((c,i)=>{
        const m=metrics(masks[i*cells+index]);return {climate:mode,grid_row:row,grid_column:col,
          source_case:c,source_nodes:packet.source_counts[c],accessible_model_month_bins:m.months,
          longest_isolation_bins:m.longest,annual_mean_inside_cutoff:!!(annual[index]&(1<<i)),
          proposal_runs_within_10km:proposals[index],scope:'access scenario, not political ownership or military strength'};
      });
      const selected=records[activeCase];
      const readouts=[[selected.accessible_model_month_bins+'/12','bins within two-day access'],
        [selected.longest_isolation_bins,'longest consecutive isolated bins'],
        [selected.annual_mean_inside_cutoff?'inside':'outside','annual mean versus two-day cutoff'],
        [proposals[index]+'/3','proposal runs with a town within 10 km']];
      $('administration-readouts').innerHTML=readouts.map(([v,k])=>`<div class="readout"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join('');
      $('administration-point').innerHTML=records.map((r,i)=>`<tr><th scope="row">${esc(packet.case_labels[i])}</th><td>${r.accessible_model_month_bins}/12</td><td>${r.longest_isolation_bins}</td><td>${r.annual_mean_inside_cutoff?'inside':'outside'}</td></tr>`).join('');
      $('administration-download').disabled=false;
    }
    $('administration-download').addEventListener('click',()=>{
      if(!records)return;
      const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';const keys=Object.keys(records[0]);
      const csv=[keys,...records.map(r=>keys.map(k=>r[k]))].map(row=>row.map(quote).join(',')).join('\r\n')+'\r\n';
      window.atlasSave('selected_imperial_access.csv',new Blob([csv],{type:'text/csv;charset=utf-8'}));
    });
    return {select:(...s)=>{selection=s;point();},show:(id,variant)=>{
      const active=id.startsWith('admin_');$('administration-section').hidden=!active;
      if(active){$('harvest-section').hidden=true;activeCase=Math.max(0,packet.cases.indexOf(variant?.value));
        $('administration-view-note').textContent=variant?.caption||'Three declared settlement-placement seeds; recurrence is not probability.';point();}
    }};
  }
  return {extend,attach,metrics};
})();

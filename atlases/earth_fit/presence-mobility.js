/* Conditional food support and closed resource circuits, never ownership. */
window.PresenceMobilityAtlas=(()=>{
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const hash=async b=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),v=>v.toString(16).padStart(2,'0')).join('');
  async function bytes(url){const r=await fetch(url);if(!r.ok)throw Error(`Presence/mobility HTTP ${r.status}`);return r.arrayBuffer();}
  async function unpack(blob){if(!window.DecompressionStream)throw Error('Updated browser required for these optional gzip packets');return new Response(new Blob([blob]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();}
  async function extend(meta,fresh,mode){
    if(!document.querySelector('script[data-presence-mobility-enabled]'))return null;
    const manifest=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/presence_mobility.json')))),packet=manifest.packets[mode];
    if(!packet||packet.expected_harvest_fingerprint!==meta.harvest?.fingerprint)throw Error('Presence/mobility climate identity mismatch');
    meta.layers.push(...packet.layers);return {manifest,packet,mode,fresh};
  }
  async function attach(state,harvest,changed,choosePlace){
    const {packet,mode,fresh}=state;
    if(!harvest||await hash(harvest.binaryBuffer)!==packet.expected_harvest_binary_sha256)throw Error('Presence/mobility Harvest input changed');
    const [compressed,gridCompressed]=await Promise.all([bytes(fresh('data/'+packet.payload)),bytes(fresh('data/'+packet.catchments))]);
    if(await hash(compressed)!==packet.payload_sha256||await hash(gridCompressed)!==packet.catchments_sha256)throw Error('Presence/mobility packet identity mismatch');
    const [raw,grid]=await Promise.all([unpack(compressed),unpack(gridCompressed)]),model=JSON.parse(new TextDecoder().decode(raw));
    if(model.climate!==mode||JSON.stringify(model.shape)!==JSON.stringify(packet.shape)||grid.byteLength!==packet.shape[0]*packet.shape[1]*2)throw Error('Invalid presence/mobility layout');
    const catchments=new Uint16Array(grid);
    if(catchments.some(v=>v>model.sites.length))throw Error('Invalid collection site index');
    const initial=new URLSearchParams(location.hash.slice(1));let active='',variant='stores90',records=[],skipInitial=true;
    let insetFrame=initial.get('pm_frame')==='whole'?'whole':'detail';
    const fmt=(n,d=1)=>n===null||!Number.isFinite(n)?'Unscored':n.toLocaleString(undefined,{maximumFractionDigits:d});
    const pct=n=>n===null?'Unscored':fmt(n*100)+'%';
    const readouts=rows=>rows.map(([v,k])=>`<div class="readout"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join('');
    function patchLabels(locations){const labels=new Map();for(const i of locations)if(!labels.has(i))labels.set(i,String.fromCharCode(65+labels.size));return labels;}
    $('pm-site').innerHTML=model.sites.map(s=>`<option value="${esc(s.id)}">${esc(s.name)} · ${esc(s.actor||'affiliation unresolved')}</option>`).join('');
    $('pm-landscape').innerHTML=model.mobility.map(e=>`<option value="${esc(e.id)}">${esc(e.label)}</option>`).join('');
    $('pm-scale').innerHTML=(packet.scales||[{id:'local',label:'Local · all bases'}]).map(s=>`<option value="${esc(s.id)}">${esc(s.label)}</option>`).join('');
    $('pm-water').innerHTML=model.specification.mobility.water_scenarios.map(c=>`<option value="${esc(c.id)}">${esc(c.label)}</option>`).join('');
    for(const [key,id] of [['pm_site','pm-site'],['pm_landscape','pm-landscape'],['pm_water','pm-water'],['pm_scale','pm-scale']])if([...$(id).options].some(o=>o.value===initial.get(key)))$(id).value=initial.get(key);
    const examples=()=>$('pm-scale').value==='local'?model.mobility:model.mobility_scales[$('pm-scale').value];
    $('pm-payload').href='data/'+packet.payload;$('pm-catchments').href='data/'+packet.catchments;
    function presence(){
      const site=model.sites.find(s=>s.id===$('pm-site').value),scenario=model.presence.find(c=>c.id===variant)||model.presence[0],j=model.sites.indexOf(site),v=scenario.sites[j];
      const ps=model.specification.presence,ruralDays=scenario.rural_store_days??ps.rural_store_demand_days,exportDays=scenario.export_store_days??ps.export_store_days_of_annual_exportable_supply,collection=scenario.collection_fraction??ps.collection_fraction_of_rural_overflow;
      $('pm-place').textContent=site.name+' · '+(site.actor||'affiliation unresolved');
      $('pm-readouts').innerHTML=readouts([[pct(v.annual_need_met),'declared annual food need met'],[pct(v.worst_bin_need_met),'worst seasonal-bin need met'],
        [v.shortfall_bins+'/12','bins with unmet food need'],[scenario.people,'people in this scenario'],[scenario.reserve_days,'destination store · demand-days'],
        [v.minimum_zero_loss_store_demand_days===null?'Annual deficit':fmt(v.minimum_zero_loss_store_demand_days),'minimum store · zero-loss lower bound'],
        [ruralDays,'protected rural store · demand-days'],[exportDays,'origin store · annual export-flow days'],[pct(collection),'rural overflow offered for collection']]);
      $('pm-point-note').textContent=`Food-support test for ${scenario.people} people at 2,500 kcal/day; ${5*(scenario.freight_multiplier||1)} tonnes edible cereal-equivalent freight slots per bin. `+
        'Single wheat/barley crop only. Local rural demand is protected over the full repeating year; a shortage prevents export from that cell. Separate origin stores feed dispatch. One-bin delivery delay and explicit losses. These assumptions do not establish staff, rights to collect food or political control.'+
        (scenario.id==='rural180'?' The cereal-only rural store test omits other staples and exchange; a failure does not establish actual rural famine.':'');
      $('pm-months').innerHTML=Array.from({length:12},(_,m)=>`<tr><th scope="row">${m+1}</th><td>${pct(v.monthly_need_met[m])}</td><td>${fmt(v.monthly_arrivals_kcal[m]/1e6)} M kcal</td><td>${fmt(v.stock_path_kcal[m+1]/1e6)} M kcal</td><td>${v.closed_dispatch_bins?.includes(m)?'Closed dispatch':'Open dispatch'}</td></tr>`).join('');
      $('pm-table-head').innerHTML='<tr><th>Seasonal bin</th><th>Need met</th><th>Arrivals</th><th>End stock</th><th>Dispatch scenario</th></tr>';
      records=[];
      for(const c of model.presence){const r=c.sites[j];for(let m=0;m<12;m++)records.push({climate:mode,site_id:site.id,site:site.name,recorded_actor:site.actor,
        scenario:c.id,people:c.people,ration_kcal_person_day:model.specification.presence.ration_kcal_person_day,site_store_demand_days:c.reserve_days,
        freight_kcal_site_bin:model.specification.presence.freight_kcal_per_site_per_bin*(c.freight_multiplier||1),seasonal_bin:m+1,
        rural_store_demand_days:c.rural_store_days??ps.rural_store_demand_days,export_store_flow_days:c.export_store_days??ps.export_store_days_of_annual_exportable_supply,
        fraction_of_rural_overflow_for_collection:c.collection_fraction??ps.collection_fraction_of_rural_overflow,
        need_met:r.monthly_need_met[m],arrivals_kcal:r.monthly_arrivals_kcal[m],unmet_kcal:r.monthly_unmet_kcal[m],end_stock_kcal:r.stock_path_kcal[m+1],
        closed_dispatch:r.closed_dispatch_bins?.includes(m)||false,scope:'conditional cereal support, not actual staffing or sovereignty'});}
      $('pm-inset').innerHTML='';$('pm-inset').hidden=true;$('pm-inset-controls').hidden=true;$('pm-download').disabled=false;
    }
    function inset(experiment,scenario){
      const patches=experiment.patches,ground=experiment.ground_nodes||patches,cell=packet.cell_px,px=ground.map(p=>p.x),py=ground.map(p=>p.y);
      let x0=Math.min(...px)-cell,y0=Math.min(...py)-cell,w=Math.max(...px)-x0+cell,h=Math.max(...py)-y0+cell;
      const circuit=scenario.mobile,visited=circuit?circuit.locations:[],counts=patches.map((_,i)=>visited.filter(j=>i===j).length);
      $('pm-inset-controls').hidden=!circuit;
      $('pm-inset-frame').textContent=insetFrame==='detail'?'Show whole tested landscape':'Focus on route';
      $('pm-inset-frame').setAttribute('aria-pressed',String(insetFrame==='whole'));
      if(circuit&&insetFrame==='detail'){
        const path=circuit.segments.flat().map(i=>ground[i]);
        const a=Math.min(...path.map(p=>p.x)),b=Math.max(...path.map(p=>p.x)),c=Math.min(...path.map(p=>p.y)),d=Math.max(...path.map(p=>p.y));
        const size=Math.max(8*cell,b-a+4*cell,d-c+4*cell);
        x0=(a+b-size)/2;y0=(c+d-size)/2;w=size;h=size;
      }
      const u=Math.max(1,w/22);
      const palette=['#e5decd','#afc6ad','#5d9c8e','#285f72'];
      let svg=`<svg viewBox="${x0} ${y0} ${w} ${h}" role="img" aria-label="Selected resource landscape and closed route; schematic seasonal endpoints connected along model land paths" style="width:100%;max-width:620px;height:auto;max-height:390px;background:var(--chip)">`;
      if(experiment.ground_nodes)for(const p of ground)svg+=`<rect x="${p.x-cell/2}" y="${p.y-cell/2}" width="${cell}" height="${cell}" fill="#dadbd3"/>`;
      for(let i=0;i<patches.length;i++){const p=patches[i],excluded=scenario.maximum_mapped_water_distance_km!==null&&p.water_distance_km>scenario.maximum_mapped_water_distance_km;
        const colour=excluded?'#ada8a2':palette[counts[i]===0?0:counts[i]<=3?1:counts[i]<=8?2:3];
        svg+=`<rect x="${p.x-cell/2}" y="${p.y-cell/2}" width="${cell}" height="${cell}" fill="${colour}" stroke="#fff" stroke-opacity=".3" stroke-width=".08"/>`;
      }
      if(circuit){
        const points=circuit.segments.flat().map(i=>`${ground[i].x},${ground[i].y}`).join(' ');
        svg+=`<polyline points="${points}" fill="none" stroke="white" stroke-width="${.8*u}"/><polyline points="${points}" fill="none" stroke="#203d50" stroke-width="${.32*u}"/>`;
        for(const [i,label] of patchLabels(visited)){const p=patches[i];
          svg+=`<circle cx="${p.x}" cy="${p.y}" r="${.55*u}" fill="#fff" stroke="#203d50" stroke-width="${.1*u}"/><text x="${p.x}" y="${p.y+.22*u}" text-anchor="middle" font-size="${.65*u}" font-family="sans-serif" fill="#203d50">${label}</text>`;
        }
      }
      const home=patches[experiment.home];svg+=`<rect x="${home.x-.75*u}" y="${home.y-.75*u}" width="${1.5*u}" height="${1.5*u}" fill="none" stroke="#9b4e62" stroke-width="${.25*u}"/></svg>`;
      $('pm-inset').innerHTML=svg;$('pm-inset').hidden=false;
    }
    function mobility(){
      const e=examples().find(e=>e.id===$('pm-landscape').value);$('pm-place').textContent=e.label+' · '+$('pm-scale').selectedOptions[0].textContent;
      records=[];$('pm-download').disabled=true;
      if(e.status!=='scored_resource_landscape'){$('pm-readouts').textContent='Resource/home location unresolved; experiment unscored.';$('pm-months').textContent='';$('pm-inset').hidden=true;$('pm-inset-controls').hidden=true;return;}
      const c=e.cases.find(c=>c.id===$('pm-water').value)||e.cases[0],m=c.mobile,s=c.stationary,best=c.best_fixed_base_continuous;
      inset(e,c);
      $('pm-readouts').innerHTML=readouts([[m?pct(m.annual_need_met):'Unscored','mobile · annual DM need met'],[s?pct(s.annual_need_met):'Unscored','fixed home · same reserve states'],
        [best?pct(best.annual_need_met):'Unscored','best fixed base anywhere · continuous reserve'],[m?fmt(m.total_travel_days):'Unscored','travel days / repeating year'],
        [m?m.shortage_bins+'/12':'Unscored','mobile · shortfall bins'],[m?m.moves:'Unscored','seasonal moves between bases'],
        ...(c.resource_upper_bound?[[pct(c.resource_upper_bound.annual_need_met),'optimistic resource-only upper bound']]:[])]);
      $('pm-point-note').textContent=c.status!=='conditional_circuit'?
        'The fixed home fails this mapped-water proximity scenario, so no route is scored. This does not establish lack of water: wells, seasonal water, permanence and drinkable volumes remain unknown.':
        'One independent experiment with 100 dry-matter reference units, not an inferred community or herd. The circuit returns to the same home AND feed reserve. Transit meals come from previously carried feed. Only current-bin forage at the occupied patch can be collected. Inset letters identify resource patches; the table gives seasonal order. The red square marks the fixed home. These are not observed camps. Best fixed-base control allows relocation and continuous feed reserves; it may outperform the circuit. No human diet, nutrition adequacy, access rights or livestock mortality is predicted.';
      if(e.ground_nodes)$('pm-point-note').textContent+=' Regional tests keep the grazing footprint and travel budget fixed. Pale land provides paths, not extra food at a base. The stronger fixed-base and optimistic bounds examine every home-connected fine cell, including unsampled bases. The resource bound ignores travel and is not a feasible route.';
      $('pm-table-head').innerHTML='<tr><th>Seasonal bin</th><th>Resource patch · row,column</th><th>DM need met</th><th>Carried feed · end</th><th>Travel</th></tr>';
      const labels=m?patchLabels(m.locations):new Map();
      $('pm-months').innerHTML=m?m.locations.map((i,t)=>{const p=e.patches[i];return `<tr><th scope="row">${t+1}</th><td>${labels.get(i)} · ${p.row}, ${p.column}</td><td>${pct(1-m.unmet[t]/(100*6.25*365/12))}</td><td>${fmt(m.reserves[t+1])} kg DM</td><td>${fmt(m.travel_days[t],2)} d</td></tr>`;}).join(''):'<tr><td colspan="5">Unscored under the selected water scenario.</td></tr>';
      for(const which of ['mobile','stationary']){const r=c[which];if(!r)continue;for(let t=0;t<12;t++){const p=e.patches[r.locations[t]];records.push({climate:mode,landscape:e.id,landscape_scale:$('pm-scale').value,water_scenario:c.id,case:which,
        seasonal_bin:t+1,patch_row:p.row,patch_column:p.column,water_distance_km:p.water_distance_km,reference_feed_units:100,reference_intake_kg_dm_day:6.25,
        supply_at_patch_kg_dm:p.monthly_dm_kg[t],collected_kg_dm:r.collected[t],consumed_kg_dm:r.consumed[t],unmet_kg_dm:r.unmet[t],
        start_reserve_kg_dm:r.reserves[t],end_reserve_kg_dm:r.reserves[t+1],travel_days:r.travel_days[t],discarded_at_visited_patch_kg_dm:r.discarded[t],
        best_fixed_base_annual_need_met:best?.annual_need_met,optimistic_resource_bound_annual_need_met:c.resource_upper_bound?.annual_need_met,
        scope:'independent conditional DM circuit, not actual camp, herd, nutrition or population'});}}
      $('pm-download').disabled=!records.length;
    }
    function overlay(){
      const el=$('pm-overlay');el.style.display=active==='mobility_circuits'?'':'none';if(active!=='mobility_circuits')return;
      el.innerHTML=model.mobility.filter(e=>e.status==='scored_resource_landscape').map((e,i)=>{const p=e.patches[e.home],selected=e.id===$('pm-landscape').value;
        return `<circle cx="${p.x}" cy="${p.y}" r="${selected?11:8}" fill="#f8faf9" stroke="#203d50" stroke-width="1.5"/><text x="${p.x}" y="${p.y+3}" text-anchor="middle" font-size="10" font-family="sans-serif" fill="#203d50">${i+1}</text>`;}).join('');
    }
    function render(){if(active==='presence_food')presence();else if(active==='mobility_circuits')mobility();overlay();}
    for(const id of ['pm-site','pm-landscape','pm-water','pm-scale'])$(id).addEventListener('change',()=>{
      render();changed();
      if(id==='pm-site'&&active==='presence_food'){const s=model.sites.find(s=>s.id===$('pm-site').value),w=packet.shape[1];choosePlace?.((s.node%w+.5)*packet.cell_px,(Math.floor(s.node/w)+.5)*packet.cell_px,s.name);}
      if(id==='pm-landscape'&&active==='mobility_circuits'){const e=examples().find(e=>e.id===$('pm-landscape').value);if(e.status==='scored_resource_landscape'){const p=e.patches[e.home];choosePlace?.(p.x,p.y,e.label);}}
    });
    $('pm-inset-frame').addEventListener('click',()=>{insetFrame=insetFrame==='detail'?'whole':'detail';render();changed();});
    $('pm-download').addEventListener('click',()=>{if(!records.length)return;const keys=Object.keys(records[0]),quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
      const csv=[keys,...records.map(r=>keys.map(k=>r[k]))].map(r=>r.map(quote).join(',')).join('\r\n')+'\r\n';window.atlasSave('selected_'+(active==='presence_food'?'food_support':'seasonal_circuit')+'.csv',new Blob([csv],{type:'text/csv;charset=utf-8'}));});
    return {state:()=>active==='presence_food'?{pm_site:$('pm-site').value}:{pm_landscape:$('pm-landscape').value,pm_water:$('pm-water').value,pm_scale:$('pm-scale').value,pm_frame:insetFrame},
      show:(id,v)=>{active=id;variant=v?.value||'stores90';const on=['presence_food','mobility_circuits'].includes(id);$('pm-section').hidden=!on;
        if(id==='mobility_circuits'&&v?.scale_files)v.file=v.scale_water_files?.[$('pm-scale').value]?.[$('pm-water').value]||v.scale_files[$('pm-scale').value];
        $('pm-site-control').hidden=id!=='presence_food';$('pm-mobility-controls').hidden=id!=='mobility_circuits';
        if(on){$('harvest-section').hidden=true;$('pm-title').textContent=id==='presence_food'?'Sustained presence · conditional cereal support':'Seasonal circuits · conditional herd resources';render();}else overlay();},
      select:(x,y)=>{if(skipInitial){skipInitial=false;return;}if(!['presence_food','mobility_circuits'].includes(active))return;
        if(active==='presence_food'){const r=Math.max(0,Math.min(packet.shape[0]-1,Math.floor(y/packet.cell_px))),c=Math.max(0,Math.min(packet.shape[1]-1,Math.floor(x/packet.cell_px))),id=catchments[r*packet.shape[1]+c];
          if(id){$('pm-site').value=model.sites[id-1].id;render();changed();}else $('pm-point-note').textContent='Outside this experiment’s fixed collection areas. No food-support or sovereignty score is assigned here; the selected-site readouts are unchanged.';
        }else{const row=Math.floor(y/packet.cell_px),col=Math.floor(x/packet.cell_px);
          const selected=examples().find(e=>(e.ground_nodes||e.patches||[]).some(p=>p.row===row&&p.column===col));
          if(selected){$('pm-landscape').value=selected.id;render();changed();}else $('pm-point-note').textContent='Outside the four independent resource experiments; no mobile community or route is inferred here. Use the landscape selector for a scored scenario.';}
      }};
  }
  return {extend,attach};
})();

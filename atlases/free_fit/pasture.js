/* Worldwide feed-resource diagnostics; no inferred people, herds or institutions. */
window.PastureAtlas=(()=>{
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const hash=async b=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),v=>v.toString(16).padStart(2,'0')).join('');
  async function bytes(url){const r=await fetch(url);if(!r.ok)throw Error(`Pasture HTTP ${r.status}`);return r.arrayBuffer();}
  async function extend(meta,fresh,mode){
    if(!document.querySelector('script[data-pasture-enabled]'))return null;
    const manifest=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/pasture.json')))),packet=manifest.packets[mode];
    if(!packet||packet.expected_harvest_fingerprint!==meta.harvest?.fingerprint)throw Error('Pasture climate does not match');
    meta.layers.push(...packet.layers);return {manifest,packet,mode,fresh};
  }
  async function attach(state,harvest){
    const {manifest,packet,mode,fresh}=state,spec=manifest.specification;
    if(!harvest||await hash(harvest.binaryBuffer)!==packet.expected_harvest_binary_sha256)throw Error('Pasture food/climate inputs changed');
    const blob=await bytes(fresh('data/'+packet.binary)),count=packet.shape[0]*packet.shape[1],views={};
    if(await hash(blob)!==packet.binary_sha256)throw Error('Pasture grid changed');
    const types={uint16:Uint16Array,uint8:Uint8Array,float32:Float32Array};let end=0;
    for(const [key,s] of Object.entries(packet.fields)){
      const Type=types[s.dtype];if(!Type||s.offset<0||s.offset!==end)throw Error('Invalid pasture field layout');
      views[key]=new Type(blob,s.offset,count);end=s.offset+count*Type.BYTES_PER_ELEMENT;
    }
    if(blob.byteLength!==end)throw Error('Incomplete pasture grid');
    const field=(key,i)=>{const value=views[key][i],s=packet.fields[key];return !Number.isFinite(value)||(s.nodata!==null&&value===s.nodata)?null:value*s.scale;};
    const fmt=(v,d=1)=>v===null?'Unavailable':v.toLocaleString(undefined,{maximumFractionDigits:d});
    let selection=null,record=null;
    $('pasture-grid').href='data/'+packet.grid;
    function point(){
      if(!selection)return;const [x,y,name]=selection;
      const row=Math.max(0,Math.min(packet.shape[0]-1,Math.floor(y/packet.cell_px))),col=Math.max(0,Math.min(packet.shape[1]-1,Math.floor(x/packet.cell_px))),i=row*packet.shape[1]+col;
      $('pasture-place').textContent=name?`Resource cell near ${name}`:'At the selected analysis cell';
      if(!views.land[i]){
        $('pasture-readouts').textContent='Choose an analysis cell containing land.';$('pasture-selection-note').textContent='';$('pasture-download').disabled=true;record=null;return;
      }
      const annual=field('annual_dm',i),lean=field('lean_fraction',i),reserve=field('reserve_days',i),shortfall=field('shortfall_bins',i),water=field('water_distance',i);
      const units=annual===null?null:annual/(spec.reference_intake_kg_dm_day*spec.year_days);
      record={climate:mode,grid_row:row,grid_column:col,status:annual===0?'no_modeled_forage':reserve===null?'seasonality_unresolved':'conditional_dm_diagnostic',
        annual_usable_dm_kg_per_land_km2:annual,annual_feed_reference_units_per_land_km2:units,lean_new_growth_fraction:lean,
        minimum_zero_loss_reserve_demand_days:reserve,shortfall_bins_with_90_demand_day_buffer:shortfall,mapped_water_distance_km:water,
        test_demand_fraction:spec.test_demand_fraction_of_annual_supply,reference_intake_kg_dm_day:spec.reference_intake_kg_dm_day,
        scope:'feed-resource scenario, not animal nutritional adequacy, human population or political control'};
      const rows=[[annual===null?'Unavailable':fmt(annual/1000)+' t','usable DM /land km²/year'],[fmt(units,2),'annual DM feed-equivalent units /land km²'],
        [lean===null?'Unavailable':fmt(lean*100)+'%','lean-bin new growth /mean'],[fmt(reserve),'minimum reserve · demand-days'],
        [shortfall===null?'Unavailable':shortfall+'/12','shortfall bins · 90-day buffer'],[water===null?'Unavailable':fmt(water)+' km','mean distance to mapped water']];
      $('pasture-readouts').innerHTML=rows.map(([v,k])=>`<div class="readout"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join('');
      $('pasture-selection-note').textContent=annual===0?'No usable forage under the current assumptions. This does not establish an uninhabitable cell.':reserve===null?
        'Annual forage exists but seasonal allocation is unresolved; no uniform growing season is invented.':
        'Reserve test: constant demand equal to half annual usable DM, zero storage loss. Feed equivalents are not actual animals or additional people. Water proximity does not establish drinkable supply.';
      $('pasture-download').disabled=false;
    }
    $('pasture-download').addEventListener('click',()=>{
      if(!record)return;const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
      const csv=[Object.keys(record),Object.values(record)].map(r=>r.map(quote).join(',')).join('\r\n')+'\r\n';
      window.atlasSave('selected_pasture_resources.csv',new Blob([csv],{type:'text/csv;charset=utf-8'}));
    });
    return {select:(...s)=>{selection=s;point();},show:(id,variant)=>{
      const active=id.startsWith('pasture_');$('pasture-section').hidden=!active;
      if(active){$('harvest-section').hidden=true;$('pasture-view-note').textContent=variant?.caption||'Proximity to mapped water; permanence, salinity and wells remain unknown.';point();}
    }};
  }
  return {extend,attach};
})();

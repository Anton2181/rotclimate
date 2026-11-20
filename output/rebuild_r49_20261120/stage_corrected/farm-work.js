/* Optional partial cereal-work maps. Reuse the exact loaded Harvest packet. */
window.FarmWorkAtlas = (() => {
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const hash=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
  async function bytes(url) {const r=await fetch(url);if(!r.ok)throw Error(`Cereal work HTTP ${r.status}`);return r.arrayBuffer();}
  async function extend(meta,fresh,mode) {
    if(!document.querySelector('script[data-farm-work-enabled]'))return null;
    const manifest=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/farm_work.json'))));
    const packet=manifest.packets[mode];
    if(!packet || packet.expected_harvest_fingerprint!==meta.harvest?.fingerprint || packet.harvest_metadata!==meta.harvest.metadata)
      throw Error('Cereal work maps do not match the selected Harvest climate');
    const metadata=await bytes(fresh('data/'+packet.harvest_metadata));
    if(await hash(metadata)!==packet.harvest_metadata_sha256)throw Error('Cereal work Harvest metadata changed');
    const mask=await bytes(fresh('data/'+packet.calendar_binary));
    if(mask.byteLength!==packet.shape[0]*packet.shape[1]*2 || await hash(mask)!==packet.calendar_binary_sha256)
      throw Error('Cereal calendar grid is incomplete or changed');
    meta.layers.push(...packet.layers);
    return {manifest,packet,boundaries:new Uint16Array(mask)};
  }
  async function attach(state,harvest) {
    if(!state)return null;
    if(!harvest || await hash(harvest.binaryBuffer)!==state.packet.harvest_binary_sha256)
      throw Error('Cereal work maps do not match the loaded Harvest binary');
    const {manifest,packet,boundaries}=state;let selection=null,record=null;
    const fmt=v=>Number.isFinite(v)?v.toLocaleString(undefined,{maximumFractionDigits:2}):'Unavailable';
    $('farm-work-grid').href='data/'+packet.grid;
    $('farm-work-method').href='../../reports/CEREAL_WORK_MAPS_20261103.md';
    function point() {
      if(!selection)return;
      const [x,y,name,sea]=selection;
      const col=Math.max(0,Math.min(packet.shape[1]-1,Math.floor(x/packet.cell_px)));
      const row=Math.max(0,Math.min(packet.shape[0]-1,Math.floor(y/packet.cell_px)));const i=row*packet.shape[1]+col;
      $('farm-work-place').textContent=name?`Field work near ${name}`:'At the selected place';
      const energy=manifest.crops.map(c=>harvest.fieldAt('kcal_'+c,i));
      if(sea || energy.every(v=>v===null)) {
        $('farm-work-readouts').textContent='Choose land to inspect a cereal field-work scenario.';
        $('farm-work-selection-note').textContent='';$('farm-work-download').disabled=true;record=null;return;
      }
      const costs=energy.map((e,c)=>e>0?manifest.food_target_kcal/e*manifest.listed_hours_per_hectare[c]:Infinity);
      const crop=costs[0]<=costs[1]?0:1;const valid=Number.isFinite(costs[crop]);
      const area=valid?manifest.food_target_kcal/energy[crop]:NaN;
      const reaping=valid?area*manifest.reaping_hours_per_hectare[crop]:NaN;
      const bins=Array.from({length:12},(_,b)=>b).filter(b=>boundaries[i]&(1<<b));
      record={climate:packet.harvest_metadata.startsWith('corrected/')?'corrected':'raw',grid_row:row,grid_column:col,
        status:valid?'partial_cereal_work_scenario':'no_modeled_cereal_output',food_target_kcal:manifest.food_target_kcal,
        cereal:valid?manifest.crops[crop]:'',listed_hours:valid?costs[crop]:null,cropped_hectares:valid?area:null,
        reaping_hours:valid?reaping:null,harvest_boundary_options:bins.length,
        staff_10_days:valid?reaping/(10*manifest.hours_per_workday):null,
        staff_20_days:valid?reaping/(20*manifest.hours_per_workday):null,
        staff_30_days:valid?reaping/(30*manifest.hours_per_workday):null};
      $('farm-work-download').disabled=false;
      const rows=valid?[
        [manifest.crops[crop],'least listed-work cereal'],[fmt(costs[crop])+' h','listed field work /million net kcal'],
        [fmt(area)+' ha','cropped land for that cereal target'],[fmt(reaping)+' h','reaping work for that target'],
        ...[10,20,30].map(d=>[fmt(reaping/(d*manifest.hours_per_workday)),`reaping worker equivalents · ${d} days`]),
        [String(bins.length),'tied optimal harvest-boundary bins'],
      ]:[['Unavailable','no positive modeled wheat/barley output']];
      $('farm-work-readouts').innerHTML=rows.map(([v,k])=>`<div class="readout"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join('');
      $('farm-work-selection-note').textContent=valid
        ?'Listed tasks to the threshing floor only. Calendar bins are alternatives in the current crop model, not probabilities or observed harvest dates.'
        :'Other crops, grazing or imported food may still be available here. Unavailable cereal work is not zero work.';
    }
    $('farm-work-download').addEventListener('click',()=>{
      if(!record)return;
      const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
      const csv=Object.keys(record).map(quote).join(',')+'\r\n'+Object.values(record).map(quote).join(',')+'\r\n';
      window.atlasSave('selected_cereal_work.csv',new Blob([csv],{type:'text/csv;charset=utf-8'}));
    });
    return {select:(...s)=>{selection=s;point();},show:(id,v)=>{
      const active=id.startsWith('farm_cereal_');
      $('farm-work-section').hidden=!active;if(active)$('harvest-section').hidden=true;
      $('farm-work-view-note').textContent=active?(v?.caption||'All equally productive harvest-boundary alternatives, not a predicted calendar.') :'';
      if(active)point();
    }};
  }
  return {extend,attach};
})();

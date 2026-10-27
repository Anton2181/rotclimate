/* Optional terrestrial-foraging scenarios, separate from agricultural support. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.ForagingAtlas=api;
})(typeof globalThis!=='undefined'?globalThis:this,()=>{
  const TYPES={uint8:Uint8Array,uint16:Uint16Array,int16:Int16Array,float32:Float32Array,float64:Float64Array};
  const $=id=>document.getElementById(id);
  const esc=value=>String(value??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const number=(value,digits=1)=>Number.isFinite(value)?value.toLocaleString(undefined,{maximumFractionDigits:digits}):'—';
  const people=value=>value>=1e6?number(value/1e6,2)+' M':value>=1e3?number(value/1e3,1)+' k':number(value,0);
  const readouts=rows=>rows.map(([value,label])=>`<div class="readout"><div class="v">${esc(value)}</div><div class="k">${esc(label)}</div></div>`).join('');

  function decodePacket(metadata,buffer){
    const shape=metadata.shape;
    if(!Array.isArray(shape)||shape.length!==2||shape.some(n=>!Number.isSafeInteger(n)||n<=0))
      throw Error('Invalid foraging grid.');
    const count=shape[0]*shape[1],fields={};let end=0;
    if(!Number.isSafeInteger(count)||!metadata.arrays||typeof metadata.arrays!=='object')
      throw Error('Invalid foraging packet.');
    for(const [name,descriptor] of Object.entries(metadata.arrays)){
      const Type=TYPES[descriptor.dtype],offset=descriptor.offset_bytes;
      if(!Type||!Number.isSafeInteger(offset)||offset<0||offset%Type.BYTES_PER_ELEMENT||
          !Array.isArray(descriptor.shape)||descriptor.shape.length!==2||descriptor.shape.some((n,i)=>n!==shape[i])||
          offset+count*Type.BYTES_PER_ELEMENT>buffer.byteLength)
        throw Error('Incomplete or mismatched foraging data.');
      const scale=descriptor.scale??1,add=descriptor.offset??0;
      if(!Number.isFinite(scale)||!Number.isFinite(add))throw Error('Invalid foraging field units.');
      fields[name]={data:new Type(buffer,offset,count),nodata:descriptor.nodata,scale,offset:add};
      end=Math.max(end,offset+count*Type.BYTES_PER_ELEMENT);
    }
    if(end!==buffer.byteLength||!fields.land_fraction||!fields.converged)
      throw Error('Foraging data size or required fields differ from its metadata.');
    return {
      shape,
      at(name,index){
        const field=fields[name];if(!field)return null;
        const value=field.data[index];
        return !Number.isFinite(value)||(field.nodata!==null&&field.nodata!==undefined&&value===field.nodata)
          ?null:value*field.scale+field.offset;
      }
    };
  }

  function indexAt(x,y,width,height,shape){
    if(![x,y,width,height].every(Number.isFinite)||width<=0||height<=0)
      throw Error('Invalid foraging map coordinates.');
    const column=Math.max(0,Math.min(shape[1]-1,Math.floor(x/width*shape[1])));
    const row=Math.max(0,Math.min(shape[0]-1,Math.floor(y/height*shape[0])));
    return row*shape[1]+column;
  }

  async function load(meta,fresh){
    const specification=meta.foraging;
    if(!specification)throw Error('This atlas has no foraging scenario packet.');
    const [response,binary]=await Promise.all([
      fetch(fresh('data/'+specification.metadata),{cache:'no-store'}),
      fetch(fresh('data/'+specification.binary),{cache:'no-store'})]);
    if(!response.ok||!binary.ok)throw Error('Foraging data could not load. Check the complete atlas folder.');
    const metadata=await response.json();
    if(!specification.fingerprint||metadata.fingerprint!==specification.fingerprint)
      throw Error('Foraging data belong to a different atlas build.');
    const buffer=await(window.atlasBytes?window.atlasBytes(binary):binary.arrayBuffer());
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buffer)),v=>v.toString(16).padStart(2,'0')).join('');
    if(digest!==metadata.binary_sha256)throw Error('Foraging data do not match their metadata. Update the complete atlas folder.');
    const packet=decodePacket(metadata,buffer);
    let selection=null;
    function point(){
      if(!selection)return;
      const [x,y,name,sea]=selection,index=indexAt(x,y,meta.width,meta.height,packet.shape);
      $('foraging-place').textContent=name?`Foraging near ${name}`:'At the selected place';
      const value=key=>packet.at(key,index),land=value('land_fraction');
      if(sea||!(land>0)){
        $('foraging-readouts').textContent='Choose land to inspect the terrestrial-foraging scenario.';
        $('foraging-status').textContent='Fishing and marine food are not included.';return;
      }
      if(value('unsupported')===1||value('floor_limited')===1){
        $('foraging-readouts').textContent='The modeled resources did not sustain a supported population.';
        $('foraging-status').textContent='The run reached its population floor. That numerical floor is not a positive density estimate.';return;
      }
      if(value('converged')!==1){
        $('foraging-readouts').textContent='No converged scenario estimate at this place.';
        $('foraging-status').textContent='The seasonal run did not meet its convergence requirement. Its trial values are not presented as support estimates.';return;
      }
      const density=value('density_people_km2'),effort=value('foraging_hours_day'),meat=value('meat_fraction'),scarcity=value('scarcity_days_year');
      const rows=[];
      if(density!==null)rows.push([`${number(density,3)} /km²`,'terrestrial-foraging scenario density']);
      if(effort!==null)rows.push([`${number(effort,2)} h/person/day`,'food procurement only']);
      if(meat!==null)rows.push([`${number(meat*100,1)}%`,'animal-food energy share']);
      if(scarcity!==null)rows.push([`${number(scarcity,0)} days/year`,'modeled food shortfall']);
      $('foraging-readouts').innerHTML=readouts(rows);
      $('foraging-status').textContent='A resource-forced scenario, not a census or an addition to agricultural population support. Procurement hours exclude water, fuel, shelter and other work.';
    }
    const summary=metadata.summary||{},totals=[];
    if(Number.isFinite(summary.total_scenario_people))totals.push([people(summary.total_scenario_people),'people in finite-horizon scenario']);
    if(Number.isFinite(summary.converged_scenario_people))totals.push([people(summary.converged_scenario_people),'people in converged subset']);
    if(Number.isFinite(summary.converged_land_share))totals.push([`${number(summary.converged_land_share*100,1)}%`,'modeled land meeting convergence']);
    if(Number.isFinite(summary.unsupported_land_share))totals.push([`${number(summary.unsupported_land_share*100,1)}%`,'modeled land reaching population floor']);
    $('foraging-totals').innerHTML=readouts(totals);
    $('foraging-context').textContent=metadata.model_note||'FORGE-inspired terrestrial-foraging scenarios with declared climate-to-resource proxies. These are not the published ORCHIDEE-driven global simulations.';
    const report=metadata.report_url||'../../reports/FORAGING_20261027.md';
    $('foraging-method').href=report;
    $('foraging-parameters').href='data/'+specification.metadata;
    $('foraging-sources').innerHTML=(metadata.sources||[]).filter(source=>source&&typeof source==='object'&&/^https?:\/\//.test(source.url||''))
      .map(source=>`<p><a href="${esc(source.url)}" target="_blank" rel="noopener">${esc(source.title||source.url)}</a>${source.used_for?' — '+esc(source.used_for):''}</p>`).join('');
    return {select:(x,y,name,sea)=>{selection=[x,y,name,sea];point();},refresh:point};
  }
  return {load,decodePacket,indexAt};
});

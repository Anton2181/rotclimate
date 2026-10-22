/* Optional land-and-people panel. Climate-only and historical atlases still work. */
window.HarvestAtlas = (() => {
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const number = (value, digits=1) => value === null ? '—' : Number(value).toLocaleString(undefined, {maximumFractionDigits:digits});
  const people = v => v >= 1e6 ? `${number(v/1e6)} M` : v >= 1e3 ? `${number(v/1e3)} k` : number(v,0);
  const readouts = rows => rows.map(([v,k]) => `<div class="readout"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join('');
  async function json(url) { const r=await fetch(url); if(!r.ok) throw Error(`Harvest HTTP ${r.status}`); return r.json(); }
  async function load(meta, fresh) {
    const [m, sources, earth, response] = await Promise.all([
      json(fresh('data/'+meta.harvest.metadata)), json(fresh('data/harvest_sources.json')),
      json(fresh('data/settlement_reference_regions.json')), fetch(fresh('data/'+meta.harvest.binary))]);
    if(!response.ok) throw Error(`Harvest binary HTTP ${response.status}`);
    const buf=await response.arrayBuffer(), types={uint8:Uint8Array,uint16:Uint16Array,float32:Float32Array};
    const fields={};
    for(const [name,a] of Object.entries(m.arrays)) {
      const count=a.shape.reduce((x,y)=>x*y,1), Type=types[a.dtype];
      if(!Type || a.offset_bytes+count*Type.BYTES_PER_ELEMENT>buf.byteLength) throw Error('Incomplete Harvest binary');
      fields[name]={...a,data:new Type(buf,a.offset_bytes,count)};
    }
    const at=(name,i) => {
      const a=fields[name], raw=a.data[i];
      return raw===a.nodata || !Number.isFinite(raw) ? null : raw*a.scale+a.offset;
    };
    const occupation=()=>$('occupation').value, disease=()=>$('disease').value;
    const fraction=()=>m.occupation.scenarios[occupation()];
    const base=()=>disease()==='absent'?'settlement_no_malaria':'settlement_base';
    let selection=null, province=null;
    function point() {
      if(!selection) return;
      const [x,y,name,sea]=selection;
      const col=Math.max(0,Math.min(m.shape[1]-1,Math.floor(x/m.cell_px)));
      const row=Math.max(0,Math.min(m.shape[0]-1,Math.floor(y/m.cell_px)));
      const i=row*m.shape[1]+col;
      $('harvest-place').textContent=name?`Land near ${name}`:'At the selected place';
      const crop=at('crop',i);
      if(sea || crop===null) {
        $('harvest-readouts').textContent='Choose land to inspect its food and settlement potential.';
        $('harvest-hex').textContent='';$('crop-yields').textContent='';return;
      }
      const v=k=>at(k,i), expected=v(base())*fraction();
      const low=v(base())*m.occupation.scenarios.frontier, high=v(base())*m.occupation.scenarios.core;
      $('harvest-readouts').innerHTML=readouts([
        [`${number(expected)} /km²`,`${occupation()} scenario population`],
        [`${number(low)}–${number(high)} /km²`,'frontier to settled-core scenarios'],
        [`${number(v('food_capacity'))} /km²`,'mixed food ceiling'],
        [`${number(v('crop_capacity'))} /km²`,'crop food ceiling'],
        [`${number(v('pastoral_capacity'))} /km²`,'grazing allowance'],
        [`${number(v(disease()==='absent'?'livability_no_malaria':'livability'))} /100`,'settlement potential'],
        [number(v('malaria'),2),'malaria potential, 0–1'],
        [`${number(v('malaria_months'),0)} months`,'potential malaria season'],
        [`${number(v('lgp_days'),0)} days`,'growing period'],
        [`${number(v('irr')*100)}%`,'potential irrigation reach'],
        [`${number(v('npp'),0)} g/m²`,'annual wild productivity'],
        [number(v('aridity'),2),'rain / evaporation'],
        [m.crop_labels[Math.round(crop)-1],'best staple'],
        [v('double_crop')>.5?'yes':'no','compatible second crop']]);
      const hid=Math.round(v('hex_id')), h=m.hexes[hid];
      $('harvest-hex').textContent=h?`Hex ${hid} · ${h.province}${h.commandery?' · '+h.commandery:''}${h.terrain?' · '+h.terrain:''}. Sheet settlement ${h.sheet_settlement??'unlisted'}, wealth ${h.sheet_wealth??'unlisted'}.`:'Outside the campaign hex grid.';
      $('crop-yields').innerHTML='<p class="note">Best single-crop edible energy, million kcal/ha/year, after seed:</p><div class="crop-key">'+['wheat','barley','millet','rice','dates'].map(k=>`<span>${esc(k)} ${number(v('kcal_'+k)/1e6,2)}</span>`).join('')+'</div>';
    }
    function highlight() {
      const p=m.provinces.find(p=>p.name===province), g=m.hexgrid, r=g.dx/Math.sqrt(3);
      $('province-overlay').innerHTML=p?p.hexes.map(id=>{
        const row=Math.floor((id-1)/g.ncol),col=(id-1)%g.ncol;
        const x=g.x0+g.dx*(col+.5*(row%2)), y=g.y0+g.dy*row;
        const points=Array.from({length:6},(_,i)=>{
          const a=(30+60*i)*Math.PI/180;return `${x+r*Math.cos(a)},${y+r*Math.sin(a)}`;
        }).join(' ');
        return `<polygon points="${points}" fill="#ffe29b" fill-opacity=".18" stroke="#7e3e09" stroke-width="1.2" vector-effect="non-scaling-stroke"/>`;
      }).join(''):'';
    }
    function refresh() {
      const s=m.summary, f=fraction();
      $('harvest-totals').innerHTML=readouts([
        [people(s.population[disease()][occupation()]),`${occupation()} scenario people`],
        [`${people(s.population[disease()].frontier)}–${people(s.population[disease()].core)}`,'frontier to settled-core scenarios'],
        [people(s.food_capacity),'mixed food ceiling'],
        [`${number(s.population[disease()][occupation()]/s.land_km2)} /km²`,'scenario land mean'],
        [`${number(s.land_km2,0)} km²`,'land area'],
        [`${number(s.double_crop_share*100)}%`,'land with compatible second crop']]);
      $('harvest-scenario').textContent=`${number(f*100)}% occupation of environmentally realized food potential; ${disease()==='absent'?'malaria penalty removed':'malaria penalty up to '+number(m.parameters.maximum_malaria_penalty*100)+'%'}. Other choices above change all population totals and the density map. These are scenarios, not confidence limits.`;
      const order=$('province-sort').value;
      const provinces=m.provinces.map((p,i)=>({...p,index:i}));
      provinces.sort((a,b)=>order==='name'?a.name.localeCompare(b.name):
        order==='food'?b.food_capacity_people-a.food_capacity_people:
        order==='wealth'?(b.sheet_wealth??-1)-(a.sheet_wealth??-1):
        order==='density'?b[base()]/b.area_km2-a[base()]/a.area_km2:b[base()]-a[base()]);
      $('province-rows').innerHTML=provinces.map(p=>{ const i=p.index;
        const pop=p[base()]*f;
        return `<tr><th scope="row"><button type="button" data-province="${i}" aria-pressed="${p.name===province}">${esc(p.name)}</button></th><td>${number(p.area_km2,0)}</td><td>${people(p.food_capacity_people)}</td><td>${people(pop)}</td><td>${number(pop/p.area_km2)}</td><td>${p.crops.map((v,i)=>({v,i})).sort((a,b)=>b.v-a.v).filter(c=>c.v>.05).slice(0,2).map(c=>esc(m.crop_labels[c.i])+" "+number(c.v*100)+"%").join(", ")}</td><td>${p.sheet_settlement===null?"—":number(p.sheet_settlement)}</td><td>${p.sheet_wealth===null?"—":number(p.sheet_wealth)}</td></tr>`;
      }).join('');point();
    }
    $('harvest-crops').innerHTML='<p class="note">Land by best staple</p><div class="crop-bar">'+slices(m.summary.crops,(s,i)=>`<span style="width:${s*100}%;background:${m.crop_colors[i]}" title="${esc(m.crop_labels[i])}: ${number(s*100)}%"></span>`)+ '</div><div class="crop-key">'+slices(m.summary.crops,(s,i)=>`<span>${esc(m.crop_labels[i])}: ${number(s*100)}%</span>`)+'</div>';
    $('harvest-sources').innerHTML=sources.components.map(s=>`<p><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a> — ${esc(s.used_for)}</p>`).join('');
    $('earth-reference').innerHTML=Object.entries(earth).map(([name,r])=>`<tr><th scope="row">${esc(name)}${r.fitted?' (crop calibration)':''}</th><td>${number(r.capacity_m,2)}</td><td>${r.historical_m.map(v=>number(v,2)).join('–')}</td><td>${esc(r.source)}</td></tr>`).join('');
    $('harvest-sheet').textContent=m.sheet_check?.note||'Sheet values are reported per hex when you select a place. They are not inputs to the climate or density model.';
    if(m.sheet_check?.correlations) $('harvest-sheet').textContent+=` Across ${m.sheet_check.hexes} sheet hexes, Spearman rank correlation of food capacity with settlement: ${number(m.sheet_check.correlations.food_capacity.settlement,2)}, wealth: ${number(m.sheet_check.correlations.food_capacity.wealth,2)}. This is a campaign consistency check, not historical validation.`;
    $('province-rows').addEventListener('click',e=>{
      const b=e.target.closest('button[data-province]');if(!b)return;
      const name=m.provinces[Number(b.dataset.province)].name;province=province===name?null:name;
      const index=b.dataset.province;
      highlight();refresh();
      $('province-rows').querySelector(`[data-province="${index}"]`)?.focus({preventScroll:true});
    });
    $('province-sort').addEventListener('change',refresh);
    $('province-clear').addEventListener('click',()=>{province=null;highlight();refresh();});
    $('harvest-section').hidden=false;refresh();
    return {refresh,select:(x,y,name,sea)=>{selection=[x,y,name,sea];point();}};
  }
  const slices=(values,fn)=>values.map(fn).join('');
  return {load};
})();

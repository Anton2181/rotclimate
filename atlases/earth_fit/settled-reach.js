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
    let feedback=null,dispatch=null,seededDispatch=null,networkVisits=null,yearCompleteVisits=null,foodCheckedVisits=null;
    if(document.querySelector('script[data-settlement-feedback-enabled]')){
      try{const supplement=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/settlement_feedback.json'))));
        const candidate=supplement.packets[mode];
        if(!candidate||candidate.parent_payload_sha256!==p.payload_sha256||candidate.expected_harvest_fingerprint!==p.expected_harvest_fingerprint||JSON.stringify(candidate.shape)!==JSON.stringify(p.shape))throw Error('Feedback parent/climate mismatch');
        feedback=candidate;
      }catch(e){feedback=null;}
    }
    if(document.querySelector('script[data-settlement-dispatch-enabled]')){
      try{const supplement=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/settlement_dispatch.json'))));
        const candidate=supplement.packets[mode];
        if(!candidate||candidate.parent_payload_sha256!==p.payload_sha256||candidate.expected_harvest_fingerprint!==p.expected_harvest_fingerprint||JSON.stringify(candidate.shape)!==JSON.stringify(p.shape))throw Error('Dispatch parent/climate mismatch');
        dispatch=candidate;
      }catch(e){dispatch=null;}
    }
    if(document.querySelector('script[data-settlement-dispatch-seeded-enabled]')){
      try{const supplement=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/settlement_dispatch_seeded.json'))));
        const candidate=supplement.packets[mode];
        if(!candidate||candidate.parent_payload_sha256!==p.payload_sha256||candidate.expected_harvest_fingerprint!==p.expected_harvest_fingerprint||JSON.stringify(candidate.shape)!==JSON.stringify(p.shape))throw Error('Threshold-checked dispatch parent/climate mismatch');
        seededDispatch=candidate;
      }catch(e){seededDispatch=null;}
    }
    if(document.querySelector('script[data-network-duty-visits-enabled]')){
      try{const supplement=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/network_duty_visits.json'))));
        const candidate=supplement.packets[mode];
        if(!candidate||candidate.parent_payload_sha256!==p.payload_sha256||candidate.expected_harvest_fingerprint!==p.expected_harvest_fingerprint||JSON.stringify(candidate.shape)!==JSON.stringify(p.shape))throw Error('Walking visit parent/climate mismatch');
        networkVisits=candidate;
      }catch(e){networkVisits=null;}
    }
    if(document.querySelector('script[data-network-visit-year-complete-enabled]')){
      try{const supplement=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/network_visit_year_complete.json'))));
        const candidate=supplement.packets[mode];
        if(!candidate||candidate.parent_payload_sha256!==p.payload_sha256||candidate.expected_harvest_fingerprint!==p.expected_harvest_fingerprint||JSON.stringify(candidate.shape)!==JSON.stringify(p.shape))throw Error('Provider-year visit parent/climate mismatch');
        yearCompleteVisits=candidate;
      }catch(e){yearCompleteVisits=null;}
    }
    if(document.querySelector('script[data-food-checked-visits-enabled]')){
      try{const supplement=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/food_checked_visits.json'))));
        const candidate=supplement.packets[mode];
        if(!candidate||candidate.parent_payload_sha256!==p.payload_sha256||candidate.expected_harvest_fingerprint!==p.expected_harvest_fingerprint||JSON.stringify(candidate.shape)!==JSON.stringify(p.shape))throw Error('Food-checked visit parent/climate mismatch');
        foodCheckedVisits=candidate;
      }catch(e){foodCheckedVisits=null;}
    }
    let release2=null;
    if(document.querySelector('script[data-settlement-release2-enabled]')){
      try{const supplement=JSON.parse(new TextDecoder().decode(await bytes(fresh('data/settlement_release2.json'))));
        const candidate=supplement.packets[mode];
        if(!candidate||candidate.parent_payload_sha256!==p.payload_sha256||candidate.expected_harvest_fingerprint!==p.expected_harvest_fingerprint||JSON.stringify(candidate.shape)!==JSON.stringify(p.shape))throw Error('Release-2 size parent/climate mismatch');
        release2=candidate;
      }catch(e){release2=null;}
    }
    const originals=meta.layers.filter(l=>['reach_towns','reach_defacto'].includes(l.id));
    if(originals.length!==2)throw Error('Missing original settlement/reach modes');
    const changed=originals.map(l=>{const options=l.variants?.options||[{value:'0',label:'Original placement',file:l.file,items:l.items,note:l.note}];
      return {...l,label:l.id==='reach_towns'?'Settlements':'Supply-supported reach',controls:[],variants:{label:'Settlement / supply scenario',default:(l.id==='reach_towns'&&release2?.options.reach_towns?.some(o=>o.value==='release2_central'))?'release2_central':(l.id==='reach_defacto'&&p.options[l.id].some(o=>o.value==='v21_joint365'))?'v21_joint365':(l.id==='reach_defacto'&&p.options[l.id].some(o=>o.value==='v2_joint365'))?'v2_joint365':(p.options[l.id].some(o=>o.value==='joint365')?'joint365':'legacy_0'),options:[...options.map(o=>({...o,value:'legacy_'+o.value,label:'Legacy · '+o.label,integrated_support:false})),...p.options[l.id],...(seededDispatch?.options[l.id]||[]),...(feedback?.options[l.id]||[]),...(dispatch?.options[l.id]||[])]}};});
    meta.layers=meta.layers.map(l=>changed.find(c=>c.id===l.id)||l);
    for(const l of changed)l.variants.options.push(...(networkVisits?.options[l.id]||[]),...(yearCompleteVisits?.options[l.id]||[]),...(foodCheckedVisits?.options[l.id]||[]),...(release2?.options[l.id]||[]));
    return {p,feedback,dispatch,seededDispatch,networkVisits,yearCompleteVisits,foodCheckedVisits,fresh,mode,restore:()=>{meta.layers=meta.layers.map(l=>originals.find(c=>c.id===l.id)||l);}};
  }
  async function attach(state,harvest,changed,choosePlace){
    const {fresh,mode}=state;let p=state.p;
    if(!harvest||await digest(harvest.binaryBuffer)!==p.expected_harvest_binary_sha256)throw Error('Settlement Harvest identity changed');
    let model=null,lookup=null,catchments=null,masks=null,active=false,layer='',variant='joint365',siteId=new URLSearchParams(location.hash.slice(1)).get('settled_site'),selected=null,generation=0,skipInitial=true;
    const packetJobs=new Map();
    if(!$('settled-point-grid')){const link=document.createElement('a');link.id='settled-point-grid';link.download='';link.hidden=true;link.textContent='Actor target points and visit outcomes (gzip CSV)';$('settled-field-grid').after(link);link.before(document.createTextNode(' · '));}
    const fmt=(v,d=0)=>Number(v).toLocaleString(undefined,{maximumFractionDigits:d}),pop=v=>{let n=0;for(;v;v&=v-1)n++;return n;};
    const readouts=rows=>rows.map(([v,k])=>`<div class="readout"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join('');
    function clear(message){$('settled-readouts').textContent='';$('settled-site-note').textContent=message;$('settled-global').textContent='';$('settled-months').textContent='';$('settled-cell').textContent='';$('settled-download').disabled=true;$('settled-point-grid').hidden=true;}
    async function load(){
      if(model)return;const packet=p,key=packet.payload_sha256;
      let job=packetJobs.get(key);
      if(!job){job=(async()=>{
        const [a,b]=await Promise.all([bytes(fresh('data/'+packet.payload)),bytes(fresh('data/'+packet.binary))]);
        if(await digest(a)!==packet.payload_sha256||await digest(b)!==packet.binary_sha256)throw Error('Settlement packet checksum mismatch');
        const [ar,br]=await Promise.all([unpack(a),unpack(b)]),m=JSON.parse(new TextDecoder().decode(ar));
        if(m.climate!==mode||JSON.stringify(m.shape)!==JSON.stringify(packet.shape)||br.byteLength!==packet.raw_bytes)throw Error('Invalid settlement packet layout');
        const size=packet.shape[0]*packet.shape[1],l=new Uint32Array(br,0,size),c=new Uint16Array(br,packet.offsets.catchments,size),v=new Uint16Array(br,packet.offsets.masks);
        if(c.some(i=>i>m.sites.length)||l.some(i=>i>packet.land_cells)||v.some(n=>n>4095))throw Error('Invalid settlement resource indices');
        return {model:m,lookup:l,catchments:c,masks:v};
      })().catch(e=>{packetJobs.delete(key);throw e;});packetJobs.set(key,job);}
      const bundle=await job;if(p!==packet)return;
      ({model,lookup,catchments,masks}=bundle);const m=model;
      $('settled-site').innerHTML=m.sites.map(s=>`<option value="${s.id}">${esc(s.name)} · ${esc(s.actor||'unresolved affiliation')}</option>`).join('');
      if(!m.sites.some(s=>s.id===siteId))siteId=m.sites.find(s=>s.marked)?.id||m.sites[0].id;
      $('settled-site').value=siteId;$('settled-ledgers').href='data/'+p.payload;$('settled-grid').href='data/'+p.binary;
    }
    function render(){
      if(!active||!model)return;
      const k=model.cases.findIndex(c=>c.id===variant),c=model.cases[k],j=model.sites.findIndex(s=>s.id===siteId),s=model.sites[j],sum=model.summaries[k],reference=model.summaries[0];
      if(!c.point_visits)$('settled-global').textContent=`${fmt(sum.viable_communities)} / ${fmt(model.sites.length)} candidate communities meet the declared minimum; ${fmt(sum.active_sources)} / ${fmt(reference.active_sources)} affiliated sources staffed. Modelled two-way access: ${fmt(sum.area_weighted_access_bins,2)} / 12 area-weighted bins (matched reference ${fmt(reference.area_weighted_access_bins,2)}). These are alternative scenarios, not extra census people.`;
      $('settled-readouts').innerHTML=readouts([[fmt(s.civilian_request_people),'reference civilian request'],[c.food_constrained?fmt(c.food_ceiling_people[j]):'Unconstrained',c.destination_food?'planning ceiling · bin-start cereal':'seasonal food ceiling · all residents'],[fmt(c.civilian_people[j]),'allocated civilian scenario'],[fmt(c.institutional_people[j]),'institutional residents · same food pool'],[c.institutional_active[j]?'Available':'Unavailable / unassigned','source for this reach scenario'],[c.community_viable[j]?'Meets minimum':'Below scenario minimum','50 civilian reference people']]);
      if(c.feedback_coupled)$('settled-readouts').innerHTML+=readouts([[fmt(c.resident_budget_people[j]),'shared origin allowance · civilians and staff'],[c.source_supported[j]?'Supported':'Unmet rural meals','rural source-food gate']]);
      if(c.dispatch_work)$('settled-readouts').innerHTML+=readouts([[fmt(c.dispatch_work.collection_hours[j].reduce((a,b)=>a+b,0)),'collector hours / year · same staff'],[fmt(c.dispatch_work.unused_hours[j].reduce((a,b)=>a+b,0)),'unused staff hours after all modeled duties']]);
      if(c.point_visits){const v=c.point_visits;
        $('settled-global').textContent=`${fmt(v.completed)} / ${fmt(v.requested)} requested point visits completed (${fmt(100*v.completed/v.requested,1)}%). ${fmt(v.route_unreachable)} lack a walking round trip; ${fmt(v.provider_work_unavailable)} lack an initially affordable crew; ${fmt(v.capacity_unmet)} lose out to competing tasks. Requests are supplied monthly tasks at fixed points, not observed demand, occupation or territorial control. Unaffiliated and mobile communities remain unscored.`;
        $('settled-readouts').innerHTML+=readouts([[fmt(v.completed_by_provider[j].reduce((a,b)=>a+b,0)),'completed point visits / year · selected provider'],[fmt(v.used_hours[j].reduce((a,b)=>a+b,0)),'visit crew-hours used · same reserved patrol slice']]);
      }
      if(c.year_schedule){const y=c.year_schedule;
        if(!c.destination_food){$('settled-global').textContent=`${fmt(c.point_visits.completed)} / ${fmt(c.point_visits.requested)} requested point visits pass the necessary provider-year schedule gate. ${fmt(c.point_visits.calendar_unqualified)} originally funded tasks lack a qualified calendar; ${fmt(c.point_visits.route_unreachable)} lack a walking route; ${fmt(c.point_visits.provider_work_unavailable)} lack an initially affordable crew; ${fmt(c.point_visits.capacity_unmet)} lose out to competing tasks. Every baseline twelve-bin-gated task is retained. This gate does not establish daily provisioning,complete annual food validation,observed roles or authority. Unaffiliated and mobile communities remain unscored.`;
        $('settled-global').textContent+=' The settlement selector shows one provider;the point CSV identifies the recorded task providers by bin.';}
        $('settled-readouts').innerHTML+=readouts([[y.policy[j]===1?'Joint duration first':'Collection first','one chosen calendar · all twelve bins'],[y.mandatory_complete[j]?'All twelve bins':'Incomplete / unassigned','necessary collection and home-work gate']]);
      }
      if(c.destination_food){const f=c.destination_food,v=c.point_visits;
        $('settled-global').textContent=`${fmt(v.completed)} / ${fmt(v.requested)} requested point visits pass BOTH a whole provider-year calendar and its OWN destination cereal inventory. ${fmt(v.schedule_unqualified)} funded jobs lack a packed,qualified provider-year; ${fmt(v.route_unreachable)} lack a route; ${fmt(v.provider_work_unavailable)} lack an initially affordable crew; ${fmt(v.capacity_unmet)} lose out to competing tasks. Every baseline task passing BOTH gates is retained. Points are tasks,not held blocks or territory. The place selector displays one provider;the point CSV records actual task providers by bin. Unaffiliated and mobile communities remain unscored.`;
        $('settled-readouts').innerHTML+=readouts([[f.active[j]?(f.no_shortage[j]?'Pass':'Unmet cereal'):'Unscored','OWN destination cereal year'],[f.active[j]?fmt(f.unmet[j],3)+' kcal':'Unscored','annual cereal gap · selected provider']]);
      }
      $('settled-point-grid').hidden=!c.point_visits;if(c.point_visits)$('settled-point-grid').href='data/'+p.point_csv[c.id];
      $('settled-grid').textContent=c.point_visits?'Catchments and actor visited-point masks (gzip binary)':'Catchments and actor access masks (gzip binary)';
      $('settled-cell').closest('table').querySelector('thead tr th:last-child').textContent=c.point_visits?'Completed visit bins at target':'Access bins here';
      if(c.year_schedule)$('settled-cell').closest('table').querySelector('thead tr th:last-child').textContent='Qualified visit bins at target';
      $('settled-field-grid').textContent=c.year_schedule?'Provider-year choices and point masks (NPZ)':'Field-work cell audit (NPZ)';
      $('settled-work-note').hidden=!c.labour_constrained;
      if(c.feedback_coupled){const w=c.work_summary;
        $('settled-work-note').textContent=`Coupled cell budget: ${c.hours_worker_year} listed field hours per remaining rural worker/year; 40% worker share and a 30-day reaping window. Moving people changes BOTH workers and rural meals before grain is collected. Local cereal production retains ${fmt(w.production_retained*100,2)}% of potential. The ${(100*c.transfer_fraction).toFixed(1)}% allowance caps civilians and staff together. ${fmt(c.rural_ledger.deficit_origins)} local origins still have unmet cereal meals; they export nothing and block positive allocations in their catchments. Diets, work availability and staff roles remain scenarios; this is not a census or sovereignty validation.`;
        $('settled-field-grid').href='data/'+p.fields[c.id];$('settled-field-grid').hidden=false;
        if(c.dispatch_work){const d=c.dispatch_work;
          $('settled-work-note').textContent+=c.year_schedule?' Parent collection demand fits aggregate monthly staff hours;the provider-year gate also checks whole collector trips and synchronized workers.':` Collection also fits every monthly staff budget: ${fmt(d.load_kcal)} kcal per collector trip, seven walking hours per graph day, and 600 supplied staff hours/year. Dispatch volumes were reduced before accepting food support. ${d.availability==='all_open'?'All collection bins are open.':'Collection bins 7–9 are closed.'} Remaining hours are shared across patrol and services.`;
          $('settled-work-note').textContent+=c.point_visits?` Walking visits use only that same reserved patrol slice; collection and other services retain their hours. Crew ${c.point_visits.crew};one on-site hour,seven duty hours per walking day,both directed legs at most two days,round trip plus on-site work at most four days. One requested visit per retained actor/point/bin;targets are about ${fmt(c.point_visits.actual_block_edge_km,2)} km apart. Cheapest initially affordable provider is assigned once,then whole visits compete for its hours. Dots mark visited points,not held blocks or intervening land. Monthly hours do not establish individual crew rosters,daily provisioning,observed patrols or authority.`:' These requests do not establish geographic patrol coverage; the map shows potential travel access from qualified sources.';
          $('settled-work-note').textContent+=d.threshold_seeded?' This version explicitly checks the existing staff-activation boundary.':' This earlier search can miss narrow staffed ranges; compare the threshold-checked version.';
          if(c.year_schedule)$('settled-work-note').textContent+=' One complete checked calendar is chosen for each provider across all twelve bins. Each worker has 50 duty hours per bin;home services,whole collector trips and synchronized crews share that same worker budget. A different policy is accepted only when the baseline year fails or EVERY baseline gated task is retained and at least one is added. No individual job successes are merged across calendars. Selected physical work remains charged even when the provider is unqualified. These are supplied-availability schedules;daily provisioning,within-bin grain timing,complete annual food validation and actual provider roles remain unqualified. Conditional parent residents are not reallocated when a roster fails.';
        }
      }else if(c.labour_constrained){const w=c.work_summary;
        $('settled-work-note').textContent=`Field-work scenario: ${c.hours_worker_year} listed hours per reference worker/year; ${c.harvest_days}-day reaping window at ${model.labour_specification.hours_worker_day} hours/day. Worker share ${100*model.labour_specification.worker_fraction_of_reference_rural_people}% of the earlier fixed rural cereal-food claim (${fmt(w.scenario_workers/1e6,2)} M reference workers), not census residents. Produces ${fmt(w.production_retained*100,2)}% of baseline cereal. Rural meals remain fixed; ${fmt(c.rural_ledger.unmet_kcal/1e12,3)} trillion kcal of scenario rural need is unmet, so affected cells export nothing. This is a partial cereal/work test, not evidence of actual famine or total household labour.`;
        $('settled-field-grid').href=p.field_support;$('settled-field-grid').hidden=!p.field_support;
      }else $('settled-field-grid').hidden=true;
      if(c.destination_food){
        $('settled-field-grid').textContent='Provider calendars,OWN cereal and point fields (NPZ)';
        $('settled-work-note').textContent=`Conditional residents come from the NEW finite source and field-work plan: ${c.hours_worker_year} listed farm hours per rural worker/year,40% worker share and a 30-day reaping window. Food at source remains monthly. Point jobs use ONLY the existing reserved patrol slice with crew ${c.point_visits.crew};one on-site hour and seven duty hours per walking day. Whole trips,funded home services and synchronized crews share 50 duty hours per person/bin. One WHOLE policy is chosen for each provider across ALL twelve bins,and its OWN destination cereal year must pass. Every baseline task passing BOTH gates is retained;no job successes or food are borrowed from another policy. Selected physical work remains charged even when unqualified. The planning ceiling uses continuous bin-start supply;the table uses actual packed deliveries and stocks at chosen return phases. The imposed one-bin lag and0.95 transport retention stay fixed. Uniform destination meals include staff once;crew-carried food and food location,source within-bin availability,complete diets/work and observed roles remain unqualified. Parent residents are not reallocated when a schedule or food test fails. Dots mark target-point tasks,not held blocks or intervening territory.`;
      }
      $('settled-site-note').textContent=s.name+' · '+(s.actor||'affiliation unresolved')+' · '+s.affiliation_basis+'. '+(s.marked?'Marked place retained as evidence even if local cereal cannot support the scenario. ':'Proposed administrative/market location; this is not a worldwide village or camp generator. ')+
        'The 7.5% civilian request is a scenario, not a validated town-size model. No imports, other foods or complete household labour budget are inferred. A failed grain scenario does not establish abandonment or political collapse.';
      $('settled-months').innerHTML=c.food_constrained?Array.from({length:12},(_,t)=>`<tr><th>${t+1}</th><td>${fmt(c.monthly_arrivals_kcal[j][t]/1e6,2)}</td><td>${fmt(c.monthly_need_kcal[j][t]/1e6,2)}</td><td>${fmt(c.stock_path_kcal[j][t+1]/1e6,2)}</td></tr>`).join(''):'<tr><td colspan="4">Transport-matched counterfactual: food unconstrained; no grain ledger or demographic validation claimed.</td></tr>';
      let index=-1;
      if(selected){const [x,y]=selected,row=Math.floor(y/p.cell_px),col=Math.floor(x/p.cell_px);if(row>=0&&row<p.shape[0]&&col>=0&&col<p.shape[1])index=lookup[row*p.shape[1]+col]-1;}
      if(c.point_visits&&selected){const row=Math.floor(selected[1]/p.cell_px),col=Math.floor(selected[0]/p.cell_px);if(!model.point_target_nodes.includes(row*p.shape[1]+col))index=-1;}
      $('settled-cell').innerHTML=index>=0?model.actors.map((a,i)=>{const bins=pop(masks[(k*model.actors.length+i)*p.land_cells+index]),v=sum.actors[i];return `<tr><th>${esc(a.name)}</th><td>${v.inventory_scored?fmt(v.active_sources)+' / '+fmt(v.candidate_sources):'Inventory missing'}</td><td>${v.inventory_scored?bins+' / 12':'Unscored'}</td></tr>`;}).join(''):'<tr><td colspan="3">Select land for actor-specific two-way reach. Missing inventories are unscored, not empty territory.</td></tr>';
      if(c.point_visits&&index<0)$('settled-cell').innerHTML='<tr><td colspan="3">Select an exact target point for completed visit bins. Background and intervening land are unscored;missing points do not establish absent communities or authority.</td></tr>';
      if(c.point_visits&&index>=0){const node=Math.floor(selected[1]/p.cell_px)*p.shape[1]+Math.floor(selected[0]/p.cell_px);for(const [i,row] of Array.from($('settled-cell').rows).entries())if(!model.point_requested_targets[i].includes(node))row.cells[2].textContent='Unrequested / unscored';}
      $('settled-download').disabled=false;
    }
    $('settled-site').addEventListener('change',()=>{siteId=$('settled-site').value;render();changed();const s=model.sites.find(s=>s.id===siteId);choosePlace?.((s.column+.5)*p.cell_px,(s.row+.5)*p.cell_px,s.name);});
    $('settled-download').addEventListener('click',()=>{
      if(!model||!active)return;const j=model.sites.findIndex(s=>s.id===siteId),s=model.sites[j],rows=[];
      for(const c of model.cases)for(let t=0;t<12;t++)rows.push({climate:mode,site_id:s.id,site:s.name,actor:s.actor,affiliation_basis:s.affiliation_basis,scenario:c.id,seasonal_bin:t+1,civilian_request_people:s.civilian_request_people,food_ceiling_people:c.food_constrained?c.food_ceiling_people[j]:null,civilian_people:c.civilian_people[j],institutional_people:c.institutional_people[j],institutional_active:c.institutional_active[j],field_hours_worker_year:c.labour_constrained?c.hours_worker_year:null,reaping_window_days:c.labour_constrained?c.harvest_days:null,worker_fraction:c.labour_constrained?model.labour_specification.worker_fraction_of_reference_rural_people:null,arrivals_kcal:c.food_constrained?c.monthly_arrivals_kcal[j][t]:null,need_kcal:c.food_constrained?c.monthly_need_kcal[j][t]:null,end_stock_kcal:c.food_constrained?c.stock_path_kcal[j][t+1]:null,scope:'conditional local cereal settlement/source allocation; not measured population or sovereignty'});
      if(model.cases.some(c=>c.dispatch_work))for(const row of rows){const c=model.cases.find(v=>v.id===row.scenario),d=c.dispatch_work,t=row.seasonal_bin-1;Object.assign(row,{collection_hours:d?d.collection_hours[j][t]:null,gross_staff_hours:d?d.gross_hours[j][t]:null,unused_staff_hours:d?d.unused_hours[j][t]:null,collector_load_kcal:d?d.load_kcal:null,dispatch_scale:d?d.dispatch_scale[j]:null});}
      if(model.cases.some(c=>c.point_visits))for(const row of rows){const v=model.cases.find(c=>c.id===row.scenario).point_visits,t=row.seasonal_bin-1;Object.assign(row,{visit_crew:v?.crew??null,completed_point_visits:v?v.completed_by_provider[j][t]:null,reserved_patrol_hours:v?v.reserved_hours[j][t]:null,visit_hours_used:v?v.used_hours[j][t]:null,unused_patrol_hours:v?v.unused_hours[j][t]:null,scope:'conditional walking point visits;not observed patrols,whole-block territory or authority'});}
      if(model.cases.some(c=>c.year_schedule))for(const row of rows){const y=model.cases.find(c=>c.id===row.scenario).year_schedule,t=row.seasonal_bin-1;Object.assign(row,{provider_year_policy:y?(y.policy[j]===1?'joint_duration_first':'collection_first'):null,all_twelve_mandatory_bins_complete:y?y.mandatory_complete[j]:null,selected_worker_hours:y?y.work_hours[j][t]:null,selected_max_worker_duty_hours:y?y.max_worker_hours[j][t]:null,selected_max_calendar_end:y?y.max_calendar_end[j][t]:null,scope:'necessary provider-year delivery schedule only;not daily provisioning,full annual food validation,observed roles or authority'});}
      if(model.cases.some(c=>c.destination_food))for(const row of rows){const c=model.cases.find(c=>c.id===row.scenario),f=c.destination_food,t=row.seasonal_bin-1;
        Object.assign(row,{provider_year_scored:f?f.active[j]:null,destination_cereal_no_shortage:f?f.no_shortage[j]:null,calendar_and_cereal_qualified:f?f.qualified[j]:null,
          selected_year_initial_stock_kcal:f?f.initial_stock[j]:null,selected_year_final_stock_kcal:f?f.final_stock[j]:null,selected_year_peak_stock_kcal:f?f.peak_stock[j]:null,
          selected_year_needed_kcal:f?f.needed[j]:null,selected_year_consumed_kcal:f?f.consumed[j]:null,selected_year_unmet_kcal:f?f.unmet[j]:null,
          selected_year_spoiled_kcal:f?f.spoiled[j]:null,selected_year_overflow_kcal:f?f.overflow[j]:null,selected_year_shortfall_days:f?f.shortfall_days[j]:null,
          selected_year_periodic_residual:f?f.periodic_residual[j]:null,selected_year_ledger_residual:f?f.ledger_residual[j]:null,
          selected_month_unmet_kcal:f?f.monthly_unmet_kcal[j][t]:null,selected_month_consumed_kcal:f?f.monthly_consumed_kcal[j][t]:null,
          selected_month_spoiled_kcal:f?f.monthly_spoiled_kcal[j][t]:null,selected_month_overflow_kcal:f?f.monthly_overflow_kcal[j][t]:null,
          physically_scheduled_point_visits:f?c.point_visits.physically_scheduled_by_provider[j][t]:null,
          food_ceiling_convention:f?'parent continuous bin-start planning ceiling':null,dispatch_scale_convention:f?'parent plan before unpacked trips':null});
        if(f)row.scope='ONE whole provider-year with OWN destination cereal;source monthly availability and crew food location remain assumptions;not complete provisioning,observed roles or territory';else row.scope='Original reference scenario;no food-checked provider-year is claimed';
      }
      const keys=Object.keys(rows[0]),q=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
      window.atlasSave('settlement_food_source.csv',new Blob([[keys,...rows.map(r=>keys.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\r\n')+'\r\n'],{type:'text/csv;charset=utf-8'}));
    });
    return {state:()=>({settled_site:siteId||''}),show:(id,v)=>{
      layer=id;variant=v?.value||'joint365';active=['reach_towns','reach_defacto'].includes(id)&&!!v?.integrated_support;const gen=++generation;$('settled-section').hidden=!active;
      const desired=v?.food_checked_visit_support?state.foodCheckedVisits:(v?.year_complete_visit_support?state.yearCompleteVisits:(v?.network_visit_support?state.networkVisits:(v?.seeded_dispatch_support?state.seededDispatch:(v?.dispatch_support?state.dispatch:(v?.feedback_support?state.feedback:state.p)))));if(desired&&p!==desired){p=desired;model=null;lookup=null;catchments=null;masks=null;}
      if(active){$('harvest-section').hidden=true;clear('Loading the joint settlement and food ledger…');load().then(()=>{if(gen===generation)render();}).catch(e=>{if(gen===generation){clear('Detailed ledger unavailable: '+e.message+'. The precomputed map remains a conditional scenario.');console.error(e);}});}
    },select:(x,y)=>{selected=[x,y];if(skipInitial){skipInitial=false;return;}if(!active||!model)return;const row=Math.floor(y/p.cell_px),col=Math.floor(x/p.cell_px),i=row>=0&&row<p.shape[0]&&col>=0&&col<p.shape[1]?catchments[row*p.shape[1]+col]:0;if(i){siteId=model.sites[i-1].id;$('settled-site').value=siteId;}render();changed();}};
  }
  return {extend,attach};
})();

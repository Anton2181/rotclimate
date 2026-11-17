/* Actual r5 integration and comparison interactions, desktop and mobile. */
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core');
const root=path.resolve(__dirname,'..'),out=path.join(root,'output/settlement_provisional_release5_20261117');
const base=process.argv[2]||'http://127.0.0.1:8775/';
const assert=(v,m)=>{if(!v)throw Error(m);};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'atlases/earth_fit/data/settlement_provisional.json')));
 const data=JSON.parse(fs.readFileSync(path.join(out,'viewer_data.json')));
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const checks=[];
 for(const [width,height,tag] of [[1440,1100,'desktop'],[390,844,'mobile']]){
  const page=await browser.newPage({viewport:{width,height}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'atlases/earth_fit/provisional/',{waitUntil:'networkidle'});
  assert((await page.title()).includes('provisional settlement atlas r5'),'Comparison title');
  for(const mode of ['raw','corrected']){
   await page.selectOption('#mode',mode);
   assert(await page.locator('#new-map circle').count()===data.modes[mode].towns.length,'All candidate towns');
   assert(await page.locator('#old-map circle').count()===data.modes[mode].towns.length,'All baseline towns');
   const town=data.modes[mode].towns.find(t=>t.symbol==='imperial capital');
   await page.fill('#search',town.name);await page.press('#search','Enter');
   assert(await page.locator('#town-name').innerText()===town.name,'Named town search');
   for(const reading of ['central','low']){
    await page.selectOption('#reading',reading);await page.selectOption('#display','grain');
    const displayed=Number((await page.locator('#new-grain').innerText()).replaceAll(',','').replace('%',''));
    assert(displayed===Number((100*town['new_grain_'+reading]).toFixed(2)),'Own cohort annual grain detail');
    assert(await page.locator('#grain-legend').isVisible(),'Grain legend');
    const resp=await page.request.get(new URL(await page.locator('#candidate-download').getAttribute('href'),page.url()).href);
    assert(resp.ok() && (await resp.text()).split('\n').length>1000,'Matching town CSV download');
    checks.push({view:'comparison',mode,reading,viewport:tag});
   }
   await page.fill('#search','');await page.selectOption('#display','change');
   assert(await page.locator('#change-legend').isVisible(),'Change legend');
   await page.locator('#old-map').focus();await page.keyboard.press('+');
   assert(await page.locator('#old-map').getAttribute('viewBox')===await page.locator('#new-map').getAttribute('viewBox'),'Synchronized zoom');
   await page.click('#reset');assert(await page.locator('#new-map').getAttribute('viewBox')==='0 0 1000 463','Reset map');
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Responsive comparison');
  }
  await page.screenshot({path:path.join(out,'comparison_'+tag+'.png'),fullPage:true});
  for(const mode of ['raw','corrected']){
   await page.goto('about:blank'); // A hash-only navigation does not reload the legacy climate packet.
   await page.goto(base+'atlases/earth_fit/#layer=reach_towns&climate='+mode,{waitUntil:'domcontentloaded'});
   await page.waitForFunction(()=>document.querySelector('#variant')?.value==='provisional_central',null,{timeout:120000});
   assert(await page.locator('#settled-section').isHidden(),'Older ledger hidden for provisional cohort');
   assert(await page.locator('#provisional-release').isVisible(),'Cohort boundary notice');
   const values=await page.locator('#variant option').evaluateAll(nodes=>nodes.map(n=>n.value));
   assert(values.includes('release3_central'),'Previous release retained');
   for(const option of manifest.packets[mode].options.reach_towns){
    assert(values.includes(option.value),'Provisional option visible without diagnostics');
    await page.selectOption('#variant',option.value);
    await page.waitForFunction(file=>{const i=document.querySelector('#base');return i.complete&&i.naturalWidth>0&&new URL(i.src).pathname.endsWith('/data/'+file);},option.file,{timeout:120000});
    const resp=await page.request.get(base+'atlases/earth_fit/data/'+option.file);
    assert(resp.ok()&&sha(await resp.body())===option.file_sha256,'Exact reviewed map asset');
    const csv=await page.request.get(new URL('data/'+option.download,base+'atlases/earth_fit/').href);
    assert(csv.ok(),'Scenario download resolves');
    assert(await page.locator('#settled-section').isHidden(),'No old population ledger on new maps');
    checks.push({view:'full_atlas',mode,option:option.value,viewport:tag});
   }
   await page.screenshot({path:path.join(out,'atlas_'+mode+'_'+tag+'.png')});
  }
  assert(errors.length===0,JSON.stringify(errors));await page.close();
 }
 await browser.close();
 fs.writeFileSync(path.join(out,'browser_review.json'),JSON.stringify({status:'passed',checks,reviewer_sha256:sha(fs.readFileSync(__filename)),javascript_errors:0},null,2)+'\n');
 console.log('Passed',checks.length,'desktop/mobile comparison and atlas scenarios');
})().catch(e=>{console.error(e);process.exit(1);});

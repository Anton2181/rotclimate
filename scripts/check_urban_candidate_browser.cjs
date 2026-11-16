/* Test the local offline candidate viewer;never publishes the main atlas. */
const fs=require('fs');
const crypto=require('crypto');
const path=require('path');
const {chromium}=require('/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core');
const out=path.resolve('output/urban_hierarchy_candidate_20261116');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const assert=(condition,message)=>{if(!condition)throw Error(message);};
(async()=>{
 const url=process.argv[2];assert(url,'Pass local viewer URL');const data=JSON.parse(fs.readFileSync(path.join(out,'viewer_data.json')));
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url,{waitUntil:'networkidle'});assert(await page.title()==='Settlement hierarchy candidate','Page title');
 assert(await page.locator('#old-map circle').count()===1053,'Old corrected count');assert(await page.locator('#new-map circle').count()===1053,'New corrected count');
 const named=data.modes.corrected.towns.find(t=>t.symbol==='imperial capital');assert(named,'Capital exists');
 await page.locator('#search').fill(named.name);await page.locator('#search').press('Enter');assert(await page.locator('#town-name').innerText()===named.name,'Exact city search selected');
 assert(Number((await page.locator('#new-area').innerText()).replaceAll(',',''))===Number(named.new_area.toFixed(2)),'Detail area');
 await page.locator('#reading').selectOption('low');assert(Number((await page.locator('#new-res').innerText()).replaceAll(',',''))===Math.round(named.new_res_low),'Low reading detail');
 await page.locator('#reading').selectOption('central');await page.locator('#display').selectOption('change');assert(await page.locator('#change-legend').isVisible(),'Change legend');
 assert(await page.locator('#new-map circle.selected').count()===1 && await page.locator('#old-map circle.selected').count()===1,'Synchronized selection');
 await page.locator('#search').fill('');await page.locator('#old-map').focus();await page.keyboard.press('+');
 let oldbox=await page.locator('#old-map').getAttribute('viewBox'),newbox=await page.locator('#new-map').getAttribute('viewBox');assert(oldbox===newbox && Number(oldbox.split(' ')[2])<1000,'Keyboard synchronized zoom');
 const box=await page.locator('#old-map').boundingBox();await page.mouse.move(box.x+5,box.y+5);await page.mouse.down();await page.mouse.move(box.x+35,box.y+20);await page.mouse.up();
 assert(await page.locator('#old-map').getAttribute('viewBox')===await page.locator('#new-map').getAttribute('viewBox'),'Synchronized pan');
 await page.locator('#reset').click();assert(await page.locator('#new-map').getAttribute('viewBox')==='0 0 1000 463','Reset');
 await page.locator('#mode').selectOption('raw');assert(await page.locator('#new-map circle').count()===1034,'Raw count');assert((await page.locator('#candidate-download').getAttribute('href')).includes('placed_raw_towns.csv'),'Raw CSV link');
 for(const mode of ['raw','corrected']){
  await page.locator('#mode').selectOption(mode);
  const positions=await page.locator('#new-map circle').evaluateAll(nodes=>nodes.map(n=>({id:n.getAttribute('data-id'),x:Number(n.getAttribute('cx')),y:Number(n.getAttribute('cy'))})));
  positions.forEach((p,i)=>{const t=data.modes[mode].towns[i];assert(p.id===t.id && p.x===t.x+.5 && p.y===t.y+.5,'All map coordinates match cell centres');});
 }
 const downloadPromise=page.waitForEvent('download');await page.locator('#candidate-download').click();const download=await downloadPromise;assert(download.suggestedFilename()==='placed_corrected_towns.csv','Download filename');
 await page.screenshot({path:path.join(out,'browser_desktop.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.reload({waitUntil:'networkidle'});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile horizontal overflow');
 const a=await page.locator('#old-map').boundingBox(),b=await page.locator('#new-map').boundingBox();assert(b.y>a.y+a.height,'Mobile stacked maps');
 await page.locator('#search').fill(named.name);await page.locator('#search').press('Enter');assert(await page.locator('#town-name').innerText()===named.name,'Mobile search');
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile detail overflow');await page.screenshot({path:path.join(out,'browser_mobile.png'),fullPage:true});
 assert(errors.length===0,'Browser exceptions: '+errors.join(';'));
 const result={status:'passed',script_sha256:hash(__filename),presentation_sha256:hash(path.join(out,'presentation.json')),viewer_sha256:hash(path.join(out,'index.html')),desktop_viewport:[1440,1100],mobile_viewport:[390,844],coordinate_checks:2087,controls:['two modes','two readings','city search','change colours','synchronized selection','keyboard zoom','pan','reset','CSV download','mobile stacking and overflow'],browser_errors:errors,main_atlas_published:false};
 fs.writeFileSync(path.join(out,'browser_review.json'),JSON.stringify(result,null,2)+'\n');await browser.close();console.log('Candidate viewer passes desktop/mobile,2087coordinates,controls and CSV download');
})().catch(e=>{console.error(e);process.exit(1);});

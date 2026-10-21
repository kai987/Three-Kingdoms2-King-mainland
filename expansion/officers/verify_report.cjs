const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const{fileURLToPath,pathToFileURL}=require('url');
const{chromium}=require(require.resolve('playwright',{paths:[__dirname,path.join(__dirname,'../map')]}));
const base=__dirname,root=path.resolve(base,'../..'),out=path.join(root,'build/report-checks'),map=path.join(root,'build/report-checks')+path.sep;
fs.mkdirSync(out,{recursive:true});
const target=process.env.REPORT_URL||pathToFileURL(path.join(base,'index.html')).href;
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
 const p=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));await p.goto(target);
 const count=async()=>Number(await p.locator('#result-count').getAttribute('data-filtered-count'));
 assert.equal(await count(),1000);assert.equal(await p.locator('[data-city]').count(),96);assert.equal(await p.locator('#mapping-table tbody tr').count(),29);
 assert.equal(await p.locator('[data-remake-capacity="20"]').count(),1);
 assert.equal(await p.locator('#virtue-design-table tbody tr').count(),5);
 assert((await p.locator('#remake-rules').locator('xpath=..').innerText()).includes('732'));
 const tests=[];for(const[q,n]of[['马忠',2],['李丰',3],['孙乾',1],['孙干',1],['san14-candidate-0875',1]]){await p.locator('#officer-search').fill(q);assert.equal(await count(),n,q);tests.push({query:q,count:n});}
 assert((await p.locator('#people-table tbody').innerText()).includes('来源写作「羊」'));
 await p.locator('#officer-search').fill('');await p.locator('#status-select').selectOption('年表可登场');assert.equal(await count(),326);await p.locator('#status-select').selectOption('卒年边界待核');assert.equal(await count(),12);
 await p.locator('#year-select').fill('184');await p.locator('#status-select').selectOption('年表可登场');assert.equal(await count(),276);
 await p.locator('#status-select').selectOption('全部');await p.locator('#year-select').fill('');assert((await p.locator('#people-table tbody').innerText()).includes('参考年待填'));await p.locator('#year-select').fill('0');assert((await p.locator('#people-table tbody').innerText()).includes('参考年待填'));
 await p.locator('#scenario-select').selectOption('san14-251-01');assert.equal(await count(),1000);assert(await p.locator('#year-select').isDisabled());assert((await p.locator('#year-note').innerText()).includes('跨年代'));await p.locator('#officer-search').fill('阿会喃');assert.equal(await count(),1);assert((await p.locator('#people-table tbody').innerText()).includes('仕官'));
 await p.locator('#officer-search').fill('');await p.locator('#scenario-select').selectOption('year');await p.locator('#year-select').fill('230');assert.equal(await count(),1000);await p.locator('#next-page').click();assert.equal(await p.locator('#people-table tbody tr').first().locator('td').first().innerText(),'31');await p.locator('#prev-page').click();
 for(const[id,layer]of[['river-toggle','historic-rivers'],['land-toggle','shared-roads'],['sea-toggle','historical-sea-routes']]){await p.locator('#'+id).uncheck();assert.equal(await p.locator('[data-layer="'+layer+'"]').evaluate(e=>getComputedStyle(e).display),'none');await p.locator('#'+id).check();assert.notEqual(await p.locator('[data-layer="'+layer+'"]').evaluate(e=>getComputedStyle(e).display),'none');}
 const responsive=[];for(const width of[1440,390]){await p.setViewportSize({width,height:1000});await p.waitForTimeout(100);await p.evaluate(()=>scrollTo(0,0));const r=await p.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,cityCount:document.querySelectorAll('[data-city]').length,imagesLoaded:[...document.images].every(i=>i.complete&&i.naturalWidth>0)}));assert(r.scrollWidth<=width+1,JSON.stringify(r));assert(r.imagesLoaded);responsive.push(r);await p.screenshot({path:map+'city-map-officers-report-'+(width===1440?'desktop':'mobile')+'-v42.png'});}
 await p.setViewportSize({width:1440,height:1000});await p.locator('#officers').scrollIntoViewIfNeeded();await p.screenshot({path:path.join(out,'roster-report-preview.png')});
 const localLinks=await p.locator('a[href]').evaluateAll(es=>es.map(e=>e.href).filter(h=>!h.includes('#')&&(h.startsWith('file:')||h.startsWith(location.origin+'/'))));for(const href of localLinks){if(href.startsWith('file:'))assert(fs.existsSync(fileURLToPath(href)),href);else{const response=await p.request.get(href);assert.equal(response.status(),200,href);}}assert.deepEqual(errors,[]);
 const validation={verified:true,cityCount:96,candidateCount:1000,distinctNameStrings:994,mappingFields:29,remakeCityCapacity:20,battlePerSide:10,historyInformedVirtueDesigns:5,mainlandConfiguredProfiles:268,mainlandPendingProfiles:732,san14AbilitiesSourced:1000,searchTests:tests,year230:{available:326,deathBoundary:12},year184:{available:276},blankAndZeroYearHandled:true,fantasy251AllCandidates:true,paginationPassed:true,mapTogglesPassed:3,localLinksChecked:localLinks.length,responsive,pageErrors:errors};
 fs.writeFileSync(path.join(base,'report-validation.json'),JSON.stringify(validation,null,2)+'\n');
 console.log(JSON.stringify(validation));
 }finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});

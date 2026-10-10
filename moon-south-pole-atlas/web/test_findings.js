// Headless check of the PR #1 review findings.
// usage: node --experimental-websocket web/test_findings.js   (needs google-chrome on PATH)
const {spawn}=require('child_process'), path=require('path'), http=require('http'), assert=require('assert');
const url='file://'+path.resolve(process.env.PAGE||path.join(__dirname,'index.html'));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const getJSON=u=>new Promise((res,rej)=>http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res(JSON.parse(d)))}).on('error',rej));
(async()=>{
  const port=9800+Math.floor(Math.random()*500);
  const ch=spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--remote-debugging-port='+port,'--window-size=1440,900','about:blank'],{stdio:'ignore'});
  let tabs; for(let i=0;i<50;i++){try{tabs=await getJSON(`http://127.0.0.1:${port}/json`);if(tabs.length)break;}catch(e){}await sleep(200);}
  const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl); await new Promise(r=>ws.onopen=r);
  let id=0; const pend={}; ws.onmessage=m=>{const d=JSON.parse(m.data);if(d.id&&pend[d.id]){pend[d.id](d.result||d);delete pend[d.id];}};
  const send=(method,params={})=>new Promise(r=>{const i=++id;pend[i]=r;ws.send(JSON.stringify({id:i,method,params}));});
  const ev=async e=>{const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});return r.result&&r.result.value;};
  await send('Page.navigate',{url}); await sleep(1500);
  const fails=[]; const ok=(n,f)=>{try{f();console.log('ok  ',n);}catch(e){console.log('FAIL',n,e.message);fails.push(n);}};
  const text=sel=>ev(`document.querySelector(${JSON.stringify(sel)}).textContent`);
  // 1 home chip counts derive from the zoom data
  const chip=await text('#chip-zoom');
  const counts=await ev(`(()=>{const c={};Object.values(ZOOM_DATA.dem).forEach(d=>c[d.source_pixel_m]=(c[d.source_pixel_m]||0)+1);return c})()`);
  ok('home chip: 5 m for seven, 20 m for two',()=>{assert.strictEqual(chip,'5 m for seven, 20 m for two');assert.deepStrictEqual(counts,{5:7,20:2});});
  // 2 caption follows eye height (Nobile Rim 2 has a strip reach; NR101 too)
  for(const [mk,site] of [['NR2','NR201'],['NR1','NR101']]){
    await ev(`document.querySelector('.mk[data-id="${mk}"]').click()`); await sleep(900);
    const t1=await text('#tl-none');
    await ev(`document.querySelector('#hseg button[data-h="5"]').click()`); await sleep(300);
    const t5=await text('#tl-none');
    await ev(`document.querySelector('#hseg button[data-h="1"]').click()`); await sleep(300);
    const t1b=await text('#tl-none');
    ok(site+' caption follows eye height',()=>{assert.ok(/eye 1 m above/.test(t1),t1);assert.ok(/eye 5 m above/.test(t5)&&!/eye 1 m above/.test(t5),t5);assert.ok(/eye 1 m above/.test(t1b));});
    // 3 caveat on every card incl. NR101
    ok(site+' shows horizon caveat',()=>{assert.ok(/outside the elevation raster/.test(t1)&&/not in the mask/.test(t1)&&/18\.6-year average/.test(t1)&&/radio link budget/.test(t1));});
  }
  // 4 compare table shows true RMS, not clamped half-bar
  await ev(`openLayer('compare')`); await sleep(300);
  const row=await ev(`[...document.querySelectorAll('#tbody tr')].find(t=>t.dataset.id==='NR2').children[1].textContent`);
  ok('NR201 table shows true RMS',()=>{assert.ok(/1\.4°±1\.6/.test(row),row);});
  // 5 nulls: reload with NR201 temperature resolution and shadow pixel label nulled before the page script runs
  await send('Page.enable'); const reg=await send('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{let v;Object.defineProperty(window,'REGIONS_DATA',{configurable:true,get(){return v},set(x){const r=x.regions.find(a=>(a.query||a).point_id==='NR201');const q=r.query||r;q.temperature_resolution_m=null;q.permanent_shadow_pixel_label=null;v=x;}});})()`});
  await send('Page.navigate',{url}); await sleep(1500);
  await ev(`document.querySelector('.mk[data-id="NR2"]').click()`); await sleep(900);
  const nul=await text('#extras'); const dial=await text('.dial[data-k="cold"]');
  ok('null temperature resolution / shadow pixel label handled',()=>{assert.ok(!/null|\b0 m pixel|NaN/.test(nul+dial),nul+dial);assert.ok(/pixel size n\/a/.test(nul),nul);});
  ws.close(); ch.kill();
  if(fails.length){console.log('FAILED',fails.join(', '));process.exit(1);} console.log('findings ok');
})();

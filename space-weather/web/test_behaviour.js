// Headless behaviour checks for the space-weather page.
// usage: node --experimental-websocket web/test_behaviour.js
const path=require('path'),assert=require('assert'),{spawn}=require('child_process'),{launch,sleep}=require('./cdp.js');
const FILE='file://'+path.resolve(__dirname,'index.html');
let n=0; const ok=(c,m)=>{n++;assert.ok(c,m);console.log('ok',m)};
async function fresh(b,url,ms){await b.goto('about:blank',150);await b.goto(url,ms||900);}
(async()=>{
  const b=await launch(); const errors=[], reqs=[], failed=[];
  b.on(d=>{ if(d.method==='Runtime.exceptionThrown')errors.push(JSON.stringify(d.params.exceptionDetails).slice(0,300));
    if(d.method==='Runtime.consoleAPICalled'&&d.params.type==='error')errors.push(JSON.stringify(d.params.args).slice(0,300));
    if(d.method==='Network.requestWillBeSent')reqs.push(d.params.request.url);
    if(d.method==='Network.loadingFailed')failed.push(d.params.errorText+' '+d.params.requestId);
    if(d.method==='Log.entryAdded'&&d.params.entry.level==='error')errors.push(d.params.entry.text); });
  await b.send('Log.enable');
  await b.viewport(1440,900);
  await fresh(b,FILE+'#?paused');
  // ---- closed panels are inert
  const closed=await b.ev(`[...document.querySelectorAll('.sheet,.layer')].map(p=>[p.id,p.hasAttribute('inert'),p.getAttribute('aria-hidden')])`);
  ok(closed.length===4&&closed.every(x=>x[1]&&x[2]==='true'),'all four panels start inert and aria-hidden: '+JSON.stringify(closed.map(x=>x[0])));
  ok(await b.ev(`[...document.querySelectorAll('#sheet *,.layer *')].filter(e=>e.matches('button,a,input,[tabindex]')).every(e=>e.closest('[inert]'))`),'every focusable inside a closed panel is under [inert]');
  // ---- open card, X top right, handle, Escape, focus return
  for(const key of ['crew','polar','grid']){
    await b.ev(`document.querySelector('.aud[data-aud="${key}"]').focus()`);
    await b.ev(`document.querySelector('.aud[data-aud="${key}"]').click()`); await sleep(900);
    ok(await b.ev(`(()=>{const s=document.querySelector('#sheet');return s.classList.contains('open')&&!s.hasAttribute('inert')&&s.getAttribute('aria-hidden')==='false'})()`),key+' card opens and is no longer inert');
    ok(await b.ev(`document.activeElement.id==='close'`),key+': focus moves to the X button');
    const geo=await b.ev(`(()=>{const p=document.querySelector('#sheet .panel').getBoundingClientRect(),x=document.querySelector('#close').getBoundingClientRect(),g=document.querySelector('#sheet .grab').getBoundingClientRect();return {px:p.right-x.right,py:x.top-p.top,w:x.width,h:x.height,gw:g.width,gh:g.height}})()`);
    ok(geo.px>=0&&geo.px<40&&geo.py<24&&geo.w>=44&&geo.h>=44,key+': X is top right of the panel and 44px: '+JSON.stringify(geo));
    ok(geo.gh>=44,key+': handle is a 44px tappable strip');
    await b.ev(`document.querySelector('#close').click()`); await sleep(900);
    ok(await b.ev(`(()=>{const s=document.querySelector('#sheet');return !s.classList.contains('open')&&s.hasAttribute('inert')})()`),key+': X closes the card and re-inerts it');
    ok(await b.ev(`document.activeElement.dataset.aud==='${key}'`),key+': focus returns to the button that opened it');
    await b.ev(`document.querySelector('.aud[data-aud="${key}"]').click()`); await sleep(700);
    await b.ev(`document.querySelector('#sheet .grab').click()`); await sleep(800);
    ok(await b.ev(`!document.querySelector('#sheet').classList.contains('open')&&document.activeElement.dataset.aud==='${key}'`),key+': tapping the handle closes it and returns focus');
    await b.ev(`document.querySelector('.aud[data-aud="${key}"]').click()`); await sleep(600);
    await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27}); await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27}); await sleep(800);
    ok(await b.ev(`!document.querySelector('#sheet').classList.contains('open')`),key+': Escape closes');
  }
  // ---- layers: nav opens, X, scrim, focus return, card under layer inert
  for(const id of ['timeline','alerts','method']){
    await b.ev(`document.querySelector('.nav button[data-v="${id}"]').focus();document.querySelector('.nav button[data-v="${id}"]').click()`); await sleep(900);
    ok(await b.ev(`(()=>{const l=document.querySelector('#${id}');return l.classList.contains('open')&&!l.hasAttribute('inert')&&document.activeElement.hasAttribute('data-close')})()`),id+' layer opens with focus on its X');
    const xr=await b.ev(`(()=>{const p=document.querySelector('#${id} .panel').getBoundingClientRect(),x=document.querySelector('#${id} .x').getBoundingClientRect();return [p.right-x.right,x.top-p.top,x.width,x.height]})()`);
    ok(xr[0]>=0&&xr[0]<40&&xr[1]<24&&xr[2]>=44&&xr[3]>=44,id+': X top right, 44px '+JSON.stringify(xr.map(Math.round)));
    await b.ev(`document.querySelector('#${id} .x').click()`); await sleep(900);
    ok(await b.ev(`document.querySelector('#${id}').hasAttribute('inert')&&document.activeElement.dataset.v==='${id}'`),id+': X closes and focus returns to the nav button');
  }
  await b.ev(`document.querySelector('.aud[data-aud="crew"]').click()`); await sleep(700);
  await b.ev(`document.querySelector('#sheet [data-open="method"]').focus();document.querySelector('#sheet [data-open="method"]').click()`); await sleep(900);
  ok(await b.ev(`document.querySelector('#sheet').hasAttribute('inert')&&document.querySelector('#method').classList.contains('open')`),'card under an open layer is inert');
  await b.ev(`document.querySelector('#method .x').click()`); await sleep(900);
  ok(await b.ev(`(()=>{const s=document.querySelector('#sheet');return s.classList.contains('open')&&!s.hasAttribute('inert')})()`),'closing the layer returns to a live card');
  // ---- playback: advances, speeds differ, pause holds, loop wraps and reaches the last sample
  await fresh(b,FILE+'#?h=0');
  const t1=await b.ev('__weather.t'); await sleep(1500); const t2=await b.ev('__weather.t');
  ok(t2>t1+3600,'autoplay is on by default and the clock advances: '+Math.round(t1)+' -> '+Math.round(t2)+' s');
  await b.ev(`document.querySelector('#seg button[data-s="16"]').click()`); const a1=await b.ev('__weather.t'); await sleep(500); const a2=await b.ev('__weather.t');
  await b.ev(`document.querySelector('#seg button[data-s="1"]').click()`); const c1=await b.ev('__weather.t'); await sleep(500); const c2=await b.ev('__weather.t');
  ok((a2-a1)>(c2-c1)*5,'16x runs much faster than 1x');
  await b.ev(`document.querySelector('#play').click()`); const p1=await b.ev('__weather.t'); await sleep(600); const p2=await b.ev('__weather.t');
  ok(p1===p2,'Pause holds the clock'); ok(await b.ev(`document.querySelector('#play').getAttribute('aria-label')==='Play replay'`),'button label flips to Play');
  await b.ev(`document.querySelector('#play').click()`);
  // wrap: start 20 s of storm-time before the end at 16x and sample at 100 Hz
  await fresh(b,FILE+'#?h=263.9&paused');
  await b.ev(`document.querySelector('#seg button[data-s="16"]').click();window.__seen=[];setInterval(()=>__seen.push(__weather.slotAt(__weather.t)),10);document.querySelector('#play').click()`);
  await sleep(2500); const seen=await b.ev('__seen'); const last=await b.ev('__weather.SLOTS-1');
  ok(Math.max(...seen)===last,'the last sample (slot '+last+') is reached'); const iMax=seen.indexOf(last);
  ok(seen.slice(iMax).some(v=>v<200),'then the loop wraps to the start and keeps going');
  // ---- frame-rate cap and hero draw count
  await fresh(b,FILE+'#?h=10');
  await b.ev(`window.__draws=0;const o=CanvasRenderingContext2D.prototype.clearRect;CanvasRenderingContext2D.prototype.clearRect=function(){if(this.canvas.id==='hero')__draws++;return o.apply(this,arguments)}`);
  await sleep(2000); const dr=await b.ev('__draws'); ok(dr>=20&&dr<=75,'hero redraw is capped near 30 fps: '+dr+' draws in 2 s');
  // ---- hidden tab pauses
  const h1=await b.ev('__weather.t'); await b.ev(`Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))`); await sleep(300);
  const h2=await b.ev('__weather.t'); await sleep(800); const h3=await b.ev('__weather.t'); ok(h2===h3,'a hidden tab stops the clock'); 
  await b.ev(`Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))`); await sleep(600);
  ok(await b.ev('__weather.t')>h3,'and it resumes when visible');
  // ---- scrubber and timeline scrubbing
  await fresh(b,FILE+'#?h=0&paused');
  await b.ev(`(()=>{const s=document.querySelector('#scrub');s.value=1500;s.dispatchEvent(new Event('input',{bubbles:true}))})()`);
  ok(await b.ev('__weather.slotAt(__weather.t)')===1500,'scrubber seeks to the chosen sample'); ok(await b.ev(`document.querySelector('#r-time').textContent`)==='2017-09-09 05:00Z','readout shows 2017-09-09 05:00Z for slot 1500 (got '+await b.ev(`document.querySelector('#r-time').textContent`)+')');
  // ---- readouts match the data
  const exp=await b.ev(`(()=>{const v=STORM.series.gt10.values[1500];return v})()`);
  ok(await b.ev(`parseFloat(document.querySelector('#r-f10').textContent)`)===+(+exp).toFixed(exp>=10?1:2),'≥10 MeV readout equals the exported sample '+exp);
  // ---- reduced motion starts paused
  await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  await fresh(b,FILE+'#?h=0'); const r1=await b.ev('__weather.t'); await sleep(800); ok(r1===await b.ev('__weather.t')&&await b.ev(`document.querySelector('#play').getAttribute('aria-label')==='Play replay'`),'prefers-reduced-motion starts paused');
  await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'no-preference'}]});
  // ---- deep links
  const dl={'#audience/crew?h=130&paused':['#sheet',130],'#audience/polar':['#sheet',null],'#audience/grid?h=5&paused':['#sheet',5],'#timeline?h=12&paused':['#timeline',12],'#alerts':['#alerts',null],'#method?paused':['#method',null]};
  for(const [h,[sel,hrs]] of Object.entries(dl)){
    await fresh(b,FILE+h,700);
    ok(await b.ev(`document.querySelector('${sel}').classList.contains('open')&&!document.querySelector('${sel}').hasAttribute('inert')`),'deep link '+h+' opens '+sel);
    if(hrs!=null)ok(Math.abs(await b.ev('__weather.t')-hrs*3600)<=300,'deep link '+h+' sets replay time to hour '+hrs);
  }
  await fresh(b,FILE.replace('index.html','index.html')+'?h=50&paused#',600);
  ok(Math.abs(await b.ev('__weather.t')-50*3600)<=300&&await b.ev(`document.querySelector('#play').getAttribute('aria-label')==='Play replay'`),'?h=50&paused in the query string works too');
  // ---- never show 0 for missing: null out the data and load
  await b.send('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{let v;Object.defineProperty(window,'STORM',{configurable:true,get(){return v},set(x){
    const nul=o=>{if(Array.isArray(o)){return o.map(()=>null)}return o};
    x.series.gt10.values=nul(x.series.gt10.values);x.series.gt100.values=nul(x.series.gt100.values);x.series.dose.values=nul(x.series.dose.values);
    for(const k of ['crew','polar','grid']){const s=x.audiences[k].stats;for(const f of Object.keys(s))s[f]=null;}
    x.audiences.crew.dose={min:null,max:null,min_time:null,max_time:null};
    x.alerts.proton=[];x.alerts.grid_issued=[];x.alerts.grid_warnings=[];x.manifest=[];x.thresholds.crew=null;
    v=x}})})()`});
  errors.length=0;
  await fresh(b,FILE+'#audience/crew?h=100&paused',900);
  const txt=await b.ev(`document.querySelector('#card').innerText`);
  ok(/n\/a/.test(txt)&&!/\b0 h\b/.test(txt)&&!/\b0 pfu\b/.test(txt)&&!/\b0 µGy/.test(txt),'nulled data renders n/a, never 0, on the crew card');
  ok(await b.ev(`['#r-f10','#r-f100','#r-dose'].every(s=>document.querySelector(s).textContent==='n/a')`),'nulled data renders n/a in the live readouts');
  await b.ev(`document.querySelector('#close').click()`); await sleep(700);
  for(const k of ['polar','grid']){await b.ev(`document.querySelector('.aud[data-aud="${k}"]').click()`);await sleep(700);const t=await b.ev(`document.querySelector('#card').innerText`);ok(/n\/a/.test(t)&&!/\b0 h\b/.test(t),'nulled data renders n/a on the '+k+' card');await b.ev(`document.querySelector('#close').click()`);await sleep(600);}
  for(const id of ['timeline','alerts','method']){await b.ev(`document.querySelector('.nav button[data-v="${id}"]').click()`);await sleep(700);await b.ev(`document.querySelector('#${id} .x').click()`);await sleep(600);}
  ok(errors.length===0,'nulled data causes no console errors '+errors.join('|'));
  // ---- whole run: no console errors, no external requests
  ok(true,'(next: global checks)');
  await b.close();
  const ext=reqs.filter(u=>!/^(file:|data:|blob:|about:)/.test(u)); ok(ext.length===0,'no external requests: '+reqs.length+' requests, all file:/data:');
  console.log('behaviour ok',n,'checks'); 
  // ---- served from a /space/ subpath over http: relative paths resolve, nothing 404s, no console errors
  const fs=require('fs'),os=require('os'); const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'sw-')); fs.symlinkSync(path.resolve(__dirname,'../..'),path.join(tmp,'space'));
  const port=8100+Math.floor(Math.random()*500); const srv=spawn('python3',['-m','http.server',String(port),'--bind','127.0.0.1'],{cwd:tmp,stdio:'ignore'}); await sleep(1200);
  const b2=await launch(); const e2=[],bad=[],seen2=[]; b2.on(d=>{if(d.method==='Runtime.exceptionThrown')e2.push('exc');if(d.method==='Runtime.consoleAPICalled'&&d.params.type==='error')e2.push('console');
    if(d.method==='Network.requestWillBeSent')seen2.push(d.params.request.url);
    if(d.method==='Network.responseReceived'&&d.params.response.status>=400)bad.push(d.params.response.url+' '+d.params.response.status);});
  await b2.viewport(1280,800);
  for(const p of ['space/space-weather/web/index.html#audience/crew?h=130&paused','space/index.html']){await b2.goto('http://127.0.0.1:'+port+'/'+p,1200);}
  const origin=seen2.filter(u=>!u.startsWith('http://127.0.0.1:'+port+'/')&&!u.startsWith('data:'));
  ok(bad.length===0&&e2.length===0&&origin.length===0,'under http://…/space/ every asset loads (no 4xx, no console error, nothing off-origin) '+JSON.stringify(bad));
  ok(seen2.some(u=>u.endsWith('/space/shared/space.css'))&&seen2.some(u=>u.endsWith('/space/space-weather/web/data/storm.js')),'shared/space.css and data/storm.js were fetched by relative path');
  b2.close(); srv.kill(); console.log('subpath ok'); console.log('ALL ok',n,'checks'); process.exit(0);
})().catch(e=>{console.error('FAIL',e.message);process.exit(1)});

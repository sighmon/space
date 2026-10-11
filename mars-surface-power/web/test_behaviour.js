// Headless behaviour checks for the Mars surface power page.
// usage: node --experimental-websocket web/test_behaviour.js
const path=require('path'),assert=require('assert'),fs=require('fs'),os=require('os'),{spawn}=require('child_process'),{launch,sleep}=require('../../space-weather/web/cdp.js');
const FILE='file://'+path.resolve(__dirname,'index.html');
const M=JSON.parse(fs.readFileSync(path.resolve(__dirname,'data/mars.json'),'utf8'));
let n=0; const ok=(c,m)=>{n++;assert.ok(c,m);console.log('ok',m)};
async function fresh(b,url,ms){await b.goto('about:blank',120);await b.goto(url,ms||800);}
const key=async(b,k,code)=>{await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:k,code:code||k,windowsVirtualKeyCode:k==='Escape'?27:9});await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:k,code:code||k,windowsVirtualKeyCode:k==='Escape'?27:9});};
(async()=>{
  const b=await launch(); const errors=[], reqs=[];
  b.on(d=>{ if(d.method==='Runtime.exceptionThrown')errors.push(JSON.stringify(d.params.exceptionDetails).slice(0,300));
    if(d.method==='Runtime.consoleAPICalled'&&d.params.type==='error')errors.push(JSON.stringify(d.params.args).slice(0,300));
    if(d.method==='Network.requestWillBeSent')reqs.push(d.params.request.url);
    if(d.method==='Log.entryAdded'&&d.params.entry.level==='error')errors.push(d.params.entry.text); });
  await b.send('Log.enable'); await b.viewport(1440,900);
  await fresh(b,FILE+'#?paused');
  // ---- closed panels are inert
  const closed=await b.ev(`[...document.querySelectorAll('.sheet,.layer')].map(p=>[p.id,p.hasAttribute('inert'),p.getAttribute('aria-hidden')])`);
  ok(closed.length===4&&closed.every(x=>x[1]&&x[2]==='true'),'all four panels (card + three layers) start inert and aria-hidden: '+JSON.stringify(closed.map(x=>x[0])));
  ok(await b.ev(`[...document.querySelectorAll('#sheet *,.layer *')].filter(e=>e.matches('button,a,input,summary,[tabindex]')).every(e=>e.closest('[inert]'))`),'every focusable inside a closed panel is under [inert]');
  // ---- six site cards: open, X top right, handle, Escape, focus return
  for(const s of M.sites){
    const sel=`.site[data-site="${s.id}"]`;
    await b.ev(`document.querySelector('${sel}').focus()`); await b.ev(`document.querySelector('${sel}').click()`); await sleep(900);
    ok(await b.ev(`(()=>{const s=document.querySelector('#sheet');return s.classList.contains('open')&&!s.hasAttribute('inert')&&s.getAttribute('aria-hidden')==='false'&&document.body.classList.contains('sheet-open')})()`),s.id+' card opens and is no longer inert');
    ok(await b.ev(`document.activeElement.id==='close'`),s.id+': focus moves to the X button');
    ok(await b.ev(`document.querySelector('#card h2').textContent`)===s.name,s.id+': card heading is '+s.name);
    const geo=await b.ev(`(()=>{const p=document.querySelector('#sheet .panel').getBoundingClientRect(),x=document.querySelector('#close').getBoundingClientRect(),g=document.querySelector('#sheet .grab').getBoundingClientRect();return {px:p.right-x.right,py:x.top-p.top,w:x.width,h:x.height,gh:g.height}})()`);
    ok(geo.px>=0&&geo.px<40&&geo.py<24&&geo.w>=44&&geo.h>=44&&geo.gh>=44,s.id+': X is top right and 44px, handle is a 44px strip: '+JSON.stringify(geo));
    ok(await b.ev(`document.querySelectorAll('#card .dial').length===4&&document.querySelectorAll('#card .spark').length===4&&document.querySelectorAll('#card .spark svg .sp-dot').length===12+12+12+6`),s.id+': four dials and four sparklines (12+12+12+6 real points)');
    await b.ev(`document.querySelector('#close').click()`); await sleep(900);
    ok(await b.ev(`(()=>{const s=document.querySelector('#sheet');return !s.classList.contains('open')&&s.hasAttribute('inert')})()`)&&await b.ev(`document.activeElement.dataset.site==='${s.id}'`),s.id+': X closes, re-inerts, and focus returns to the site button');
    await b.ev(`document.querySelector('${sel}').click()`); await sleep(700);
    await b.ev(`document.querySelector('#sheet .grab').click()`); await sleep(800);
    ok(await b.ev(`!document.querySelector('#sheet').classList.contains('open')&&document.activeElement.dataset.site==='${s.id}'`),s.id+': tapping the handle closes it and returns focus');
    await b.ev(`document.querySelector('${sel}').click()`); await sleep(600); await key(b,'Escape'); await sleep(800);
    ok(await b.ev(`!document.querySelector('#sheet').classList.contains('open')`),s.id+': Escape closes');
  }
  // keyboard: Enter on the focused handle closes
  await b.ev(`document.querySelector('.site[data-site="curiosity"]').click()`); await sleep(700);
  await b.ev(`document.querySelector('#sheet .grab').focus()`); await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13}); await sleep(800);
  ok(await b.ev(`!document.querySelector('#sheet').classList.contains('open')`),'Enter on the focused handle closes the card');
  // map marker click opens the nearest site
  await b.ev(`(()=>{const sv=document.querySelector('#map svg'),r=sv.getBoundingClientRect(),c=document.querySelector('#map .mk[data-site="opportunity"] .mk-c').getBoundingClientRect();sv.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:c.left+c.width/2,clientY:c.top+c.height/2}))})()`); await sleep(700);
  ok(await b.ev(`document.querySelector('#card h2').textContent`)==='Opportunity'&&await b.ev(`document.querySelectorAll('#map .mk').length`)===6,'tapping a marker on the Mars strip opens that site (six markers)');
  await key(b,'Escape'); await sleep(700);
  // ---- layers
  for(const id of ['compare','opportunity','method']){
    await b.ev(`document.querySelector('.nav button[data-v="${id}"]').focus();document.querySelector('.nav button[data-v="${id}"]').click()`); await sleep(900);
    ok(await b.ev(`(()=>{const l=document.querySelector('#${id}');return l.classList.contains('open')&&!l.hasAttribute('inert')&&document.activeElement.hasAttribute('data-close')})()`),id+' layer opens with focus on its X');
    const xr=await b.ev(`(()=>{const p=document.querySelector('#${id} .panel').getBoundingClientRect(),x=document.querySelector('#${id} .x').getBoundingClientRect();return [p.right-x.right,x.top-p.top,x.width,x.height]})()`);
    ok(xr[0]>=0&&xr[0]<40&&xr[1]<24&&xr[2]>=44&&xr[3]>=44,id+': X top right, 44px '+JSON.stringify(xr.map(Math.round)));
    await b.ev(`document.querySelector('#${id} .x').click()`); await sleep(900);
    ok(await b.ev(`document.querySelector('#${id}').hasAttribute('inert')&&document.activeElement.dataset.v==='${id}'`),id+': X closes and focus returns to the nav button');
  }
  // ---- card -> layer -> close: card inert beneath, focus returns to the trigger inside the card
  for(const id of ['compare','opportunity','method']){
    await fresh(b,FILE+'#?paused');
    await b.ev(`document.querySelector('.site[data-site="perseverance"]').click()`); await sleep(800);
    const sel=`#sheet [data-open="${id}"]`;
    for(const how of ['x','scrim','escape']){
      await b.ev(`document.querySelector('${sel}').focus();document.querySelector('${sel}').click()`); await sleep(800);
      ok(await b.ev(`document.querySelector('#sheet').hasAttribute('inert')&&document.querySelector('#${id}').classList.contains('open')`),id+' from the card ('+how+'): card is inert while the layer is open');
      if(how==='x')await b.ev(`document.querySelector('#${id} .x').click()`); else if(how==='scrim')await b.ev(`document.querySelector('#scrim').click()`); else await key(b,'Escape');
      await sleep(800);
      ok(await b.ev(`document.activeElement===document.querySelector('${sel}')&&!document.querySelector('#sheet').hasAttribute('inert')`),id+' closed with '+how+': focus is back on the card trigger and the card is live again');
    }
  }
  // ---- scrim is visible and clickable with a layer open; a real click in the gutter dismisses it
  await fresh(b,FILE+'#?paused');
  ok(await b.ev(`(()=>{const s=getComputedStyle(document.querySelector('#scrim'));return +s.opacity===0&&s.pointerEvents==='none'})()`),'scrim is invisible and not clickable with no layer open');
  for(const id of ['compare','opportunity','method']){
    await b.ev(`document.querySelector('.nav button[data-v="${id}"]').click()`); await sleep(900);
    const sc=await b.ev(`(()=>{const s=getComputedStyle(document.querySelector('#scrim')),r=document.querySelector('#${id}').getBoundingClientRect();return {o:+s.opacity,pe:s.pointerEvents,gx:Math.floor(r.left/2),top:document.elementFromPoint(Math.max(2,Math.floor(r.left/2)),450)===document.querySelector('#scrim'),left:r.left}})()`);
    ok(sc.o===1&&sc.pe==='auto'&&sc.left>20&&sc.top,id+': scrim is visible, clickable and is the element in the gutter '+JSON.stringify(sc));
    await b.send('Input.dispatchMouseEvent',{type:'mousePressed',x:sc.gx,y:450,button:'left',clickCount:1});await b.send('Input.dispatchMouseEvent',{type:'mouseReleased',x:sc.gx,y:450,button:'left',clickCount:1}); await sleep(900);
    ok(await b.ev(`!document.querySelector('#${id}').classList.contains('open')&&!document.body.classList.contains('layer-open')`),id+': a real click in the gutter dismisses the layer');
  }
  // ---- playback: autoplay by default, 12 steps, speeds, pause, wrap, last step reachable
  await fresh(b,FILE+'#?scenario=warm&ls=0',500);
  ok(await b.ev(`document.querySelector('#play').getAttribute('aria-label')==='Pause replay'`),'autoplay is on by default');
  await b.ev(`document.querySelector('#seg button[data-s="4"]').click()`);
  await b.ev(`window.__seen=[];setInterval(()=>__seen.push(__mars.step),10)`); await sleep(5600); let seen=await b.ev('__seen');
  ok(Math.max(...seen)===11,'the last step (Ls 330, step 12) is reached: max step '+Math.max(...seen));
  const iMax=seen.indexOf(11); ok(seen.slice(iMax).some(v=>v<=1),'then the loop wraps back to the start and keeps going');
  ok(new Set(seen).size===12,'all 12 seasonal steps are visited, no more and no fewer: '+[...new Set(seen)].join(','));
  await b.ev(`document.querySelector('#seg button[data-s="1"]').click()`); const c1=await b.ev('__mars.t'); await sleep(700); const c2=await b.ev('__mars.t');
  await b.ev(`document.querySelector('#seg button[data-s="4"]').click()`); const a1=await b.ev('__mars.t'); await sleep(450); const a2=await b.ev('__mars.t');
  ok(Math.abs(a2-a1)>Math.abs(c2-c1)*2,'4x runs faster than 1x');
  await b.ev(`document.querySelector('#play').click()`); const p1=await b.ev('__mars.t'); await sleep(600); const p2=await b.ev('__mars.t');
  ok(p1===p2,'Pause holds the clock'); ok(await b.ev(`document.querySelector('#play').getAttribute('aria-label')==='Play replay'`),'button label flips to Play');
  await b.ev(`document.querySelector('#play').click()`); await sleep(300); ok(await b.ev('__mars.t')!==p2,'Play resumes');
  // storm replay loops over its six samples only
  await fresh(b,FILE+'#?scenario=storm&ls=180&speed=4',400);
  await b.ev(`window.__seen=[];setInterval(()=>__seen.push(__mars.step),10)`); await sleep(3800); seen=await b.ev('__seen');
  ok(Math.min(...seen)===6&&Math.max(...seen)===11&&new Set(seen).size===6,'storm replay loops over Ls 180..330 only (six steps): '+[...new Set(seen)].join(','));
  // ---- frame-rate cap
  await fresh(b,FILE+'#?scenario=warm&ls=0',400);
  await b.ev(`window.__draws=0;const o=CanvasRenderingContext2D.prototype.clearRect;CanvasRenderingContext2D.prototype.clearRect=function(){if(this.canvas.id==='hero')__draws++;return o.apply(this,arguments)}`);
  await sleep(2000); const dr=await b.ev('__draws'); ok(dr>=20&&dr<=75,'hero redraw is capped near 30 fps: '+dr+' draws in 2 s');
  // ---- hidden tab pauses
  const h1=await b.ev('__mars.t'); await b.ev(`Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))`); await sleep(300);
  const h2=await b.ev('__mars.t'); await sleep(800); const h3=await b.ev('__mars.t'); ok(h2===h3,'a hidden tab stops the clock');
  await b.ev(`Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))`); await sleep(600);
  ok(await b.ev('__mars.t')!==h3,'and it resumes when visible');
  // ---- opening a card pauses the replay and closing it resumes
  await fresh(b,FILE+'#?scenario=warm&ls=0',400);
  await b.ev(`document.querySelector('.site[data-site="curiosity"]').click()`); await sleep(300); const k1=await b.ev('__mars.t'); await sleep(600);
  ok(await b.ev('__mars.t')===k1&&await b.ev(`document.querySelector('#play').getAttribute('aria-label')==='Play replay'`),'an open card pauses the replay');
  await b.ev(`document.querySelector('#close').click()`); await sleep(700); ok(await b.ev('__mars.t')!==k1,'closing the card resumes a replay that was playing');
  // ---- scrubber seeks, one slot for every readout, scene and ring
  await fresh(b,FILE+'#?scenario=warm&ls=0&paused',500);
  for(const i of [0,1,5,6,8,11]){
    await b.ev(`(()=>{const s=document.querySelector('#scrub');s.value=${i};s.dispatchEvent(new Event('input',{bubbles:true}))})()`); await sleep(60);
    const g=await b.ev(`({step:__mars.step,ls:document.querySelector('#live').dataset.ls,rl:document.querySelector('#r-ls').textContent,scene:__mars.scene.step,stamp:document.querySelector('#stamp').textContent,sc:__mars.scene.flux,rf:document.querySelector('#r-flux').textContent})`);
    const f=M.series.curiosity.warm[i].flux;
    ok(g.step===i&&g.scene===i&&g.ls==String(i*30)&&g.rl.startsWith(String(i*30))&&g.stamp.includes('step '+(i+1)+' of 12')&&Math.abs(g.sc-f)<1e-9&&g.rf===String(Math.round(f)),'scrub to step '+i+': readouts, stamp and scene all show Ls '+i*30+' and flux '+Math.round(f));
  }
  // open card: dials follow the same step
  await b.ev(`document.querySelector('.site[data-site="curiosity"]').click()`); await sleep(700);
  ok(await b.ev(`document.querySelector('#card .dial[data-d="cold"]').dataset.value`)===String(Math.round(M.series.curiosity.cold[11].flux))&&await b.ev(`document.querySelector('#card-ls').textContent.includes('Ls 330')`),'the card dials show the same step (Ls 330)');
  await key(b,'Escape'); await sleep(600);
  // ---- storm scenario disabled below Ls 180, never faked
  await fresh(b,FILE+'#?scenario=warm&ls=120&paused',500);
  ok(await b.ev(`document.querySelector('#scn [data-s="storm"]').getAttribute('aria-disabled')`)==='true','storm is aria-disabled at Ls 120');
  await b.ev(`document.querySelector('#scn [data-s="storm"]').click()`); await sleep(200);
  ok(await b.ev(`__mars.state.scn`)==='warm'&&/only for Ls 180 to 330/.test(await b.ev(`document.querySelector('#snote').textContent`)),'clicking disabled storm changes nothing and the explanation is visible: '+await b.ev(`document.querySelector('#snote').textContent`));
  await b.ev(`(()=>{const s=document.querySelector('#scrub');s.value=6;s.dispatchEvent(new Event('input',{bubbles:true}))})()`); await sleep(100);
  ok(await b.ev(`document.querySelector('#scn [data-s="storm"]').getAttribute('aria-disabled')`)==='false','storm is enabled at Ls 180');
  await b.ev(`document.querySelector('#scn [data-s="storm"]').click()`); await sleep(200);
  ok(await b.ev(`__mars.state.scn`)==='storm'&&await b.ev(`document.querySelector('#scrub').min`)==='6','storm selected at Ls 180; the scrubber now spans Ls 180..330 only');
  await fresh(b,FILE+'#?scenario=storm&ls=60&paused',500);
  ok(await b.ev(`['#r-flux','#r-dod','#r-def'].every(s=>document.querySelector(s).textContent==='n/a')&&__mars.scene.flux===null&&__mars.scene.dod===null`),'?scenario=storm&ls=60: readouts say n/a and the scene draws no storm (neutral sky, no Sun disc)');
  ok(/No dust-storm sample before Ls 180/.test(await b.ev(`document.querySelector('#snote').textContent`)),'and the page explains why');
  // ---- reduced motion starts paused
  await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  await fresh(b,FILE+'#?ls=0'); const r1=await b.ev('__mars.t'); await sleep(800); ok(r1===await b.ev('__mars.t')&&await b.ev(`document.querySelector('#play').getAttribute('aria-label')==='Play replay'`),'prefers-reduced-motion starts paused');
  await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'no-preference'}]});
  // ---- deep links
  const dl={'#site/curiosity?paused':['#sheet','curiosity'],'#site/opportunity?ls=180&scenario=storm&paused':['#sheet','opportunity'],'#compare?paused':['#compare',null],'#opportunity?paused':['#opportunity',null],'#method?paused':['#method',null]};
  for(const [h,[sel,site]] of Object.entries(dl)){
    await fresh(b,FILE+h,700);
    ok(await b.ev(`document.querySelector('${sel}').classList.contains('open')&&!document.querySelector('${sel}').hasAttribute('inert')`),'deep link '+h+' opens '+sel);
    if(site)ok(await b.ev(`__mars.state.site`)===site,'deep link '+h+' selects '+site);
  }
  await fresh(b,FILE+'?ls=240&scenario=storm&site=mesopotamia&paused',600);
  ok(await b.ev(`__mars.step`)===8&&await b.ev(`__mars.state.scn`)==='storm'&&await b.ev(`__mars.state.site`)==='mesopotamia'&&await b.ev(`document.querySelector('#play').getAttribute('aria-label')`)==='Play replay','?ls=240&scenario=storm&site=mesopotamia&paused in the query string works');
  await fresh(b,FILE+'#?ls=100&paused',600); ok(await b.ev(`__mars.step`)===3,'?ls=100 snaps to the nearest 30 degree step (Ls 90)');
  // ---- never show 0 for missing: null out the data and load
  await b.send('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{let v;Object.defineProperty(window,'MARS',{configurable:true,get(){return v},set(x){
    for(const s of Object.keys(x.series))for(const k of Object.keys(x.series[s]))for(const r of x.series[s][k]){r.flux=null;r.dod=null;r.file=null;r.sha256=null}
    for(const d of x.deficits)d.value=null;
    x.opportunity.points=[];x.manifest=[];x.sentences=[];x.method='';
    v=x}})})()`});
  errors.length=0;
  await fresh(b,FILE+'#site/curiosity?ls=240&paused',900);
  const txt=await b.ev(`document.querySelector('#card').innerText`);
  ok(/n\/a/.test(txt)&&!/(^|[^\d.])0 W\/m/.test(txt)&&!/\b0\.00\b/.test(txt)&&!/\b0 optical/.test(txt),'nulled data renders n/a, never 0, on the site card');
  ok(await b.ev(`[...document.querySelectorAll('#card .dial')].every(d=>d.dataset.value==='n/a')`),'every dial reads n/a');
  await key(b,'Escape'); await sleep(700);
  ok(await b.ev(`['#r-flux','#r-dod','#r-def'].every(s=>document.querySelector(s).textContent==='n/a')`),'nulled data renders n/a in the live readouts');
  for(const id of ['compare','opportunity','method']){await b.ev(`document.querySelector('.nav button[data-v="${id}"]').click()`);await sleep(700);
    if(id!=='method'){const t=await b.ev(`document.querySelector('#${id}').innerText`);ok(/n\/a/.test(t),id+' layer shows n/a for nulled data');}
    await b.ev(`document.querySelector('#${id} .x').click()`);await sleep(600);}
  ok(errors.length===0,'nulled data causes no console errors '+errors.join('|'));
  await b.close();
  const ext=reqs.filter(u=>!/^(file:|data:|blob:|about:)/.test(u)); ok(ext.length===0,'no external requests: '+reqs.length+' requests, all file:/data:');
  ok(errors.length===0,'no console errors in the whole run');
  console.log('behaviour ok',n,'checks');
  // ---- served from a /space/ subpath over http
  const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'mars-')); fs.symlinkSync(path.resolve(__dirname,'../..'),path.join(tmp,'space'));
  const port=8100+Math.floor(Math.random()*500); const srv=spawn('python3',['-m','http.server',String(port),'--bind','127.0.0.1'],{cwd:tmp,stdio:'ignore'}); await sleep(1200);
  const b2=await launch(); const e2=[],bad=[],seen2=[]; b2.on(d=>{if(d.method==='Runtime.exceptionThrown')e2.push('exc');if(d.method==='Runtime.consoleAPICalled'&&d.params.type==='error')e2.push('console');
    if(d.method==='Network.requestWillBeSent')seen2.push(d.params.request.url);
    if(d.method==='Network.responseReceived'&&d.params.response.status>=400)bad.push(d.params.response.url+' '+d.params.response.status);});
  await b2.viewport(1280,800);
  await b2.goto('http://127.0.0.1:'+port+'/space/mars-surface-power/web/index.html#site/curiosity?ls=240&paused',1300);
  for(let i=0;i<30&&!await b2.ev(`!!document.querySelector('#card h2')&&document.querySelector('#card h2').textContent!==''`);i++)await sleep(200);
  const deepOk=await b2.ev(`document.querySelector('#sheet').classList.contains('open')&&document.querySelector('#card h2').textContent==='Curiosity'`);
  await b2.goto('http://127.0.0.1:'+port+'/space/index.html',1200);
  const origin=seen2.filter(u=>!u.startsWith('http://127.0.0.1:'+port+'/')&&!u.startsWith('data:'));
  ok(bad.length===0&&e2.length===0&&origin.length===0,'under http://…/space/ every asset loads (no 4xx, no console error, nothing off-origin) '+JSON.stringify(bad));
  ok(seen2.some(u=>u.endsWith('/space/shared/space.css'))&&seen2.some(u=>u.endsWith('/space/mars-surface-power/web/data/mars.js'))&&seen2.some(u=>u.endsWith('/space/shared/space.js')),'shared/space.css, shared/space.js and data/mars.js were fetched by relative path');
  ok(deepOk,'the deep link works under the subpath');
  b2.close(); srv.kill(); console.log('subpath ok'); console.log('ALL ok',n,'checks'); process.exit(0);
})().catch(e=>{console.error('FAIL',e.message);process.exit(1)});

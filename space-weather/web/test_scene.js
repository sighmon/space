// Checks for the hero scene (Earth's limb + power grid, polar flight arc + aircraft, crew capsule + Sun direction, proton stream).
// Every expected state is recomputed here from web/data/storm.json, independently of the page code.
// usage: node --experimental-websocket web/test_scene.js
const path=require('path'),fs=require('fs'),assert=require('assert'),{launch,sleep}=require('./cdp.js');
const FILE='file://'+path.resolve(__dirname,'index.html');
const D=JSON.parse(fs.readFileSync(path.join(__dirname,'data/storm.json'),'utf8'));
let n=0; const ok=(c,m)=>{n++;assert.ok(c,m);console.log('ok',m)};
async function fresh(b,url,ms){await b.goto('about:blank',150);await b.goto(url,ms||900);}
const STEP=D.series.step_seconds, T0=Date.parse(D.series.t0);
const slot=h=>Math.max(0,Math.min(D.series.slots-1,Math.round(h*3600/STEP)));
const flux=(arr,thr,h)=>{const v=arr[slot(h)];return v==null?'na':v>=thr?'above':'below'};
function grid(h){const t=slot(h)*STEP;
  const iss=D.alerts.grid_issued.map(a=>(Date.parse(a.start)-T0)/1000), wn=D.alerts.grid_warnings.map(w=>[(Date.parse(w.start)-T0)/1000,(Date.parse(w.end)-T0)/1000]);
  const cnt=iss.filter(x=>x<=t).length, valid=wn.some(w=>t>=w[0]&&t<=w[1]);
  return {cnt,valid,state:cnt>0&&valid?'alert':valid?'warning':cnt>0?'ended':'none'}}
const TITLE={crew:'Crew beyond low Earth orbit',polar:'Polar flight',grid:'Power grid'};
const HOURS=[0,20,41.5,95.2,98,100,114,118,140,170,200,225,250];
const read=`(()=>{const o={};for(const k of ['crew','polar','grid']){const s=document.querySelector('.sc[data-el="'+k+'"]'),a=document.querySelector('.aud[data-aud="'+k+'"]'),r=s.getBoundingClientRect();
  o[k]={st:s.dataset.state,glow:s.dataset.glow,lit:s.dataset.lit,warn:s.dataset.warning,aria:s.getAttribute('aria-label'),ringState:a.dataset.state,ringHot:a.classList.contains('hot'),ringAria:a.getAttribute('aria-label'),ringCount:a.querySelector('.rv').textContent,w:r.width,h:r.height,model:JSON.parse(JSON.stringify(__weather.scene[k]))}}return o})()`;
// mean luminance of the canvas in a square around the centre of an element's button
const lum=(k,half)=>`(()=>{const s=document.querySelector('.sc[data-el="${k}"]').getBoundingClientRect(),cv=document.getElementById('hero'),sc=cv.width/innerWidth,cx=(s.left+s.width/2)*sc,cy=(s.top+s.height/2)*sc,h=${half}*sc;
  const d=cv.getContext('2d').getImageData(Math.max(0,cx-h),Math.max(0,cy-h),2*h,2*h).data;let t=0;for(let i=0;i<d.length;i+=4)t+=0.2126*d[i]+0.7152*d[i+1]+0.0722*d[i+2];return t/(d.length/4)})()`;
const click=async(b,x,y)=>{await b.send('Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',clickCount:1});await b.send('Input.dispatchMouseEvent',{type:'mouseReleased',x,y,button:'left',clickCount:1})};
const center=(b,k)=>b.ev(`(()=>{const r=document.querySelector('.sc[data-el="${k}"]').getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()`);
(async()=>{
  const b=await launch(); const errors=[], reqs=[];
  b.on(d=>{if(d.method==='Runtime.exceptionThrown')errors.push('exc '+JSON.stringify(d.params.exceptionDetails).slice(0,300));
    if(d.method==='Runtime.consoleAPICalled'&&d.params.type==='error')errors.push('console');
    if(d.method==='Network.requestWillBeSent')reqs.push(d.params.request.url);
    if(d.method==='Log.entryAdded'&&d.params.entry.level==='error')errors.push(d.params.entry.text)});
  await b.send('Log.enable');
  await b.viewport(1440,900);
  // ---- each element's state equals its own ring's state, at fixed times (and only that ring's)
  const lumOn={crew:[],polar:[],grid:[]}, lumOff={crew:[],polar:[],grid:[]};
  for(const h of HOURS){
    await fresh(b,FILE+'#?h='+h+'&paused&static');
    const r=await b.ev(read), c=flux(D.series.gt100.values,D.thresholds.crew.value,h), p=flux(D.series.gt10.values,D.thresholds.polar.value,h), g=grid(h);
    ok(r.crew.st===c&&r.crew.ringState===c&&r.crew.glow===(c==='above'?'on':'off')&&r.crew.model.glow===(c==='above'?1:0)&&r.crew.ringHot===(c==='above'),`h=${h}: capsule is ${c} (>100 MeV vs 1 pfu), glow ${r.crew.glow}, same as the crew ring`);
    ok(r.polar.st===p&&r.polar.ringState===p&&r.polar.glow===(p==='above'?'on':'off')&&r.polar.model.glow===(p==='above'?1:0)&&r.polar.ringHot===(p==='above'),`h=${h}: aircraft is ${p} (≥10 MeV vs 100 pfu), glow ${r.polar.glow}, same as the polar ring`);
    ok(r.grid.st===g.state&&r.grid.ringState===g.state&&r.grid.glow===(g.state==='alert'?'on':'off')&&r.grid.model.glow===(g.state==='alert'?1:0)&&r.grid.lit===String(g.cnt)&&r.grid.ringCount===String(g.cnt)&&r.grid.warn===(g.valid?'on':'off')&&r.grid.model.lit===g.cnt&&r.grid.model.valid===g.valid,`h=${h}: surface is ${g.state}: ${g.cnt} substations lit (= ring count), warning ${g.valid?'valid':'not valid'}, glow only on an issued alert`);
    ok(r.grid.model.aurora===({none:.08,ended:.12,warning:.45,alert:.95}[g.state]),`h=${h}: auroral band strength follows only the grid state (${g.state})`);
    ok(!/µGy|dose/i.test(r.crew.aria+r.polar.aria+r.grid.aria)&&!/pfu/.test(r.grid.aria),`h=${h}: scene labels carry no dose and the grid label no flux unit`);
    for(const k of ['crew','polar','grid']){const hot=r[k].glow==='on';const half=k==='grid'?60:34;(hot?lumOn:lumOff)[k].push(await b.ev(lum(k,half)));}
  }
  for(const k of ['crew','polar','grid']){ok(lumOn[k].length>0&&lumOff[k].length>0,`${k}: fixed times include lit and unlit states`);
    ok(Math.min(...lumOn[k])>Math.max(...lumOff[k]),`${k}: the drawn element is brighter when its ring is lit than at every unlit time (${Math.min(...lumOn[k]).toFixed(1)} > ${Math.max(...lumOff[k]).toFixed(1)})`);}
  // independence: crew lit with polar unlit never happens in this storm, but polar lit with crew unlit does
  const ind=await (async()=>{await fresh(b,FILE+'#?h=100&paused&static');return b.ev(read)})();
  ok(ind.polar.glow==='on'&&ind.crew.glow==='off'&&ind.grid.glow==='on','h=100: aircraft and surface glow while the capsule does not (elements are independent)');
  // ---- labels, targets, honesty text
  const r0=await b.ev(read);
  ok(['crew','polar','grid'].every(k=>/in the picture/.test(r0[k].aria)&&r0[k].aria.includes(r0[k].ringAria)&&/Open the/.test(r0[k].aria)),'scene buttons are buttons with aria labels that include the ring label and name the card they open');
  ok(await b.ev(`[...document.querySelectorAll('.sc')].every(e=>e.tagName==='BUTTON')&&document.querySelectorAll('.sc').length===3`),'three real <button> elements, one per audience');
  ok(/Not observed K/.test(await b.ev(`document.querySelector('.viz').innerText`))&&/illustrat/i.test(await b.ev(`document.querySelector('.viz').innerText`)),'honesty note on the page: illustrative drawing, real values, grid = issued alerts not observed K');
  const cl=await b.ev(`document.getElementById('hero').getAttribute('aria-label')`);
  ok(/Illustration, real values/.test(cl)&&/not observed K/.test(cl)&&/greater than 100 MeV/.test(cl)&&!/dose/i.test(cl),'canvas label: illustration with real values; each element named with its own ring input; no dose');
  ok(/Illustrative[\s\S]*hero scene/.test(await b.ev(`document.getElementById('method').innerText`)),'method layer labels the hero scene as illustrative');
  // pixels are drawn: the canvas is not blank and has a bright limb
  ok(await b.ev(`(()=>{const cv=document.getElementById('hero'),d=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;let mx=0,nz=0;for(let i=0;i<d.length;i+=40){const v=d[i]+d[i+1]+d[i+2];if(v>30)nz++;if(v>mx)mx=v}return nz>500&&mx>300})()`),'the scene is actually drawn on the canvas');
  // ---- layout at every width: found a free spot for all three, targets >=44, inside the viewport, nothing overlapping the UI
  const SIZES=[[1440,900],[1280,720],[1024,800],[901,800],[900,800],[768,1024],[430,932],[412,915],[390,844],[375,667],[360,740],[360,640],[320,640],[320,568]];
  for(const [w,h] of SIZES){await b.viewport(w,h);await fresh(b,FILE+'#?h=100&paused&static',700);await sleep(300);
    const o=await b.ev(`(()=>{const L=__weather.layout(),els=[...document.querySelectorAll('.sc')].map(e=>({k:e.dataset.el,r:e.getBoundingClientRect()}));
      const ui=['.brand .label','.brand .small','.brand .ghlink','.nav button','#r-time','#r-f10','#r-f100','#r-dose','.live .viz','.aud','#play','#seg button','#scrub','.dock','.hero-copy p','.hero-copy .hint'].flatMap(s=>[...document.querySelectorAll(s)].filter(e=>{const c=getComputedStyle(e);return c.display!=='none'&&c.visibility!=='hidden'}).map(e=>({s,r:e.getBoundingClientRect()})));
      const bad=[];for(const a of els){if(a.r.width<43.5||a.r.height<43.5)bad.push('small '+a.k);if(a.r.left<0||a.r.right>innerWidth||a.r.top<0||a.r.bottom>innerHeight)bad.push('outside '+a.k);
        for(const u of ui)if(u.r.width&&u.r.height&&a.r.left<u.r.right&&u.r.left<a.r.right&&a.r.top<u.r.bottom&&u.r.top<a.r.bottom)bad.push(a.k+' x '+u.s);
        for(const q of els)if(q.k<a.k&&a.r.left<q.r.right&&q.r.left<a.r.right&&a.r.top<q.r.bottom&&q.r.top<a.r.bottom)bad.push(a.k+' x '+q.k)}
      for(const a of els){const q=a.r,e=document.elementFromPoint(q.left+q.width/2,q.top+q.height/2);if(!e||!e.closest('.sc')||e.closest('.sc').dataset.el!==a.k)bad.push('covered '+a.k+' by '+(e&&(e.className||e.tagName)))}
      return {fail:L.fail,bad,doc:document.documentElement.scrollWidth<=innerWidth}})()`);
    ok(!o.fail&&o.bad.length===0&&o.doc,`${w}x${h}: all three elements placed in free space, ≥44 px, in the viewport, no overlap with controls, text, readouts or the GitHub link ${JSON.stringify(o.bad)}`);}
  // ---- tap opens the right card (real pointer events), at desktop and phone sizes; Escape returns to the element; keyboard
  for(const [w,h] of [[1440,900],[390,844],[320,640]]){await b.viewport(w,h);
    for(const k of ['crew','polar','grid']){
      await fresh(b,FILE+'#?h=100&paused&static',700);await sleep(300);
      const pt=await center(b,k); await click(b,pt.x,pt.y); await sleep(800);
      ok(await b.ev(`document.querySelector('#sheet').classList.contains('open')&&document.querySelector('#card h2').textContent`)===TITLE[k],`${w}px: tapping the ${k} element opens the ${TITLE[k]} card`);
      await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});await sleep(800);
      ok(await b.ev(`document.activeElement.dataset.el`)===k&&!(await b.ev(`document.querySelector('#sheet').classList.contains('open')`)),`${w}px: Escape closes the card and returns focus to the ${k} element`);
    }}
  await b.viewport(1440,900);
  for(const k of ['crew','polar','grid'])for(const [key,code,vk,txt] of [['Enter','Enter',13,'\r'],[' ','Space',32,' ']]){
    await fresh(b,FILE+'#?h=100&paused&static',700);await sleep(250);
    await b.ev(`document.querySelector('.sc[data-el="${k}"]').focus()`);
    await b.send('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:vk,text:txt});await b.send('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:vk});await sleep(800);
    ok(await b.ev(`document.querySelector('#sheet').classList.contains('open')&&document.querySelector('#card h2').textContent`)===TITLE[k],`keyboard ${code} on the ${k} element opens ${TITLE[k]}`);}
  await fresh(b,FILE+'#?h=100&paused&static',700);
  const tab=async()=>{await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9})};
  await b.ev(`document.querySelector('#scrub').focus()`);const order=[];for(let i=0;i<3;i++){await tab();order.push(await b.ev(`document.activeElement.dataset.el||document.activeElement.id`))}
  ok(order.join()==='crew,polar,grid','Tab reaches the three scene elements in order after the controls: '+order.join(' > '));
  const f=await b.ev(`(()=>{const e=document.querySelector('.sc[data-el=grid]');e.focus();const c=getComputedStyle(e);return {fv:e.matches(':focus-visible'),os:c.outlineStyle,ow:parseFloat(c.outlineWidth),lab:getComputedStyle(e.querySelector('.sl')).display}})()`);
  ok(f.fv&&f.os==='solid'&&f.ow>=2&&f.lab==='block','a focused element shows a 2 px outline and its name');
  // ---- hover opens the card after a short dwell, a pass-through does not
  await fresh(b,FILE+'#?h=100&paused&static',700);await sleep(300);
  let pt=await center(b,'polar');
  await b.send('Input.dispatchMouseEvent',{type:'mouseMoved',x:pt.x,y:pt.y});await sleep(200);await b.send('Input.dispatchMouseEvent',{type:'mouseMoved',x:5,y:5});await sleep(1000);
  ok(!(await b.ev(`document.querySelector('#sheet').classList.contains('open')`)),'a mouse passing over the aircraft does not open the card');
  await b.send('Input.dispatchMouseEvent',{type:'mouseMoved',x:pt.x,y:pt.y});await sleep(1100);
  ok(await b.ev(`document.querySelector('#sheet').classList.contains('open')&&document.querySelector('#card h2').textContent`)==='Polar flight','hovering the aircraft for a moment opens the Polar flight card');
  // ---- a card or layer hides the scene buttons (nothing to tab to behind it)
  ok(await b.ev(`getComputedStyle(document.querySelector('.sc')).visibility`)==='hidden','scene buttons are hidden while a card is open');
  // ---- reduced motion: static scene, nothing redrawn, no loop
  await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  await b.viewport(1440,900);await b.goto('about:blank',150);
  await b.send('Page.addScriptToEvaluateOnNewDocument',{source:`window.__d=0;(()=>{const o=CanvasRenderingContext2D.prototype.clearRect;CanvasRenderingContext2D.prototype.clearRect=function(){if(this.canvas.id==='hero')__d++;return o.apply(this,arguments)}})()`});
  await b.goto(FILE+'#?h=170',1200);
  const d1=await b.ev('__d'), s1=await b.ev(`document.getElementById('hero').toDataURL()`), t1=await b.ev('__weather.t');
  await sleep(1500);
  ok(await b.ev('__d')===d1&&await b.ev(`document.getElementById('hero').toDataURL()`)===s1&&await b.ev('__weather.t')===t1,'prefers-reduced-motion: the scene is static (no redraw, identical pixels after 1.5 s, replay not running)');
  const rr=await b.ev(read);
  ok(rr.crew.glow==='on'&&rr.polar.glow==='on'&&rr.grid.glow==='off','reduced motion still shows the real states (h=170: capsule and aircraft lit, grid not)');
  await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'no-preference'}]});
  // ---- cost: draw time, fps cap, hidden tab
  await b.goto('about:blank',150);await fresh(b,FILE+'#?h=100',900);
  const ms=await b.ev(`(()=>{const t=performance.now();for(let i=0;i<40;i++)__weather.draw();return (performance.now()-t)/40})()`);
  ok(ms<14,'one scene frame costs '+ms.toFixed(1)+' ms on the main thread at 1440x900 (static layers are cached, only the stream and glows are redrawn)');
  await b.ev('window.__d=0');
  await sleep(2000);const dr=await b.ev('__d');ok(dr>=15&&dr<=70,'scene redraw is capped near 30 fps while playing: '+dr+' draws in 2 s');
  await b.ev(`Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))`);await sleep(400);
  await b.ev('window.__d=0');await sleep(1200);ok(await b.ev('__d')===0,'a hidden tab stops scene redraws');
  await b.ev(`Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))`);
  await fresh(b,FILE+'#?h=100&paused',700);await b.ev('window.__d=0');await sleep(1500);
  ok(await b.ev('__d')===0,'a paused replay redraws nothing (no idle loop)');
  // ---- no external requests, no console errors
  const ext=reqs.filter(u=>!/^(file:|data:|about:)/.test(u));
  ok(ext.length===0,'no request leaves the page (only file: and data: URLs) '+JSON.stringify(ext.slice(0,3)));
  ok(!reqs.some(u=>/\.(png|jpe?g|webp|gif|mp4|webm)(\?|$)/i.test(u)),'no image or video file is loaded: the scene is drawn procedurally');
  ok(errors.length===0,'no console errors '+errors.join('|'));
  // ---- n/a: null every sample and alert; the scene elements say n/a, do not glow, and still open their cards
  await b.send('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{let v;Object.defineProperty(window,'STORM',{configurable:true,get(){return v},set(x){
    x.series.gt10.values=x.series.gt10.values.map(()=>null);x.series.gt100.values=x.series.gt100.values.map(()=>null);
    x.alerts.grid_issued=[];x.alerts.grid_warnings=[];x.thresholds.crew=null;x.thresholds.polar=null;v=x}})})()`});
  await fresh(b,FILE+'#?h=100&paused&static',900);
  const na=await b.ev(read);
  ok(['crew','polar','grid'].every(k=>na[k].st==='na'&&na[k].glow==='off'&&na[k].model.glow===0),'no data: every scene element is n/a and unlit');
  ok(na.grid.lit==='n/a'&&na.grid.model.lit===0,'no data: no substation lit, count n/a (never 0)');
  const pt2=await center(b,'grid');await click(b,pt2.x,pt2.y);await sleep(800);
  ok(await b.ev(`document.querySelector('#sheet').classList.contains('open')`),'with no data the surface element still opens its card');
  ok(errors.length===0,'no console errors with null data '+errors.join('|'));
  b.close(); console.log('scene ok',n,'checks'); process.exit(0);
})().catch(e=>{console.error('FAIL',e.message);process.exit(1)});

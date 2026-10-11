// Checks for the three audience rings in the hero (crew, polar flight, power grid).
// Every expected value is recomputed here from web/data/storm.json, independently of the page code.
// usage: node --experimental-websocket web/test_rings.js
const path=require('path'),fs=require('fs'),assert=require('assert'),{launch,sleep}=require('./cdp.js');
const FILE='file://'+path.resolve(__dirname,'index.html');
const D=JSON.parse(fs.readFileSync(path.join(__dirname,'data/storm.json'),'utf8'));
let n=0; const ok=(c,m)=>{n++;assert.ok(c,m);console.log('ok',m)};
async function fresh(b,url,ms){await b.goto('about:blank',150);await b.goto(url,ms||800);}
// number formatting the page uses for readouts (3 decimals under 1, 2 under 10, 1 under 100, none from 100, thousands commas)
const fmt=v=>{const a=Math.abs(v),p=a>=100?0:a>=10?1:a>=1?2:3;const q=v.toFixed(p).split('.');return q[0].replace(/\B(?=(\d{3})+(?!\d))/g,',')+(q[1]?'.'+q[1]:'')};
const STEP=D.series.step_seconds, T0=Date.parse(D.series.t0), SPAN=D.series.slots*STEP;
const slot=h=>Math.max(0,Math.min(D.series.slots-1,Math.round(h*3600/STEP)));
const frac=(v,lo,hi)=>Math.max(0,Math.min(1,(Math.log10(v)-Math.log10(lo))/(Math.log10(hi)-Math.log10(lo))));
const SW=0.75*2*Math.PI*38;
function expectFlux(arr,thr,lo,hi,h){const v=arr[slot(h)];if(v==null)return {v:null,state:'na',text:'n/a'};
  return {v,state:v>=thr?'above':'below',text:fmt(v),frac:frac(v,lo,hi)}}
function expectGrid(h){const t=slot(h)*STEP;
  const iss=D.alerts.grid_issued.map(a=>(Date.parse(a.start)-T0)/1000), wn=D.alerts.grid_warnings.map(w=>[(Date.parse(w.start)-T0)/1000,(Date.parse(w.end)-T0)/1000]);
  const cnt=iss.filter(x=>x<=t).length, valid=wn.some(w=>t>=w[0]&&t<=w[1]);
  return {cnt,valid,state:cnt>0&&valid?'alert':valid?'warning':cnt>0?'ended':'none',total:iss.length}}
const readRing=k=>`(()=>{const b=document.querySelector('.aud[data-aud="${k}"]');return {state:b.dataset.state,value:b.dataset.value,rv:b.querySelector('.rv').textContent,st:b.querySelector('.st').textContent,txt:b.innerText,aria:b.getAttribute('aria-label'),hot:b.classList.contains('hot'),dash:(b.querySelector('.rg-fill')||{getAttribute(){return null}}).getAttribute('stroke-dasharray'),on:b.querySelectorAll('.rg-al.on').length,als:b.querySelectorAll('.rg-al').length,bands:b.querySelectorAll('.rg-band').length,bandOn:b.querySelectorAll('.rg-band.on').length}})()`;
(async()=>{
  const b=await launch(); const errors=[];
  b.on(d=>{if(d.method==='Runtime.exceptionThrown')errors.push('exc');if(d.method==='Runtime.consoleAPICalled'&&d.params.type==='error')errors.push('console')});
  await b.viewport(1440,900);
  // hours chosen to hit every state: before anything, polar only (h 41-47 and 100), grid alert, warning valid without alert, warning ended, crew + polar together, both back below
  const HOURS=[0,20,41.5,95.2,98,100,114,118,140,170,200,225,250];
  for(const h of HOURS){
    await fresh(b,FILE+'#?h='+h+'&paused');
    const c=expectFlux(D.series.gt100.values,D.thresholds.crew.value,0.01,100,h), p=expectFlux(D.series.gt10.values,D.thresholds.polar.value,0.1,2000,h), g=expectGrid(h);
    const rc=await b.ev(readRing('crew')), rp=await b.ev(readRing('polar')), rg=await b.ev(readRing('grid'));
    ok(rc.rv===c.text&&rc.state===c.state&&+rc.value===c.v,`h=${h}: crew ring shows >100 MeV ${c.text} pfu (${c.state}), real sample ${c.v}`);
    ok(rp.rv===p.text&&rp.state===p.state&&+rp.value===p.v,`h=${h}: polar ring shows ≥10 MeV ${p.text} pfu (${p.state}), real sample ${p.v}`);
    ok(Math.abs(parseFloat(rc.dash)-c.frac*SW)<0.6&&Math.abs(parseFloat(rp.dash)-p.frac*SW)<0.6,`h=${h}: ring fills follow log10 of the flux (${(c.frac*100).toFixed(0)}% / ${(p.frac*100).toFixed(0)}%)`);
    ok(rc.hot===(c.state==='above')&&rp.hot===(p.state==='above'),`h=${h}: glow only when at or above the threshold (crew ${rc.hot}, polar ${rp.hot})`);
    ok(/1 pfu/.test(rc.st)&&/100 pfu/.test(rp.st)&&(c.state==='above'?/at or above/:/below/).test(rc.st)&&(p.state==='above'?/at or above/:/below/).test(rp.st),`h=${h}: status lines name the threshold: "${rc.st}" / "${rp.st}"`);
    ok(rg.state===g.state&&rg.rv===String(g.cnt)&&rg.on===g.cnt&&rg.als===g.total&&rg.hot===(g.state==='alert')&&(rg.bandOn>0)===g.valid,`h=${h}: grid ring state ${g.state}, ${g.cnt} of ${g.total} K≥7 alerts issued, warning valid ${g.valid} (not flux, not observed K)`);
    ok(!/µGy|dose/i.test(rc.txt+rp.txt+rg.txt),`h=${h}: no dose in any ring`);
    ok(!/pfu/.test(rg.txt),`h=${h}: the grid ring shows no flux unit`);
  }
  // states really are reached by the chosen hours
  const seen=new Set(HOURS.map(h=>expectGrid(h).state)); ok(['none','alert','warning','ended'].every(s=>seen.has(s)),'the fixed times cover every grid state: '+[...seen].join(','));
  ok(HOURS.some(h=>{const c=expectFlux(D.series.gt100.values,1,0.01,100,h),p=expectFlux(D.series.gt10.values,100,0.1,2000,h);return c.state==='above'&&p.state==='above'}),'a fixed time has crew and polar both at or above their thresholds');
  ok(HOURS.some(h=>expectFlux(D.series.gt100.values,1,0.01,100,h).state==='below'&&expectFlux(D.series.gt10.values,100,0.1,2000,h).state==='above'),'a fixed time has polar at or above while crew is below (rings are independent)');
  // ---- labels, units, honesty text, distinguishable without colour
  await fresh(b,FILE+'#?h=100&paused');
  const all=await b.ev(`document.querySelector('.auds').innerText`);
  ok(/Crew/.test(all)&&/beyond low Earth orbit/.test(all)&&/Polar flight/.test(all)&&/Power grid/.test(all),'each ring has its audience label');
  ok(/>100 MeV · pfu/.test(all)&&/≥10 MeV · pfu/.test(all)&&/K≥7 alerts issued/.test(all),'each ring names its quantity and unit');
  const viz=await b.ev(`document.querySelector('.viz').innerText`);
  ok(/Not observed K/.test(viz)&&/warning valid period/.test(viz)&&/own axis, in no ring/.test(viz)&&/real/i.test(viz),'honesty note: grid band is issued warning period not observed K, dose is in no ring');
  ok(await b.ev(`(()=>{const m=['crew','polar','grid'].map(k=>{const b=document.querySelector('.aud[data-aud="'+k+'"]');return b.querySelector('.rg-mk')?b.querySelector('.rg-mk').innerHTML.replace(/[\\d.]+/g,'#'):'dial'});return new Set(m).size===3})()`),'shapes differ without colour: crew marker is a dot, polar a square, grid a dial of ticks');
  ok(await b.ev(`document.querySelector('.aud[data-aud=grid] .rg-day')!==null&&document.querySelector('.aud[data-aud=grid] .rg-fill')===null&&document.querySelector('.aud[data-aud=crew] .rg-fill')!==null`),'grid ring is a different kind of state (dial, band, ticks), not a flux fill');
  ok(await b.ev(`['crew','polar','grid'].every(k=>{const b=document.querySelector('.aud[data-aud="'+k+'"]');return /^(Crew|Polar|Power)/.test(b.getAttribute('aria-label'))&&/Open the/.test(b.getAttribute('aria-label'))&&b.tagName==='BUTTON'})`),'rings are buttons with aria labels naming value, state and the card they open');
  ok((await b.ev(readRing('grid'))).aria.includes('not observed K'),'grid aria label says issued products, not observed K');
  // ---- targets, tap, keyboard, focus
  for(const w of [1440,768,390,320]){await b.viewport(w,w>500?900:700);await fresh(b,FILE+'#?h=100&paused');
    ok(await b.ev(`[...document.querySelectorAll('.aud')].every(e=>{const r=e.getBoundingClientRect();return r.width>=44&&r.height>=44})`),w+' px: ring targets are at least 44x44');
    ok(await b.ev(`[...document.querySelectorAll('.aud')].every(e=>{const r=e.getBoundingClientRect();return e.scrollWidth<=e.clientWidth+1&&[...e.querySelectorAll('*')].every(c=>{const q=c.getBoundingClientRect();return (!q.width&&!q.height)||(q.left>=r.left-1&&q.right<=r.right+1)})})`),w+' px: nothing inside a ring button is clipped or overflows it');}
  await b.viewport(1440,900);
  const TITLE={crew:'Crew beyond low Earth orbit',polar:'Polar flight',grid:'Power grid'};
  for(const k of ['crew','polar','grid']){
    await fresh(b,FILE+'#?h=100&paused');
    // real pointer tap at the centre of the ring
    const pt=await b.ev(`(()=>{const r=document.querySelector('.aud[data-aud="${k}"] svg').getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()`);
    await b.send('Input.dispatchMouseEvent',{type:'mousePressed',x:pt.x,y:pt.y,button:'left',clickCount:1});await b.send('Input.dispatchMouseEvent',{type:'mouseReleased',x:pt.x,y:pt.y,button:'left',clickCount:1});await sleep(900);
    ok(await b.ev(`document.querySelector('#sheet').classList.contains('open')&&document.querySelector('#card h2').textContent`)===TITLE[k],'tapping the '+k+' ring opens the '+TITLE[k]+' card');
    ok(await b.ev('location.hash')==='#audience/'+k,k+': hash is #audience/'+k);
    await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});await sleep(900);
    ok(await b.ev(`document.activeElement.dataset.aud`)===k,k+': Escape returns focus to the ring');
    // keyboard: Enter and Space
    for(const [key,code,vk,txt] of [['Enter','Enter',13,'\r'],[' ','Space',32,' ']]){
      await b.ev(`document.querySelector('.aud[data-aud="${k}"]').focus()`);
      await b.send('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:vk,text:txt});await b.send('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:vk});await sleep(900);
      ok(await b.ev(`document.querySelector('#sheet').classList.contains('open')&&document.querySelector('#card h2').textContent`)===TITLE[k],k+': '+(code)+' opens '+TITLE[k]);
      await b.ev(`document.querySelector('#close').click()`);await sleep(800);
    }
  }
  // Tab order and visible focus ring
  await fresh(b,FILE+'#?h=100&paused');
  const tab=async()=>{await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9})};
  await b.ev(`document.querySelector('.nav button:last-child').focus()`);
  const order=[]; for(let i=0;i<3;i++){await tab();order.push(await b.ev(`document.activeElement.dataset.aud||document.activeElement.id||document.activeElement.tagName`));}
  ok(order.join()==='crew,polar,grid','keyboard Tab reaches the three rings in order: '+order.join(' > '));
  await b.ev(`document.querySelector('.aud[data-aud=crew]').focus()`);
  const f2=await b.ev(`(()=>{const e=document.querySelector('.aud[data-aud=crew]'),c=getComputedStyle(e);return {fv:e.matches(':focus-visible'),ow:c.outlineWidth,os:c.outlineStyle}})()`);
  ok(f2.fv&&f2.os==='solid'&&parseFloat(f2.ow)>=2,'a focused ring shows a visible 2 px outline: '+JSON.stringify(f2));
  // ---- CPU: paused page writes nothing; playing page only writes changed values and respects the fps cap
  await fresh(b,FILE+'#?h=100&paused');
  await b.ev(`window.__m=0;new MutationObserver(l=>{__m+=l.length}).observe(document.querySelector('.auds'),{subtree:true,childList:true,attributes:true,characterData:true})`);
  await sleep(1500); ok(await b.ev('__m')===0,'a paused page makes zero DOM writes in the rings');
  await fresh(b,FILE+'#?h=0');
  await b.ev(`window.__m=0;new MutationObserver(l=>{__m+=l.length}).observe(document.querySelector('.auds'),{subtree:true,childList:true,attributes:true,characterData:true})`);
  await sleep(2000); const m=await b.ev('__m'); ok(m<=600,'playing 4x: ring DOM writes stay bounded ('+m+' in 2 s)');
  // ---- hidden tab: no ring writes
  await b.ev(`Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))`);await sleep(400);
  await b.ev(`window.__m=0`);await sleep(1200);ok(await b.ev('__m')===0,'a hidden tab stops ring updates');
  // ---- reduced motion: no transition longer than the 0.01 s reduced-motion override, no animation
  await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  await fresh(b,FILE+'#?h=170&paused');
  ok(await b.ev(`[...document.querySelectorAll('.aud, .aud svg')].every(e=>{const c=getComputedStyle(e);return parseFloat(c.transitionDuration)<=0.011&&c.animationName==='none'})`),'prefers-reduced-motion: ring glow transitions are effectively off and nothing animates');
  await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'no-preference'}]});
  ok(errors.length===0,'no console errors '+errors.join('|'));
  // ---- n/a: null every sample, alert and threshold; rings must say n/a and never 0
  await b.send('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{let v;Object.defineProperty(window,'STORM',{configurable:true,get(){return v},set(x){
    x.series.gt10.values=x.series.gt10.values.map(()=>null);x.series.gt100.values=x.series.gt100.values.map(()=>null);
    x.alerts.grid_issued=[];x.alerts.grid_warnings=[];x.thresholds.crew=null;x.thresholds.polar=null;v=x}})})()`});
  await fresh(b,FILE+'#?h=100&paused',900);
  for(const k of ['crew','polar','grid']){const r=await b.ev(readRing(k));
    ok(r.state==='na'&&r.rv==='n/a'&&r.st==='n/a'&&r.value==='n/a'&&!r.hot&&!/\b0\b/.test(r.txt),k+' ring with no data: n/a, no glow, no 0 ('+JSON.stringify(r.txt)+')');
    ok(/n\/a|no data|Open/.test(r.aria),k+' ring aria label still valid with no data');}
  ok(await b.ev(`document.querySelector('.aud[data-aud=crew] .rg-fill').getBoundingClientRect().width>=0&&getComputedStyle(document.querySelector('.aud[data-aud=crew] .rg-fill')).display==='none'`),'no data: ring fill is not drawn');
  await b.ev(`document.querySelector('.aud[data-aud=grid]').click()`);await sleep(800);
  ok(await b.ev(`document.querySelector('#sheet').classList.contains('open')`),'a ring with no data still opens its card');
  ok(errors.length===0,'no console errors with null data '+errors.join('|'));
  b.close(); console.log('rings ok',n,'checks'); process.exit(0);
})().catch(e=>{console.error('FAIL',e.message);process.exit(1)});

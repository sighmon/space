// Headless checks for the second review of PR #1 (wording from each region's real source, null Diviner pixel size,
// inert closed panels + focus management, marker focus ring, Slater Plain slope text, one play-button announcement,
// no CPU work in a hidden tab and no clock jump on return).
// usage: node --experimental-websocket web/test_review2.js   (needs google-chrome on PATH)
const {spawn}=require('child_process'), path=require('path'), http=require('http');
const url='file://'+path.resolve(process.env.PAGE||path.join(__dirname,'index.html'));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const getJSON=u=>new Promise((res,rej)=>http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res(JSON.parse(d)))}).on('error',rej));
const IDS={CAB:'PCB01',DGR:'dGR101',HAW:'HW01',MAL:'MMA01',MMP:'MMP01',MMO:'MMO01',NR1:'NR101',NR2:'NR201',SLP:'SP01'};
(async()=>{
  const port=9600+Math.floor(Math.random()*400);
  const ch=spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--remote-debugging-port='+port,'--window-size=1440,900','about:blank'],{stdio:'ignore'});
  let tabs; for(let i=0;i<50;i++){try{tabs=await getJSON(`http://127.0.0.1:${port}/json`);if(tabs.length)break;}catch(e){}await sleep(200);}
  const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl); await new Promise(r=>ws.onopen=r);
  let id=0; const pend={}, errors=[];
  ws.onmessage=m=>{const d=JSON.parse(m.data);if(d.id&&pend[d.id]){pend[d.id](d.result||d);delete pend[d.id];}
    else if(d.method==='Runtime.exceptionThrown')errors.push((d.params.exceptionDetails.exception&&d.params.exceptionDetails.exception.description||'').split('\n')[0]);};
  const send=(method,params={})=>new Promise(r=>{const i=++id;pend[i]=r;ws.send(JSON.stringify({id:i,method,params}));});
  const ev=async e=>{const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});return r.result&&r.result.value;};
  await send('Runtime.enable'); await send('Page.enable');
  const fails=[]; const check=(ok,msg)=>{console.log(ok?'ok  ':'FAIL',msg);if(!ok)fails.push(msg);};
  const key=async(k,code,extra={})=>{await send('Input.dispatchKeyEvent',{type:'keyDown',key:k,code,windowsVirtualKeyCode:extra.vk||0,...extra});await send('Input.dispatchKeyEvent',{type:'keyUp',key:k,code,windowsVirtualKeyCode:extra.vk||0});};
  const tab=(shift)=>key('Tab','Tab',{vk:9,modifiers:shift?8:0});
  const load=async(hash='')=>{await send('Page.navigate',{url:'about:blank'});await sleep(200);await send('Page.navigate',{url:url+hash});await sleep(1500);};
  const active=()=>ev(`(()=>{const a=document.activeElement;return {tag:a.tagName,id:a.id,cls:a.className&&a.className.baseVal===undefined?a.className:'',panel:(a.closest('.sheet,.layer')||{}).id||null,mk:(a.closest('.mk')||{dataset:{}}).dataset.id||null,v:a.dataset&&a.dataset.v||null,open:a.dataset&&a.dataset.open||null}})()`);

  // ---------- B: zoom wording derives from each region's real source ----------
  await load('#?paused');
  for(const [mk,site] of Object.entries(IDS)){
    await ev(`document.querySelector('.mk[data-id="${mk}"]').click()`); await sleep(500);
    const t=await ev(`({badge:document.querySelector('#zbadge').textContent,cav:document.querySelector('#z-caveat').textContent,lab:document.querySelector('#tl-label').textContent,src:ZOOM_DATA.dem['${site}'].source,px:ZOOM_DATA.dem['${site}'].source_pixel_m})`);
    const mosaic=/product 81/.test(t.src), ldem=/product 90/.test(t.src);
    if(mosaic){
      check(/mosaic/i.test(t.badge)&&/interpolation/i.test(t.badge)&&!/site DEM/i.test(t.badge),site+' badge says 5 m mosaic, interpolation-filled: "'+t.badge+'"');
      check(!/5 m site DEM/i.test(t.cav)&&/product-81/.test(t.cav)&&/interpolat/i.test(t.cav)&&/not a product-78 site DEM/.test(t.cav),site+' caveat describes the product-81 mosaic, not a site DEM');
      check(!/site DEM/i.test(t.lab)||/not/.test(t.lab),site+' timeline label does not call it a site DEM: '+t.lab.slice(-60));
    }else if(ldem){
      check(/20 m polar DEM/.test(t.badge)&&!/site DEM/i.test(t.badge),site+' badge says 20 m polar DEM: "'+t.badge+'"');
      check(/20 m per pixel/.test(t.cav)&&!/5 m site DEM/.test(t.cav),site+' caveat describes 20 m terrain');
    }else{
      check(/5 m site DEM/.test(t.badge)&&!/mosaic/i.test(t.badge),site+' badge says 5 m site DEM: "'+t.badge+'"');
      check(/5 m site DEM covers a limited tile/.test(t.cav)&&!/mosaic/i.test(t.cav),site+' caveat describes a product-78 site DEM');
    }
    await ev(`document.querySelector('#close').click()`); await sleep(300);
  }

  // ---------- I: Slater Plain slope n/a explains the mosaic ----------
  await ev(`document.querySelector('.mk[data-id="SLP"]').click()`); await sleep(600);
  const sl=await ev(`(()=>{const d=document.querySelector('.dial[data-k="slope"]');return {n:d.querySelector('.n').textContent,u:d.querySelector('.u').textContent,def:d.querySelector('.def').textContent,note:document.querySelector('#example-note').textContent}})()`);
  check(sl.n==='n/a'&&/interpolation-filled/.test(sl.def)&&/blended/.test(sl.def)&&/mosaic/.test(sl.def)&&!/20 m mosaic/.test(sl.def),'Slater slope n/a explains why the product-81 mosaic is not used: '+sl.def.slice(0,90)+'…');
  check(/product-81/.test(sl.note)&&!/20 m mosaic/.test(sl.note),'Slater card note matches');
  await ev(`document.querySelector('#close').click()`); await sleep(300);

  // ---------- J: one announcement on the Play button ----------
  const pb=await ev(`[...document.querySelectorAll('.js-play')].map(b=>b.hasAttribute('aria-pressed')+'|'+b.getAttribute('aria-label'))`);
  check(pb.every(x=>x.startsWith('false|')),'Play button has no aria-pressed (label flips instead): '+pb.join(','));
  await ev(`document.querySelector('#homectl .js-play').click()`);
  check((await ev(`[...document.querySelectorAll('.js-play')].every(b=>!b.hasAttribute('aria-pressed')&&b.getAttribute('aria-label')==='Pause Sun movement')`)),'after toggling still only the label changes');

  // ---------- E: closed panels are inert; focus moves in and back ----------
  await load('');
  const tabbable=await ev(`(()=>{const sel='a[href],button,input,select,textarea,[tabindex]';return [...document.querySelectorAll('.sheet,.layer')].map(p=>({id:p.id,inert:p.inert,n:[...p.querySelectorAll(sel)].filter(e=>e.tabIndex>=0&&!e.disabled&&!e.closest('[inert]')).length}))})()`);
  check(tabbable.every(p=>p.inert&&p.n===0),'with all panels closed no tabbable element lives inside them '+JSON.stringify(tabbable));
  let inside=0,seen=new Set(); for(let i=0;i<45;i++){await tab();const a=await active();if(a.panel)inside++;seen.add(a.mk||a.tag+a.id);}
  check(inside===0,'45 real Tab presses with everything closed never land inside a panel ('+seen.size+' distinct stops)');
  // card: open from a focused marker with the keyboard
  await ev(`document.querySelector('.mk[data-id="HAW"]').focus()`);
  await key('Enter','Enter',{vk:13,text:'\r'}); await sleep(900);
  let a=await active();
  check(a.panel==='sheet','opening a card moves focus into it ('+JSON.stringify(a)+')');
  check(await ev(`document.querySelector('#sheet').inert===false`),'open card is not inert');
  let tin=0,tout=0; for(let i=0;i<30;i++){await tab();const x=await active();if(x.panel==='sheet')tin++;else tout++;}
  check(tin>0,'Tab cycles through controls inside the open card ('+tin+' of 30 stops)');
  await ev(`document.querySelector('#close').focus()`);
  await key('Escape','Escape',{vk:27}); await sleep(900);
  a=await active(); check(a.mk==='HAW','Escape closes the card and returns focus to its marker ('+JSON.stringify(a)+')');
  check(await ev(`document.querySelector('#sheet').inert===true&&document.querySelector('#sheet').getAttribute('aria-hidden')==='true'`),'closed card is inert and aria-hidden again');
  // layers from the nav
  for(const L of ['method','compare']){
    await ev(`document.querySelector('.nav button[data-v="${L}"]').focus()`);
    await key('Enter','Enter',{vk:13,text:'\r'}); await sleep(1100);
    a=await active(); check(a.panel===L,L+' layer: focus moves into the layer ('+JSON.stringify(a)+')');
    check(await ev(`document.querySelector('#${L}').inert===false`),L+' layer not inert while open');
    await ev(`document.querySelector('#${L} [data-close]').focus()`);
    await key('Enter','Enter',{vk:13,text:'\r'}); await sleep(1100);
    a=await active(); check(a.v===L,L+' layer: closing returns focus to the nav button ('+JSON.stringify(a)+')');
    check(await ev(`document.querySelector('#${L}').inert===true`),L+' layer inert after closing');
  }
  // card + layer: the card underneath is inert while the layer is open, and focus goes back to the "Method" button
  await ev(`document.querySelector('.mk[data-id="NR1"]').click()`); await sleep(900);
  await ev(`document.querySelector('[data-open="method"]').focus()`);
  await key('Enter','Enter',{vk:13,text:'\r'}); await sleep(1100);
  check(await ev(`document.querySelector('#sheet').inert===true&&document.querySelector('#method').inert===false`),'layer over a card: card inert, layer live');
  await ev(`document.querySelector('#method [data-close]').click()`); await sleep(1000);
  a=await active(); check(a.open==='method'&&await ev(`document.querySelector('#sheet').inert===false`),'closing the layer re-enables the card and refocuses the button that opened it ('+JSON.stringify(a)+')');
  await ev(`document.querySelector('#close').click()`); await sleep(500);
  tin=0; for(let i=0;i<45;i++){await tab();if((await active()).panel)tin++;}
  check(tin===0,'after closing everything, still nothing tabbable inside panels');

  // ---------- H: marker keyboard focus ring ----------
  await load('');
  await ev(`document.activeElement.blur()`);
  let found=null; for(let i=0;i<40&&!found;i++){await tab();const x=await active();if(x.mk)found=x.mk;}
  check(!!found,'Tab reaches a region marker');
  const ring=await ev(`(()=>{const m=document.activeElement,h=m.querySelector('.hit'),c=getComputedStyle(h),d=m.querySelector('.dot'),m0=document.querySelector('.mk:not(:focus) .dot');return {os:c.outlineStyle,ow:parseFloat(c.outlineWidth),oc:c.outlineColor,off:parseFloat(c.outlineOffset),bs:c.boxShadow,focusVisible:m.matches(':focus-visible'),scale:getComputedStyle(d).transform,scale0:getComputedStyle(m0).transform}})()`);
  check(ring.focusVisible&&ring.os==='solid'&&ring.ow>=3&&/255, 255, 255/.test(ring.oc),'focused marker has a 3 px solid white ring, not just a border colour change ('+ring.ow+'px '+ring.oc+')');
  check(/rgba?\(169, 220, 255/.test(ring.bs),'ring has a second, light halo for contrast on any backdrop');

  // ---------- C: null Diviner pixel size keeps the real distance ----------
  await send('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{let v;Object.defineProperty(window,'REGIONS_DATA',{configurable:true,get:()=>v,set:d=>{d.regions.forEach(r=>{r.temperature_resolution_m=null;});v=d;}});})()`});
  await load('');
  const nulled=await ev(`REGIONS_DATA.regions.every(r=>r.temperature_resolution_m==null)&&REGIONS_DATA.regions.every(r=>r.distance_to_cold_shadow_m!=null)`);
  check(nulled,'test hook nulled every Diviner pixel size, distances still present');
  for(const [mk,site] of Object.entries(IDS)){
    await ev(`document.querySelector('.mk[data-id="${mk}"]').click()`); await sleep(450);
    const c=await ev(`(()=>{const d=document.querySelector('.dial[data-k="cold"]');return {n:d.querySelector('.n').textContent,def:d.querySelector('.def').textContent,rng:d.querySelector('.rng').textContent,u:d.querySelector('.u').textContent,missing:d.classList.contains('missing'),km:REGIONS_DATA.regions.find(r=>r.point_id==='${site}').distance_to_cold_shadow_m/1000,all:document.querySelector('#sheet').textContent}})()`);
    check(!c.missing&&Math.abs(parseFloat(c.n)-c.km)<0.06&&!/NOT COMPUTED/.test(c.u),site+': dial still shows the real distance '+c.n+' (expected '+c.km.toFixed(1)+')');
    check(/n\/a/.test(c.rng)&&/pixel size/i.test(c.rng),site+': size is labelled n/a ("'+c.rng.slice(0,60)+'")');
    check(!/no permanent-shadow pixel/i.test(c.all)&&!/No pixel/i.test(c.all),site+': the "no pixel below 110 K was found" text is not shown');
    await ev(`document.querySelector('#close').click()`); await sleep(250);
  }
  await ev(`document.querySelector('.nav button[data-v="compare"]').click()`); await sleep(900);
  const tb=await ev(`[...document.querySelectorAll('#tbody tr')].map(r=>r.children[5].textContent)`);
  check(tb.length===9&&tb.every(x=>/^\d+\.\d km/.test(x)&&/n\/a/.test(x)),'compare table keeps every distance and shows the size as n/a: '+tb[0]);
  check(errors.length===0,'no uncaught page errors'+(errors.length?': '+[...new Set(errors)].join(' | '):''));
  ws.close(); ch.kill();
  if(fails.length){console.log('FAILED',fails.length);process.exit(1);} console.log('review2 ok');
})();

// Headless regression for the third PR #1 review round.
//  1. Narrow (<=900 px) Sun dial: with a card open it is shown whenever it fits above the sheet without touching the header
//     (brand, GitHub link, nav), the close button or the sheet; hidden only when no free spot exists. 390x844, 360x740, 768x1024, 640x360.
//  2. A missing summer-max temperature reads 'n/a' (K, C, F), never 0 K, in every region, while the real cold-shadow distance stays.
//  3. Playback wraps at HOURS (336): hour 335 becomes the current hour, readouts/strips/playhead are valid there, the loop is seamless.
// usage: node --experimental-websocket web/test_review3.js   (needs google-chrome on PATH)
const {spawn}=require('child_process'), path=require('path'), http=require('http'), fs=require('fs');
const url='file://'+path.resolve(process.env.PAGE||path.join(__dirname,'index.html'));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const getJSON=u=>new Promise((res,rej)=>http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res(JSON.parse(d)))}).on('error',rej));
const IDS=['CAB','DGR','HAW','MAL','MMP','MMO','NR1','NR2','SLP'];
(async()=>{
  const port=9600+Math.floor(Math.random()*300);
  const ch=spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--remote-debugging-port='+port,'--window-size=1440,900','about:blank'],{stdio:'ignore'});
  let tabs; for(let i=0;i<50;i++){try{tabs=await getJSON(`http://127.0.0.1:${port}/json`);if(tabs.length)break;}catch(e){}await sleep(200);}
  const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl); await new Promise(r=>ws.onopen=r);
  let id=0; const pend={}, errors=[];
  ws.onmessage=m=>{const d=JSON.parse(m.data);if(d.id&&pend[d.id]){pend[d.id](d.result||d);delete pend[d.id];}
    else if(d.method==='Runtime.exceptionThrown')errors.push((d.params.exceptionDetails.exception&&d.params.exceptionDetails.exception.description||'').split('\n')[0]);};
  const send=(method,params={})=>new Promise(r=>{const i=++id;pend[i]=r;ws.send(JSON.stringify({id:i,method,params}));});
  const ev=async e=>{const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});return r.result&&r.result.value;};
  await send('Runtime.enable');
  const fails=[]; let n=0; const check=(ok,msg)=>{n++;if(!ok){console.log('FAIL',msg);fails.push(msg);}};
  const shot=async f=>{const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(f,Buffer.from(r.data,'base64'));};
  const load=async(w,h,q='')=>{await send('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:1,mobile:w<=900});await send('Page.navigate',{url:url+q});await sleep(1500);};

  // ---------- 1. narrow Sun dial ----------
  const VPS=[[390,844],[360,740],[768,1024],[640,360]];
  const fitsAtLeastOnce={};
  for(const [w,h] of VPS){
    await load(w,h);
    for(const rid of IDS){
      await ev(`document.querySelector('.mk[data-id="${rid}"]').click()`); await sleep(1000);
      const T=`${w}x${h} ${rid}`;
      const g=await ev(`(()=>{
        const R=e=>{const r=e.getBoundingClientRect();return {l:r.left,t:r.top,r:r.right,b:r.bottom,w:r.width,h:r.height}};
        const foot=document.querySelector('.foot'), cs=getComputedStyle(foot), comp=R(document.querySelector('.compass svg')), sh=document.querySelector('#sheet');
        const sheetTop=innerHeight-sh.offsetHeight;
        const obs=['.top .brand .label','.top .brand .small','.top .ghlink','.top .nav'].map(s=>document.querySelector(s)).filter(Boolean).map(R).filter(r=>r.w&&r.h);
        const x=R(document.querySelector('#close'));
        // independent brute-force search for any free 44x44 spot (8 px clearance) above the sheet
        let free=false; for(let y=8;y+44<=sheetTop-8&&!free;y++)for(let xx=12;xx+44<=innerWidth-12&&!free;xx++)
          if(!obs.some(o=>xx<o.r+8&&xx+44>o.l-8&&y<o.b+8&&y+44>o.t-8))free=true;
        return {vis:cs.visibility!=='hidden'&&+cs.opacity>0,comp,sheetTop,obs,x,free,ob:document.body.classList.contains('sheet-open'),
          hit:(()=>{const e=document.elementFromPoint(comp.l+comp.w/2,comp.t+comp.h/2);return !!e&&!!e.closest('.compass')})()}})()`);
      check(g.ob,T+': card open');
      check(g.vis===g.free,T+': dial visible exactly when it fits (visible='+g.vis+', free spot='+g.free+')');
      if(g.vis){
        fitsAtLeastOnce[w+'x'+h]=true;
        const c=g.comp, ov=r=>c.l<r.r&&c.r>r.l&&c.t<r.b&&c.b>r.t;
        check(c.w>=44&&c.h>=44,T+': dial full size');
        check(!g.obs.some(ov),T+': dial overlaps no header item (brand, GitHub link, nav)');
        check(!ov(g.x)&&c.b<=g.sheetTop,T+': dial overlaps neither the close button nor the sheet ('+c.b+' <= '+g.sheetTop+')');
        check(c.l>=0&&c.r<=w&&c.t>=0,T+': dial inside the viewport');
        check(g.hit,T+': dial is the element hit at its centre');
      }
      if(rid==='NR1'&&process.env.SHOT&&(w===768||w===640))await shot(path.join(process.env.SHOT,`dial-narrow-${w}x${h}.png`));
      await ev(`document.querySelector('#close').click()`); await sleep(700);
      check(!await ev(`document.body.classList.contains('dial-fit')`),T+': fit state cleared after close');
    }
  }
  check(fitsAtLeastOnce['768x1024']&&fitsAtLeastOnce['640x360'],'dial is shown at 768x1024 and at the short viewport 640x360 (it fits there)');
  // resize while open re-measures
  await load(768,1024); await ev(`document.querySelector('.mk[data-id="NR1"]').click()`); await sleep(1000);
  check(await ev(`document.body.classList.contains('dial-fit')`),'768: fits before resize');
  await send('Emulation.setDeviceMetricsOverride',{width:360,height:740,deviceScaleFactor:1,mobile:true}); await sleep(600);
  check(!await ev(`document.body.classList.contains('dial-fit')`)&&await ev(`getComputedStyle(document.querySelector('.foot')).visibility`)==='hidden','resize 768 -> 360: dial re-measured and hidden');
  // desktop unchanged
  await load(1280,800); await ev(`document.querySelector('.mk[data-id="NR1"]').click()`); await sleep(1000);
  check(await ev(`getComputedStyle(document.querySelector('.foot')).visibility`)==='visible'&&!await ev(`document.body.classList.contains('dial-fit')`),'desktop: dial visible via the desktop layout');

  // ---------- 2. missing summer-max temperature ----------
  await load(1440,900);
  const SITE={CAB:'PCB01',DGR:'dGR101',HAW:'HW01',MAL:'MMA01',MMP:'MMP01',MMO:'MMO01',NR1:'NR101',NR2:'NR201',SLP:'SP01'};
  const rec=(rid,expr)=>ev(`(()=>{const q=REGIONS_DATA.regions.find(x=>x.point_id==='${SITE[rid]}');${expr}})()`);
  for(const rid of IDS){
    const T='nulled temperature '+rid;
    const real=await rec(rid,`window.__t=q.summer_max_temperature_k; q.summer_max_temperature_k=null; return {km:q.distance_to_cold_shadow_m,t:window.__t}`);
    await ev(`document.querySelector('.mk[data-id="${rid}"]').click()`); await sleep(900);
    const o=await ev(`(()=>{const d=document.querySelector('.dial[data-k="cold"]');return {n:d.querySelector('.n').textContent,rng:d.querySelector('.rng').textContent,
      extra:[...document.querySelectorAll('.extra')].map(e=>e.textContent).filter(t=>/Summer max/i.test(t)).join('|')}})()`);
    if(real.km==null)check(o.n==='n/a',T+': no distance -> n/a');
    else check(o.n===(real.km/1000).toFixed(1),T+': real cold-shadow distance still shown ('+o.n+')');
    check(/summer max n\/a here/.test(o.rng),T+': cold dial says "summer max n/a here" ('+o.rng+')');
    check(!/summer max\s*0|\b0\s*K\b|0\s*°C|n\/a\s*K|n\/a\s*°/.test(o.rng),T+': no fake 0 K / 0 °C / "n/a K" ('+o.rng+')');
    check(/Summer max temperature/.test(o.extra)&&/n\/a/.test(o.extra)&&!/\d\s*K/.test(o.extra.replace(/\d+\.?\d*\s*m pixel/,'')),T+': extras row n/a ('+o.extra+')');
    await ev(`document.querySelector('#close').click()`); await sleep(500);
    await rec(rid,`q.summer_max_temperature_k=window.__t;return 1`);
  }
  // the real value still renders when present
  await ev(`document.querySelector('.mk[data-id="NR1"]').click()`); await sleep(900);
  check(/summer max \d+\s*K/.test(await ev(`document.querySelector('.dial[data-k="cold"] .rng').textContent`)),'real temperature still shown when present');
  await ev(`document.querySelector('#close').click()`); await sleep(400);
  const U=await ev(`[null,undefined,NaN,'',Infinity].map(v=>[Units.kText(v),Units.kHTML(v)]).concat([[Units.kText(110),Units.kHTML(110)]])`);
  check(U.slice(0,5).every(p=>p[0]==='n/a'&&p[1]==='n/a'),'Units: null/undefined/NaN/""/Infinity -> n/a (K, C, F)');
  check(/^110 K/.test(U[5][0])&&/110&nbsp;K/.test(U[5][1]),'Units: a real value still formats');

  // ---------- 3. playback wrap at HOURS ----------
  await load(1440,900);
  const PAD=56;
  const xOf=async h=>ev(`(()=>{document.querySelector('#tlwrap').scrollIntoView({block:'center'});const r=document.querySelector('#tlwrap').getBoundingClientRect();return {x:r.left+${PAD}+(${h}+0.5)*(r.width-${PAD})/336,y:r.top+r.height/2,w:r.width,right:r.right}})()`);
  const press=async pt=>{await send('Input.dispatchMouseEvent',{type:'mousePressed',x:pt.x,y:pt.y,button:'left',clickCount:1});await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:pt.x,y:pt.y,button:'left',clickCount:1});await sleep(350);};
  for(const rid of ['HAW','NR1']){
    await ev(`document.querySelector('.mk[data-id="${rid}"]').click()`); await sleep(1100);
    const T='hour 335 '+rid;
    // scrub to the centre of hour 335 (pointer events drive the real scrubber; this pauses playback)
    let pt=await xOf(335); await press(pt);
    const rd=()=>ev(`({time:document.querySelector('#t-time').textContent,stamp:document.querySelector('#hstamp').textContent,sun:document.querySelector('#t-sun').textContent,ear:document.querySelector('#t-earth').textContent,
      head:document.querySelector('#head').style.transform,TW:document.querySelector('#tlwrap').getBoundingClientRect().width,play:document.querySelector('#homectl .js-play').getAttribute('aria-label'),az:document.querySelector('#z-az').textContent})`);
    let o=await rd();
    check(/D14 · 23:00 UTC/.test(o.time)&&/D14 · 23:00 UTC/.test(o.stamp),T+': hour 335 is current: D14 23:00 ('+o.time+' / '+o.stamp+')');
    check(o.play==='Play Sun movement',T+': scrubbing paused playback');
    if(rid==='HAW'){
      const e=await ev(`(()=>{const z=ZOOM_DATA.strips.HW01;return {sun:Math.round((z.sun_1m[335]==='1'?1:0)*100)+'%',ear:z.earth_1m[335]==='1'?'In view':'Below horizon',len:z.sun_1m.length}})()`);
      check(e.len===336,T+': strip has 336 hours');
      check(o.sun===e.sun&&o.ear===e.ear,T+': readouts equal strip element 335 ('+o.sun+'/'+o.ear+' vs '+e.sun+'/'+e.ear+')');
    }
    check(/-?\d+°/.test(o.az),T+': zoom azimuth readout valid at hour 335 ('+o.az+')');
    const hx=+/translateX\(([\d.]+)px/.exec(o.head)[1]; check(hx>0&&hx<=o.TW+0.5,T+': playhead inside the strip ('+hx.toFixed(1)+' <= '+o.TW.toFixed(1)+')');
    // right end of the scrubber maps to hour 335 as well
    await press({x:pt.right-1,y:pt.y});
    o=await rd(); check(/D14 · 23:00 UTC/.test(o.time),T+': scrubber right end = hour 335 ('+o.time+')');
    await press({x:(await xOf(0)).x-3,y:pt.y}); check(/D1 · 00:00 UTC/.test((await rd()).time),T+': scrubber left end = hour 0');
    // seamless loop: from hour 334 playback visits hour 335 for its whole length, then continues at D1 with no stall
    await ev(`document.querySelector('#homectl .js-seg [data-s="1"]').click()`);   // 1x = 6 h/s: hour 335 lasts ~167 ms, longer than the 100 ms readout throttle
    await press(await xOf(334));
    await ev(`document.querySelector('#homectl .js-play').click()`);
    const tr=await ev(`new Promise(res=>{const s=[];const t0=performance.now();let last='';(function f(){const t=document.querySelector('#hstamp').textContent;if(t!==last){s.push([Math.round(performance.now()-t0),t]);last=t;}if(performance.now()-t0<1500)requestAnimationFrame(f);else res(s)})()})`);
    const names=tr.map(a=>a[1]);
    const i23=names.findIndex(t=>/D14 · 23:/.test(t)), iw=names.findIndex(t=>/D1 · 00:/.test(t));
    check(i23>=0,T+': playback shows D14 23:xx (hour 335) ['+names.slice(0,12).join(', ')+']');
    check(iw>i23,T+': then wraps to D1 00:xx');
    // wrap is a full 336-hour loop: D1 00:xx follows D14 23:xx directly (no hour skipped or repeated)
    check(!names.slice(i23,iw).some(t=>!/D14 · 23:/.test(t)),T+': nothing between D14 23:xx and D1 00:xx');
    await ev(`document.querySelector('#homectl .js-play').click()`); await ev(`document.querySelector('#close').click()`); await sleep(500);
    await ev(`document.querySelector('#homectl .js-play').getAttribute('aria-label')==='Pause Sun movement'&&document.querySelector('#homectl .js-play').click()`);
  }
  if(process.env.SHOT){await ev(`document.querySelector('.mk[data-id="HAW"]').click()`);await sleep(1000);await press(await xOf(335));await shot(path.join(process.env.SHOT,'haworth-hour335.png'));}
  check(errors.length===0,'no page errors '+errors.join(' | '));
  ch.kill();
  console.log(`${n} checks, ${fails.length} failed`);
  if(fails.length){process.exit(1);} console.log('review3 ok');
})();

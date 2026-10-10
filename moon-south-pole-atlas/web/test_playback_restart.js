// Headless regression: opening/closing region cards (click, Escape, hash, back, layers) must never stop the Sun clock;
// Pause then Play on Home must always work; paused / reduced-motion states are respected.
// usage: node --experimental-websocket web/test_playback_restart.js   (needs google-chrome on PATH)
const {spawn}=require('child_process'), path=require('path'), http=require('http');
const base='file://'+path.resolve(process.env.PAGE||path.join(__dirname,'index.html'));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const getJSON=u=>new Promise((res,rej)=>http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res(JSON.parse(d)))}).on('error',rej));
(async()=>{
  const port=9800+Math.floor(Math.random()*500);
  const ch=spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--remote-debugging-port='+port,'--window-size=1440,900','about:blank'],{stdio:'ignore'});
  let tabs; for(let i=0;i<50;i++){try{tabs=await getJSON(`http://127.0.0.1:${port}/json`);if(tabs.length)break;}catch(e){}await sleep(200);}
  const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl); await new Promise(r=>ws.onopen=r);
  let id=0; const pend={}, errors=[];
  ws.onmessage=m=>{const d=JSON.parse(m.data);if(d.id&&pend[d.id]){pend[d.id](d.result||d);delete pend[d.id];}
    else if(d.method==='Runtime.exceptionThrown')errors.push((d.params.exceptionDetails.exception&&d.params.exceptionDetails.exception.description||'').split('\n')[0]);};
  const send=(method,params={})=>new Promise(r=>{const i=++id;pend[i]=r;ws.send(JSON.stringify({id:i,method,params}));});
  const ev=async e=>{const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});return r.result&&r.result.value;};
  await send('Runtime.enable');
  const fails=[]; const check=(ok,msg)=>{console.log(ok?'ok  ':'FAIL',msg);if(!ok)fails.push(msg);};
  const stamp=()=>ev(`document.querySelector('#hstamp').textContent`);
  const label=()=>ev(`document.querySelector('#homectl .js-play').getAttribute('aria-label')`);
  const click=s=>ev(`document.querySelector(${JSON.stringify(s)}).click()`);
  const advancing=async()=>{const a=await stamp();await sleep(600);return a!==await stamp();};
  const frozen=async()=>{const a=await stamp();await sleep(600);return a===await stamp();};
  async function load(hash,reduced){
    await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:reduced?'reduce':'no-preference'}]});
    await send('Page.navigate',{url:'about:blank'}); await sleep(200); await send('Page.navigate',{url:base+hash}); await sleep(1800);
  }
  async function homeToggle(tag){   // Pause then Play on Home
    await click('#homectl .js-play'); await sleep(150);
    check(await label()==='Play Sun movement'&&await frozen(),tag+': Pause freezes the Sun, button says Play');
    await click('#homectl .js-play'); await sleep(150);
    check(await label()==='Pause Sun movement'&&await advancing(),tag+': Play restarts the Sun, button says Pause');
  }

  await load('',false);
  check(await advancing(),'autoplay advances on load');
  const openClose=[
    ['click open/close card',async()=>{await click('.mk[data-id="NR1"]');await sleep(500);await click('#close');}],
    ['Escape closes card',async()=>{await click('.mk[data-id="HAW"]');await sleep(500);await ev(`dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}))`);}],
    ['card without hourly strip',async()=>{const ids=await ev(`[...document.querySelectorAll('.mk')].map(m=>m.dataset.id)`);for(const i of ids){await click(`.mk[data-id="${i}"]`);await sleep(250);await click('#close');}}],
    ['hash deep link then close',async()=>{await ev(`location.hash='#region/NR1';`);await sleep(100);await click('.mk[data-id="NR1"]');await sleep(400);await click('#close');}],
    ['method + compare layers and back',async()=>{await click('.mk[data-id="NR1"]');await click('[data-open="method"]');await sleep(300);await ev(`document.querySelector('#method [data-close]').click()`);await click('[data-open="compare"]');await sleep(300);await ev(`document.querySelector('#compare [data-close]').click()`);await click('#close');await ev(`history.back()`);await sleep(200);}],
  ];
  for(let round=1;round<=3;round++)for(const [name,fn] of openClose){
    await fn(); await sleep(250);
    check(await advancing(),`round ${round}: Sun still advances after "${name}"`);
  }
  await homeToggle('after open/close cycles');
  // card open while playing: shared state kept, then closed
  await click('.mk[data-id="NR1"]'); await sleep(500);
  check(await label()==='Pause Sun movement'&&await advancing(),'card open: shared play state still playing');
  await click('#close'); await sleep(200);
  await homeToggle('after card close');
  // paused state is preserved across open/close
  await click('#homectl .js-play'); await sleep(150);
  await click('.mk[data-id="HAW"]'); await sleep(500); await click('#close'); await sleep(300);
  check(await label()==='Play Sun movement'&&await frozen(),'paused stays paused across open/close');
  await click('#homectl .js-play'); await sleep(150);
  check(await advancing(),'Play after paused open/close works');
  // deep links: paused and reduced motion
  await load('#?paused',false);
  check(await label()==='Play Sun movement'&&await frozen(),'#?paused starts paused');
  await click('.mk[data-id="NR1"]'); await sleep(400); await click('#close');
  await click('#homectl .js-play'); await sleep(150);
  check(await advancing(),'paused deep link: Play works after open/close');
  await load('',true);
  check(await label()==='Play Sun movement'&&await frozen(),'reduced motion starts paused');
  await click('.mk[data-id="NR1"]'); await sleep(400); await click('#close'); await sleep(200);
  check(await frozen(),'reduced motion stays paused after open/close');
  await click('#homectl .js-play'); await sleep(150);
  check(await advancing(),'reduced motion: explicit Play works');
  await load('#region/NR1',false);
  check(await advancing(),'#region/NR1 deep link plays');
  await click('#close'); await sleep(250);
  check(await advancing(),'deep-linked card closed: Sun still advances');
  await homeToggle('deep-link');
  // hidden tab: the loop stops (no rAF, no redraw), the clock does not run or jump, and everything resumes on return
  await send('Page.enable');
  await send('Page.addScriptToEvaluateOnNewDocument',{source:`window.__raf=0;const o=window.requestAnimationFrame.bind(window);window.requestAnimationFrame=f=>{window.__raf++;return o(f)};`});
  await load('#?h=100',false);
  await click('#homectl .js-seg button[data-s="1"]'); await sleep(200);
  const mins=async()=>{const m=(await stamp()).match(/D(\d+) · (\d+):(\d+)/);return ((+m[1])*24+(+m[2]))*60+(+m[3]);};
  check(await advancing(),'(visibility) playing at 1x before hiding');
  const m0=await mins();
  await ev(`Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))`);
  await sleep(300); const r0=await ev(`window.__raf`); await sleep(1500); const r1=await ev(`window.__raf`);
  check(r1===r0,'hidden tab: no requestAnimationFrame callbacks are scheduled ('+(r1-r0)+' in 1.5 s)');
  const m1=await mins(); check(Math.abs(m1-m0)<=45,'hidden tab: simulated clock stands still ('+(m1-m0)+' min)');
  await ev(`delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))`);
  await sleep(120); const m2=await mins();
  check(m2-m1>=0&&m2-m1<=90,'return to the tab: clock resumes without a jump ('+(m2-m1)+' min after 120 ms)');
  check(await advancing(),'return to the tab: Sun advances again');
  const r2=await ev(`window.__raf`); await sleep(500); check(await ev(`window.__raf`)>r2,'return to the tab: frame loop running again');
  check(errors.length===0,'no uncaught page errors'+(errors.length?': '+[...new Set(errors)].join(' | '):''));
  ws.close(); ch.kill();
  if(fails.length){console.log('FAILED',fails.length);process.exit(1);} console.log('playback restart ok');
})();

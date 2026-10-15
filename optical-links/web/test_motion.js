// Clock and motion checks with a simulated requestAnimationFrame (60 Hz and 120 Hz, no real waiting):
//  - real-time light: after N simulated seconds the page clock reads N s at either refresh rate (30 fps cap kept)
//  - speed change never teleports an orbit; afterwards phase advances at the new rate
//  - the Mars pulse accumulator is monotonic with smooth steps (no jitter from a changing screen duration)
//  - link / speed clicks redraw while paused; Escape does nothing when the panel is closed and closes it when open
//  - hash forms #scene=mars, #?scene=mars, #scene=conj&link=direct&paused
//  - hidden tab pauses the clock; prefers-reduced-motion starts paused
// usage: node --experimental-websocket web/test_motion.js   (OPTICAL_FILE=other.html to point at another copy)
const path=require('path'),assert=require('assert'),{launch,sleep}=require('../../space-weather/web/cdp.js');
const FILE='file://'+path.resolve(__dirname,process.env.OPTICAL_FILE||'index.html');
let n=0; const ok=(c,m)=>{n++;assert.ok(c,m);console.log('ok',m)};
const FAKE=`(()=>{let q=new Map(),id=0,now=1000;window.requestAnimationFrame=cb=>{q.set(++id,cb);return id};window.cancelAnimationFrame=i=>q.delete(i);
  window.__pump=(hz,sec)=>{const k=Math.round(hz*sec);for(let i=0;i<k;i++){now+=1000/hz;const c=[...q.values()];q.clear();c.forEach(f=>f(now));}return now};})()`;
const key=async(b,k)=>{await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:k,code:k,windowsVirtualKeyCode:27});await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:k,code:k,windowsVirtualKeyCode:27});};
(async()=>{
  const b=await launch(); const errs=[]; b.on(d=>{if(d.method==='Runtime.exceptionThrown')errs.push(JSON.stringify(d.params.exceptionDetails).slice(0,300));});
  await b.viewport(1440,900);
  const {identifier}=await b.send('Page.addScriptToEvaluateOnNewDocument',{source:FAKE});
  try{
    // ---- clock accuracy at 60 and 120 Hz
    for(const hz of [60,120]){
      await b.goto('about:blank',100); await b.goto(FILE+'#scene=moon',700);
      const t0=await b.ev('__opt.time()'), d0=await b.ev('__opt.draws?__opt.draws():0');
      await b.ev(`__pump(${hz},10)`);
      const t1=await b.ev('__opt.time()'), d1=await b.ev('__opt.draws?__opt.draws():0');
      const el=t1-t0;
      ok(Math.abs(el-10)<0.1,hz+' Hz: 10.00 s of frames advances the light clock '+el.toFixed(3)+' s');
      if(d1)ok(d1-d0>=290&&d1-d0<=305,hz+' Hz: 30 fps cap kept, '+(d1-d0)+' draws in 10 s');
    }
    // ---- no teleport on speed change
    await b.goto('about:blank',100); await b.goto(FILE+'#scene=mars',700);
    await b.ev('__pump(60,1)');
    const p0=await b.ev('__opt.phases()'); await b.ev(`document.querySelector('#speeds [data-s="4"]').click()`); const p1=await b.ev('__opt.phases()');
    const jump=Math.max(...Object.keys(p0).map(k=>Math.abs(p1[k]-p0[k])));
    ok(jump<1e-9,'clicking 4× does not move any orbit (max jump '+jump.toExponential(2)+' rad)');
    await b.ev('__pump(60,1)'); const p2=await b.ev('__opt.phases()');
    const rate=(p2.earth-p1.earth)/1;
    ok(Math.abs(rate-0.12*4)<0.02,'after 4×, Earth advances '+rate.toFixed(3)+' rad/s = 4 × 0.12');
    await b.ev(`document.querySelector('#speeds [data-s="1"]').click()`); const p3=await b.ev('__opt.phases()');
    ok(Math.abs(p3.earth-p2.earth)<1e-9,'back to 1×: no jump either');
    // ---- Mars pulse accumulator: monotonic, smooth
    const s=await b.ev(`(()=>{const a=[];for(let i=0;i<240;i++){__pump(60,1/60);a.push(__opt.pulse());}return a})()`);
    const st=s.slice(1).map((v,i)=>v-s[i]), pos=st.filter(x=>x>0);
    ok(st.every(x=>x>=0),'Mars pulse phase never goes backwards over 240 frames');
    const big=pos.map((x,i)=>i?Math.abs(x/pos[i-1]-1):0).reduce((a,c)=>Math.max(a,c),0);
    ok(pos.length>=110&&big<0.02,'Mars pulse steps are even: '+pos.length+' moves, max step-to-step change '+(big*100).toFixed(2)+'%');
    // ---- redraw on click while paused
    await b.goto('about:blank',100); await b.goto(FILE+'#scene=moon&paused',700);
    ok(!(await b.ev('__opt.playing()')),'#paused starts paused');
    const img=()=>b.ev(`(()=>{const c=document.querySelector('#hero'),d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let h=0;for(let i=0;i<d.length;i+=97)h=(h*31+d[i])>>>0;return h})()`);
    const h0=await img(); await b.ev(`document.querySelector('#links [data-link="l2"]').click()`); const h1=await img();
    ok(h0!==h1,'link click while paused repaints the canvas');
    const d2=await b.ev('__opt.draws()'); await b.ev(`document.querySelector('#speeds [data-s="2"]').click()`); const d3=await b.ev('__opt.draws()');
    ok(d3>d2&&/Orbits 2×/.test(await b.ev(`document.querySelector('#ruler-k').textContent`)),'speed click while paused redraws and updates the label');
    // ---- Escape only when open
    const d4=await b.ev('__opt.draws()'); await key(b,'Escape'); await sleep(50); const d5=await b.ev('__opt.draws()');
    ok(d5===d4,'Escape with the panel closed does nothing');
    await b.ev(`document.querySelector('#nav-method').focus();document.querySelector('#nav-method').click()`); await sleep(300);
    ok(await b.ev(`document.querySelector('#method').classList.contains('open')`),'method opens');
    await key(b,'Escape'); await sleep(300);
    ok(await b.ev(`!document.querySelector('#method').classList.contains('open')&&document.activeElement.id==='nav-method'`),'Escape closes the open panel and returns focus');
    // ---- hash forms
    for(const [h,sc,link,paused] of [['#scene=mars','mars','trunk',false],['#?scene=mars','mars','trunk',false],['#scene=conj&link=direct&paused','conj','direct',true],['#?scene=mesh&paused','mesh','neighbour',true],['#scene=nope','moon','direct',false]]){
      await b.goto('about:blank',100); await b.goto(FILE+h,600);
      const r=await b.ev(`({s:document.querySelector('#scenes button.on').dataset.scene,l:document.querySelector('#links button.on').dataset.link,p:document.querySelector('#play').getAttribute('aria-label')})`);
      ok(r.s===sc&&r.l===link&&(r.p==='Play')===paused,h+' -> scene '+r.s+', link '+r.l+', '+r.p);
    }
    // ---- hidden tab pauses
    await b.goto('about:blank',100); await b.goto(FILE+'#scene=moon',600);
    await b.send('Emulation.setFocusEmulationEnabled',{enabled:false});
    await b.ev(`Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))`);
    const h2=await b.ev('__opt.time()'); await b.ev('__pump(60,2)'); const h3=await b.ev('__opt.time()');
    ok(h3===h2,'hidden tab: clock does not advance');
    await b.ev(`Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))`);
    await b.ev('__pump(60,2)'); const h4=await b.ev('__opt.time()');
    ok(h4-h3>1.9&&h4-h3<2.05,'visible again: resumes without a jump ('+(h4-h3).toFixed(3)+' s for 2 s)');
    // ---- reduced motion
    await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
    await b.goto('about:blank',100); await b.goto(FILE+'#scene=mars',600);
    const r0=await b.ev('__opt.time()'); await b.ev('__pump(60,2)');
    ok(!(await b.ev('__opt.playing()'))&&await b.ev('__opt.time()')===r0,'prefers-reduced-motion: starts paused, nothing animates');
    await b.ev(`document.querySelector('#scenes [data-scene="conj"]').click()`);
    ok(await b.ev(`document.querySelector('#r-km').textContent`)==='3.73 AU','reduced motion: scene change lands without a tween');
    await b.send('Emulation.setEmulatedMedia',{features:[]});
    ok(!errs.length,'no exceptions '+errs.join(' | '));
  }finally{await b.send('Page.removeScriptToEvaluateOnNewDocument',{identifier}); b.close();}
  console.log('motion ok',n,'checks');
})().catch(e=>{console.error(e.message);process.exit(1)});

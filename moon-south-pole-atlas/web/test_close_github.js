// Headless regression for the close controls and the GitHub link.
//  - X close button is top right (>=44x44, inside the panel's top-right corner, not overlapping header content),
//    stays put while the card is scrolled, in every region card, the method layer and the compare layer, at 1440/390/360 px
//  - the top handle (role=button, aria-label, tabindex) is >=44 px tall, full panel width and closes on click, Enter and Space
//  - GitHub link: correct href/target/rel, inline SVG, visible on the home screen without colliding with other controls, also in the method layer
//  - Sun keeps running after closing via X and via handle
// usage: node --experimental-websocket web/test_close_github.js   (needs google-chrome on PATH)
const {spawn}=require('child_process'), path=require('path'), http=require('http'), fs=require('fs');
const url='file://'+path.resolve(process.env.PAGE||path.join(__dirname,'index.html'));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const getJSON=u=>new Promise((res,rej)=>http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res(JSON.parse(d)))}).on('error',rej));
const WIDTHS=[1440,390,360], IDS=['CAB','DGR','HAW','MAL','MMP','MMO','NR1','NR2','SLP'];
(async()=>{
  const port=9100+Math.floor(Math.random()*500);
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
  // geometry of the X inside root, relative to its panel
  const geo=(root,xsel)=>ev(`(()=>{const R=document.querySelector(${JSON.stringify(root)}),p=R.querySelector('.panel'),x=R.querySelector(${JSON.stringify(xsel)});
    const pr=p.getBoundingClientRect(),xr=x.getBoundingClientRect(),g=R.querySelector('.grab').getBoundingClientRect(),vw=innerWidth;
    const ov=[...p.querySelectorAll('h2,.label,.meta,.head-r .btn,.btn,.lh *')].filter(e=>e!==x&&!e.closest('.xwrap')&&e.getClientRects().length).filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.height&&r.left<xr.right&&r.right>xr.left&&r.top<xr.bottom&&r.bottom>xr.top}).map(e=>e.tagName+'.'+e.className);
    return {w:xr.width,h:xr.height,top:xr.top-pr.top,right:pr.right-xr.right,left:xr.left,vw,pw:pr.width,gh:g.height,gw:g.width,gl:g.left-pr.left,ov,vis:getComputedStyle(x).visibility,xt:xr.top,xb:xr.bottom,ptop:pr.top,
      hit:(()=>{const e=document.elementFromPoint(xr.left+xr.width/2,xr.top+xr.height/2);return e===x||x.contains(e)})()}})()`);
  const okGeo=(g,tag,scrolled)=>{
    check(g.w>=44&&g.h>=44,tag+': X is at least 44x44 ('+g.w+'x'+g.h+')');
    check(g.top>=0&&g.top<=24,tag+': X sits at the top of the panel (top offset '+Math.round(g.top)+')');
    check(g.right>=0&&g.right<=40,   // 10 px inset + up to ~16 px classic scrollbar
    tag+': X sits at the right edge (right offset '+Math.round(g.right)+')');
    check(g.xb<=g.ptop+g.h+30&&g.left+g.w<=g.vw+0.5,tag+': X fully inside the viewport');
    if(!scrolled)check(g.ov.length===0,tag+': X overlaps no header content '+g.ov.join(','));
    check(g.hit,tag+': X is the element hit at its centre (not covered)');
  };
  for(const w of WIDTHS){
    await send('Emulation.setDeviceMetricsOverride',{width:w,height:800,deviceScaleFactor:1,mobile:w<=430});
    await send('Page.navigate',{url}); await sleep(1500);
    const T=w+'px';
    // --- GitHub link on home
    const gh=await ev(`(()=>{const a=document.querySelector('.top .js-gh');const r=a.getBoundingClientRect();
      const others=[...document.querySelectorAll('.nav,#homectl,.play,.foot .chip,.compass,.brand .label')].map(e=>e.getBoundingClientRect());
      const hit=others.some(o=>r.left<o.right&&r.right>o.left&&r.top<o.bottom&&r.bottom>o.top);
      return {href:a.href,target:a.target,rel:a.rel,svg:!!a.querySelector('svg'),ext:/<(img|link|script)[^>]+src|url\\(http/.test(a.outerHTML),txt:a.textContent.trim(),inView:r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight,hit,h:r.height,vis:getComputedStyle(a).visibility}})()`);
    check(gh.href==='https://github.com/sighmon/space',T+': GitHub href '+gh.href);
    check(gh.target==='_blank',T+': GitHub target _blank');
    check(/\bnoopener\b/.test(gh.rel)&&/\bnoreferrer\b/.test(gh.rel),T+': GitHub rel noopener noreferrer ('+gh.rel+')');
    check(gh.svg&&!gh.ext,T+': inline SVG icon, no external resources');
    check(gh.txt==='View on GitHub',T+': link text');
    check(gh.inView&&!gh.hit,T+': GitHub link visible, no collision with nav/play/chip/compass/brand ('+JSON.stringify(gh)+')');
    if(process.env.SHOT&&w===1440||process.env.SHOT&&w===390)await shot(path.join(process.env.SHOT,`home-github-${w}.png`));
    // --- cards
    for(const rid of IDS){
      await ev(`document.querySelector('.mk[data-id="${rid}"]').click()`); await sleep(1000);
      const tag=T+' card '+rid;
      okGeo(await geo('#sheet','#close'),tag);
      // scrolled: X stays in the same place
      await ev(`(()=>{const p=document.querySelector('#sheet .panel');p.scrollTop=p.scrollHeight})()`); await sleep(250);
      const sc=await ev(`document.querySelector('#sheet .panel').scrollTop`);
      const g2=await geo('#sheet','#close'); okGeo(g2,tag+' scrolled',1);
      if(rid==='NR1'&&process.env.SHOT&&(w===390||w===1440))await shot(path.join(process.env.SHOT,`card-close-scrolled-${w}.png`));
      await ev(`document.querySelector('#sheet .panel').scrollTop=0`); await sleep(150);
      const h=await geo('#sheet','#close'); check(Math.abs(h.xt-g2.xt)<1.5,tag+': X identical position at top and scrolled');
      const gr=await ev(`(()=>{const g=document.querySelector('#sheet .grab'),p=document.querySelector('#sheet .panel'),r=g.getBoundingClientRect(),pr=p.getBoundingClientRect();return {role:g.getAttribute('role'),al:g.getAttribute('aria-label'),ti:g.tabIndex,h:r.height,w:r.width,pw:pr.width-2}})()`);
      check(gr.role==='button'&&!!gr.al&&gr.ti===0,tag+': handle has role=button, aria-label, tabindex');
      check(gr.h>=44,tag+': handle >= 44 px tall');
      check(gr.w>=gr.pw-100,tag+': handle spans the panel width');
      // handle tap closes (real mouse click at handle's left third, away from the X)
      const pt=await ev(`(()=>{const r=document.querySelector('#sheet .grab').getBoundingClientRect();return {x:r.left+r.width*0.3,y:r.top+r.height/2}})()`);
      await send('Input.dispatchMouseEvent',{type:'mousePressed',x:pt.x,y:pt.y,button:'left',clickCount:1});await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:pt.x,y:pt.y,button:'left',clickCount:1});
      await sleep(400);
      check(!await ev(`document.querySelector('#sheet').classList.contains('open')`),tag+': handle tap closes the card');
      await sleep(500);
    }
    // keyboard on handle (one region per width, alternating keys)
    for(const key of ['Enter',' ']){
      await ev(`document.querySelector('.mk[data-id="HAW"]').click()`); await sleep(900);
      await ev(`document.querySelector('#sheet .grab').focus()`);
      await send('Input.dispatchKeyEvent',{type:'keyDown',key,code:key===' '?'Space':'Enter',text:key==='Enter'?'\r':key});await send('Input.dispatchKeyEvent',{type:'keyUp',key,code:key===' '?'Space':'Enter'});
      await sleep(400);
      check(!await ev(`document.querySelector('#sheet').classList.contains('open')`),T+': handle key '+JSON.stringify(key)+' closes the card');
      await sleep(400);
    }
    // X click closes too
    await ev(`document.querySelector('.mk[data-id="NR1"]').click()`); await sleep(900);
    await send('Input.dispatchMouseEvent',{type:'mousePressed',x:0,y:0,button:'none'});
    const xp=await ev(`(()=>{const r=document.querySelector('#close').getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()`);
    await send('Input.dispatchMouseEvent',{type:'mousePressed',x:xp.x,y:xp.y,button:'left',clickCount:1});await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:xp.x,y:xp.y,button:'left',clickCount:1});
    await sleep(500); check(!await ev(`document.querySelector('#sheet').classList.contains('open')`),T+': X tap closes the card');
    // --- layers
    for(const L of ['method','compare']){
      await ev(`document.querySelector('.nav button[data-v="${L}"]').click()`); await sleep(1300);
      const tag=T+' layer '+L;
      okGeo(await geo('#'+L,'[data-close]'),tag);
      await ev(`(()=>{const p=document.querySelector('#${L} .panel');p.scrollTop=p.scrollHeight})()`); await sleep(250);
      okGeo(await geo('#'+L,'[data-close]'),tag+' scrolled',1);
      if(L==='method'){
        const g=await ev(`(()=>{const a=document.querySelector('#method .js-gh');return a?{href:a.href,target:a.target,rel:a.rel,svg:!!a.querySelector('svg')}:null})()`);
        check(g&&g.href==='https://github.com/sighmon/space'&&g.target==='_blank'&&/noopener/.test(g.rel)&&/noreferrer/.test(g.rel)&&g.svg,tag+': GitHub link in sources');
        if(process.env.SHOT&&(w===390||w===1440))await shot(path.join(process.env.SHOT,`method-github-${w}.png`));
      }
      const gr=await ev(`(()=>{const g=document.querySelector('#${L} .grab'),r=g.getBoundingClientRect();return {role:g.getAttribute('role'),al:g.getAttribute('aria-label'),ti:g.tabIndex,h:r.height}})()`);
      check(gr.role==='button'&&!!gr.al&&gr.ti===0&&gr.h>=44,tag+': handle role/label/tabindex/>=44px');
      await ev(`document.querySelector('#${L} .panel').scrollTop=0`); await sleep(150);
      const pt=await ev(`(()=>{const r=document.querySelector('#${L} .grab').getBoundingClientRect();return {x:r.left+r.width*0.3,y:r.top+r.height/2}})()`);
      await send('Input.dispatchMouseEvent',{type:'mousePressed',x:pt.x,y:pt.y,button:'left',clickCount:1});await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:pt.x,y:pt.y,button:'left',clickCount:1});
      await sleep(500);
      check(!await ev(`document.querySelector('#${L}').classList.contains('open')`),tag+': handle tap closes the layer');
      // reopen, close with X
      await ev(`document.querySelector('.nav button[data-v="${L}"]').click()`); await sleep(1000);
      await ev(`document.querySelector('#${L} [data-close]').click()`); await sleep(500);
      check(!await ev(`document.querySelector('#${L}').classList.contains('open')`),tag+': X closes the layer');
    }
    // playback keeps running after close via handle
    const st=()=>ev(`document.querySelector('#hstamp').textContent`);
    await ev(`document.querySelector('.mk[data-id="NR1"]').click()`); await sleep(800);
    await ev(`document.querySelector('#sheet .grab').click()`); await sleep(400);
    const a=await st(); await sleep(700); check(a!==await st(),T+': Sun still advances after handle close');
  }
  check(errors.length===0,'no uncaught page errors '+[...new Set(errors)].join('|'));
  ws.close(); ch.kill();
  if(fails.length){console.log('FAILED',fails.length,'of',n);process.exit(1);} console.log('close buttons + handle + GitHub link ok ('+n+' checks)');
})();

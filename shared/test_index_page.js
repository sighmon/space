// Headless checks for the root landing page (index.html): links, Mars not a link, no overflow at phone widths,
// keyboard reachable, no console errors, no external requests, reduced motion respected, starfield capped.
// usage: node --experimental-websocket shared/test_index_page.js
const path=require('path'),assert=require('assert'),{launch,sleep}=require('../space-weather/web/cdp.js');
const FILE='file://'+path.resolve(__dirname,'../index.html'); let n=0; const ok=(c,m)=>{n++;assert.ok(c,m);console.log('ok',m)};
(async()=>{
  const b=await launch(),errs=[],reqs=[]; b.on(d=>{if(d.method==='Runtime.exceptionThrown')errs.push('exc');if(d.method==='Runtime.consoleAPICalled'&&d.params.type==='error')errs.push('console');if(d.method==='Network.requestWillBeSent')reqs.push(d.params.request.url);});
  for(const w of [320,360,390,430,768,1440]){await b.viewport(w,w>=768?900:800);await b.goto('about:blank',100);await b.goto(FILE,800);
    const m=await b.ev(`(()=>{const vw=innerWidth,de=document.documentElement,bad=[];const sb=vw-de.clientWidth;if(de.scrollWidth>de.clientWidth)bad.push('scrollWidth '+de.scrollWidth+' > '+de.clientWidth);
      for(const e of document.body.querySelectorAll('*')){const r=e.getBoundingClientRect();if(!r.width)continue;if(r.left<-0.5||r.right>de.clientWidth+0.5)bad.push(e.tagName+'.'+e.className+' '+r.left.toFixed(0)+'..'+r.right.toFixed(0));}
      const tg=[...document.querySelectorAll('a.card,.ghlink')].filter(e=>{const r=e.getBoundingClientRect();return r.height<43.5}).map(e=>e.className);
      return {bad:bad.slice(0,6),tg}})()`);
    ok(!m.bad.length&&!m.tg.length,w+'px: no horizontal overflow, link targets >= 44px '+JSON.stringify(m));}
  await b.viewport(1440,900); await b.goto('about:blank',100); await b.goto(FILE,800);
  const links=await b.ev(`[...document.querySelectorAll('a')].map(a=>a.getAttribute('href'))`);
  ok(links.includes('moon-south-pole-atlas/web/index.html')&&links.includes('space-weather/web/index.html'),'links to both prototypes are relative: '+links.join(', '));
  ok(links.filter(h=>!/^https:\/\/github\.com\/sighmon\/space$/.test(h)&&!/^[a-z-]+\/web\/index\.html$/.test(h)).length===0,'the only other link is the GitHub repository');
  ok(await b.ev(`(()=>{const m=[...document.querySelectorAll('.card')].find(c=>/Mars/.test(c.textContent));return m&&m.tagName!=='A'&&!m.closest('a')&&!m.querySelector('a')&&/Coming soon/i.test(m.textContent)})()`),'Mars surface power is "coming soon" and is not a link');
  ok(await b.ev(`document.querySelectorAll('.card').length===3`),'three projects listed');
  ok((await b.ev(`document.body.innerText`)).includes('sighmon/space'),'GitHub link text present');
  // keyboard: Tab reaches GitHub link and both cards
  const order=[]; for(let i=0;i<5;i++){await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});order.push(await b.ev(`document.activeElement.getAttribute('href')`));}
  ok(order.includes('moon-south-pole-atlas/web/index.html')&&order.includes('space-weather/web/index.html')&&order.includes('https://github.com/sighmon/space'),'keyboard Tab reaches the GitHub link and both project links: '+order.join(' | '));
  ok(await b.ev(`(()=>{document.querySelector('a.card').focus();const cs=getComputedStyle(document.activeElement);return cs.outlineStyle!=='none'&&parseFloat(cs.outlineWidth)>=2})()`),'focused card has a visible focus ring');
  // starfield: capped fps
  await b.ev(`window.__d=0;const o=CanvasRenderingContext2D.prototype.clearRect;CanvasRenderingContext2D.prototype.clearRect=function(){__d++;return o.apply(this,arguments)}`);
  await sleep(2000); const d=await b.ev('__d'); ok(d>=15&&d<=50,'starfield is capped near 20 fps: '+d+' frames in 2 s');
  await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]}); await b.goto('about:blank',100); await b.goto(FILE,600);
  await b.ev(`window.__d=0;const o=CanvasRenderingContext2D.prototype.clearRect;CanvasRenderingContext2D.prototype.clearRect=function(){__d++;return o.apply(this,arguments)}`); await sleep(1200);
  ok(await b.ev('__d')===0,'reduced motion: the starfield is drawn once and does not animate');
  ok(errs.length===0,'no console errors'); const ext=reqs.filter(u=>!/^(file:|data:|about:)/.test(u)); ok(ext.length===0,'no external requests ('+reqs.length+' total)');
  b.close(); console.log('index page ok',n,'checks'); process.exit(0);
})().catch(e=>{console.error('FAIL',e.message);process.exit(1)});

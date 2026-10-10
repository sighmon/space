// Headless geometry check: no horizontal overflow at phone/tablet widths.
// For every region card, the method layer and the compare view at 320/360/390/430/768 px:
//  - document.documentElement.scrollWidth <= innerWidth (and body too)
//  - the open panel has no horizontal scroll of its own (scrollWidth <= clientWidth)
//  - no element inside the open card/layer has a bounding box outside the viewport,
//    except inside the intentional comparison-table scroller (.tablewrap)
// usage: node --experimental-websocket web/test_no_overflow.js   (needs google-chrome on PATH)
//   SHOT=dir  also writes screenshots (card-<id>-<w>.png, method-<w>.png, compare-<w>.png) for widths in SHOTW (default 360,390)
const {spawn}=require('child_process'), path=require('path'), http=require('http'), fs=require('fs');
const url='file://'+path.resolve(process.env.PAGE||path.join(__dirname,'index.html'));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const getJSON=u=>new Promise((res,rej)=>http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res(JSON.parse(d)))}).on('error',rej));
const WIDTHS=[320,360,390,430,768], IDS=['CAB','DGR','HAW','MAL','MMP','MMO','NR1','NR2','SLP'];
const shotW=(process.env.SHOTW||'360,390').split(',').map(Number);
(async()=>{
  const port=9300+Math.floor(Math.random()*500);
  const ch=spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--remote-debugging-port='+port,'--window-size=500,900','about:blank'],{stdio:'ignore'});
  let tabs; for(let i=0;i<50;i++){try{tabs=await getJSON(`http://127.0.0.1:${port}/json`);if(tabs.length)break;}catch(e){}await sleep(200);}
  const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl); await new Promise(r=>ws.onopen=r);
  let id=0; const pend={}; ws.onmessage=m=>{const d=JSON.parse(m.data);if(d.id&&pend[d.id]){pend[d.id](d.result||d);delete pend[d.id];}};
  const send=(method,params={})=>new Promise(r=>{const i=++id;pend[i]=r;ws.send(JSON.stringify({id:i,method,params}));});
  const ev=async e=>{const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});return r.result&&r.result.value;};
  const shot=async f=>{const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(f,Buffer.from(r.data,'base64'));};
  const measure=`((rootSel)=>{
    const vw=innerWidth, root=document.querySelector(rootSel), panel=root.querySelector('.panel'), bad=[];
    const de=document.documentElement;
    if(de.scrollWidth>vw)bad.push('documentElement.scrollWidth '+de.scrollWidth+' > '+vw);
    if(document.body.scrollWidth>vw)bad.push('body.scrollWidth '+document.body.scrollWidth+' > '+vw);
    if(panel.scrollWidth>panel.clientWidth)bad.push('panel scrollWidth '+panel.scrollWidth+' > clientWidth '+panel.clientWidth);
    const pr=panel.getBoundingClientRect();
    if(pr.left<-0.5||pr.right>vw+0.5)bad.push('panel box '+pr.left.toFixed(1)+'..'+pr.right.toFixed(1));
    for(const e of root.querySelectorAll('*')){
      if(e.closest('.tablewrap'))continue;
      const cs=getComputedStyle(e); if(cs.display==='none'||cs.visibility==='hidden')continue;
      const r=e.getBoundingClientRect(); if(!r.width&&!r.height)continue;
      if(r.left<-0.5||r.right>vw+0.5){const c=(e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className)||'';bad.push(e.tagName.toLowerCase()+(e.id?'#'+e.id:'')+(c?'.'+String(c).trim().split(/\\s+/).join('.'):'')+' '+r.left.toFixed(1)+'..'+r.right.toFixed(1)+' (vw '+vw+')');}
      if(e.closest('.tablewrap'))continue;
      if(e!==panel&&e.scrollWidth>e.clientWidth+1&&cs.overflowX!=='visible'&&cs.overflowX!=='hidden'&&e.clientWidth>0)bad.push('inner scroller '+e.tagName+(e.id?'#'+e.id:'')+' '+e.className);
    }
    const tw=document.querySelector('#compare .tablewrap');
    return {bad:bad.slice(0,12),n:bad.length};
  })`;
  const fails=[]; let checks=0;
  for(const w of WIDTHS){
    await send('Emulation.setDeviceMetricsOverride',{width:w,height:800,deviceScaleFactor:2,mobile:w<=430});
    await send('Page.navigate',{url}); await sleep(1500);
    const check=async(label,root,file)=>{
      await sleep(1100);
      const m=await ev(`${measure}(${JSON.stringify(root)})`); checks++;
      console.log(w+'px',label,m.n?'FAIL':'ok'); if(m.n)fails.push([w,label,m.bad]);
      if(process.env.SHOT&&shotW.includes(w)&&file)await shot(path.join(process.env.SHOT,file.replace('@',w)));
    };
    for(const rid of IDS){
      await ev(`document.querySelector('.mk[data-id="${rid}"]').click()`);
      await sleep(600);
      // scroll through the card so lazy layouts settle, then back to top
      await ev(`(()=>{const p=document.querySelector('#sheet .panel');p.scrollTop=0})()`);
      await check('card '+rid,'#sheet',`card-${rid.toLowerCase()}-@.png`);
      // also check the bottom of the card (zoom, caveats) as a screenshot
      if(process.env.SHOT&&shotW.includes(w)){await ev(`(()=>{const p=document.querySelector('#sheet .panel');p.scrollTop=p.scrollHeight})()`);await sleep(300);await shot(path.join(process.env.SHOT,`card-${rid.toLowerCase()}-lower-${w}.png`));}
      await ev(`document.querySelector('#close').click()`); await sleep(500);
    }
    await ev(`document.querySelector('.nav button[data-v="method"]').click()`); await check('method layer','#method','method-@.png');
    await ev(`document.querySelector('#method [data-close]').click()`); await sleep(500);
    await ev(`document.querySelector('.nav button[data-v="compare"]').click()`); await check('compare view','#compare','compare-@.png');
    // the table may scroll, but only inside its own container
    const tw=await ev(`(()=>{const t=document.querySelector('#compare .tablewrap');return {sw:t.scrollWidth,cw:t.clientWidth,ov:getComputedStyle(t).overflowX}})()`);
    if(tw.sw>tw.cw&&tw.ov!=='auto'&&tw.ov!=='scroll'){fails.push([w,'tablewrap not scrollable',tw]);console.log('tablewrap FAIL')}
    await ev(`document.querySelector('#compare [data-close]').click()`); await sleep(500);
  }
  ws.close(); ch.kill();
  if(fails.length){console.log('FAILED',JSON.stringify(fails,null,1));process.exit(1);} console.log('no horizontal overflow ('+checks+' checks)');
})();

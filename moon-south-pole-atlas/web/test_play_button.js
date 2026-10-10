// Headless geometry check: the Play/Pause buttons must not move or resize on press, release, toggle, speed change.
// usage: node --experimental-websocket web/test_play_button.js   (needs google-chrome on PATH)
const {spawn}=require('child_process'), path=require('path'), http=require('http');
const url='file://'+path.resolve(process.env.PAGE||path.join(__dirname,'index.html'));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const getJSON=u=>new Promise((res,rej)=>http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res(JSON.parse(d)))}).on('error',rej));
(async()=>{
  const port=9300+Math.floor(Math.random()*500);
  const ch=spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--remote-debugging-port='+port,'--window-size='+(process.argv[2]||'1440,900'),'about:blank'],{stdio:'ignore'});
  let tabs; for(let i=0;i<50;i++){try{tabs=await getJSON(`http://127.0.0.1:${port}/json`);if(tabs.length)break;}catch(e){}await sleep(200);}
  const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl); await new Promise(r=>ws.onopen=r);
  let id=0; const pend={}; ws.onmessage=m=>{const d=JSON.parse(m.data);if(d.id&&pend[d.id]){pend[d.id](d.result||d);delete pend[d.id];}};
  const send=(method,params={})=>new Promise(r=>{const i=++id;pend[i]=r;ws.send(JSON.stringify({id:i,method,params}));});
  const ev=async e=>{const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});return r.result&&r.result.value;};
  await send('Page.navigate',{url}); await sleep(1500);
  const fails=[]; const rects=[];
  const rectOf=sel=>ev(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height].map(v=>Math.round(v*100)/100)})()`);
  async function exercise(label,sel,pre){
    if(pre)await ev(pre); await ev(`document.querySelector(${JSON.stringify(sel)}).scrollIntoView({block:'center'})`); await sleep(600);
    const r0=await rectOf(sel); const [x,y,w,h]=r0; const cx=x+w/2, cy=y+h/2; const seen=[r0];
    for(let k=0;k<6;k++){
      await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:cx,y:cy});
      await send('Input.dispatchMouseEvent',{type:'mousePressed',x:cx,y:cy,button:'left',clickCount:1}); await sleep(120);
      seen.push(await rectOf(sel));
      await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:cx,y:cy,button:'left',clickCount:1});
      for(let j=0;j<8;j++){await sleep(100);seen.push(await rectOf(sel));}
    }
    for(const s of ['1','4','16']){await ev(`document.querySelector(${JSON.stringify(sel)}).closest('.tl-ctl,.homectl').querySelector('.js-seg button[data-s="${s}"]').click()`);await sleep(200);seen.push(await rectOf(sel));}
    const bad=seen.filter(r=>r.some((v,i)=>Math.abs(v-r0[i])>0.01));
    console.log(label,bad.length?'FAIL':'ok',JSON.stringify(r0),'samples',seen.length); if(bad.length)fails.push([label,bad.slice(0,3)]);
  }
  await exercise('home play button','#homectl .js-play');
  await ev(`document.querySelector('.mk[data-id="NR1"]').click()`); await sleep(900);
  await exercise('card play button (NR101)','#sheet .js-play');
  await ev(`document.querySelector('.mk[data-id="HAW"]').click()`); await sleep(900);
  await exercise('card play button (Haworth)','#sheet .js-play');
  ws.close(); ch.kill();
  if(fails.length){console.log('FAILED',JSON.stringify(fails));process.exit(1);} console.log('play button stable');
})();

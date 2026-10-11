// Minimal headless-Chrome (CDP) helper shared by the space-weather web tests. node --experimental-websocket
const {spawn}=require('child_process'), http=require('http'), fs=require('fs');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const getJSON=u=>new Promise((res,rej)=>http.get(u,r=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res(JSON.parse(d)))}).on('error',rej));
async function launch(){
  const port=9300+Math.floor(Math.random()*600);
  const ch=spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--remote-debugging-port='+port,'--window-size=500,900','about:blank'],{stdio:'ignore'});
  let tabs; for(let i=0;i<60;i++){try{tabs=await getJSON(`http://127.0.0.1:${port}/json`);if(tabs.length)break;}catch(e){}await sleep(200);}
  const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl); await new Promise(r=>ws.onopen=r);
  let id=0; const pend={}; const listeners=[];
  ws.onmessage=m=>{const d=JSON.parse(m.data); if(d.id&&pend[d.id]){pend[d.id](d.result||d);delete pend[d.id];} else if(d.method)listeners.forEach(f=>f(d));};
  const send=(method,params={})=>new Promise(r=>{const i=++id;pend[i]=r;ws.send(JSON.stringify({id:i,method,params}));});
  const ev=async e=>{const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails).slice(0,400));return r.result&&r.result.value;};
  const shot=async f=>{const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(f,Buffer.from(r.data,'base64'));};
  const on=f=>listeners.push(f);
  const viewport=(w,h)=>send('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:1,mobile:w<=430});
  const goto=async(url,ms)=>{await send('Page.navigate',{url});await sleep(ms||1200);};
  const close=()=>{try{ws.close()}catch(e){}ch.kill('SIGKILL');};
  await send('Page.enable');await send('Runtime.enable');await send('Network.enable');
  return {send,ev,shot,on,viewport,goto,close,sleep};
}
module.exports={launch,sleep};

// Regenerates screenshots/ (desktop 1440x900 and phone 390x844, one per scene). usage: node --experimental-websocket web/shots.js
const path=require('path'),fs=require('fs'),{launch,sleep}=require('../../space-weather/web/cdp.js');
const FILE='file://'+path.resolve(__dirname,'index.html'), OUT=path.resolve(__dirname,'screenshots');
(async()=>{fs.mkdirSync(OUT,{recursive:true}); const b=await launch();
  for(const [kind,w,h] of [['desktop',1440,900],['phone',390,844]])for(const s of ['mesh','moon','mars','conj']){
    await b.viewport(w,h); await b.goto('about:blank',100); await b.goto(FILE+'#scene='+s,2600);
    await b.ev(`document.querySelector('#play').click()`); await sleep(150);
    const f=path.join(OUT,`optical-${s}-${kind}-${w}x${h}.png`); await b.shot(f); console.log(f);}
  b.close();})();

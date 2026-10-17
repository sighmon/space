// Regressions for the PR #4 review (2 bugs, 3 suggestions, 1 nit). Black-box where possible, so they run on older copies.
//  1 bug: conjunction straight line: the ruler stops where the packet reaches the Sun (1/2.524 of the way from Earth, 0.604 of the way from Mars), not at 0.50
//  2 bug: during the 600 ms scene tween, the light time matches the path length shown next to it
//  3 suggestion: the blocked beam is clamped to the Mars–Earth segment (nothing is drawn past the Earth disc), 320x500
//  4 suggestion: the Mars DSOC block hides wherever the other notes hide (short or narrow phones)
//  5 suggestion: 901–1230 px: nothing in the scene is drawn under the fixed readout
//  6 nit: no ternary written as ?.digit (reads like optional chaining)
// usage: node --experimental-websocket web/test_review.js   (OPTICAL_FILE=other.html to point at another copy; ONLY=1,3 to run some)
const path=require('path'),fs=require('fs'),assert=require('assert'),{launch,sleep}=require('../../space-weather/web/cdp.js');
const NAME=process.env.OPTICAL_FILE||'index.html', FILE='file://'+path.resolve(__dirname,NAME);
const ONLY=(process.env.ONLY||'1,2,3,4,5,6').split(',').map(Number);
let n=0, fails=[]; const ok=(c,m)=>{n++;if(!c){fails.push(m);console.log('FAIL',m);}else console.log('ok',m)};
const AU=149597870.7, C=299792.458, MA=1.524;
const FAKE=`(()=>{let q=new Map(),id=0,now=1000;window.requestAnimationFrame=cb=>{q.set(++id,cb);return id};window.cancelAnimationFrame=i=>q.delete(i);
  window.__pump=(hz,sec)=>{const k=Math.round(hz*sec);for(let i=0;i<k;i++){now+=1000/hz;const c=[...q.values()];q.clear();c.forEach(f=>f(now));}return now};})()`;
const parseKm=s=>/AU/.test(s)?parseFloat(s)*AU:parseFloat(s.replace(/,/g,''));
const parseT=s=>/min/.test(s)?parseFloat(s)*60:/ms/.test(s)?parseFloat(s)/1000:parseFloat(s);
(async()=>{
  // ---- 6: source scan
  if(ONLY.includes(6)){const src=fs.readFileSync(path.resolve(__dirname,NAME),'utf8'),js=src.slice(src.lastIndexOf('<script>'));
    const hits=js.match(/\?\.\d/g)||[]; ok(!hits.length,'6: no ternary of the form ?.5 in the page script ('+hits.length+' found)');}
  const b=await launch();
  try{
    // ---- 1: blocked ruler stops at the Sun, label says when
    if(ONLY.includes(1)){
      const {identifier}=await b.send('Page.addScriptToEvaluateOnNewDocument',{source:FAKE});
      await b.viewport(1440,900); await b.goto('about:blank',60); await b.goto(FILE+'#?scene=conj&link=direct',600);
      const max=await b.ev(`(()=>{let m=0;for(let i=0;i<30*24;i++){__pump(30,1/30);const t=document.querySelector('#ruler-fill').style.transform,v=parseFloat((t.match(/scaleX\\(([\\d.]+)/)||[0,0])[1]);if(v>m)m=v;}return m})()`);
      const sunFrac=MA/(1+MA);
      ok(Math.abs(max-sunFrac)<0.01,'1: straight-line ruler peaks at '+max.toFixed(3)+', the Sun is '+sunFrac.toFixed(3)+' of the Mars→Earth path');
      const lab=await b.ev(`document.querySelector('#ruler-k').textContent`), tSun=(sunFrac*(1+MA)*AU/C/60).toFixed(1);
      ok(lab.includes(tSun+' min'),'1: label gives the time to the Sun, '+tSun+' min: "'+lab+'"');
      await b.send('Page.removeScriptToEvaluateOnNewDocument',{identifier});
    }
    // ---- 2: tween keeps km and light time consistent
    if(ONLY.includes(2)){
      await b.viewport(1440,900); await b.goto('about:blank',60); await b.goto(FILE+'#?scene=moon',700);
      const samples=await b.ev(`new Promise(res=>{const out=[];document.querySelector('#scenes [data-scene="mars"]').click();const iv=setInterval(()=>{out.push([document.querySelector('#r-km').textContent,document.querySelector('#r-time').textContent])},20);setTimeout(()=>{clearInterval(iv);res(out)},750)})`);
      const bad=samples.filter(([k,t])=>{const v=parseKm(k), e=/AU/.test(k)?0.005*AU:0.5, got=parseT(t), et=/min/.test(t)?3:0.05;return got<(v-e)/C-et||got>(v+e)/C+et;});   // within the rounding of the km/AU shown
      const mid=samples.filter(([k])=>parseKm(k)<0.5*AU).length;
      ok(samples.length>20&&mid>0,'2: '+samples.length+' samples during the Moon→Mars tween, '+mid+' mid-count');
      ok(!bad.length,'2: light time matches path length in every sample '+JSON.stringify(bad.slice(0,3)));
    }
    // ---- 3: blocked beam clamped to the segment
    if(ONLY.includes(3)){
      await b.viewport(320,500);
      const grab=async link=>{await b.goto('about:blank',60); await b.goto(FILE+'#?scene=conj&paused&link='+link,500);
        return b.ev(`(()=>{const c=document.querySelector('#hero'),d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;return {w:c.width,h:c.height,d:Array.from(d)}})()`);};
      const A=await grab('direct'), B=await grab('relay');
      const G=await b.ev(`window.__opt&&__opt.geom?__opt.geom():null`);
      ok(!!G,'3: page exposes the drawn Earth position (__opt.geom)');
      const ex=G?G.earth[0]:0, ey=G?G.earth[1]:0; let past=0;
      if(G)for(let y=Math.round(ey-4);y<=Math.round(ey+4);y++)for(let x=0;x<ex-G.pd-3;x++){const i=(y*A.w+x)*4;if(Math.abs(A.d[i]-B.d[i])+Math.abs(A.d[i+1]-B.d[i+1])+Math.abs(A.d[i+2]-B.d[i+2])>12)past++;}
      ok(past===0,'3: 320x500: no straight-line beam pixels beyond the Earth disc ('+past+')');
    }
    // ---- 4: DSOC block hides with the notes
    if(ONLY.includes(4)){
      for(const [w,h] of [[320,640],[360,740],[390,640],[430,700],[390,844]]){
        await b.viewport(w,h); await b.goto('about:blank',60); await b.goto(FILE+'#?scene=mars&paused',400);
        const r=await b.ev(`({note:getComputedStyle(document.querySelector('#r-note')).display,dsoc:getComputedStyle(document.querySelector('#dsoc')).display})`);
        ok((r.note==='none')===(r.dsoc==='none'),'4: '+w+'x'+h+': note '+r.note+', DSOC block '+r.dsoc);
      }
    }
    // ---- 5: nothing under the fixed readout at mid widths
    if(ONLY.includes(5)){
      for(const w of [901,1024,1100,1230,1280,1440])for(const s of ['mesh','moon','mars','conj']){
        await b.viewport(w,800); await b.goto('about:blank',60); await b.goto(FILE+'#?scene='+s+'&paused',400);
        const hit=await b.ev(`(()=>{const c=document.querySelector('#hero'),k=c.width/innerWidth,r=document.querySelector('#live').getBoundingClientRect();
          const x0=Math.floor((r.left-8)*k),w=Math.ceil((r.width+16)*k),y0=Math.floor(r.top*k),h=Math.ceil(r.height*k);
          const d=c.getContext('2d').getImageData(x0,y0,w,h).data;let n=0;for(let i=0;i<d.length;i+=4)if(Math.max(d[i],d[i+1],d[i+2])>60)n++;return n})()`);
        ok(hit===0,'5: '+w+'px '+s+': '+hit+' scene pixels under the readout');
      }
    }
  }finally{b.close();}
  console.log((fails.length?'review FAILED ':'review ok ')+(n-fails.length)+'/'+n+' checks');
  if(fails.length)process.exit(1);
})().catch(e=>{console.error(e.message);process.exit(1)});

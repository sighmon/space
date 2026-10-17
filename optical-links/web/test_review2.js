// Regressions for the second PR #4 review.
//  7 bug: mid-tween, the ruler label and the Mars distance marker follow the same animated distance as path length and light time;
//         a second scene click mid-tween starts from the value on screen
//  8 bug: 901–1240 px with short heights: the fixed readout does not cover the link row or the dock, and stays inside the window
//  9 bug: the scene fade multiplies every beam / packet alpha (nothing in the dynamic layer paints above the fade alpha)
// 10 suggestion: no comments that only restate the next line (the ones flagged in review)
// The tween is frozen by stubbing performance.now, so the checks are deterministic.
// usage: node --experimental-websocket web/test_review2.js   (OPTICAL_FILE=other.html for another copy)
const path=require('path'),fs=require('fs'),{launch}=require('../../space-weather/web/cdp.js');
const NAME=process.env.OPTICAL_FILE||'index.html', FILE='file://'+path.resolve(__dirname,NAME);
let n=0, fails=[]; const ok=(c,m)=>{n++;if(!c){fails.push(m);console.log('FAIL',m);}else console.log('ok',m)};
const AU=149597870.7, C=299792.458;
const parseKm=s=>/AU/.test(s)?parseFloat(s)*AU:parseFloat(s.replace(/,/g,''));
const parseT=s=>/min/.test(s)?parseFloat(s)*60:/ms/.test(s)?parseFloat(s)/1000:parseFloat(s);
const FREEZE=`(()=>{const real=performance.now.bind(performance);let off=null;window.__freeze=t=>{off=t};window.__thaw=()=>{off=null};performance.now=()=>off==null?real():off;})()`;
const read=b=>b.ev(`({km:document.querySelector('#r-km').textContent,t:document.querySelector('#r-time').textContent,rk:document.querySelector('#ruler-k').textContent,where:document.querySelector('#dsoc-where').textContent,pt:document.querySelector('#dsoc-pt').style.transform})`);
(async()=>{
  // ---- 10: restating comments
  {const src=fs.readFileSync(path.resolve(__dirname,NAME),'utf8');
   const flagged=['one pre-rendered packet glow, drawn with drawImage','the L4 route lights up','clamp to the Mars–Earth segment','light time follows the path length shown','heartbeat: one pulse hopping around the ring','km→AU count-up','the ruler stops where the light meets the Sun'];
   const left=flagged.filter(c=>src.includes(c)); ok(!left.length,'10: restating comments removed '+JSON.stringify(left));}
  const b=await launch();
  const {identifier}=await b.send('Page.addScriptToEvaluateOnNewDocument',{source:FREEZE});
  try{
    // ---- 7: mid-tween consistency and restart from the value on screen
    await b.viewport(1440,900); await b.goto('about:blank',60); await b.goto(FILE+'#?scene=moon&paused',600);
    await b.ev(`__freeze(100000);document.querySelector('#scenes [data-scene="mars"]').click();__freeze(100300);__opt.draw()`);
    const m=await read(b), km=parseKm(m.km), rkT=parseT((m.rk.match(/Light: ([\d.,]+ (?:min|s|ms))/)||[0,'0 s'])[1]);
    ok(km>0.01*AU&&km<1.2*AU,'7: frozen mid-tween, path length is counting: '+m.km+' / '+m.t);
    ok(Math.abs(rkT-parseT(m.t))<=Math.max(0.051,parseT(m.t)*0.01),'7: ruler label light time "'+m.rk.slice(0,24)+'" matches readout '+m.t);
    const wAU=parseFloat((m.where.match(/([\d.]+) AU/)||[0,'-1'])[1]);
    ok(Math.abs(wAU-km/AU)<0.006,'7: Mars marker text '+wAU+' AU matches the path length shown ('+(km/AU).toFixed(3)+' AU)');
    const px=parseFloat((m.pt.match(/translateX\(([-\d.]+)px/)||[0,'-1'])[1]);
    ok(px<=1,'7: Mars marker sits at the near end while the counting distance is below 0.36 AU ('+px+' px)');
    await b.ev(`__freeze(100300);document.querySelector('#scenes [data-scene="conj"]').click();__opt.draw()`);
    const m2=await read(b);
    ok(m2.km===m.km,'7: second click mid-tween starts from the value on screen: '+m.km+' -> '+m2.km);
    await b.ev(`__thaw()`);
    // ---- 9: fade multiplies every alpha
    await b.goto('about:blank',60); await b.goto(FILE+'#?scene=mars&paused',600);
    for(const to of ['conj','moon','mesh']){
      const r=await b.ev(`(()=>{__freeze(200000);document.querySelector('#scenes [data-scene="${to}"]').click();__freeze(200000+300);
        const P=CanvasRenderingContext2D.prototype,ctx=document.querySelector('#hero').getContext('2d'),seen=[];const wrap=k=>{const f=P[k];P[k]=function(){if(this===ctx)seen.push([k,this.globalAlpha]);return f.apply(this,arguments)};return ()=>P[k]=f};
        const un=['stroke','fill','fillRect','drawImage','fillText'].map(wrap);__opt.draw();un.forEach(u=>u());__thaw();
        const fillBg=seen.shift();return {max:Math.max(...seen.map(s=>s[1])),n:seen.length,top:seen.filter(s=>s[1]>0.51).slice(0,4)}})()`);
      ok(r.n>5&&r.max<=0.51,'9: '+to+' at fade 0.5: '+r.n+' paint calls, max alpha '+r.max.toFixed(3)+' '+JSON.stringify(r.top));
    }
    // ---- 8: short heights at mid widths
    const inter=(a,c)=>a.left<c.right-0.5&&c.left<a.right-0.5&&a.top<c.bottom-0.5&&c.top<a.bottom-0.5;
    for(const w of [901,1024,1100,1210,1240])for(const h of [600,640,700,768])for(const s of ['moon','mars','conj']){
      await b.viewport(w,h); await b.goto('about:blank',40); await b.goto(FILE+'#?scene='+s+'&paused',300);
      const g=await b.ev(`(()=>{const R=e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom}};
        const vis=[...document.querySelectorAll('#live > *')].filter(e=>getComputedStyle(e).display!=='none'&&e.getClientRects().length);
        const live=vis.reduce((a,e)=>{const r=R(e);return {left:Math.min(a.left,r.left),right:Math.max(a.right,r.right),top:Math.min(a.top,r.top),bottom:Math.max(a.bottom,r.bottom)}},{left:1e9,right:-1e9,top:1e9,bottom:-1e9});
        return {live,links:R(document.querySelector('#links')),dock:R(document.querySelector('.dock')),top:R(document.querySelector('.top')),H:innerHeight}})()`);
      const bad=[]; if(inter(g.live,g.links))bad.push('links'); if(inter(g.live,g.dock))bad.push('dock'); if(g.live.bottom>g.H+0.5)bad.push('below window '+g.live.bottom.toFixed(0)); if(inter(g.live,g.top))bad.push('header');
      ok(!bad.length,'8: '+w+'x'+h+' '+s+': readout clear of links, dock and header, inside the window '+(bad.length?bad.join(', '):''));
    }
  }finally{await b.send('Page.removeScriptToEvaluateOnNewDocument',{identifier}); b.close();}
  console.log((fails.length?'review2 FAILED ':'review2 ok ')+(n-fails.length)+'/'+n+' checks');
  if(fails.length)process.exit(1);
})().catch(e=>{console.error(e.message);process.exit(1)});

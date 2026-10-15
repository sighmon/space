// Layout, contrast and cost checks for the optical-links page.
//  - no horizontal overflow at 320–1440 px in every scene; controls at least 44 px; the dock is at most two rows on phones
//  - the scene band on phones keeps at least 32% of the viewport height
//  - WCAG AA (4.5:1) for active .seg / link buttons (ice on #061018) and the ruler / marker text, measured from computed styles at phone and desktop widths
//  - cost: mean draw() under 6 ms, no layout reads inside draw, no readout DOM writes while nothing changes, static layer cached
// usage: node --experimental-websocket web/test_layout.js
const path=require('path'),assert=require('assert'),{launch,sleep}=require('../../space-weather/web/cdp.js');
const FILE='file://'+path.resolve(__dirname,'index.html');
let n=0; const ok=(c,m)=>{n++;assert.ok(c,m);console.log('ok',m)};
const SCENES=['mesh','moon','mars','conj'];
const SIZES=[[320,640],[360,740],[390,844],[430,932],[768,1024],[900,900],[901,900],[1024,768],[1280,800],[1440,900]];
const contrastFn=`(()=>{const P=s=>{const m=s.match(/[\\d.]+/g).map(Number);return {c:m.slice(0,3),a:m.length>3?m[3]:1}};
  const lin=c=>{c/=255;return c<=0.03928?c/12.92:Math.pow((c+0.055)/1.055,2.4)};const L=c=>0.2126*lin(c[0])+0.7152*lin(c[1])+0.0722*lin(c[2]);
  const R=(a,b)=>{const x=L(a),y=L(b);return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05)};const over=(f,a,b)=>f.map((v,i)=>v*a+b[i]*(1-a));
  const out=[];for(const e of document.querySelectorAll('.seg button.on,.links button.on,.seg button,.links button,#ruler-k,#dsoc .ends span,#dsoc-where,#stamp,.live .k,.live .n,#r-note')){
    const cs=getComputedStyle(e);if(cs.display==='none'||!e.getClientRects().length)continue;
    let bg=[5,6,7];for(let p=e;p;p=p.parentElement){const b=P(getComputedStyle(p).backgroundColor);if(b.a>0){bg=over(b.c,b.a,[5,6,7]);if(b.a>=0.99)break;}}
    const f=P(cs.color);out.push([(e.id||e.className||e.tagName)+':'+e.textContent.trim().slice(0,14),R(over(f.c,f.a,bg),bg)]);}
  return out})()`;
(async()=>{
  const b=await launch(); const errs=[]; b.on(d=>{if(d.method==='Runtime.exceptionThrown')errs.push(JSON.stringify(d.params.exceptionDetails).slice(0,300));});
  try{
    for(const [w,h] of SIZES){await b.viewport(w,h);
      for(const s of SCENES){
        await b.goto('about:blank',60); await b.goto(FILE+'#scene='+s+'&paused',350);
        const m=await b.ev(`(()=>{const vw=innerWidth,de=document.documentElement,bad=[];if(de.scrollWidth>vw)bad.push('scrollWidth '+de.scrollWidth);
          for(const e of document.body.querySelectorAll('*')){if(e.closest('.layer'))continue;const cs=getComputedStyle(e);if(cs.display==='none'||cs.visibility==='hidden')continue;const r=e.getBoundingClientRect();if(!r.width&&!r.height)continue;if(r.left<-0.5||r.right>vw+0.5)bad.push((e.id||e.className||e.tagName)+' '+r.left.toFixed(0)+'..'+r.right.toFixed(0));}
          const small=[...document.querySelectorAll('.stage button,.nav button')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&(r.height<43.5||r.width<43.5)}).map(e=>e.textContent);
          const ys=[...document.querySelectorAll('.dock > *')].filter(e=>getComputedStyle(e).display!=='none').map(e=>{const r=e.getBoundingClientRect();return r.top+r.height/2}).sort((a,b)=>a-b);let rows=0,last=-1e9;for(const y of ys){if(y-last>20)rows++;last=y;}
          const band=document.querySelector('.stage').getBoundingClientRect().top-document.querySelector('.top').getBoundingClientRect().bottom;
          return {bad:bad.slice(0,6),small,rows,band:band/innerHeight}})()`);
        ok(!m.bad.length&&!m.small.length,w+'x'+h+' '+s+': no overflow, targets >= 44px '+(m.bad.length||m.small.length?JSON.stringify(m):''));
        if(w<=520){ok(m.rows<=2,w+' '+s+': dock wraps to at most two rows ('+m.rows+')');
          if(h>=740)ok(m.band>=0.32,w+'x'+h+' '+s+': scene band is '+(m.band*100).toFixed(0)+'% of the viewport');}
      }
    }
    for(const [w,h] of [[320,640],[360,740],[390,844],[1440,900]])for(const s of ['moon','mars']){
      await b.viewport(w,h); await b.goto('about:blank',60); await b.goto(FILE+'#scene='+s+'&paused',350);
      const c=await b.ev(contrastFn); const bad=c.filter(x=>x[1]<4.5);
      ok(c.length>5&&!bad.length,w+' '+s+': '+c.length+' text items at >= 4.5:1 (min '+Math.min(...c.map(x=>x[1])).toFixed(2)+') '+JSON.stringify(bad));
      const on=await b.ev(`(()=>{const e=document.querySelector('#scenes button.on'),cs=getComputedStyle(e);return [cs.color,cs.backgroundColor]})()`);
      ok(on[0]==='rgb(6, 16, 24)'&&on[1]==='rgb(169, 220, 255)',w+': active scene button is #061018 on ice '+on.join(' / '));
    }
    // ---- cost
    await b.viewport(1440,900);
    for(const s of SCENES){
      await b.goto('about:blank',60); await b.goto(FILE+'#scene='+s+'&paused',400);
      const r=await b.ev(`(()=>{let reads=0;const g=Element.prototype.getBoundingClientRect;Element.prototype.getBoundingClientRect=function(){reads++;return g.call(this)};
        let muts=0;const mo=new MutationObserver(l=>muts+=l.length);mo.observe(document.querySelector('.stage'),{subtree:true,childList:true,characterData:true});
        __opt.draw();const t0=performance.now();for(let i=0;i<200;i++)__opt.draw();const ms=(performance.now()-t0)/200;
        Element.prototype.getBoundingClientRect=g;return new Promise(res=>setTimeout(()=>{mo.disconnect();res({ms,reads,muts,st:__opt.staticLayer()})},0))})()`);
      ok(r.ms<6,s+': mean draw '+r.ms.toFixed(2)+' ms');
      ok(r.reads===0,s+': no layout reads inside draw ('+r.reads+')');
      ok(r.muts===0,s+': repeated draws with nothing changed write no readout DOM ('+r.muts+' mutations)');
      ok(r.st.w===1440&&r.st.h===900,s+': static layer cached at canvas size');
    }
    await b.goto('about:blank',60); await b.goto(FILE+'#scene=moon',400);
    const d0=await b.ev('__opt.draws()'); await sleep(3000); const d1=await b.ev('__opt.draws()');
    ok(d1-d0>=60&&d1-d0<=95,'playing: '+(d1-d0)+' frames in 3 s (30 fps cap)');
    ok(!errs.length,'no exceptions '+errs.join(' | '));
  }finally{b.close();}
  console.log('layout ok',n,'checks');
})().catch(e=>{console.error(e.message);process.exit(1)});

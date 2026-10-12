// Headless geometry checks for the Mars surface power page at 320/360/390/430/768 px (and 900/901/1024/1440):
//  - no horizontal overflow of the document, the open panel, or any element (except the intentional .tablewrap scrollers)
//  - fixed controls on the home view do not overlap each other, sit inside the viewport and are at least 44x44 CSS px
//  - the open site cards and layers keep their X and handle at 44 px
// usage: node --experimental-websocket web/test_overflow.js
const path=require('path'), {launch,sleep}=require('../../space-weather/web/cdp.js');
const base='file://'+path.resolve(__dirname,'index.html');
const WIDTHS=[320,360,390,430,768,900,901,1024];
const PHONES=[[320,640],[360,740],[390,844],[430,932]];
const STATES=[['home','#?ls=240&paused',null],['home-clear','#?ls=60&scenario=cold&paused',null],['home-storm','#?ls=270&scenario=storm&paused',null],['home-storm-na','#?ls=90&scenario=storm&paused',null],
  ['deuteronilus','#site/deuteronilus?ls=240&paused','#sheet'],['protonilus','#site/protonilus?ls=300&scenario=storm&paused','#sheet'],['mesopotamia','#site/mesopotamia?ls=60&paused','#sheet'],
  ['curiosity','#site/curiosity?ls=270&paused','#sheet'],['perseverance','#site/perseverance?ls=0&paused','#sheet'],['opportunity','#site/opportunity?ls=180&paused','#sheet'],
  ['compare','#compare?paused','#compare'],['opportunity-layer','#opportunity?paused','#opportunity'],['method','#method?paused','#method'],['sol','#sol?paused','#sol']];
const measure=`((rootSel)=>{
  const vw=innerWidth,bad=[],de=document.documentElement;
  if(de.scrollWidth>vw)bad.push('documentElement.scrollWidth '+de.scrollWidth+' > '+vw);
  if(document.body.scrollWidth>vw)bad.push('body.scrollWidth '+document.body.scrollWidth+' > '+vw);
  const root=rootSel?document.querySelector(rootSel):document.body, panel=rootSel?root.querySelector('.panel'):null;
  if(panel){ if(panel.scrollWidth>panel.clientWidth)bad.push('panel scrollWidth '+panel.scrollWidth+' > '+panel.clientWidth); const pr=panel.getBoundingClientRect(); if(pr.left<-0.5||pr.right>vw+0.5)bad.push('panel box '+pr.left+'..'+pr.right);}
  for(const e of root.querySelectorAll('*')){
    if(e.closest('.tablewrap'))continue;
    const cs=getComputedStyle(e); if(cs.display==='none'||cs.visibility==='hidden')continue;
    const r=e.getBoundingClientRect(); if(!r.width&&!r.height)continue;
    if(r.left<-0.5||r.right>vw+0.5)bad.push(e.tagName.toLowerCase()+(e.id?'#'+e.id:'')+'.'+String(e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className).trim().split(/\\s+/).join('.')+' '+r.left.toFixed(1)+'..'+r.right.toFixed(1)+' (vw '+vw+')');
  }
  return bad.slice(0,10);
})`;
const overlap=`(()=>{
  const sels=['.brand .label','.brand .small','.brand .ghlink','.nav button','#r-ls','#r-flux','#r-dod','#r-def','.hero-copy h1','.hero-copy p','#map svg','#scn button','#snote','.site','#play','#seg button','#stamp','#scrub','.viz'];
  const items=[]; for(const s of sels)for(const e of document.querySelectorAll(s)){const cs=getComputedStyle(e);if(cs.display==='none'||cs.visibility==='hidden')continue;
    if(s==='.hero-copy h1'||s==='.hero-copy p'){const rg=document.createRange();rg.selectNodeContents(e);const m={};for(const q of rg.getClientRects()){if(!q.width)continue;const k=Math.round(q.top/4);m[k]=m[k]?{left:Math.min(m[k].left,q.left),right:Math.max(m[k].right,q.right),top:Math.min(m[k].top,q.top),bottom:Math.max(m[k].bottom,q.bottom)}:{left:q.left,right:q.right,top:q.top,bottom:q.bottom}}
      const lh=parseFloat(cs.lineHeight);for(const k in m){const q=m[k];if(lh>0&&q.bottom-q.top>lh){const mid=(q.top+q.bottom)/2;q.top=mid-lh/2;q.bottom=mid+lh/2}items.push({n:s+' (text line)',e,r:q})}continue}
    const r=e.getBoundingClientRect();if(!r.width||!r.height)continue;items.push({n:s,e,r});}
  const bad=[];
  for(let i=0;i<items.length;i++)for(let j=i+1;j<items.length;j++){const a=items[i].r,b=items[j].r; if(items[i].e.contains(items[j].e)||items[j].e.contains(items[i].e))continue;
    if(a.left<b.right-0.5&&b.left<a.right-0.5&&a.top<b.bottom-0.5&&b.top<a.bottom-0.5)bad.push(items[i].n+' x '+items[j].n);}
  const small=[]; for(const s of ['.nav button','.site','#play','#seg button','#scn button','#scrub','.brand .ghlink']){for(const e of document.querySelectorAll(s)){const r=e.getBoundingClientRect();if(r.width&&(r.height<43.5||r.width<43.5))small.push(s+' '+r.width.toFixed(1)+'x'+r.height.toFixed(1));}}
  const vh=innerHeight,vw=innerWidth, off=items.filter(x=>x.r.bottom>vh+0.5||x.r.top<-0.5||x.r.right>vw+0.5||x.r.left<-0.5).map(x=>x.n);
  return {bad,small,off};
})()`;
const tap=`(()=>{const out=[];for(const s of ['#sheet .x','#sheet .grab','.layer .x','.layer .grab','[data-open]','[data-site-open]','.layer .ghlink','details summary']){for(const e of document.querySelectorAll(s)){if(e.closest('[inert]'))continue;const r=e.getBoundingClientRect();if(r.width&&(r.height<43.5||r.width<43.5))out.push(s+' '+r.width.toFixed(1)+'x'+r.height.toFixed(1));}}return out})()`;
(async()=>{
  const b=await launch(); const fails=[]; let checks=0;
  for(const w of WIDTHS.concat([1440])){
    await b.viewport(w,w===1440?900:800);
    for(const [name,hash,root] of STATES){
      if(w===1440&&!/^(home|curiosity|compare|sol)$/.test(name))continue;
      await b.goto('about:blank',60); await b.goto(base+hash,400); await sleep(650);
      const bad=await b.ev(`${measure}(${JSON.stringify(root)})`); checks++;
      if(bad.length){fails.push([w,name,bad]);console.log(w,name,'FAIL',bad);} else console.log(w,name,'overflow ok');
      if(!root){const o=await b.ev(overlap);checks++; if(o.bad.length||o.small.length||o.off.length){fails.push([w,name+' controls',o]);console.log(w,name,'controls FAIL',JSON.stringify(o));}else console.log(w,name,'controls: no overlap, targets>=44, inside viewport');}
      else {const t=await b.ev(tap);checks++; if(t.length){fails.push([w,name+' tap',t]);console.log(w,name,'tap FAIL',t);}}
    }
  }
  for(const [w,h] of PHONES){await b.viewport(w,h);
    for(const hash of ['#?ls=240&paused','#?ls=270&scenario=storm&paused','#?ls=90&scenario=storm&paused']){await b.goto('about:blank',60);await b.goto(base+hash,400);await sleep(650);const o=await b.ev(overlap);checks++;
      if(o.bad.length||o.small.length||o.off.length){fails.push([w+'x'+h,hash,o]);console.log(w+'x'+h,hash,'controls FAIL',JSON.stringify(o));}else console.log(w+'x'+h,hash,'controls ok');}}
  b.close(); console.log(fails.length?'FAILED':'ok',checks,'checks'); process.exit(fails.length?1:0);
})();

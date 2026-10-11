// Headless geometry checks for the space-weather page at 320/360/390/430/768 px (and 1440 for the overlap test):
//  - no horizontal overflow of the document, the open panel, or any element (except the intentional .tablewrap scrollers)
//  - fixed controls on the home view do not overlap each other (brand, GitHub link, nav buttons, live readouts, audience buttons, play, speed, scrubber, hero copy)
//  - tap targets are at least 44x44 CSS px
//  - the three audience rings (gauge buttons): nothing inside one is clipped or spills out, and no ring text overlaps another's
// usage: node --experimental-websocket web/test_overflow.js
const path=require('path'), {launch,sleep}=require('./cdp.js');
const base='file://'+path.resolve(__dirname,'index.html');
const WIDTHS=[320,360,390,430,768,900,901,1024];
const PHONES=[[320,640],[360,740],[390,844]];   // real phone heights for the home-view overlap check
const STATES=[['home','#?h=120&paused',null],['crew','#audience/crew?h=130&paused','#sheet'],['polar','#audience/polar?h=140&paused','#sheet'],['grid','#audience/grid?h=100&paused','#sheet'],
  ['timeline','#timeline?h=130&paused','#timeline'],['alerts','#alerts?h=130&paused','#alerts'],['method','#method?h=130&paused','#method']];
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
  const sels=['.brand .label','.brand .small','.brand .ghlink','.nav button','#r-time','#r-f10','#r-f100','#r-dose','.hero-copy h1','.aud','#play','#seg button','#scrub'];
  const items=[]; for(const s of sels)for(const e of document.querySelectorAll(s)){const cs=getComputedStyle(e);if(cs.display==='none'||cs.visibility==='hidden')continue;const r=e.getBoundingClientRect();if(!r.width||!r.height)continue;items.push({n:s,e,r});}
  const bad=[];
  for(let i=0;i<items.length;i++)for(let j=i+1;j<items.length;j++){const a=items[i].r,b=items[j].r; if(items[i].e.contains(items[j].e)||items[j].e.contains(items[i].e))continue;
    if(a.left<b.right-0.5&&b.left<a.right-0.5&&a.top<b.bottom-0.5&&b.top<a.bottom-0.5)bad.push(items[i].n+' x '+items[j].n);}
  const small=[]; for(const s of ['.nav button','.aud','#play','#seg button','#scrub','.brand .ghlink']){for(const e of document.querySelectorAll(s)){const r=e.getBoundingClientRect();if(r.width&&(r.height<43.5||r.width<43.5))small.push(s+' '+r.width.toFixed(1)+'x'+r.height.toFixed(1));}}
  const gfit=[...document.querySelectorAll('.aud')].flatMap(e=>{const r=e.getBoundingClientRect(),o=[];if(e.scrollWidth>e.clientWidth+1)o.push('aud scrollWidth');
    for(const c of e.querySelectorAll('*')){const q=c.getBoundingClientRect();if(!q.width&&!q.height)continue;if(q.left<r.left-1||q.right>r.right+1||q.top<r.top-1||q.bottom>r.bottom+1)o.push(e.dataset.aud+' '+c.tagName+'.'+(c.className.baseVal!==undefined?c.className.baseVal:c.className));}
    const ts=[...e.querySelectorAll('.t b,.t span,.rv')].filter(x=>x.getBoundingClientRect().width);for(let i=0;i<ts.length;i++)for(let j=i+1;j<ts.length;j++){const a=ts[i].getBoundingClientRect(),b=ts[j].getBoundingClientRect();if(a.left<b.right-.5&&b.left<a.right-.5&&a.top<b.bottom-.5&&b.top<a.bottom-.5)o.push(e.dataset.aud+' text overlap '+ts[i].className+'/'+ts[j].className)}
    return o});
  bad.push(...gfit);
  const vh=innerHeight, off=items.filter(x=>x.r.bottom>vh+0.5||x.r.top<-0.5).map(x=>x.n);
  return {bad,small,off};
})()`;
const tap=`(()=>{const out=[];for(const s of ['#sheet .x','#sheet .grab','.layer .x','.layer .grab','[data-open]','.layer .ghlink']){for(const e of document.querySelectorAll(s)){if(e.closest('[inert]'))continue;const r=e.getBoundingClientRect();if(r.width&&(r.height<43.5||r.width<43.5))out.push(s+' '+r.width.toFixed(1)+'x'+r.height.toFixed(1));}}return out})()`;
(async()=>{
  const b=await launch(); const fails=[]; let checks=0;
  for(const w of WIDTHS.concat([1440])){
    await b.viewport(w,w===1440?900:800);
    for(const [name,hash,root] of STATES){
      if(w===1440&&name!=='home')continue;
      await b.goto(base+hash,500); await sleep(700);
      const bad=w===1440?[]:await b.ev(`${measure}(${JSON.stringify(root)})`); checks++;
      if(bad.length){fails.push([w,name,bad]);console.log(w,name,'FAIL',bad);} else console.log(w,name,'overflow ok');
      if(name==='home'){const o=await b.ev(overlap);checks++; if(o.bad.length||o.small.length||o.off.length){fails.push([w,'home controls',o]);console.log(w,'controls FAIL',JSON.stringify(o));}else console.log(w,'controls: no overlap, targets>=44, inside viewport');}
      else {const t=await b.ev(tap);checks++; if(t.length){fails.push([w,name+' tap',t]);console.log(w,name,'tap FAIL',t);}}
    }
  }
  for(const [w,h] of PHONES){await b.viewport(w,h);await b.goto(base+'#?h=120&paused',500);await sleep(700);const o=await b.ev(overlap);checks++;
    if(o.bad.length||o.small.length||o.off.length){fails.push([w+'x'+h,'home controls',o]);console.log(w+'x'+h,'controls FAIL',JSON.stringify(o));}else console.log(w+'x'+h,'controls ok');}
  b.close(); console.log(fails.length?'FAILED':'ok',checks,'checks'); process.exit(fails.length?1:0);
})();

// Conjunction geometry: Earth at 180°, Mars at 0°, the relay at Sun–Mars L4 (60° ahead of Mars on its 1.524 AU orbit).
// Earth–L4 is then 120° (2π/3) apart as seen from the Sun: ≈2.20 AU; L4–Mars 1.524 AU; total ≈3.73 AU ≈31.0 min of light.
// The page readout must show those numbers, computed from positions. Black-box on #r-km / #r-time, so it also runs on old copies.
// usage: node --experimental-websocket web/test_geometry.js   (OPTICAL_FILE=other.html to point at another copy)
const path=require('path'),assert=require('assert'),{launch}=require('../../space-weather/web/cdp.js');
const FILE='file://'+path.resolve(__dirname,process.env.OPTICAL_FILE||'index.html');
let n=0; const ok=(c,m)=>{n++;assert.ok(c,m);console.log('ok',m)};
const AU=149597870.7, C=299792.458, MA=1.524;
// independent expectation, law of cosines with the 120° angle
const eL4=Math.sqrt(1+MA*MA-2*MA*Math.cos(2*Math.PI/3)), total=eL4+MA, min=total*AU/C/60;
(async()=>{
  ok(Math.abs(eL4-2.2015)<0.001&&Math.abs(total-3.7255)<0.001&&Math.abs(min-30.98)<0.05,'expected: Earth–L4 '+eL4.toFixed(4)+' AU, total '+total.toFixed(4)+' AU, '+min.toFixed(2)+' min');
  const b=await launch(); await b.viewport(1440,900);
  try{
    await b.goto(FILE+'#?scene=conj&link=relay&paused',900);
    const r=await b.ev(`({km:document.querySelector('#r-km').textContent,t:document.querySelector('#r-time').textContent,name:document.querySelector('#r-name').textContent})`);
    ok(r.name==='Via Sun–Mars L4','relay link selected: '+r.name);
    ok(Math.abs(parseFloat(r.km)-total)<0.006&&/AU/.test(r.km),'path length readout '+r.km+' ≈ '+total.toFixed(2)+' AU');
    ok(Math.abs(parseFloat(r.t)-min)<0.06&&/min/.test(r.t),'light time readout '+r.t+' ≈ '+min.toFixed(1)+' min');
    await b.ev(`document.querySelector('#links [data-link="direct"]').click()`); await b.sleep(200);
    const d=await b.ev(`document.querySelector('#r-km').textContent`);
    ok(Math.abs(parseFloat(d)-(1+MA))<0.006,'direct line through the Sun '+d+' = 2.52 AU');
    const has=await b.ev(`!!(window.__opt&&__opt.conj)`);
    if(has){const c=await b.ev(`__opt.conj()`);
      ok(Math.abs(c.angleEarthL4-2*Math.PI/3)<1e-9,'Earth–L4 heliocentric angle is 2π/3 from positions');
      ok(Math.abs(c.earth/AU-eL4)<1e-6&&Math.abs(c.mars/AU-MA)<1e-6,'legs from positions: '+(c.earth/AU).toFixed(4)+' + '+(c.mars/AU).toFixed(4)+' AU');}
    const m=await b.ev(`document.querySelector('#method').textContent`);
    ok(/2\.20 AU/.test(m)&&/31\.0 min/.test(m)&&/2π\/3/.test(m),'method panel states 2π/3, 2.20 AU and 31.0 minutes');
  }finally{b.close();}
  console.log('geometry ok',n,'checks');
})().catch(e=>{console.error(e.message);process.exit(1)});

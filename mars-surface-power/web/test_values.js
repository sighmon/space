// Checks that the values the page DISPLAYS match data/mars.json, and that mars.json carries the project's own numbers.
// usage: node --experimental-websocket web/test_values.js
const path=require('path'),assert=require('assert'),fs=require('fs'),{launch,sleep}=require('../../space-weather/web/cdp.js');
const FILE='file://'+path.resolve(__dirname,'index.html');
const M=JSON.parse(fs.readFileSync(path.resolve(__dirname,'data/mars.json'),'utf8'));
let n=0; const ok=(c,m)=>{n++;assert.ok(c,m);console.log('ok',m)};
const MIN='\u2212', fmt=(v,d=0)=>(v<0&&+Math.abs(v).toFixed(d)!==0?MIN:'')+Math.abs(v).toFixed(d).replace(/\B(?=(\d{3})+(?!\d))/g,',');
const def=(s,k,ls)=>M.deficits.find(d=>d.site===s&&d.scenario===k&&d.ls===ls);
// display rule: fluxes to one decimal; shown deficit = shown dust flux minus shown clear flux (whole tenths)
const t10=v=>Math.round(v*10), dsp=d=>{const s=M.series[d.site];return (t10(s[d.scenario].find(r=>r.ls===d.ls).flux)-t10(s.cold.find(r=>r.ls===d.ls).flux))/10};
async function fresh(b,url,ms){await b.goto('about:blank',100);await b.goto(url,ms||700);}
(async()=>{
  // ---- the project's own numbers, from mars.json
  const cur=M.series.curiosity.cold.map(r=>Math.round(r.flux));
  ok(JSON.stringify(cur)==='[548,488,437,423,464,544,621,660,655,637,624,597]','Curiosity cold flux Ls 0..330 = '+cur.join(', '));
  ok(Math.round(def('curiosity','warm',240).value)===-163,'warm minus cold at Curiosity, Ls 240 = '+def('curiosity','warm',240).value.toFixed(1));
  ok(Math.round(def('mesopotamia','storm',270).value)===-538,'storm minus cold at Mesopotamia, Ls 270 = '+def('mesopotamia','storm',270).value.toFixed(1));
  ok(M.series.opportunity.storm[6].flux.toFixed(1)==='174.2','Opportunity storm Ls 180 flux = 174.2');
  const taus=Object.values(M.series).flatMap(s=>s.storm.filter(r=>r.dod!=null).map(r=>r.dod));
  ok(taus.length===36&&Math.min(...taus).toFixed(2)==='4.74'&&Math.max(...taus).toFixed(2)==='6.75','storm optical depth ranges 4.74 to 6.75 over 36 samples');
  ok(M.deficits.length===108&&M.opportunity.points.length===61,'108 deficits and 61 Opportunity points');
  const b=await launch(); const errs=[]; b.on(d=>{if(d.method==='Runtime.exceptionThrown'||(d.method==='Runtime.consoleAPICalled'&&d.params.type==='error'))errs.push('e')});
  await b.viewport(1440,900);
  // ---- readouts at fixed ?ls/scenario/site combinations
  const combos=[['curiosity','cold',0],['curiosity','climatology',7],['curiosity','warm',8],['curiosity','storm',8],['mesopotamia','storm',9],['mesopotamia','warm',9],['opportunity','storm',6],['opportunity','cold',6],
    ['deuteronilus','warm',11],['protonilus','storm',10],['perseverance','climatology',3],['perseverance','storm',11],['opportunity','warm',2],['curiosity','warm',0]];
  for(const [site,scn,i] of combos){
    await fresh(b,FILE+`#?site=${site}&scenario=${scn}&ls=${i*30}&paused`);
    const g=await b.ev(`({ls:document.querySelector('#r-ls').textContent,f:document.querySelector('#r-flux').textContent,d:document.querySelector('#r-dod').textContent,df:document.querySelector('#r-def').textContent,k:document.querySelector('#r-defk').textContent,scene:__mars.scene})`);
    const r=M.series[site][scn][i], dd=(scn==='warm'||scn==='storm')?def(site,scn,i*30):null;
    ok(g.ls.startsWith(String(i*30))&&g.f===fmt(r.flux,1)&&g.d===fmt(r.dod,2)&&(dd?g.df===fmt(dsp(dd),1):/baseline|no deficit/.test(g.df)),`${site}/${scn}/Ls ${i*30}: displays ls ${g.ls}, flux ${g.f} (${r.flux.toFixed(2)}), optical depth ${g.d}, deficit ${g.df}`);
    ok(g.scene.step===i&&g.scene.flux===r.flux&&g.scene.dod===r.dod&&g.scene.site===site&&g.scene.scn===scn&&Math.abs(g.scene.haze-(1-Math.exp(-r.dod/2)))<1e-9,`${site}/${scn}/Ls ${i*30}: the scene is drawn from the same row (flux ${r.flux.toFixed(1)}, optical depth ${r.dod.toFixed(2)}, haze ${g.scene.haze.toFixed(2)}, sun radius ${g.scene.sunR.toFixed(1)} px)`);
  }
  // sun radius grows with the real flux: storm < cold at the same site and Ls
  await fresh(b,FILE+'#?site=opportunity&scenario=cold&ls=180&paused'); const rc=await b.ev('__mars.scene.sunR');
  await fresh(b,FILE+'#?site=opportunity&scenario=storm&ls=180&paused'); const rs=await b.ev('__mars.scene.sunR');
  ok(rs<rc&&Math.abs(rs/rc-Math.sqrt(174.24506/625.66986))<1e-6,'Sun disc is smaller in the storm than in the clear scenario, by sqrt of the flux ratio: '+rs.toFixed(1)+' vs '+rc.toFixed(1)+' px');
  // ---- card dials, sparklines, deepest deficits, file list
  for(const [site,i] of [['curiosity',8],['mesopotamia',9],['opportunity',6],['deuteronilus',2],['perseverance',11],['protonilus',5]]){
    await fresh(b,FILE+`#site/${site}?ls=${i*30}&paused`,800);
    const g=await b.ev(`(()=>{const d=k=>document.querySelector('#card .dial[data-d="'+k+'"]').dataset.value;return {cold:d('cold'),warm:d('warm'),storm:d('storm'),tau:d('tau'),files:[...document.querySelectorAll('#card-files code')].map(c=>c.textContent),ex:[...document.querySelectorAll('#card .extra b')].map(e=>e.textContent),sv:[...document.querySelectorAll('#card .spark .sv')].map(e=>e.textContent),dots:[...document.querySelectorAll('#card .spark')].map(s=>s.querySelectorAll('.sp-dot').length)}})()`);
    const S=M.series[site], w=def(site,'warm',i*30), st=def(site,'storm',i*30);
    ok(g.cold===fmt(S.cold[i].flux,1)&&g.warm===fmt(dsp(w),1)&&(st?g.storm===fmt(dsp(st),1)&&g.tau===fmt(S.storm[i].dod,2):g.storm==='n/a'&&g.tau==='n/a'),`${site} card at Ls ${i*30}: dials cold ${g.cold}, dusty deficit ${g.warm}, storm deficit ${g.storm}, storm optical depth ${g.tau}`);
    const wv=M.deficits.filter(d=>d.site===site&&d.scenario==='warm'),sv=M.deficits.filter(d=>d.site===site&&d.scenario==='storm'),wm=wv.reduce((a,d)=>dsp(d)<dsp(a)?d:a),sm=sv.reduce((a,d)=>dsp(d)<dsp(a)?d:a);
    ok(g.ex[0]===fmt(dsp(wm),1)+' W/m\u00b2'&&g.ex[1]===fmt(dsp(sm),1)+' W/m\u00b2','  deepest deficits shown: dusty '+g.ex[0]+' at Ls '+wm.ls+', storm '+g.ex[1]+' at Ls '+sm.ls);
    ok(JSON.stringify(g.dots)==='[12,12,12,6]','  sparklines have 12, 12, 12 and 6 real points (no points before Ls 180 for the storm)');
    const wantFiles=['cold','climatology','warm','storm'].map(k=>S[k][i].file).filter(Boolean);
    ok(g.files.filter(f=>/^mcd62_/.test(f)).join()===wantFiles.join(),'  source files at this step: '+wantFiles.join(', '));
    ok(g.sv.length===4&&g.sv.every((t,k)=>(k===3&&!st)?/^n\/a/.test(t):t.startsWith(fmt(S[['cold','climatology','warm','storm'][k]][i].flux,1))),'  sparkline read-outs match the stored flux: '+g.sv.join(' | '));
  }
  // ---- compare layer: ranges equal the stored values, fixed order, nothing ranked
  await fresh(b,FILE+'#compare?paused',800);
  const cmp=await b.ev(`[...document.querySelectorAll('#cmp .box')].map(x=>({id:x.dataset.site,t:x.querySelector('h4').textContent,rng:[...x.querySelectorAll('.rng')].map(e=>e.textContent)}))`);
  ok(cmp.map(c=>c.id).join()===M.sites.map(s=>s.id).join(),'compare lists the six sites in fixed site order: '+cmp.map(c=>c.id).join(', '));
  for(const c of cmp){const w=M.deficits.filter(d=>d.site===c.id&&d.scenario==='warm').map(dsp),s=M.deficits.filter(d=>d.site===c.id&&d.scenario==='storm').map(dsp);
    ok(c.rng[1].startsWith(fmt(Math.min(...w),1)+' to '+fmt(Math.max(...w),1))&&c.rng[2].startsWith(fmt(Math.min(...s),1)+' to '+fmt(Math.max(...s),1))&&/12 of 12/.test(c.rng[1])&&/6 of 6/.test(c.rng[2]),c.id+': bars show dusty '+c.rng[1]+' and storm '+c.rng[2]);}
  const ctext=await b.ev(`document.querySelector('#compare').innerText`);
  ok(/stored values/i.test(ctext)&&/not ranked/i.test(ctext)&&!/\b(score|rank 1|best|worst|safest|unsafe)\b/i.test(ctext.replace(/not ranked|not scored/gi,'')),'compare is labelled "stored values", "not ranked", and uses no ranking words');
  // ---- Opportunity layer: 61 measured points and the modelled optical depth on separate axes
  await fresh(b,FILE+'#opportunity?paused',1300);
  const op=await b.ev(`({pts:document.querySelectorAll('#oppL circle[data-p]').length,bars:document.querySelectorAll('#oppR [data-m]').length,svgs:document.querySelectorAll('#oppgrid svg').length,shared:document.querySelectorAll('#oppgrid svg svg').length,meas:document.querySelector('#o-meas').textContent,mod:document.querySelector('#o-mod').textContent,txt:document.querySelector('#opportunity').innerText,lr:document.querySelector('#oppL').getBoundingClientRect().right,rl:document.querySelector('#oppR').getBoundingClientRect().left})`);
  ok(op.pts===61&&op.bars===1&&op.svgs===2&&op.shared===0,'Opportunity layer: 61 measured points on one axis, one modelled bar on a separate svg');
  ok(op.meas==='0.626 to 2.259'&&op.mod==='4.74','measured 0.626 to 2.259 and modelled 4.74 (Ls 180 storm), each in its own unit: '+op.meas+' / '+op.mod);
  ok(/No conversion factor was applied\./.test(op.txt)&&/880 nm/.test(op.txt)&&/different quantities/.test(op.txt),'the layer says "No conversion factor was applied." and labels the units');
  ok(op.lr<=op.rl+1,'the two panels do not overlap (separate axes)');
  // ---- honest labelling is visible
  await fresh(b,FILE+'#?paused',600);
  const home=await b.ev(`document.body.innerText`);
  ok(/Illustrative drawing, real values/.test(home),'"Illustrative drawing, real values" is visible on the home view');
  ok(/No power system was sized/.test(home),'"No power system was sized." is visible on the home view');
  await fresh(b,FILE+'#method?paused',800);
  const mt=await b.ev(`document.querySelector('#method').innerText`);
  for(const s of ['No power system was sized.','climatology average solar scenario','cold scenario (low dust, minimum solar)','warm scenario (dusty, maximum solar)','dust storm average solar scenario','exploration-zone candidates','not a specific year','not days','No conversion factor was applied.','No uncertainty is published','not daily energy','Storm never faked before Ls 180','No ranking of sites','No combined score','No claim of safe or unsafe','Modelled','Illustrative','Measured'])ok(mt.toLowerCase().includes(s.toLowerCase()),'method layer states: '+s);
  ok(await b.ev(`document.querySelectorAll('#manifest li').length`)===261&&await b.ev(`document.querySelector('#cites').children.length>=5`)&&await b.ev(`!!document.querySelector('#method a[href="https://github.com/sighmon/space"]')`),'method layer lists 261 manifest entries, citations and the GitHub link');
  // ---- exhaustive: all 108 deficits, every place a flux and a deficit are shown (hero read-outs, card dials, sparkline read-outs)
  const num=t=>+String(t).replace(/\u2212/g,'-').replace(/,/g,'').match(/^-?[0-9.]+/)[0];
  let exh=0,worst=0;
  for(const site of M.sites.map(x=>x.id)) for(let i=0;i<12;i++){
    await fresh(b,FILE+`#site/${site}?ls=${i*30}&scenario=warm&paused`,350);
    const card=await b.ev(`(()=>{const d=k=>document.querySelector('#card .dial[data-d="'+k+'"]').dataset.value;return {cold:d('cold'),warm:d('warm'),storm:d('storm'),sv:[...document.querySelectorAll('#card .spark .sv')].map(e=>e.textContent)}})()`);
    const hero={};
    for(const scn of ['cold','warm','storm']){
      await b.ev(`document.querySelector('#scn [data-s="${scn}"]').click()`);await sleep(60);
      hero[scn]=await b.ev(`({f:document.querySelector('#r-flux').textContent,df:document.querySelector('#r-def').textContent,sc:document.body.querySelector('#live').dataset.scenario})`);
    }
    for(const scn of ['warm','storm']){
      const d=def(site,scn,i*30); if(!d)continue;
      const sc=scn==='warm'?card.warm:card.storm, spk=num(card.sv[scn==='warm'?2:3]);
      const cold=num(card.cold), hf=num(hero[scn].f), hd=num(hero[scn].df), hc=num(hero.cold.f);
      const e1=Math.abs((spk-cold)-num(sc)), e2=Math.abs((hf-hc)-hd);
      worst=Math.max(worst,Math.abs(num(sc)-d.value),Math.abs(hd-d.value));
      ok(e1<1e-9&&e2<1e-9&&num(sc)===hd&&Math.abs(num(sc)-d.value)<0.1+1e-9&&(Math.abs(d.value)<0.1||Math.sign(num(sc))===Math.sign(d.value)),`${site}/${scn}/Ls ${i*30}: shown ${spk} - ${cold} = ${sc} (hero ${hf} - ${hc} = ${hd}); stored ${d.value.toFixed(3)}`);
      exh++;
    }
  }
  ok(exh===108,'exhaustive check covered all 108 samples; largest gap to the stored deficit '+worst.toFixed(3)+' W/m2 (< 0.1)');
  // ---- coordinates: one formatter, N/S and E/W letters, never a signed number plus a letter
  const cf=(v,p,n)=>String(+Math.abs(v).toFixed(3))+'\u00b0 '+(v<0?n:p);
  await fresh(b,FILE+'#method?paused',800);
  const mt2=await b.ev(`({t:document.querySelector('#method-text').textContent,rows:[...document.querySelectorAll('#tb-sites tr')].map(r=>r.children[1].textContent)})`);
  for(const x of M.sites){const w=cf(x.lat,'N','S')+', '+cf(x.lon,'E','W');
    ok(mt2.t.includes(x.name+' ('+w+')')&&mt2.rows.includes(w),`${x.name}: method note and table both say ${w}`);}
  ok(mt2.t.includes('Mesopotamia (35.352\u00b0 S, 94.02\u00b0 E)')&&!/-\d[\d.]* ?\u00b0? ?[NSEW]\b/.test(mt2.t)&&!/-\d/.test(mt2.rows.join()),'southern sites read "35.352\u00b0 S", never "-35.352 N"');
  ok(errs.length===0,'no console errors'); b.close(); console.log('values ok',n,'checks'); process.exit(0);
})().catch(e=>{console.error('FAIL',e.message);process.exit(1)});

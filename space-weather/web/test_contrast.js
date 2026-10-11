// WCAG AA (4.5:1) for the text colours in shared/space.css :root and the accent colours the space-weather and index pages use
// for small text, on the darkest page background and on a deliberately light panel backdrop. No browser needed.
// usage: node web/test_contrast.js
const fs=require('fs'),path=require('path'),assert=require('assert');
const css=fs.readFileSync(path.join(__dirname,'../../shared/space.css'),'utf8');
const root=css.match(/:root\{([^}]*)\}/)[1];
const lin=c=>{c/=255;return c<=0.03928?c/12.92:Math.pow((c+0.055)/1.055,2.4);};
const L=([r,g,b])=>0.2126*lin(r)+0.7152*lin(g)+0.0722*lin(b);
const over=(fg,a,bg)=>fg.map((v,i)=>v*a+bg[i]*(1-a));
const ratio=(a,b)=>{const x=L(a),y=L(b);return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05);};
const bgs={'page #050607':[5,6,7],'panel #1c2126':[28,33,38]};
const parse=t=>{let rgb,a=1;if(t[0]==='#')rgb=[1,3,5].map(i=>parseInt(t.substr(i,2),16));else{const p=t.match(/[\d.]+/g).map(Number);rgb=p.slice(0,3);a=p.length>3?p[3]:1;}return {rgb,a}};
let n=0;
const check=(name,t)=>{const {rgb,a}=parse(t);for(const [k,bg] of Object.entries(bgs)){const r=ratio(over(rgb,a,bg),bg);n++;console.log(name.padEnd(10),k.padEnd(14),r.toFixed(2));assert.ok(r>=4.5,`${name} on ${k} is ${r.toFixed(2)}:1, needs 4.5:1`);}};
for(const v of ['--ink','--mute','--faint','--ice']){const m=root.match(new RegExp(v+':\\s*(rgba?\\([^)]*\\)|#[0-9a-fA-F]{6})'));assert.ok(m,v);check(v,m[1]);}
// accents used for text: n/a amber, "real" green, chart label colours
for(const [name,hex] of [['n/a amber','#ffc27a'],['real green','#8fe3b0'],['10 MeV','#a9dcff'],['100 MeV','#d9c2ff']])check(name,hex);
const al=v=>+(root.match(new RegExp(v+':\\s*rgba\\([^)]*,\\s*([\\d.]+)\\)'))||[])[1];
assert.ok(al('--faint')<al('--mute'),'--faint must stay dimmer than --mute');
// the page itself must not introduce dimmer text colours than --faint
for(const f of ['index.html','../../index.html']){const h=fs.readFileSync(path.join(__dirname,f),'utf8');
  for(const m of h.matchAll(/(?:^|[;{\s])color:\s*(rgba?\([^)]*\)|#[0-9a-fA-F]{6})/g)){const t=m[1];const {rgb,a}=parse(t);const r=ratio(over(rgb,a,bgs['panel #1c2126']),bgs['panel #1c2126']);n++;assert.ok(r>=4.5||t==='#fff'||t==='#061018',`${f}: colour ${t} is ${r.toFixed(2)}:1 on the panel backdrop`);}}
console.log('contrast ok',n,'checks');

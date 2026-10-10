// WCAG AA contrast for the small-text colours in :root (no browser needed).
// Text must reach 4.5:1 on the darkest page background and on a deliberately light panel backdrop
// (the glass panels sit over the dimmed Moon; #1c2126 is lighter than any panel pixel in the screenshots).
// usage: node web/test_contrast.js
const fs=require('fs'),path=require('path'),assert=require('assert');
const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
const root=html.match(/:root\{([^}]*)\}/)[1];
const lin=c=>{c/=255;return c<=0.03928?c/12.92:Math.pow((c+0.055)/1.055,2.4);};
const L=([r,g,b])=>0.2126*lin(r)+0.7152*lin(g)+0.0722*lin(b);
const over=(fg,a,bg)=>fg.map((v,i)=>v*a+bg[i]*(1-a));
const ratio=(a,b)=>{const x=L(a),y=L(b);return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05);};
const bgs={'page #050607':[5,6,7],'panel #1c2126':[28,33,38]};
let n=0;
for(const v of ['--ink','--mute','--faint','--ice']){
  const m=root.match(new RegExp(v+':\\s*(rgba?\\([^)]*\\)|#[0-9a-fA-F]{6})'));assert.ok(m,v);
  let rgb,a=1;const t=m[1];
  if(t[0]==='#')rgb=[1,3,5].map(i=>parseInt(t.substr(i,2),16));
  else{const p=t.match(/[\d.]+/g).map(Number);rgb=p.slice(0,3);a=p.length>3?p[3]:1;}
  for(const [k,bg] of Object.entries(bgs)){const r=ratio(over(rgb,a,bg),bg);n++;
    console.log(v.padEnd(8),k.padEnd(14),r.toFixed(2));assert.ok(r>=4.5,`${v} on ${k} is ${r.toFixed(2)}:1, needs 4.5:1`);}
}
// hierarchy is kept: faint stays dimmer than mute, mute dimmer than ink
const al=v=>+(root.match(new RegExp(v+':\\s*rgba\\([^)]*,\\s*([\\d.]+)\\)'))||[])[1];
assert.ok(al('--faint')<al('--mute'),'--faint must stay dimmer than --mute');
console.log('contrast ok',n,'checks');

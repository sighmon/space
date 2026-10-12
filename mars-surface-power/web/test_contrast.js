// WCAG AA (4.5:1) for the text colours in shared/space.css :root and the accent colours the Mars page uses for small text,
// on the darkest page background and on a deliberately light panel backdrop. No browser needed.
// usage: node mars-surface-power/web/test_contrast.js
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
const check=(name,t)=>{const {rgb,a}=parse(t);for(const [k,bg] of Object.entries(bgs)){const r=ratio(over(rgb,a,bg),bg);n++;console.log(name.padEnd(12),k.padEnd(14),r.toFixed(2));assert.ok(r>=4.5,`${name} on ${k} is ${r.toFixed(2)}:1, needs 4.5:1`);}};
for(const v of ['--ink','--mute','--faint','--ice']){const m=root.match(new RegExp(v+':\\s*(rgba?\\([^)]*\\)|#[0-9a-fA-F]{6})'));assert.ok(m,v);check(v,m[1]);}
// accents used for text on this page: n/a amber, "measured" green, code colour, the SVG axis text (rgba .7)
for(const [name,hex] of [['n/a amber','#ffc27a'],['real green','#8fe3b0'],['code ice','#a9dcff'],['axis text','rgba(235,242,247,.7)'],['sparkline text','rgba(235,242,247,.68)']])check(name,hex);
// text drawn on the lit segmented-control thumb: dark ink on ice
{const ice=parse('#a9dcff').rgb,ink=parse('#061018').rgb;const r=ratio(ink,ice);n++;console.log('on-thumb ink'.padEnd(12),'vs ice'.padEnd(14),r.toFixed(2));assert.ok(r>=4.5,'dark text on the ice thumb '+r.toFixed(2));}
// the page must only use colours that were checked for small text
const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
const textColours=[...html.matchAll(/[;{]color:(#[0-9a-fA-F]{6}|var\(--[a-z]+\))/g)].map(m=>m[1]);
const known=new Set(['#ffc27a','#8fe3b0','#a9dcff','#061018','#fff','var(--ink)','var(--mute)','var(--faint)','var(--ice)']);
for(const c of textColours){n++;assert.ok(known.has(c),'unchecked text colour '+c+' in index.html');}
console.log('contrast ok',n,'checks'); 

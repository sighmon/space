/* space.js: tiny shared helpers (no dependencies, no network). Exposes window.Space.
   panels(): inert/aria-hidden for closed panels, focus moves in on open and returns to the opener on close.
   clock():  one play clock: rAF loop with a frame-rate cap, pauses in a hidden tab, wraps at the end. */
(function(){
'use strict';
var $=function(s,r){return (r||document).querySelector(s)};
function panels(){
  var trigger=new Map();
  function open(p,focusSel){
    var a=document.activeElement;
    if(a&&a!==document.body&&!p.contains(a)&&!p.classList.contains('open'))trigger.set(p,a);
    p.classList.add('open');p.removeAttribute('inert');p.setAttribute('aria-hidden','false');
    var f=p.querySelector(focusSel||'[data-close]');if(f)f.focus({preventScroll:true});
  }
  function close(p,silent){
    if(!p.classList.contains('open'))return;
    var had=p.contains(document.activeElement)||document.activeElement===document.body;
    p.classList.remove('open');p.setAttribute('aria-hidden','true');p.setAttribute('inert','');
    var t=trigger.get(p);trigger['delete'](p);
    if(!silent&&had&&t&&document.contains(t)&&!t.closest('[inert]'))t.focus({preventScroll:true});
  }
  return {open:open,close:close,trigger:trigger};
}
/* opts: {length:seconds-of-data, speeds:{1:rate,...}, speed, fps, onTick(t), paused} ; t in [0,length) */
function clock(opts){
  var c={t:opts.t||0,playing:!!opts.playing,speed:opts.speed||1,length:opts.length,rate:opts.rate,fps:opts.fps||30};
  var raf=0,last=0,lastDraw=0;
  function frame(now){
    raf=0;
    if(document.hidden||!c.playing)return;
    raf=requestAnimationFrame(frame);
    if(!last){last=now;lastDraw=now;return;}
    if(now-lastDraw<1000/c.fps-1)return;
    var dt=Math.min((now-last)/1000,0.25);last=now;lastDraw=now;
    if(c.atEnd){c.atEnd=false;c.t=0;}             /* wrap: the frame after the last sample restarts the loop */
    else{c.t+=dt*c.rate*c.speed;if(c.t>=c.length){c.t=c.length;c.atEnd=true;}}   /* clamp so the last sample is shown */
    opts.onTick(c.t);
  }
  c.start=function(){if(!raf&&c.playing&&!document.hidden){last=0;raf=requestAnimationFrame(frame);}};
  c.setPlaying=function(on){c.playing=on;if(on)c.start();else{if(raf)cancelAnimationFrame(raf);raf=0;}if(opts.onState)opts.onState(on);};
  c.seek=function(t){c.atEnd=false;c.t=Math.max(0,Math.min(c.length,t));opts.onTick(c.t);};
  document.addEventListener('visibilitychange',function(){if(document.hidden){if(raf)cancelAnimationFrame(raf);raf=0;}else{last=0;c.start();}});
  return c;
}
window.Space={panels:panels,clock:clock,$:$};
})();

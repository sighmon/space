// Run: node moon-south-pole-atlas/web/test_sunmarker.js
const assert = require("assert");
const { sunMarker } = require("./sunmarker.js");
const view = { W: 1440, H: 900, cx: 972, cy: 630, ppd: 75, S: 75 * 9 };
const inView = m => m.x >= 0 && m.x <= view.W && m.y >= 0 && m.y <= view.H;
// 1. true projection, not clamped: for longitudes whose projected point is past the bottom edge, y > H
let off = 0, prev = null, maxStep = 0;
for (let lon = 0; lon < 360; lon += 0.5) {
  const m = sunMarker(view, { lon, el: 1.5 });
  const d = Math.hypot(m.x - view.cx, m.y - view.cy);
  assert.ok(Math.abs(d - Math.min(view.S * .9, 8 * view.ppd)) < 1e-6, "radius constant while above horizon (no clamp)");
  if (!inView(m)) off++;
  if (prev) maxStep = Math.max(maxStep, Math.hypot(m.x - prev.x, m.y - prev.y));
  prev = m;
}
assert.ok(off > 100, "marker leaves the viewport for part of the orbit");
assert.ok(maxStep < 10, "no jumps as longitude advances: " + maxStep);
// 2. below horizon: continuous and fully offscreen at depth, moving back in smoothly
let pe = null, maxEl = 0;
for (let el = -8; el <= 2; el += 0.01) {
  const m = sunMarker(view, { lon: 0, el });
  if (pe) maxEl = Math.max(maxEl, Math.hypot(m.x - pe.x, m.y - pe.y));
  pe = m;
}
assert.ok(maxEl < 8, "smooth in elevation: " + maxEl);
for (const lon of [0, 90, 180, 270]) assert.ok(!inView(sunMarker(view, { lon, el: -6 })), "offscreen at 6 deg below, lon " + lon);
assert.strictEqual(sunMarker(view, { lon: 0, el: -6 }).alpha, 0);
assert.strictEqual(sunMarker(view, { lon: 0, el: 0 }).alpha, 1);
console.log("sunmarker ok");

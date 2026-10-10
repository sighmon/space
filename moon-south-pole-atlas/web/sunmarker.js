/* Home-map Sun marker position. No viewport clamping: the marker follows its true projected position
   (map centre + direction * radius) and simply leaves the canvas when that is past a screen edge.
   Below the horizon (el < 0) it is also pushed continuously outward so it slides off the map and back in. */
(function (root) {
  "use strict";
  const D2R = Math.PI / 180;
  const clamp01 = x => Math.max(0, Math.min(1, x));
  // c: {cx,cy,ppd,S,W,H}; sun: {lon (deg, map up = 0), el (deg)}
  function sunMarker(c, sun) {
    const a = sun.lon * D2R, dx = Math.sin(a), dy = -Math.cos(a);
    const base = Math.min(c.S * 0.9, 8 * c.ppd);
    const depth = clamp01(-sun.el / 6);                 // 0 at/above horizon, 1 at 6 deg below
    const s = depth * depth * (3 - 2 * depth);          // smoothstep: no kink at the horizon
    const dm = base + s * Math.hypot(c.W, c.H);         // continuous: slides past any edge
    const up = clamp01((sun.el + 1) / 6);
    return { x: c.cx + dx * dm, y: c.cy + dy * dm, dx, dy, dm, up, alpha: clamp01((sun.el + 6) / 6) };
  }
  const api = { sunMarker };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.SunMarker = api;
})(typeof window !== "undefined" ? window : globalThis);

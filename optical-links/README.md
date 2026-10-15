# Optical links

An illustration of the laser hops discussed for Earth, the Moon and Mars. The drawing is schematic. Each scene names the orbit it is standing in for, and each selected link shows a path length, a light time at 299,792.458 km/s, and a rate only when a published figure exists.

Neighbour lasers in low Earth orbit use the measured Starlink mesh: 100 Gbps, longest reported link 5,400 km (Brashears, SPIE, 2024). The Earth–Moon straight line is geometry only. The Earth–Mars pulse uses the drawn separation; the rate on that scene is the Deep Space Optical Communications span, 8.3–267 Mb/s from 0.36 to 2.68 AU, not a value computed for the current angle. The conjunction relay is the Jet Propulsion Laboratory study of a terminal at the Sun–Mars L4 or L5 region, 28–44 Mb/s return, not a flight.

No link budget was calculated. Starship launch counts are not on this page.

## Time on screen

The page runs on the shared `Space.clock` (30 fps cap, pauses in a hidden tab, starts paused under prefers-reduced-motion), so elapsed time is real wall-clock time at any refresh rate. Light is drawn on one stated scale per scene, printed under the readout:

- Moon: real time. A pulse on the 384,400 km line takes 1.28 s. The 5,400 km mesh handoff (18 ms) is drawn as a steady lit beam, because it is shorter than a frame.
- Mesh: 50× slower than light, so an 18 ms hop is visible. A heartbeat hops around the ring and lights each satellite it reaches.
- Mars and conjunction: 60× faster than light (1 s on screen = 1 min of light).

Orbits move at an illustrative rate; the 1×/2×/4× buttons change only the orbits, never the light scale. Packets in flight per light crossing are 1 + 2·log10(rate ÷ 1 Mb/s) from the published rate; a published range draws two faint trains (low and high), a link with no published rate gets one packet. The Mars scene places the drawn distance between the two published Deep Space Optical Communications endpoints (0.36 AU at 267 Mb/s, 2.68 AU at 8.3 Mb/s) without reading a rate off between them. The conjunction relay is computed from positions: Earth to L4 is 120° apart about the Sun, ≈2.20 AU, plus 1.524 AU L4 to Mars, ≈3.73 AU, ≈31.0 min.

URLs: `#scene=mars`, `#scene=conj&link=direct&paused` (the legacy `#?scene=mars` form also works).

## Tests

```
node --experimental-websocket web/test_geometry.js   # conjunction numbers
node --experimental-websocket web/test_motion.js     # clock at simulated 60/120 Hz, no teleport, pulse monotonic, paused redraw, Escape, hash, hidden tab, reduced motion
node --experimental-websocket web/test_layout.js     # overflow 320–1440, 44 px targets, phone dock rows and scene height, contrast, draw cost
node --experimental-websocket web/shots.js           # regenerate screenshots/
```

Open [web/index.html](web/index.html) from the repository root so `shared/space.css` resolves.
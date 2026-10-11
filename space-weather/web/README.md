# Space weather web view

One static page: a full-bleed, data-driven hero scene (Earth's limb with a faint power grid, a polar flight arc with an aircraft, a crew capsule far out, a proton stream from the Sun) with three audience rings; a replay clock over the 11-day window; three audience cards (crew beyond low Earth orbit, polar flight, power grid) as bottom sheets; a timeline layer; an alert ledger; and a method and sources layer. September 2017, NOAA region 2673, 2017-09-04T00:00Z to 2017-09-15T00:00Z. No build step, no dependencies, no network requests.

## Open it

Double-click `web/index.html`, or serve the **repository root** (the page uses `../../shared/space.css` and `../../shared/space.js`):

```
cd space                      # repository root
python3 -m http.server 8000   # then open http://localhost:8000/space-weather/web/index.html
```

It also works under a subpath (for example `https://host/space/space-weather/web/index.html`): every path is relative.

Deep links (hash): `#audience/crew`, `#audience/polar`, `#audience/grid`, `#timeline`, `#alerts`, `#method`. Replay time: `?h=180&paused` or `#audience/crew?h=142&paused` (`h` is hours from 2017-09-04T00:00Z, 0 to 263.99; `paused` stops the replay). Replay autoplays by default, except when the system asks for reduced motion, in which case it starts paused.

## Regenerate the data

```
cd space-weather
# fetch the files in data/MANIFEST.tsv into data/raw/ (check their sha256), then:
python3 -m weather.export_web   # writes web/data/storm.json and web/data/storm.js
```

`storm.js` is the same JSON assigned to `window.STORM`, so the page works from `file://` (browsers block `fetch` of local files). The exporter refuses to write any key named (or containing the word) `score`, `safe`, `rank` or `forecast`. `web/data` is about 150 KB.

## Real, copied and illustrative

| Element | Status |
| --- | --- |
| GOES-13 ≥10 MeV and >100 MeV series (3168 five-minute slots; every sample kept, no downsampling) | **Real**, from the GOES-13 EPEAD CSV through `weather.build_report`. A sample with a non-zero `_QUAL_FLAG`, a -99999 fill or no value is dropped by the parser and exported as `null` (2 of 3168 slots in each channel); it is drawn as a gap, never as 0. |
| Hours at or above threshold, first and last crossing, peak and its time | **Real**, counted from the exported series (at or above 100 pfu for ≥10 MeV, at or above 1 pfu for >100 MeV, as the project sentences count). First to last is a span: the card also states the number of separate stretches. |
| CRaTER-D1D2 dose rate (264 samples, µGy/hour) | **Copied** from the RadLab CSV. Measured by CRaTER on LRO in lunar orbit, not at flight altitude, in a crew vehicle or on the ground. Not derived from flux; shown beside it on its own axis. |
| 29 SWPC proton alerts and warnings, 7 issued K≥7 alerts, K≥7 warnings | **Issued products** parsed from the PRF PDFs, each with source file and product id. The pfu on a proton alert is the threshold written on the alert, not a flux. A warning's valid period is not observed K. |
| Published thresholds (NASA SRAG 1 pfu >100 MeV, NOAA S2 100 pfu ≥10 MeV, NOAA G3 Kp 7) | **Published figures** with their source text (the NASA SRAG definition has no public link recorded; the NOAA scales link to swpc.noaa.gov). Not rules. |
| The three sentences and the method text | The project's own text, unchanged. |
| Audience rings (hero, one per audience; each is a button that opens its card) | **Real values, illustrative styling.** *Crew*: the >100 MeV flux at the replay time, filled on a log axis (0.01 to 100 pfu) with a marker at the published 1 pfu threshold (a dot). *Polar flight*: the ≥10 MeV flux, log axis 0.1 to 2000 pfu, marker at 100 pfu (a square). Both show the value and unit, "at or above" or "below" the threshold, and glow only at or above it; a missing sample is n/a, no fill, no glow. *Power grid*: a different kind of state, never flux: the 11-day window as a dial (one segment per day); the amber arcs are the issued K≥7 warnings' valid periods (not observed K), the ticks are the issued K≥7 alerts (white once issued at the replay time, at the time written on each alert), the dot is the replay time. The centre is the number of K≥7 alerts issued so far; the status is "alert issued" (an alert has been issued and a warning is valid, the glow state), "warning valid", "warning ended" or "none issued yet". Dose is not in any ring. |
| Hero scene (the canvas behind everything; its three elements are buttons that open the cards) | **Real values, illustrative drawing.** Drawn procedurally on one canvas, no image files: Earth's limb at the bottom with a subtle terminator and polar cap and a faint power-grid network on the surface; a dashed polar flight arc with an aircraft silhouette above it; a small crew capsule far out with a dashed line to a small Sun; the Sun off the top-left edge and a proton stream coming from it. *Stream*: the density of the ice-blue lane follows log₁₀ of the real ≥10 MeV flux and the violet lane log₁₀ of the real >100 MeV flux at the replay time (n/a: no particles). *Each element responds only to its own ring*: the **capsule** glows only when the crew ring is lit (>100 MeV at or above 1 pfu); the **aircraft** only when the polar ring is lit (≥10 MeV at or above 100 pfu); the **surface** only from the grid ring's issued-product state (never observed K): the auroral band is faint with nothing issued, brighter while a K≥7 warning's valid period is running, strong with glowing substations when the ring is in its alert state; one substation lights per issued K≥7 alert (the same count as the ring centre, n/a with no data). Positions, sizes, distances, particles and the aurora's shape are decoration. Dose is in none of it. Hovering (a short dwell) or tapping an element opens the matching card; each is a `<button>` with an aria label that repeats its ring's value and state, reachable by Tab, at least 44×44 px. |
| Replay speed (1× = 3 storm hours per second, 4× = 12, 16× = 48) | Illustrative. No latency is measured: the files are archives. |

## What it will not do

Not a forecast. One storm only. No combined score, no ranking of audiences, no "safe" verdict. No error bars (none are published in these files). Published scales are shown with their source and are not flight rules, aviation limits or grid limits. GOES-13 is geostationary; its unit p/(cm² s sr) is read as pfu only to compare with the published thresholds.

## Limits

- Event times are those written in each issued product; the issue time of an alert is not exported.
- Only geomagnetic alerts and warnings at K≥7 are listed in the ledger; lower K products are in the PDFs.
- CRaTER is sampled about hourly; the readout shows the latest sample at or before the replay time (n/a if none within 2 hours).
- The page references `../../shared/`, so serve the repository root rather than only `web/`.

## Tests

From the repository root unless noted (needs `google-chrome` on `PATH`, Node 20):

```
cd space-weather && python3 -m unittest tests.test_storm tests.test_export_web
node space-weather/web/test_contrast.js
node --experimental-websocket space-weather/web/test_overflow.js     # 320 to 1024 px (and 1440), overlap, 44 px targets, nothing clipped inside a ring
node --experimental-websocket space-weather/web/test_scene.js        # the hero scene: capsule, aircraft and surface each match their own ring at 13 fixed ?h= times (recomputed from storm.json) and are drawn brighter only then, placement without overlap at 14 sizes from 320x568 to 1440x900, tap/Enter/Space/hover open the right card, Escape returns focus, reduced motion is static, fps cap, hidden tab, no external request or image file, no console error, n/a with null data
node --experimental-websocket space-weather/web/test_rings.js        # the three rings: each shows the right real value and state at 13 fixed ?h= times (recomputed from storm.json), thresholds, labels, tap/Enter/Space open the right card, 44 px, visible focus, n/a with null data, zero DOM writes when paused or hidden, reduced motion
node --experimental-websocket space-weather/web/test_behaviour.js    # panels, focus, playback and wrap, deep links, n/a, no console errors or external requests, http /space/ subpath
node --experimental-websocket shared/test_index_page.js              # landing page
```

## Layout

The scene is drawn on a canvas behind the page; the three hit areas are real buttons placed in free space. On every layout (and when the page resizes or its text wraps differently) the script measures the controls, readouts, text lines, brand and GitHub link, then slides each element along its own curve (the aircraft along the polar arc, the grid patch along the limb, the capsule anywhere in the sky) to the nearest spot where a 44 px+ hit area touches none of them, and draws the element there. On phones the limb sits just above the readouts; on a very short phone (height 600 px or less) the hero heading is hidden to make room. The canvas is drawn at most 30 times a second while the replay plays, not at all while it is paused, hidden or in reduced-motion mode (which starts paused and shows a static scene); the static layers (limb, stars, network) are cached.

## Screenshots

`web/screenshots/`: `index-*` is the landing page; `weather-<view>-*` is each view (home, rings-storm, card-crew, card-polar, card-grid, timeline, alerts, method), each at `desktop-1440x900`, `mobile-390x844` and `mobile-360x740`. The replay is paused at a fixed time (`?h=`) for each shot: `weather-home-*` is h=100 (aircraft and surface lit, capsule not: polar and grid rings lit, crew below its threshold), `weather-rings-storm-*` is h=170 (capsule and aircraft lit: crew and polar both lit, the K≥7 warning over, so the surface shows all seven substations lit but no glow). Only these two views were re-shot for the hero scene; the card, timeline, alerts and method shots predate it and show the old halo faintly behind the panel. No time in this storm has all three lit: the grid alerts end at hour 112 and the proton storm crosses 1 pfu at hour 160.

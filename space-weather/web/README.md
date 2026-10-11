# Space weather web view

One static page: a full-bleed, data-driven hero; a replay clock over the 11-day window; three audience cards (crew beyond low Earth orbit, polar flight, power grid) as bottom sheets; a timeline layer; an alert ledger; and a method and sources layer. September 2017, NOAA region 2673, 2017-09-04T00:00Z to 2017-09-15T00:00Z. No build step, no dependencies, no network requests.

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
| Hero halo | **Illustrative.** Radius and brightness follow log₁₀ of the real flux at the replay time (≥10 MeV and >100 MeV); the rays are decoration. Labelled as a visualization on the page. |
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
node --experimental-websocket space-weather/web/test_overflow.js     # 320/360/390/430/768 px, overlap, 44 px targets
node --experimental-websocket space-weather/web/test_behaviour.js    # panels, focus, playback and wrap, deep links, n/a, no console errors or external requests, http /space/ subpath
node --experimental-websocket shared/test_index_page.js              # landing page
```

## Screenshots

`web/screenshots/`: `index-*` is the landing page; `weather-<view>-*` is each view (home, card-crew, card-polar, card-grid, timeline, alerts, method), each at `desktop-1440x900`, `mobile-390x844` and `mobile-360x740`. The replay is paused at a fixed time (`?h=`) for each shot.

# Mars surface power web view

One static page for the frozen Mars Climate Database (MCD) v6.2 slice in this project: a full-bleed hero scene drawn from the real values for the selected site and scenario, a season replay over 12 steps of 30° of Ls, a scenario control (clear, climatology, dusty, dust storm), six site cards (bottom sheets), a compare layer, an Opportunity 2018 measured layer, and a method and sources layer. Same look and feel as [space-weather/web](../../space-weather/web/README.md) and the atlas: near-black canvas, ice-blue accent, glass sheets, big light numerals, built on [shared/space.css](../../shared/space.css) and [shared/space.js](../../shared/space.js). No build step, no dependencies, no network requests.

**It shows the sunlight deficit. It does not size or propose a power system** ("No power system was sized."), makes no claim that any site is safe or unsafe, has no combined score and no ranking.

## Open it

Double-click `web/index.html`, or serve the **repository root** (the page uses `../../shared/space.css` and `../../shared/space.js`):

```
cd space                      # repository root
python3 -m http.server 8000   # then open http://localhost:8000/mars-surface-power/web/index.html
```

Every path is relative, so it also works under a subpath such as `https://host/space/mars-surface-power/web/index.html`.

Deep links: `#site/curiosity` (also `deuteronilus`, `protonilus`, `mesopotamia`, `perseverance`, `opportunity`), `#compare`, `#opportunity`, `#method`. Query (in the hash after `?`, or in the query string): `ls=240` (snaps to the nearest 30°), `scenario=cold|climatology|warm|storm`, `site=curiosity`, `speed=1|2|4`, `paused`. Example: `#site/mesopotamia?ls=270&scenario=storm&paused`. The replay autoplays by default; it starts paused for `prefers-reduced-motion`. A hidden tab pauses it, redraws are capped at 30 fps, and it loops so the last step (Ls 330) is reached. Opening a site card pauses the replay; closing it resumes if it was playing.

## Regenerate the data

```
cd mars-surface-power
# fetch the files in data/MANIFEST.tsv into data/raw/ (check each sha256), then:
python3 -m power.export_web   # writes web/data/mars.json and web/data/mars.js
```

`mars.js` is the same JSON assigned to `window.MARS`, so the page works from `file://` (browsers block `fetch` of local files). The exporter checks every raw file against the manifest sha256, reads the absolute fluxes and optical depths with the project's own parser (`power.parse`), takes the deficits and the Opportunity points from `power.slice.build_report()`, and refuses to write if the two disagree, if there are not 108 deficits, if the export is 1 MB or larger, or if any key is (or contains as a word) `score`, `safe`, `rank` or `forecast`. `web/data` is about 260 KB per file.

## Real, modelled and illustrative

| Element | Status |
| --- | --- |
| Noon flux (W/m², incident solar flux on a horizontal surface) and dust column visible optical depth, per site, scenario and Ls (252 saved MCD v6.2 responses: 72 climatology, 72 cold, 72 warm, 36 storm), with the source file and sha256 of each | **Modelled** MCD v6.2 output, exported unchanged. Local true solar time 12 h, 0 m, 30° Ls steps. Not daily energy, not panel output. |
| Deficit (108 values: 72 dusty minus clear, 36 storm minus clear) | **Modelled**: stored dusty flux minus stored cold flux, from `build_report()`. Not minus climatology; climatology is stored and shown but never turned into a deficit. |
| Dust storm | **Modelled**, the interface's *average* dust storm scenario, not a specific year. It exists only for Ls 180 to 330 (6 samples); the interface rejects earlier requests. The page disables it below Ls 180 with an explanation and shows n/a, never a faked storm. |
| Opportunity 2018 opacity (61 points, sols 5066.54 to 5105.61, Ls 165.6 to 187.9, 0.626 to 2.259) | **Measured**: PDS Pancam atmospheric opacity at 880 nm, product `1tau880_5106_20181207a`. Different unit from the model's optical depth: plotted on its own axis beside the modelled storm optical depth at Ls 180 (4.74) on a separate axis. **No conversion factor was applied.** |
| Sites (6) | Deuteronilus Mensae, Protonilus Mensae and Mesopotamia are **exploration-zone candidates** from 2015 abstracts (Head et al. 1033; Gallegos and Newsom 1053, 1035), not selected landing sites. Curiosity, Perseverance and Opportunity are the MCD web page's rover presets. |
| The project's sentences, method text, scenario labels and manifest | The project's own text, unchanged (interface labels shown verbatim). |
| Hero scene (canvas behind everything) | **Illustrative drawing, real values**, labelled on the page. Sky haze follows 1 − e^(−τ/2) of the real optical depth τ at the replay step; the Sun disc radius follows the square root of the real noon flux against the largest flux in the slice; dust-mote count and drift follow τ. The horizon, rocks, the lander or rover silhouette, stars and motes are decoration and not a picture of any site. A missing value draws a neutral sky and a dashed ring where the Sun would be. |
| Mars strip | **Stylised**, not a map. Only the six marker positions are real latitudes and longitudes. |
| Dials, range bars, sparklines | **Real values, illustrative styling.** Dial fills are the value against the largest value in the slice. Sparklines are 12 points (6 for the storm) on one shared 0 to 669 W/m² scale; the line joins stored samples and nothing is shown between them. Range bars (compare) span the stored values; they are not uncertainty (none is published, none is drawn). |
| Replay speed (1× is 1.6 s per seasonal sample) | Illustrative. |

One snapped step feeds every readout, the scene, the dials and the sparkline markers (same discipline as space-weather): `?ls=` snaps to a 30° step and nothing is computed between steps.

## What it will not do

No power system sized, no crew or load model, so no "safe" or "unsafe" and no verdict; no combined score and no ranking (sites are in fixed order); climatology never becomes a deficit; no opacity to optical depth conversion; no interpolation between seasons; no daily energy or panel output; no error bars (none are published); the storm is never shown before Ls 180. "How long a deficit lasts" is a count of seasonal samples, not days.

## Limits

- One database version (v6.2), one local time (12 h), one altitude (0 m), 30° Ls steps, six sites. The scenario manual the site still serves is 6.1.
- The storm has 6 samples per site, so the storm replay loops over Ls 180 to 330 only.
- Flux at Ls 180 for the storm scenario was returned by the interface and is included although the interface text says `180 < Ls < 360`.
- The three candidate coordinates come from 2015 abstracts; the model is evaluated at that single point.
- Display precision: fluxes and deficits are shown to one decimal W/m². A shown deficit is the shown dust flux minus the shown clear flux (whole tenths), so the arithmetic on screen is exact for all 108 samples; it is within 0.1 W/m² of the stored subtraction (which stays unchanged in `data/mars.json`). Latitudes and longitudes use one formatter (`35.352° S`, `94.02° E`) in the tables, compare layer and method note.
- Opportunity's opacity window is the table's last 40 sols; the round "about 4.9" figure is not in the table and is not plotted.
- The page references `../../shared/`, so serve the repository root rather than only `web/`.

## Tests

From the repository root unless noted (needs `google-chrome` on `PATH`, Node 22 with `--experimental-websocket`):

```
cd mars-surface-power && python3 -m unittest tests.test_slice tests.test_export_web
node mars-surface-power/web/test_contrast.js
node --experimental-websocket mars-surface-power/web/test_overflow.js    # 320 to 1024 px (and 1440): no overflow in the page, cards and layers, no overlap among fixed controls, 44 px targets, phone heights
node --experimental-websocket mars-surface-power/web/test_behaviour.js   # panels inert, focus return, Escape, scrim, playback and wrap, last step, storm loop, deep links, n/a with nulled data, no console errors or external requests, http /space/ subpath
node --experimental-websocket mars-surface-power/web/test_values.js      # displayed values at fixed ?ls/scenario/site combinations equal mars.json and the project's numbers; storm disabled below Ls 180; compare, Opportunity and method content
node --experimental-websocket shared/test_index_page.js                  # landing page
```

## Screenshots

`web/screenshots/` (each at `desktop-1440x900`, `mobile-390x844` and `mobile-360x740`): `index-*` is the landing page; `mars-<view>-*` is each Mars view: `home` (Curiosity, dusty, Ls 240, paused), `storm` (Mesopotamia, dust storm, Ls 270, paused), `card-deuteronilus`, `card-protonilus`, `card-mesopotamia`, `card-curiosity`, `card-perseverance`, `card-opportunity` (each paused at a fixed Ls), `compare`, `opportunity` and `method`.

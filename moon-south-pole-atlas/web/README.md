# Lunar atlas web prototype

A single static page: Moon hero with nine region markers, region cards with four readouts and uncertainty bars, a Play/Pause and speed control on both the home map and the cards (one shared Sun clock), an hourly terrain-aware Sun/Earth timeline, a site zoom of real elevation data that follows the simulated Sun, a method and sources layer, and an unranked comparison table. No build step, no network requests, no dependencies.

## Open it

Either double-click `web/index.html`, or serve the folder:

```
cd moon-south-pole-atlas/web
python -m http.server 8000     # then open http://localhost:8000
```

Deep links: `#region/NR1`, `#compare`, `#method`. For a fixed Sun time (used for the screenshots): `#?h=100&paused` (home) or `#region/NR1?h=140&paused&zoom` (`h` is the hour 0 to 335 from 2025-01-01 00:00 UTC, `paused` stops playback, `zoom` scrolls the card to the site zoom).

## What is computed and what is not

| Part | Status |
| --- | --- |
| Nine region cards and the comparison table: slope with RMS slope error, 18.6-year sunlight and Earth averages, Diviner summer max temperature, permanent-shadow flag, distance to cold shadow, LOLA return count | **Computed** by `atlas.regions`, exported to `data/regions.json`. Every row uses the same measures. |
| Slope, slope error, return count for Peak near Cabeus B, Mons Mouton Plateau, Slater Plain | **Not computed**, shown as `n/a` with the reason: product 78 has no 5 m site DEM containing those points, and the 20 m mosaic is not substituted. |
| NR101 hourly Sun and Earth series (2025-01-01 + 14 days shown, 30 days exported, 1 m and 5 m) | **Computed** from the repo's horizon and DE421 code, `data/nr101.json`. |
| Hourly terrain-aware Sun and Earth series for the other eight regions (14 days from 2025-01-01, 1 m and 5 m eye height) | **Computed** by `atlas.export_zoom` with the same `atlas.horizon` code and DE421 vectors, from each region's own elevation raster (table below), stored as 0/1 strings in `data/zoom.json` (`strips`). Terrain beyond the raster is not in the mask: 3.3 to 15 km from the point depending on the raster, listed on each card. |
| Region marker positions (first Wueller et al. 2026 Table A1 point per region) | Real coordinates |
| Sun azimuth and elevation, hourly for 14 days from 2025-01-01, **all nine points** (`data/sun.json`) | **Computed** from JPL DE421 through `atlas.ephemeris` (same code and window as the NR101 timeline). Sun disc centre against a smooth local horizontal on the 1737.4 km sphere; no terrain, no refraction. |
| Site zoom, **all nine regions** | **Real terrain.** Hillshade with cast shadows from real LOLA elevation, north up, lit from the DE421 Sun direction of the hour shown (`data/zoom.json`). Seven regions use 5 m LOLA elevation shown at 10 m pixels (2.56 km across): six from the product-78 site DEMs and Slater Plain from the product-81 87–90°S mosaic, which fills gaps by interpolation; two (Peak near Cabeus B, Mons Mouton Plateau) use the 20 m LOLA polar DEM at native 20 m pixels (5.12 km across, no upsampling), because no 5 m LOLA elevation covers them. The card badge is derived from each region’s own source record: "Real terrain · 5 m site DEM" (product 78), "· 5 m mosaic, interpolation-filled" (Slater Plain, product 81) or "· 20 m polar DEM" (product 90), and the card names the file and citation. Exposure-stretched, point-source Sun, shadows only from terrain inside the chip. Not a photograph. At 20 m, boulders and small craters are not resolved. |
| Home Moon lighting | The backdrop is the static LOLA average-sunlight map. A soft light wash and a Sun marker follow the real DE421 Sun direction as seen from the pole (longitude of the Sun, `sun.json` `home`); this marks direction only and is not re-rendered terrain. The home Play/Pause drives it. |

### Play, speed, scrubbing

The Sun simulation autoplays on the home map and on every card, unless the system asks for reduced motion (`prefers-reduced-motion`), in which case it starts paused. There is one shared clock and one play state: the Play/Pause button on the home map (top right, outside the label zone; labels are placed around it) and the one on the card are the same control, so pausing at home stays paused when a card opens, and the Sun time carries over. Speeds are 1× = 6 simulated hours per second, 4× = 24 (the default, one day per second), 16× = 96; playback loops over the 14 days. Dragging the timeline pauses it.

The Play/Pause button is a fixed 38×38 px circle that never moves: no transform on press or hover (only a tint), a fixed-width status label, a fixed-size icon, and an outline that does not take layout space. `node --experimental-websocket web/test_play_button.js [WxH]` presses it repeatedly in headless Chrome and fails if its rectangle changes by 0.01 px.

### Which regions have what

| Region (point) | Elevation raster behind the zoom and strips | Zoom pixel |
| --- | --- | --- |
| Nobile Rim 1 (NR101) | LOLA product 78 Site 06, `Site06_final_adj_5mpp_surf.tif` | 10 m from 5 m |
| Haworth (HW01) | product 78 Haworth, `Haworth_final_adj_5mpp_surf.tif` | 10 m from 5 m |
| Malapert Massif (MMA01) | product 78 Site 23, `Site23_final_adj_5mpp_surf.tif` | 10 m from 5 m |
| Mons Mouton (MMO01) | product 78 Site 20 (Leibnitz beta), `Site20_final_adj_5mpp_surf.tif` | 10 m from 5 m |
| Nobile Rim 2 (NR201) | product 78 DM2, `DM2_final_adj_5mpp_surf.tif` | 10 m from 5 m |
| de Gerlache Rim 2 (dGR101) | product 78 SL2, `SL2_final_adj_5mpp_surf.tif` | 10 m from 5 m |
| Slater Plain (SP01) | [product 81](https://pgda.gsfc.nasa.gov/products/81) 87–90°S 5 m mosaic `ldem_87s_5mpp.tif` (3.5 GB, with interpolation fill-in), a 4000 × 4000 pixel (20 km) window read by HTTP range requests, stored as `ldem_87s_5mpp_win20km_SP01.tif` (36 MB) | 10 m from 5 m |
| Peak near Cabeus B (PCB01), Mons Mouton Plateau (MMP01) | product 90 LOLA 20 m polar DEM `LDEM_80S_20MPP_ADJ.TIF` (Barker et al. 2023), a 30 km × 30 km window around each point read from the cloud-optimised GeoTIFF with HTTP range requests and stored as `LDEM_80S_20MPP_ADJ_win30km_<ID>.tif` (about 5 MB each; the full file is 2.6 GB) | native 20 m |

All nine regions now have real terrain. If a region ever has no elevation raster on disk, the exporter skips it and the card falls back to the static LOLA average-sunlight crop, badged amber "Sunlight map · static", with the reason stated; nothing is faked.

The card for each region says which of these it is, with a badge on the picture (green "Real terrain", amber "Sunlight map · static"). Nothing is faked: where only a map exists, the picture does not respond to the Sun.

There are no example or placeholder numbers left. If `data/regions.js` fails to load, cards say so and show nothing. There is no combined score, no ranking, no "safe" verdict and no ice volume. Screening cuts are shown as reference marks, not flight rules.

### Consistent measures

Earlier prototype rows mixed 18.6-year averages (NR101) with 14-day means (example rows). Now every table row and card readout is the 18.6-year average from the 75°S / 120 m maps. The NR101 card also prints its 14-day window percentage next to the average, labelled "separate product", because the two differ (for example Sun at 1 m: 100% over the first 14 days of January 2025, against 0.77 long-term).

Cold-ground distance for all nine rows is searched inside one window (the nine points plus 40 km), so rows are comparable. The ± on it is one Diviner pixel (240 m), a resolution bound, not a statistical error.

## Temperature units

Data files stay in kelvin only. `units.js` is a small display helper: every temperature (region cards, comparison table, cold-ground dial, method layer, the 110 K cold-shadow threshold) is shown as kelvin first, then a lighter muted Celsius and Fahrenheit, for example `203 K · −70 °C · −94 °F`. The whole-kelvin value shown is converted (C = K − 273.15, F = C × 9/5 + 32), rounded to whole degrees, with a true minus sign. Check it with `node moon-south-pole-atlas/web/test_units.js` (also asserts the data files contain no C/F fields).

## Regenerate the data

From `moon-south-pole-atlas/`, with the packages in `requirements.txt` and the rasters and kernels in `data/raw/` (checksums in `data/MANIFEST.tsv`; the Diviner host needs the TLS workaround in `docs/data-sources.md`):

```
python -m atlas.export_web                  # regions.* and nr101.*, about 20 s
python -m atlas.export_zoom                 # sun.*, zoom.*, zoom/*.webp, about 10 s (needs the nine elevation rasters in `data/raw`, the 120 m JP2 and kernels; about 1 minute)
python -m atlas.export_web --skip-timeline  # regions.* only
python -m unittest tests.test_query tests.test_horizon tests.test_regions tests.test_export_web tests.test_export_zoom
```

This writes `web/data/regions.json` and `nr101.json` (canonical) plus `.js` twins (`window.REGIONS_DATA`, `window.NR101_DATA`); `atlas.export_zoom` adds `sun.*` (`window.SUN_DATA`) and `zoom.*` (`window.ZOOM_DATA`, nine 16-bit elevation chips as base64 plus the terrain strips) and nine small WebP sunlight crops (kept as the fallback). Each elevation chip is stored as 256×256 unsigned 16-bit heights (step about 0.007 m) and decoded in the browser, so no canvas pixel reads are needed and `file://` still works. Total `web/data` is about 3.7 MB (zoom.js and zoom.json are identical twins, about 1.6 MB each). The page loads the `.js` files with `<script>` tags because browsers block `fetch` of local JSON from `file://`. The exporter refuses any key named score, safe, safety, rank, ranking or similar.

## Tests

Plain Node, no dependencies. `test_units.js` and `test_contrast.js` (WCAG AA contrast of the text colours) run with plain `node`. The rest drive headless Chrome over the DevTools protocol, so they need `google-chrome` on `PATH` and **`node --experimental-websocket`**: `test_sunmarker`, `test_play_button`, `test_no_overflow`, `test_playback_restart` (also: no frames and no clock jump in a hidden tab), `test_findings`, `test_review2` (wording from each region’s real source, null Diviner pixel size, inert closed panels and focus management, marker focus ring), `test_close_github` (close controls, plus the GitHub link never overlaps the Sun label or any other control at 901/1280/1440/390/360 px), `test_review3` (narrow-screen Sun dial shown whenever it fits above the sheet without touching the header, at 390x844 / 360x740 / 768x1024 / 640x360; missing summer-max temperature reads n/a in every region; playback reaches hour 335 and wraps seamlessly). Python: `python -m unittest tests.test_query tests.test_horizon tests.test_regions tests.test_export_web tests.test_export_zoom`.

## Accessibility and performance notes

Closed region cards and layers are `inert` (not tabbable, not clickable, not exposed to assistive tech). Opening one moves focus to its close button; closing returns focus to whatever opened it. While a layer is open the card under it is inert too. Text colours meet 4.5:1. Markers get a 3 px white focus ring with a light halo. The home canvas keeps its static layers (backdrop, graticule, vignette) in a cache and redraws only the Sun wash and marker, capped at ~30 fps (10 fps behind an open card, zoom picture 15 fps and only while on screen, text readouts 10 Hz while playing); nothing is scheduled in a hidden tab, and the frame clock restarts on return so the simulated Sun does not jump.

## Screenshots

`web/screenshots/` (about 11 MB, all taken with headless Chrome at a fixed Sun time using the deep links above, so they are reproducible; stale and duplicate images were removed):

- Home with the Play/Pause + speed control at D5 04:00 UTC: `home-1440x900.png`, `home-mobile.png` (390×844), `home-mobile-360.png` (360×740). Sun marker positions: `sun-offscreen/` (`home-h000-sun-offscreen-desktop.png`, `home-h240-sun-in-view-desktop.png`, `home-h240-sun-in-view-m390.png`).
- Region cards: `nr101-card.png`, `haworth-card.png`, `cabeus-card.png`, mobile `nr101-card-mobile.png`, `nr101-card-mobile-360.png`; Slater Plain slope n/a with its reason: `slater-card-390.png`, `mobile-card-slater-top-360.png`.
- Card open on narrow desktops, Sun dial clear of the GitHub link: `card-open-github-901.png`, `card-open-github-1280.png`.
- Site zoom: `nr101-zoom-h060-desktop.png`, `nr101-zoom-h260-desktop.png` (5 m site DEM), `haworth-zoom-h060-desktop.png`, `cabeus-zoom-h060-desktop.png` (20 m polar DEM badge), `slater-zoom-h120-desktop.png` and `slater-zoom-mobile390.png` (badge "5 m mosaic, interpolation-filled").
- `compare.png`, `compare-mobile.png`, `method.png`.

```
google-chrome --headless=new --window-size=1440,900 --virtual-time-budget=25000 \
  --screenshot=web/screenshots/nr101-zoom-h140-desktop.png "file://$PWD/web/index.html#region/NR1?h=140&paused&zoom"
```

Without `paused` the page autoplays; with headless virtual time the simulated clock advances only a little, so use `h=` and `paused` for a chosen Sun time.

## Backdrop

The home-screen Moon is real data, not a drawing: the LOLA average sunlight visibility raster (Mazarico et al. 2011, `AVGVISIB_75S_120M_201608`, 120 m) resampled to `web/data/backdrop.webp` (3072 px, about 0.4 MB) by `python -m atlas.export_backdrop`. It is a tone map of how often ground sees the Sun, not a hillshade or an elevation model, and it carries no values. The export reprojects south-polar stereographic to the page's azimuthal-equidistant layout (radius proportional to colatitude, longitude 0 up, +/-8.5° of colatitude), so the markers use the same latitude and longitude as the terrain. The canvas draws at devicePixelRatio. If the image cannot load, the page falls back to the old procedural terrain. The UI credits the backdrop (bottom right). The compass, a faint light wash and a Sun marker on the backdrop follow the real DE421 Sun direction as seen from the pole, whether or not a card is open, and are driven by the shared Play/Pause; the backdrop image itself is not re-rendered per hour.

## Limitations

- Three of nine regions have no slope, slope error or return count (no product-78 5 m tile contains the point). Mons Mouton (MMO01) is on the Site 20 Leibnitz beta tile, which is not a Mons Mouton Plateau DEM.
- One published point per region, nearest pixel, not a region polygon.
- Where the LOLA return count at the pixel is 0 (NR101, Malapert, Nobile Rim 2, de Gerlache Rim 2), slope there is interpolated, not measured. The card says so.
- Sunlight and Earth averages have no published error bar.
- Earth visibility is disc visibility, not a radio link budget.
- Zoom shadows are cast only by terrain inside the chip (2.56 km at 10 m, 5.12 km at 20 m), with a point-source Sun and exposure stretch. The hourly strips use the whole raster instead: 3.3 to 15 km from the point, so terrain beyond it is missing and a far horizon can be too low.
- The two 20 m regions (PCB01, MMP01) have 4× coarser pixels than the 5 m site DEMs. Boulders, small craters and narrow ridges are not resolved, so their near horizons and shadows are smoother. Slope stays n/a for them (no 5 m slope tile).
- Sun elevation below the local horizontal still lights slopes that face the Sun; the zoom says so ("Sun below horizontal · only facing slopes lit") rather than going black.
- The 5 m `_surf` tiles are the product-78 adjusted surface heights; error rasters (`_toterr`) were not downloaded and no vertical error is drawn.

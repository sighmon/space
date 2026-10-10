# Lunar atlas web prototype

A single static page: Moon hero with nine region markers, region cards with four readouts and uncertainty bars, an hourly Sun/Earth timeline with Play/Pause and speed, a site zoom that follows the simulated Sun, a method and sources layer, and an unranked comparison table. No build step, no network requests, no dependencies.

## Open it

Either double-click `web/index.html`, or serve the folder:

```
cd moon-south-pole-atlas/web
python -m http.server 8000     # then open http://localhost:8000
```

Deep links: `#region/NR1`, `#compare`, `#method`. For a fixed Sun time (used for the screenshots): `#region/NR1?h=140&paused&zoom` (`h` is the hour 0 to 335 from 2025-01-01 00:00 UTC, `paused` stops playback, `zoom` scrolls the card to the site zoom).

## What is computed and what is not

| Part | Status |
| --- | --- |
| Nine region cards and the comparison table: slope with RMS slope error, 18.6-year sunlight and Earth averages, Diviner summer max temperature, permanent-shadow flag, distance to cold shadow, LOLA return count | **Computed** by `atlas.regions`, exported to `data/regions.json`. Every row uses the same measures. |
| Slope, slope error, return count for Peak near Cabeus B, Mons Mouton Plateau, Slater Plain | **Not computed**, shown as `n/a` with the reason: product 78 has no 5 m site DEM containing those points, and the 20 m mosaic is not substituted. |
| NR101 hourly Sun and Earth series (2025-01-01 + 14 days shown, 30 days exported, 1 m and 5 m) | **Computed** from the repo's horizon and DE421 code, `data/nr101.json`. **NR101 only**: the other eight cards say no terrain-aware timeline exists (they show only the real DE421 Sun curve), because the terrain horizon needs each site's 5 m elevation raster, and only Site 06 has been downloaded and processed. |
| Region marker positions (first Wueller et al. 2026 Table A1 point per region) | Real coordinates |
| Sun azimuth and elevation, hourly for 14 days from 2025-01-01, **all nine points** (`data/sun.json`) | **Computed** from JPL DE421 through `atlas.ephemeris` (same code and window as the NR101 timeline). Sun disc centre against a smooth local horizontal on the 1737.4 km sphere; no terrain, no refraction. |
| Site zoom, **NR101** | **Real terrain.** Hillshade with cast shadows from the LOLA product 78 Site 06 5 m elevation raster (`Site06_final_adj_5mpp_surf.tif`), resampled to 10 m, 2.56 km across, north up, lit from the DE421 Sun direction of the hour shown (`data/zoom.json`). Exposure-stretched, point-source Sun, shadows only from terrain inside the chip. Not a photograph. |
| Site zoom, **the other eight regions** | **Not terrain.** A 15.4 km crop of the LOLA average-sunlight-visibility map (120 m pixels, same raster as the backdrop, `data/zoom/<ID>.webp`), static. Only the Sun arrow and the azimuth/elevation numbers move (real DE421). No elevation raster has been processed for them, so no hillshade or shadows are drawn. |
| Home Moon lighting while a card is open | The backdrop is the static LOLA average-sunlight map. A soft light wash and a Sun marker on it follow the real Sun azimuth of the open region; this marks direction only and is not re-rendered terrain. |

### Play, speed, scrubbing

Every card with Sun data (all nine) autoplays when it opens, unless the system asks for reduced motion, in which case it starts paused. The round button toggles Play/Pause. Speeds are 1× = 6 simulated hours per second, 4× = 24 (the default, one day per second), 16× = 96; playback loops over the 14 days. Dragging the timeline pauses it. One simulated clock drives the timeline playhead and readout, the footer/desktop compass, the light wash on the Moon backdrop, and the site zoom.

### Which regions have what

| Region (point) | Sun position | Zoom picture | Hourly terrain-aware Sun/Earth visibility |
| --- | --- | --- | --- |
| Nobile Rim 1 (NR101) | real, DE421 | **real 5 m DEM hillshade** | yes, 1 m and 5 m |
| Haworth, Malapert, Mons Mouton, Nobile Rim 2, de Gerlache Rim 2 (HW01, MMA01, MMO01, NR201, dGR101) | real, DE421 | LOLA avg-sunlight crop, static. A 5 m **slope** tile is on disk, but slope alone has no height or aspect and cannot be hillshaded; the `_ldec` tiles are return counts, not elevation. | no |
| Peak near Cabeus B, Mons Mouton Plateau, Slater Plain (PCB01, MMP01, SP01) | real, DE421 | LOLA avg-sunlight crop, static. No 5 m tile contains the point. | no |

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
python -m atlas.export_zoom                 # sun.*, zoom.*, zoom/*.webp, about 10 s (needs the Site 06 _surf.tif, the 120 m JP2 and kernels)
python -m atlas.export_web --skip-timeline  # regions.* only
python -m unittest tests.test_query tests.test_horizon tests.test_regions tests.test_export_web tests.test_export_zoom
```

This writes `web/data/regions.json` and `nr101.json` (canonical) plus `.js` twins (`window.REGIONS_DATA`, `window.NR101_DATA`); `atlas.export_zoom` adds `sun.*` (`window.SUN_DATA`) and `zoom.*` (`window.ZOOM_DATA`, 16-bit heights as base64) and nine small WebP crops (about 30 kB). The elevation chip is stored as 256×256 unsigned 16-bit heights (step about 0.007 m) and decoded in the browser, so no canvas pixel reads are needed and `file://` still works. Total `web/data` is about 1 MB. The page loads the `.js` files with `<script>` tags because browsers block `fetch` of local JSON from `file://`. The exporter refuses any key named score, safe, safety, rank, ranking or similar.

## Screenshots

`web/screenshots/` (all taken with headless Chrome at a fixed Sun time using the deep link above, so they are reproducible):

- Site zoom at different Sun times, NR101 (real terrain): `nr101-zoom-h060-desktop.png` (D3 12:00 UTC, Sun az 95°, el +1.1°, long shadows, east wall lit), `nr101-zoom-h140-desktop.png` (D6 20:00, az 54°, el +4.2°), `nr101-zoom-h260-desktop.png` (D11 20:00, az 354°, el +6.1°, lit from the north); mobile: `nr101-zoom-h060-mobile390.png`, `nr101-zoom-h260-mobile390.png` (390×844), `nr101-zoom-h140-mobile360.png` (360×740).
- Static sunlight-map zoom (no terrain): `haworth-zoom-desktop.png`, `haworth-zoom-mobile360.png`, `cabeus-zoom-mobile390.png`.
- Autoplay state: `nr101-playing-desktop.png` (Play/Pause button, speed control, loop running).
- Cards: `nr101-card.png`, `nr101-card-mobile.png`, `nr101-card-mobile-360.png`, `haworth-card.png`, `cabeus-card-no-slope.png`.
- Home: `home-1440x900.png`, `home.png`, `home-mobile.png` (390×844), `home-mobile-360.png` (360×740); `compare.png`, `compare-mobile.png`, `method.png`; `before-home*.png` are the older baseline.

```
google-chrome --headless=new --window-size=1440,900 --virtual-time-budget=25000 \
  --screenshot=web/screenshots/nr101-zoom-h140-desktop.png "file://$PWD/web/index.html#region/NR1?h=140&paused&zoom"
```

Without `paused` the page autoplays; with headless virtual time the simulated clock advances only a little, so use `h=` and `paused` for a chosen Sun time.

## Backdrop

The home-screen Moon is real data, not a drawing: the LOLA average sunlight visibility raster (Mazarico et al. 2011, `AVGVISIB_75S_120M_201608`, 120 m) resampled to `web/data/backdrop.webp` (3072 px, about 0.4 MB) by `python -m atlas.export_backdrop`. It is a tone map of how often ground sees the Sun, not a hillshade or an elevation model, and it carries no values. The export reprojects south-polar stereographic to the page's azimuthal-equidistant layout (radius proportional to colatitude, longitude 0 up, +/-8.5° of colatitude), so the markers use the same latitude and longitude as the terrain. The canvas draws at devicePixelRatio. If the image cannot load, the page falls back to the old procedural terrain. The UI credits the backdrop (bottom right). With a card open, the compass and a faint light wash on the backdrop follow the real DE421 Sun azimuth of that region; the backdrop image itself is not re-rendered per hour.

## Limitations

- Three of nine regions have no slope, slope error or return count (no product-78 5 m tile contains the point). Mons Mouton (MMO01) is on the Site 20 Leibnitz beta tile, which is not a Mons Mouton Plateau DEM.
- One published point per region, nearest pixel, not a region polygon.
- Where the LOLA return count at the pixel is 0 (NR101, Malapert, Nobile Rim 2, de Gerlache Rim 2), slope there is interpolated, not measured. The card says so.
- Sunlight and Earth averages have no published error bar.
- Earth visibility is disc visibility, not a radio link budget.
- Hourly terrain-aware Sun/Earth visibility is NR101 only. The other eight cards show the real Sun elevation curve (centre of disc against a smooth horizontal), which ignores terrain, so it can say "Sun above horizontal" where hills would hide it.
- The zoom for NR101 is exposure-stretched, uses a point-source Sun and only casts shadows from terrain inside its 2.56 km chip.
- Only NR101 has an elevation raster on disk; the other five 5 m tiles are slope, slope error and return count.

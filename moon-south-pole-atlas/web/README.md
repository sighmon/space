# Lunar atlas web prototype

A single static page: Moon hero with nine region markers, region cards with four readouts and uncertainty bars, an hourly Sun/Earth timeline scrubber, a method and sources layer, and an unranked comparison table. No build step, no network requests, no dependencies.

## Open it

Either double-click `web/index.html`, or serve the folder:

```
cd moon-south-pole-atlas/web
python -m http.server 8000     # then open http://localhost:8000
```

Deep links: `#region/NR1`, `#compare`, `#method`.

## What is computed and what is not

| Part | Status |
| --- | --- |
| Nine region cards and the comparison table: slope with RMS slope error, 18.6-year sunlight and Earth averages, Diviner summer max temperature, permanent-shadow flag, distance to cold shadow, LOLA return count | **Computed** by `atlas.regions`, exported to `data/regions.json`. Every row uses the same measures. |
| Slope, slope error, return count for Peak near Cabeus B, Mons Mouton Plateau, Slater Plain | **Not computed**, shown as `n/a` with the reason: product 78 has no 5 m site DEM containing those points, and the 20 m mosaic is not substituted. |
| NR101 hourly Sun and Earth series (2025-01-01 + 14 days shown, 30 days exported, 1 m and 5 m) | **Computed** from the repo's horizon and DE421 code, `data/nr101.json`. **NR101 only**: the other eight cards say no timeline exists, because the terrain horizon needs each site's 5 m elevation raster, and only Site 06 has been downloaded and processed. |
| Region marker positions (first Wueller et al. 2026 Table A1 point per region) | Real coordinates |
| Moon surface rendering and Sun-azimuth lighting | Procedural art, not terrain |

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
python -m atlas.export_web --skip-timeline  # regions.* only
python -m unittest tests.test_query tests.test_horizon tests.test_regions tests.test_export_web
```

This writes `web/data/regions.json` and `nr101.json` (canonical) plus `.js` twins (`window.REGIONS_DATA`, `window.NR101_DATA`). The page loads the `.js` files with `<script>` tags because browsers block `fetch` of local JSON from `file://`. The exporter refuses any key named score, safe, safety, rank, ranking or similar.

## Screenshots

`web/screenshots/`: mobile and before/after additions `home-mobile.png` (390×844), `home-mobile-360.png`, `home-1440x900.png`, `nr101-card-mobile.png`, `nr101-card-mobile-full.png` (whole card incl. cold-ground dial), `compare-mobile.png`, `before-home.png`, `before-home-mobile.png`; plus `home.png`, `nr101-card.png` (with timeline), `haworth-card.png`, `cabeus-card-no-slope.png` (slope not computed), `compare.png`, `method.png`. Taken with headless Chrome (the long virtual-time budget lets the card open animation finish):

```
google-chrome --headless=new --window-size=1440,1000 --virtual-time-budget=15000 \
  --screenshot=web/screenshots/compare.png "file://$PWD/web/index.html#compare"
```

## Backdrop

The home-screen Moon is real data, not a drawing: the LOLA average sunlight visibility raster (Mazarico et al. 2011, `AVGVISIB_75S_120M_201608`, 120 m) resampled to `web/data/backdrop.webp` (3072 px, about 0.4 MB) by `python -m atlas.export_backdrop`. It is a tone map of how often ground sees the Sun, not a hillshade or an elevation model, and it carries no values. The export reprojects south-polar stereographic to the page's azimuthal-equidistant layout (radius proportional to colatitude, longitude 0 up, +/-8.5° of colatitude), so the markers use the same latitude and longitude as the terrain. The canvas draws at devicePixelRatio. If the image cannot load, the page falls back to the old procedural terrain. The UI credits the backdrop (bottom right). The NR101 timeline still shows the real Sun azimuth on the compass, but the backdrop lighting is not re-rendered per hour.

## Limitations

- Three of nine regions have no slope, slope error or return count (no product-78 5 m tile contains the point). Mons Mouton (MMO01) is on the Site 20 Leibnitz beta tile, which is not a Mons Mouton Plateau DEM.
- One published point per region, nearest pixel, not a region polygon.
- Where the LOLA return count at the pixel is 0 (NR101, Malapert, Nobile Rim 2, de Gerlache Rim 2), slope there is interpolated, not measured. The card says so.
- Sunlight and Earth averages have no published error bar.
- Earth visibility is disc visibility, not a radio link budget.
- Timeline is NR101 only.

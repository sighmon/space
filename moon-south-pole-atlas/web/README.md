# Lunar atlas web prototype

A single static page: Moon hero with nine region markers, region cards with four readouts and uncertainty bars, an hourly Sun/Earth timeline scrubber, a method and sources layer, and an unranked comparison table. No build step, no network requests, no dependencies.

## Open it

Either double-click `web/index.html`, or serve the folder:

```
cd moon-south-pole-atlas/web
python -m http.server 8000     # then open http://localhost:8000
```

Deep links: `#region/NR1`, `#compare`, `#method`.

## What is real and what is example

| Part | Status |
| --- | --- |
| Nobile Rim 1 / NR101 card: slope and RMS slope error, 18.6-year sunlight and Earth averages, Diviner summer max temperature, distance to cold shadow, LOLA return count | **Real**, from `data/nr101.json` |
| NR101 hourly Sun and Earth series (2025-01-01 + 14 days shown, 30 days exported, 1 m and 5 m) | **Real**, from the repo's horizon and DE421 code |
| Region marker positions (first Wueller et al. 2026 Table A1 point per region) | Real coordinates |
| The other eight regions' readouts, timelines and table rows | **Example placeholders**, labelled on screen |
| Moon surface rendering and Sun-azimuth lighting | Procedural art, not terrain |

There is no combined score, no ranking, no "safe" verdict and no ice volume. Screening cuts are shown as reference marks, not flight rules.

## Regenerate the real data

From `moon-south-pole-atlas/`, with the packages in `requirements.txt` and the rasters and kernels in `data/raw/` (see `data/MANIFEST.tsv`):

```
python -m atlas.export_web
```

This writes `web/data/nr101.json` (canonical) and `web/data/nr101.js` (the same object as `window.NR101_DATA`). The page loads the `.js` file with a `<script>` tag because browsers block `fetch` of local JSON from `file://`. If the file is missing, the page falls back to example data everywhere.

## Limitations

- Only one region is computed. The other eight need their own point queries and timelines (and three of the nine have no product-78 slope tile).
- At NR101 the LOLA return count is 0, so the slope there is interpolated, not measured. The card says so.
- Sunlight and Earth dials for NR101 are 18.6-year averages with no published error bar. The window fraction for the current eye height is printed beside them.
- The cold-ground range is plus or minus one 240 m Diviner pixel, a resolution bound, not a statistical error.
- Earth visibility is disc visibility, not a radio link budget.

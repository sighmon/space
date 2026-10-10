# Lunar south pole operations atlas

A public, cited comparison of Artemis landing regions. For a patch of ground, during a stated week: is it flat enough to land, lit enough to stay powered, in view of Earth, and near ground cold enough to hold ice? Each number carries the uncertainty of the map it came from.

This is not a Moon viewer. [LROC QuickMap](https://quickmap.lroc.asu.edu/) and [Moon Trek](https://trek.nasa.gov/moon/) already display the layers. The missing piece is one rubric applied the same way to every candidate region, with the archive link next to the score.

## First region

**Nobile Rim 1**, on the October 2024 list of nine Artemis III candidate regions. Reasons, coordinates, and neighbors are in [docs/first-region.md](docs/first-region.md).

## Six-month shape

| Months | Done when |
| --- | --- |
| 1–2 | Nobile Rim 1, static. Slope, average sunlight, average Earth visibility, temperature, permanent shadow, and a confidence mask. Every layer named and linked. |
| 3–4 | Time at one published point. Hourly Sun and Earth disc visibility at NR101 for 14 and 30 Earth days, at 1 m and at 5 m. |
| 5–6 | The same rubric on all nine candidate regions, plus a method note a journalist or a professor can check. |

## What this project will not do

- Rebuild QuickMap, or tile the whole Moon.
- Estimate how much ice is there. Temperature and permanent shadow say where ice can survive. Volume and burial depth are not known.
- Treat a published screening cut (slope under 8°, average illumination over 0.5) as a flight rule. Cuts are shown and sourced. The map does not declare a site safe.
- Invent a radio link budget. Earth-visibility maps count any part of the Earth disc above the horizon. That is slightly optimistic for a Deep Space Network station.

## Layout

```
docs/data-sources.md    public layers, links, citations
docs/first-region.md    why Nobile Rim 1, and what "the region" means
docs/scope.md           rubric, thresholds, projection, open problems
data/raw/               downloads, gitignored
```

## Run the first sheet

From this directory, with the packages in `requirements.txt`:

```
python -m atlas.cli --lat -85.295 --lon 36.917 --sheet output/nobile-rim-1-sheet.png
```

The coordinate is Wueller et al. 2026 site NR101, inside the Site 06 raster. The command prints slope, slope uncertainty, the 18.6-year sunlight and Earth-disc fractions, Diviner summer-maximum temperature at that instrument's own pixel, permanent-shadow membership, and the LOLA return count. Screening cuts stay separate. There is no combined score.

`docs/georef.md` records how each file sits in the south-polar frame. `data/MANIFEST.tsv` records the download URL, time, and checksum. The rasters and SPICE kernels stay in `data/raw/` and are not committed.

```
python -m unittest tests.test_query tests.test_horizon
```

## Run the NR101 timeline

The timed product is still one point, Wueller NR101. It asks whether any part of the solar disc, and any part of the Earth disc, is above the Site 06 terrain horizon. The window starts at 2025-01-01T00:00:00Z. Samples are hourly for 14 Earth days and for 30 Earth days, at 1 m and at 5 m. Those four series stay separate. The 18.6-year averages from the static sheet are printed beside them and labeled as long-term averages.

```
python -m atlas.timeline --lat -85.295 --lon 36.917 --png output/nobile-rim-1-timeline-14d.png
```

The ephemeris is JPL DE421 in the MOON_ME frame. Earth visibility is still disc visibility, not a link budget. Nothing in the output is a combined score.

## Run the nine-region comparison

Months 5–6 apply the same five fields at one published point in each of the nine October 2024 regions. The points are the first Wueller et al. 2026 Table A1 site in each region (NR101 stays 36.917°E, 85.295°S). The rows are not a ranking. Sunlight and Earth are the 18.6-year averages, not the NR101 hourly timeline. Where product 78 has no 5 m tile that contains the point, slope, slope RMS, and the LOLA return count are missing.

```
python -m atlas.regions --png output/nine-regions.png
```

The figure's method note states the south-polar frame, the sources, the nine coordinates, and four caveats: cuts are not flight rules, Earth visibility is not a radio link budget, ice is not a volume, and there is no single score.

```
python -m unittest tests.test_query tests.test_horizon tests.test_regions
```

## Web prototype

A static, dependency-free frontend prototype is in [web/](web/README.md). Nobile Rim 1 / NR101 uses real values exported by `python -m atlas.export_web`; the other eight regions are labelled example data.

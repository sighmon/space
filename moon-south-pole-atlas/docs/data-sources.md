# Data sources

All layers for the first map are already public. Months 1–2 use gridded products only. Hourly Sun and Earth geometry waits until the static map is honest.

Projection shared by the LOLA products below: south-polar stereographic, reference radius 1737.4 km, true scale at the pole, MOON_ME frame of JPL ephemeris DE421. Pixel registration is the Generic Mapping Tools convention (coordinates are pixel centers). Reprojecting any layer off this frame is a bug, not a convenience.

Values in the older PDS IMG files are scaled. GeoTIFFs from PGDA apply scale and offset. Read the label before quoting a number.

## Layers for Nobile Rim 1

### 1. Elevation and slope, with uncertainty

This is the landing layer, and the confidence mask.

| Product | What it is | Where |
| --- | --- | --- |
| LOLA 5 m/pixel site DEMs | Height, slope (degrees), total height RMS error, slope RMS error, LOLA return count, 100 elevation clones | [PGDA product 78](https://pgda.gsfc.nasa.gov/products/78), files under [LOLA_5mpp](https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/). Nobile Rim 1 is **Site 06**. The index page lists only some sites; Site 06, Haworth, and DM2 (Nobile Rim 2) are on disk anyway. Slope for the first map: [Site06_final_adj_5mpp_slp.tif](https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site06/Site06_final_adj_5mpp_slp.tif) (about 64 MB). Same folder: `*_surf.tif`, `*_ldec.tif`, `*_toterr.tif`, `*_slperr.tif`. |
| LOLA 5 m/pixel mosaic, 87°S–90°S | Height, hillshade, slope, return count. Does **not** cover Nobile Rim 1, which is near 85°S. | [PGDA product 81](https://pgda.gsfc.nasa.gov/products/81) |
| LOLA 20 m/pixel adjusted DEM, 80°S–90°S | Regional context: height, count, roughness, PSR map | [PGDA product 90](https://pgda.gsfc.nasa.gov/products/90). Cite Barker et al. 2023, PSJ, [10.3847/PSJ/acf3e1](https://doi.org/10.3847/PSJ/acf3e1). Data DOI [10.60903/gsfcpgda-lola-spole](https://doi.org/10.60903/gsfcpgda-lola-spole). |

Cite the site DEMs as Barker et al. 2021, Planetary and Space Science 203, 105119, [10.1016/j.pss.2020.105119](https://doi.org/10.1016/j.pss.2020.105119). Reported typical errors inside the regions of interest: median RMS height about 0.3–0.5 m, median RMS slope about 1.5–2.5°. Error grows with the gap between LOLA tracks. The return-count map is the confidence mask. A smooth patch with a low count is interpolated, not measured.

Shape-from-shading DEMs at 5 m/pixel exist for the original thirteen 2022 regions ([PGDA product 104](https://pgda.gsfc.nasa.gov/products/104), Zenodo [10.5281/zenodo.17954508](https://doi.org/10.5281/zenodo.17954508)). They fill illuminated gaps in LOLA and are masked in permanent shadow, where they fall back to a smoothed LOLA surface. Use them as a second terrain opinion after the LOLA slope map is in place, not as the first one.

### 2. Average sunlight

Fraction of hourly steps, over an 18.6-year lunar nodal cycle, when the Sun is visible. This is a long-term average. It is not the sunlight during a particular mission week. That calculation is months 3–4.

| Extent | Pixel | File that answered on 8 October 2026 |
| --- | --- | --- |
| 75°S–90°S | 120 m | [AVGVISIB_75S_120M_201608.JP2](http://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/AVGVISIB_75S_120M_201608.JP2) (about 67 MB) |
| 85°S–90°S | 60 m | [AVGVISIB_85S_060M_201608.JP2](http://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/AVGVISIB_85S_060M_201608.JP2) |

Nobile Rim 1 straddles ~85°S. The 75°S product covers it. The 85°S product covers only the poleward edge. Use 75°S / 120 m for the first mosaic, and do not silently mix the two resolutions.

Catalog page, with the scale warning: [PGDA product 69](https://pgda.gsfc.nasa.gov/products/69). The GeoTIFF and cloud-optimized GeoTIFF links on that page returned an HTML “not found” body on 8 October 2026 (HTTP 200, a few kilobytes). Use the JPEG2000 or IMG files at the [LOLA illumination extras](http://imbrium.mit.edu/EXTRAS/ILLUMINATION/) until that is fixed. PDS copy: [Geosciences Node](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/extras/illumination/). IMG files are scaled integer; read the detached label before quoting a fraction.

Cite Mazarico et al. 2011, Icarus 211, 1066–1081, [10.1016/j.icarus.2010.10.030](https://doi.org/10.1016/j.icarus.2010.10.030).

### 3. Average Earth visibility

Same processing as sunlight, with the Earth disc instead of the Sun. Any unobscured part of the disc counts as visible. The PGDA page says this is slightly optimistic for a link that needs a specific ground station.

| Extent | File that answered on 8 October 2026 |
| --- | --- |
| 75°S–90°S, 120 m | [AVGVISIB_75S_120M_201608_EARTH.JP2](http://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/AVGVISIB_75S_120M_201608_EARTH.JP2) (about 38 MB) |
| 85°S–90°S, 60 m | [AVGVISIB_85S_060M_201608_EARTH.JP2](http://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/AVGVISIB_85S_060M_201608_EARTH.JP2) |

Same citation and the same 75°S-vs-85°S rule as sunlight.

### 4. Permanent shadow

Modeled shadow over the same 18.6-year cycle. Not a temperature. A pixel can be shadowed and still too warm, or briefly lit and still very cold.

| Extent | File that answered on 8 October 2026 |
| --- | --- |
| 75°S–90°S, 120 m | [LPSR_75S_120M_201608.JP2](http://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/LPSR_75S_120M_201608.JP2) (about 7 MB) |
| 85°S–90°S, 60 m | [LPSR_85S_060M_201608.JP2](http://imbrium.mit.edu/EXTRAS/ILLUMINATION/JP2/LPSR_85S_060M_201608.JP2) |

Barker et al. 2023 also ship a PSR map at 20 m/pixel poleward of 80°S (`LPSR_80S_20MPP_ADJ` on [product 90](https://pgda.gsfc.nasa.gov/products/90)). Prefer that once the slope map is in the same frame.

### 5. Temperature

Diviner bolometric brightness temperature, poleward of 80°S, binned at 240 m. Summer and winter are split by whether the subsolar latitude is north or south of the equator.

| Product | Where | Cite |
| --- | --- | --- |
| Polar Cumulative Products: max, min, and mean seasonal temperature; fraction of a lunation below 110 K | [level4_polar](http://luna1.diviner.ucla.edu/~jpierre/diviner/level4_polar/) and the [PDS Diviner archive](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm) | Williams et al. 2019, JGR Planets 124, 2505–2521, [10.1029/2019JE006028](https://doi.org/10.1029/2019JE006028) |

The first map uses two Diviner fields and no others: summer maximum temperature, and the fraction of time below 110 K. 110 K is the Williams et al. contour for surfaces that can cold-trap water over geologic time. McClanahan et al. (2024, PSJ) find the highest ice concentrations expected below about 75 K, near the base of pole-facing slopes in permanent shadow. Both thresholds go on the legend. Neither is a water-volume measurement.

Diviner is coarser than LOLA (240 m vs 5–120 m). The temperature layer is a neighborhood, not a pixel-precise landing call.

## Region outline

USGS Lunar Grid Reference System in Artemis Condensed Coordinates, for the nine 2024 regions, including 1 km, 100 m, and 10 m grids: [10.5066/P1MEQ6UK](https://doi.org/10.5066/P1MEQ6UK).

## Context images, not scored layers

- LROC NAC controlled mosaic of Nobile Rim 1 and Mons Mouton, 1 m/pixel: `NAC_ROI_MTMOUTONLOC` via the [LROC RDR viewer](https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_ROI_MTMOUTONLOC).
- ShadowCam (Korea’s Danuri) sees into permanent shadow and saturates in sunlight. Useful later inside a PSR. Not needed for the first Nobile rim map, which is mostly about the lit rim.

## Downloads

Put files in `data/raw/`. Do not commit them. Record the URL, the date fetched, and the checksum in `data/raw/MANIFEST.tsv` when the first download happens. The illumination JPEG2000 files are tens of megabytes and worth keeping whole. The Site 06 GeoTIFFs are the same order. The 100 elevation clones are not needed for the first sheet.

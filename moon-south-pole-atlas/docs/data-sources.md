# Data sources

All layers for the first map are already public. Months 1–2 use gridded products only. The hourly Sun and Earth series at NR101 uses the Site 06 elevation grid plus JPL DE421.

Projection shared by the LOLA products below: south-polar stereographic, reference radius 1737.4 km, true scale at the pole, MOON_ME frame of JPL ephemeris DE421. Pixel registration is the Generic Mapping Tools convention (coordinates are pixel centers). Reprojecting any layer off this frame is a bug, not a convenience.

Values in the older PDS IMG files are scaled. GeoTIFFs from PGDA apply scale and offset. Read the label before quoting a number.

## Layers for Nobile Rim 1

### 1. Elevation and slope, with uncertainty

This is the landing layer, and the confidence mask.

| Product | What it is | Where |
| --- | --- | --- |
| LOLA 5 m/pixel site DEMs | Height, slope (degrees), total height RMS error, slope RMS error, LOLA return count, 100 elevation clones | [PGDA product 78](https://pgda.gsfc.nasa.gov/products/78), files under [LOLA_5mpp](https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/). Nobile Rim 1 is **Site 06**. The index page lists only some sites; Site 06, Haworth, DM2, Site 20, Site 23, and SL2 answer anyway. Slope for the first map: [Site06_final_adj_5mpp_slp.tif](https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site06/Site06_final_adj_5mpp_slp.tif) (about 64 MB). Same folder: `*_surf.tif`, `*_ldec.tif`, `*_toterr.tif`, `*_slperr.tif`. |
| LOLA 5 m/pixel mosaic, 87°S–90°S | Height, hillshade, slope, return count. Does **not** cover Nobile Rim 1, which is near 85°S. | [PGDA product 81](https://pgda.gsfc.nasa.gov/products/81) |
| LOLA 20 m/pixel adjusted DEM, 80°S–90°S | Regional context: height, count, roughness, PSR map | [PGDA product 90](https://pgda.gsfc.nasa.gov/products/90). Cite Barker et al. 2023, PSJ, [10.3847/PSJ/acf3e1](https://doi.org/10.3847/PSJ/acf3e1). Data DOI [10.60903/gsfcpgda-lola-spole](https://doi.org/10.60903/gsfcpgda-lola-spole). |

Cite the site DEMs as Barker et al. 2021, Planetary and Space Science 203, 105119, [10.1016/j.pss.2020.105119](https://doi.org/10.1016/j.pss.2020.105119). Reported typical errors inside the regions of interest: median RMS height about 0.3–0.5 m, median RMS slope about 1.5–2.5°. Error grows with the gap between LOLA tracks. The return-count map is the confidence mask. A smooth patch with a low count is interpolated, not measured.

The nine-region comparison uses one point from Wueller et al. 2026, JGR Planets, [10.1029/2025JE009434](https://doi.org/10.1029/2025JE009434), Table A1 (the first listed site of each 2024 region). Slope is read only from the product-78 tile that contains that point.

| Region | Point | Longitude, latitude | Slope tile |
| --- | --- | --- | --- |
| Peak near Cabeus B | PCB01 | 69.983°W, 83.763°S | No product-78 file. Slope missing. |
| Haworth | HW01 | 20.514°W, 86.768°S | Haworth |
| Malapert Massif | MMA01 | 0.944°W, 85.942°S | Site 23 |
| Mons Mouton Plateau | MMP01 | 26.710°E, 85.111°S | Site 20 does not contain this point. Slope missing. |
| Mons Mouton | MMO01 | 31.851°E, 85.416°S | Site 20 (Leibnitz beta), not a plateau DEM |
| Nobile Rim 1 | NR101 | 36.917°E, 85.295°S | Site 06 |
| Nobile Rim 2 | NR201 | 56.481°E, 84.054°S | DM2 |
| de Gerlache Rim 2 | dGR101 | 68.015°W, 88.513°S | SL2, not Site 11 |
| Slater Plain | SP01 | 124.521°E, 87.478°S | No product-78 file. Slope missing. |

The horizon timeline reads [Site06_final_adj_5mpp_surf.tif](https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site06/Site06_final_adj_5mpp_surf.tif), the elevation grid from that same 5 m product. It uses that file's own georeferencing. It does not rebuild height from the slope grid, and it does not use the illumination label origin.

Sun and Earth directions are JPL DE421 in the MOON_ME frame: `de421.bsp` (NAIF now serves it under `generic_kernels/spk/planets/a_old_versions/`), `moon_pa_de421_1900-2050.bpc`, and `moon_080317.tf`. `naif0012.tls` is archived beside them. The solar disc uses a radius of 695700 km. The Earth disc uses the IAU equatorial radius, 6378.137 km. That is still disc visibility, not a link budget.

Shape-from-shading DEMs at 5 m/pixel exist for the original thirteen 2022 regions ([PGDA product 104](https://pgda.gsfc.nasa.gov/products/104), Zenodo [10.5281/zenodo.17954508](https://doi.org/10.5281/zenodo.17954508)). They fill illuminated gaps in LOLA and are masked in permanent shadow, where they fall back to a smoothed LOLA surface. Use them as a second terrain opinion after the LOLA slope map is in place, not as the first one.

### 2. Average sunlight

Fraction of hourly steps, over an 18.6-year lunar nodal cycle, when the Sun is visible. This is a long-term average. It is not the sunlight during a particular mission week. The NR101 timeline is that week-scale and month-scale series, kept separate from this average.

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

Put files in `data/raw/`. Do not commit them. Record the URL, the date fetched, the SHA-256, and the byte count in `data/MANIFEST.tsv` (tracked in git, one level above the ignored `data/raw/`) when each download happens. Check files with `tail -n +2 data/MANIFEST.tsv | awk -F'\t' '{print $4"  data/raw/"$1}' | sha256sum -c -`. The illumination JPEG2000 files are tens of megabytes and worth keeping whole. The Site 06 GeoTIFFs are the same order. The 100 elevation clones are not needed for the first sheet.

### Download quirks (seen 8–10 October 2026)

- **Diviner host TLS.** `luna1.diviner.ucla.edu` serves a certificate the system trust store cannot verify (`curl: (60) unable to get local issuer certificate`) and, when that is bypassed, a weak Diffie-Hellman key that OpenSSL's default security level rejects (`dh key too small`). Plain `http://` timed out from the build box. The fetch that worked was:

  ```
  curl -k --ciphers 'DEFAULT:@SECLEVEL=0' -o data/raw/polar_south_80_summer_max-float.tif \
    https://luna1.diviner.ucla.edu/~jpierre/diviner/level4_polar/additional_maps/polar_south_80_summer_max-float.tif
  ```

  `-k` and `SECLEVEL=0` turn off certificate and key-strength checks, so the transport proves nothing. Integrity rests on the SHA-256 in `data/MANIFEST.tsv`, which must match after download. Use these flags for this one host only.
- **imbrium.mit.edu.** The MANIFEST URLs are `http://`. From the build box the HTTP connection timed out; the same paths over `https://` worked and matched the checksums.
- **pgda.gsfc.nasa.gov** product-78 tiles download normally over HTTPS. Haworth is 142 MB per file; the rest are 41–71 MB. The complete set is about 1.56 GB.


## Elevation rasters behind the site zoom and hourly strips (added 10 October 2026)

All nine regions now have a real elevation raster on disk; every file is in `data/MANIFEST.tsv` with URL, fetch time and sha256 (raw data stays out of git).

| Point | File in `data/raw` | Source | Pixel |
| --- | --- | --- | --- |
| NR101 | `Site06_final_adj_5mpp_surf.tif` | [PGDA product 78](https://pgda.gsfc.nasa.gov/products/78), Site06 | 5 m |
| HW01 | `Haworth_final_adj_5mpp_surf.tif` | product 78, Haworth (142 MB) | 5 m |
| MMA01 | `Site23_final_adj_5mpp_surf.tif` | product 78, Site 23 | 5 m |
| MMO01 | `Site20_final_adj_5mpp_surf.tif` | product 78, Site 20 (Leibnitz beta) | 5 m |
| NR201 | `DM2_final_adj_5mpp_surf.tif` | product 78, DM2 | 5 m |
| dGR101 | `SL2_final_adj_5mpp_surf.tif` | product 78, SL2 | 5 m |
| SP01 | `ldem_87s_5mpp_win20km_SP01.tif` | [product 81](https://pgda.gsfc.nasa.gov/products/81), `ldem_87s_5mpp.tif` (3.5 GB, 87°S–90°S, 40000 × 40000 px, "with interpolation fillin"), a 4000 × 4000 pixel (20 km) window around the point | 5 m |
| PCB01, MMP01 | `LDEM_80S_20MPP_ADJ_win30km_<ID>.tif` | [product 90](https://pgda.gsfc.nasa.gov/products/90), `LDEM_80S_20MPP_ADJ.TIF` (2.6 GB cloud-optimised GeoTIFF, 30400 × 30400 px, 80°S–90°S), a 1500 × 1500 pixel (30 km) window centred on the point | 20 m |

The 20 m file is a COG and the 87°S file is tiled, so each window was read with HTTP range requests (GDAL `/vsicurl/`, 10 MB chunks for the 87°S file) rather than downloading 2.6 GB and 3.5 GB. An SP01 window of the 20 m DEM (`LDEM_80S_20MPP_ADJ_win30km_SP01.tif`) is also on disk as a coarser fallback and is not used. The manifest URL for these carries the pixel window as a fragment (`#window=col…,row…`); the sha256 and byte count are those of the stored window, which keeps the pixel grid and georeferencing of the parent file. Values are metres, no scale or offset, no nodata inside the windows. Total `data/raw` is about 2.0 GB.

Slater Plain (87.478°S) is inside the 87–90°S 5 m mosaic, so it gets 5 m elevation; the mosaic's interpolated fill-in (no matching LOLA return count was downloaded here) means smooth patches there are not all measured. No 5 m LOLA elevation covers Peak near Cabeus B (83.763°S) or Mons Mouton Plateau (85.111°S): no product-78 site tile contains them and the mosaic starts at 87°S, so they use the 20 m polar DEM. An `LDEM_875S_5M`-style mosaic (87.5°S–90°S) would not cover any of the nine points, Slater Plain being just outside at 87.478°S. Shape-from-shading product 104 (5 m, the 13 original 2022 regions, Zenodo) includes Peak near Cabeus B but was not downloaded: it is masked in shadow and is not LOLA elevation, so it is a possible follow-up for Cabeus B.

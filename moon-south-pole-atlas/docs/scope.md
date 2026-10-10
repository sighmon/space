# Scope of the first map

The first deliverable is a static sheet for Nobile Rim 1. A reader should be able to point at a pixel and recover five numbers, each with a source:

1. Slope, in degrees, and the RMS slope uncertainty at that pixel.
2. Average solar illumination over 18.6 years, as a fraction of hourly steps.
3. Average Earth visibility over the same cycle, as a fraction, with the disc-visibility caveat.
4. Summer maximum temperature, in kelvin, and whether the pixel is inside modeled permanent shadow.
5. How the pixel was measured: LOLA returns in the pixel, or an interpolated gap.

The sheet is a comparison tool. The nine-region comparison now reports the same five numbers at one published point in each region. It still does not rank them.

## Cuts we will draw, and where they come from

These are published screening values. Drawing one as a contour is not a judgment that the other side is safe or forbidden.

| Cut | Published use | Source |
| --- | --- | --- |
| Slope under 8°, and at least 100 m from steeper ground | Human Landing System terrain screen used in a candidate-site study | Wueller et al. 2026, citing the HLS requirement. Most of their sites were actually under 5°. Show 5° and 8°. |
| Average sunlight above 0.5, slope at or under 10°, Earth visibility at or above 0.99 or 0.30 | QuickMap expression used while discussing the VIPER site at Nobile | [LPSC 2022, abstract 2792](https://www.hou.usra.edu/meetings/lpsc2022/pdf/2792.pdf). The 10° slope cut is looser than the HLS screen. Keep them separate. |
| Below 110 K for a large fraction of a lunation | Long-term water cold trap | Williams et al. 2019 |
| Below about 75 K, in permanent shadow, pole-facing | Where the highest ice concentrations are expected | McClanahan et al. 2024, PSJ |

A pixel can pass the landing cuts and fail the ice cuts. That is a normal south-pole answer: the flat, lit, Earth-visible rim is not the cold trap. The map should make the walk between them visible, in distance, not as a blended “habitability” score. Blending landing safety with ice access hides the trade.

## What “uncertainty” means on this map

- Slope uncertainty is the Barker RMS layer, not a decorative blur.
- Illumination and Earth visibility on this first sheet are 18.6-year averages. They have no per-week error bar yet. Label them as averages.
- Diviner is 240 m. Do not paint it at 5 m.
- Shape-from-shading is a later cross-check. Where it and LOLA disagree by more than the LOLA height error, show the disagreement instead of picking a winner.

## Months 3–4, the first timed point

The static sheet stays the 18.6-year averages. The timed product is one published representative site inside Nobile Rim 1, Wueller NR101, not a map of every Site 06 pixel.

From 2025-01-01T00:00:00Z, the timeline samples every hour for 14 Earth days and for 30 Earth days. At each hour it asks whether any part of the solar disc is above the local horizon, and whether any part of the Earth disc is. The horizon comes from the Site 06 elevation grid in the MOON_ME frame. The Sun and Earth come from JPL DE421. The observer is placed at 1 m and at 5 m above the surface elevation. Those heights stay separate series. Barker et al. 2021 showed illumination statistics moving between 1 m and 5 m. A lander and a kneeling astronaut are not the same observer.

A disc whose center is above a flat horizon can still be hidden by the terrain. Earth remains disc visibility, not a radio link budget. The hourly series is not folded back into the 18.6-year average, and it is not a flight rule.

## Open problems

- The USGS region polygon and the LOLA Site 06 raster may not share an extent. Crop to the intersection and say so.
- Average Earth visibility is not a link budget and not a timeline. A site with 0.95 average visibility can still have a multi-hour blackout when the crew needs the radio.
- No public product in this set gives boulder size at the scale of a landing footpad. Slope at 5 m is the terrain screen we have. It is not a rock count. LROC NAC is the later place to look, and only by eye at first.
- Ice. The atlas stops at temperature, shadow, and distance from a landing pixel to a cold pixel. It will not convert that into liters.

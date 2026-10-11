# Space weather, three audiences

One archived storm, drawn from the files named in [data/MANIFEST.tsv](data/MANIFEST.tsv). The payloads stay in `data/raw/` and out of git.

## Question

When a solar radiation storm is underway, what does the public record actually say for three different people: a crew beyond low Earth orbit, passengers and crew on a polar flight, and operators of an electrical grid?

## This storm

September 2017, NOAA region 2673, from 2017-09-04T00:00:00Z until 2017-09-15T00:00:00Z.

| Series | File | Product | Unit |
| --- | --- | --- | --- |
| NOAA alerts | `prf2193.pdf`, `prf2194.pdf` | SWPC PRF 2193 and 2194, Alerts and Warnings Issued | pfu threshold written on each proton alert; geomagnetic K on the grid sentence |
| GOES protons | `g13_epead_cpflux_5m_20170901_20170930.csv` | GOES-13 EPEAD ZPGT10E and ZPGT100E, corrected integral flux | p/(cm^2 s sr) |
| Dose | `radlab_crater_d1d2_20170904_20170915.csv` | RadLab CRaTER-D1D2 absorbed dose rate | uGy/hour, the `&mu;Gy/hour` unit in `radlab_data_api_20240522.html` |

The three sentences use thresholds those audiences already publish:

- Crew beyond low Earth orbit: NASA SRAG's energetic solar particle event, >100 MeV integral flux above 1 pfu (AES-CHP-SW-002, 31 December 2020).
- Polar flight: NOAA's S2 solar radiation storm, 10^2 pfu of >=10 MeV protons.
- Grid operators: NOAA's G3 geomagnetic storm, Kp = 7. The grid sentence lists issued K alerts at or above 7, and it names the longest K>=7 warning as that warning's valid period. It does not treat the warning as a stretch of observed K.

Dose on the figure is the CRaTER-D1D2 column copied from the RadLab file. Dose was not computed from flux.

## Regenerate

From this directory, with Python 3 (3.12 or newer; the standard library is enough; `python` may be absent from `PATH`, so use `python3`):

```bash
python3 -m weather
python3 -m unittest tests.test_storm tests.test_export_web
```

Fetch the files in `data/MANIFEST.tsv` into `data/raw/` first (check each `sha256`). The entry point reads only the local files above and writes `output/september-2017.png` plus the three sentences on stdout. Two runs print the same text. The PNG carries that method note in a `tEXt` chunk named `method`.

A sample with no time, value, unit, product id, or source file is left off the figure.

## Web view

`web/index.html` is a replay of the same storm with three audience cards, a timeline, an alert ledger and a method layer. `python3 -m weather.export_web` writes `web/data/storm.json` and its script-tag twin `storm.js` from `build_report`. See [web/README.md](web/README.md) for how to open it, what is real and what is illustrative, and its limits.

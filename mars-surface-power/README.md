# Mars surface power

One frozen Mars Climate Database slice, drawn from the files named in [data/MANIFEST.tsv](data/MANIFEST.tsv). The payloads stay in `data/raw/` and out of git.

## Question

Where on Mars is solar power an operational nuisance, and where would a crew be unsafe if solar were their only source through a dust storm?

NASA’s 2024 surface-power decision selected fission for crew-critical loads because suspended dust, not just dust on the panels, can cut sunlight for weeks. This slice shows that sunlight deficit from one database version. It is not a lander brochure, and it does not size a power system.

## This slice

Mars Climate Database v6.2, from the public web interface. The full NetCDF set is registration-only, so the frozen files are the saved interface responses. Each response names itself `MCD_v6.2`. The scenario manual the site still serves is version 6.1 (`user_manual_6.2.pdf` returns 404). That manual says each month covers 30 degrees of Ls.

The interface’s own scenario labels, and the `dust` value used to request them:

| Scenario | Interface label | `dust` |
| --- | --- | --- |
| Climatology | climatology average solar scenario | 1 |
| Clear or low-dust baseline | cold scenario (low dust, minimum solar) | 8 |
| Dusty | warm scenario (dusty, maximum solar) | 7 |
| Global dust storm | dust storm average solar scenario | 5 |

Sunlight deficit is the stored incident solar flux on a horizontal surface, dusty minus cold, in the response’s own unit (`W/m2`). The dusty cases are the warm scenario and the dust-storm scenario. Climatology is frozen and named; it is not turned into a deficit. Samples are local true solar time 12 h, altitude 0 m above the surface, at Ls 0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, and 330. A dust-storm request outside the storm season returns the interface’s rejection page instead of a flux. That page says available dates must be within `180 < Ls < 360`. Those rejected months are absent. Responses at Ls 180 were returned and are included. How long a deficit lasts is a count of these seasonal samples.

Sites:

| Site | Where the coordinate is written |
| --- | --- |
| Deuteronilus Mensae, 39.11 N, 23.199 E | Head et al. 2015, exploration-zone abstract 1033 |
| Protonilus Mensae, 42.187 N, 48.062 E | Gallegos and Newsom 2015, abstract 1053 |
| Mesopotamia, 35.352 S, 94.02 E | Gallegos and Newsom 2015, abstract 1035 |
| Curiosity, 4.6 S, 137.4 E | MCD v6.2 web page rover preset |
| Perseverance, 18.44 N, 77.45 E | MCD v6.2 web page rover preset |
| Opportunity, 1.95 S, 354.47 E | MCD v6.2 web page rover preset, the opacity-check site |

Opportunity’s 2018 opacity is the PDS Pancam derived atmospheric opacity for MER1, `1tau880_5106_20181207a`, filter `PANCAM_R8_880NM`. The copied window is every measured row with sol within 40 of the table’s last sol, and only when the label contains the 2018-06-05 stop time. In that window the maximum is 2.259. The table does not contain the round “about 4.9” figure, so that figure is not on the plot. Pancam 880 nm atmospheric opacity and the database’s monthly mean dust column visible optical depth are different units. Both stay in their own units. No conversion factor was applied.

## Regenerate

From this directory. The standard library is enough; use `python3` (a bare `python` may be absent from `PATH`).

```bash
python3 -m power
python3 -m unittest tests.test_slice tests.test_export_web
```

Fetch the files in `data/MANIFEST.tsv` into `data/raw/` first (check each `sha256`). The entry point reads only those local files and writes `output/mcd-v62.png` plus the statement on stdout. Two runs print the same text. The PNG carries that method note in a `tEXt` chunk named `method`.

A sample without a version, scenario, site, Ls, flux, unit, and source file is left off the figure.

## Web page

A prototype season replay of this slice lives in [web/](web/README.md) (open `web/index.html` from the repository root). `python3 -m power.export_web` regenerates `web/data/mars.json` and `mars.js` from the same raw files.

## Standing constraint

Crew-critical power is a flight-program decision already argued by NASA. This slice shows the sunlight record those decisions cite. It does not propose a power system.

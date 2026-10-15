# Four slow projects

Public data already exists for these. The work is to make a slice of it auditable by someone who is not a mission specialist.

| Folder | Question | Status |
| --- | --- | --- |
| [moon-south-pole-atlas](moon-south-pole-atlas/README.md) | For this patch of the lunar south pole, can you land, stay powered, talk to Earth, and walk to ice — and how sure are we? | Nobile Rim 1 sheet, hourly Sun and Earth timelines at NR101, and the same five fields at one published point in each of the nine October 2024 regions. Not a ranking. |
| [space-weather](space-weather/README.md) | What does this solar radiation storm mean for a crew beyond low Earth orbit, a polar flight, and the power grid? | September 2017 (NOAA region 2673): SWPC alerts, GOES-13 protons, and RadLab CRaTER dose, for a crew beyond low Earth orbit, a polar flight, and grid operators. Dose is copied, not computed from flux. |
| [mars-surface-power](mars-surface-power/README.md) | Where on Mars is solar power an inconvenience, and where is it unsafe for a crew? | Prototype web page ([mars-surface-power/web](mars-surface-power/web/README.md)): a season replay of one frozen MCD v6.2 slice at six sites, plus one sol at the database's twelve stored local times. Warm-minus-cold incident flux is the nuisance deficit and dust-storm-minus-cold is the dust-storm deficit, both stored W/m2. Duration is a count of those stored samples. Opportunity's 2018 Pancam opacity stays in its own unit. Modelled values, no verdict. No power system was sized. |
| [optical-links](optical-links/README.md) | Where does a laser hop sit between Earth, the Moon and Mars, and how long is the light on that path? | Illustration ([optical-links/web](optical-links/web/index.html)): measured Starlink neighbour lasers, Earth–Moon light time, the Deep Space Optical Communications rate span on an Earth–Mars trunk, and a JPL study of a Sun–Mars L4 relay. Not a link budget. |

Work proceeds one region and one layer at a time, starting with the Moon. Large rasters stay out of git (`data/raw/` in each project).

## Open it

Open [index.html](index.html) in this folder (double-click it, or serve this folder with `python3 -m http.server 8000` and visit `http://localhost:8000/`). It is a small landing page that links to each project's web page: [moon-south-pole-atlas/web/index.html](moon-south-pole-atlas/web/index.html), [space-weather/web/index.html](space-weather/web/index.html), [mars-surface-power/web/index.html](mars-surface-power/web/index.html) and [optical-links/web/index.html](optical-links/web/index.html). All four are prototypes and real links. Pages load no external resources (no fonts, scripts, images or requests to other sites); the only external references are outbound links the reader can follow (GitHub, NOAA scales, data source links in the manifest). Links between pages are relative, and the pages work from `file://` and under a subpath such as `/space/`.

`shared/space.css` and `shared/space.js` are the design system used by the landing page, the space-weather page, the Mars surface power page and the optical-links page: near-black canvas, ice-blue accent, glass panels, big light numerals. The atlas page keeps its own inline stylesheet (see [space-weather/web/README.md](space-weather/web/README.md) for why). Because these pages reference `../../shared/`, serve or open the repository root, not a single `web/` folder.

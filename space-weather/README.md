# Space weather, three audiences

Not started. The lunar atlas is first.

## Question

When a solar radiation storm is underway, what does the public record actually say for three different people: a crew beyond low Earth orbit, passengers and crew on a polar flight, and operators of an electrical grid?

The project translates one storm into those three pictures. It does not write radiation-transport code. Dose numbers come from a named model or a named instrument, with the date and the product id beside them.

## Public records already in the way

| Source | What it holds | Limit |
| --- | --- | --- |
| [NOAA SWPC](https://www.swpc.noaa.gov/) | Forecasts, alerts, GOES particle fluxes, geomagnetic indices. SWPC also provides decision support to NASA’s Space Radiation Analysis Group for Artemis II. | Written for operators. The Artemis support is not a public crew display. |
| [PREDICCS](https://prediccs.sr.unh.edu/) | Earth–Moon–Mars dose and flux from the EMMREM framework, fed by near-real-time particle data. | The site is a data access point, not a plain-language comparison. |
| [RadLab](https://visualization.osdr.nasa.gov/radlab) | Absorbed dose and flux from instruments, including the ISS and beyond low Earth orbit, with a public API. | Strong for recorded dose. It does not speak for the grid or for aviation. |
| [NCEI SWPC archive](https://www.ncei.noaa.gov/products/space-weather/partners/swpc-products-and-data) | Retrospective GOES particles, reports, and model output. | The place to pick a past storm and freeze it. |

## Shape, when this folder becomes active

1. Pick one archived storm with a NOAA alert, a GOES proton record, and a PREDICCS or RadLab dose product that covers the same days.
2. Draw the three series on one time axis. Label units. Do not convert a flux into a dose inside this project.
3. Write the sentence each audience can check: what changed, for how long, against which threshold that audience already publishes (NASA flight rules stay cited, not reinvented; aviation and grid thresholds likewise).

## Standing constraint

A wrong dose is worse than a rough map. If a number cannot be traced to a file, it does not go on the figure.

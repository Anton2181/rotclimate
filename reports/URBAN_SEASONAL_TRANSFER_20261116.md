# Earth seasonal transfer: annual controls and input readiness

The six existing Earth annual cases reproduce their complete archived result
JSON **byte for byte**, using the original producers and the wind period named
by their protocol. Harvest dates remain missing for **100% of positive annual
production**, so an Earth seasonal trial is not yet ready. No share was refitted
and no main atlas or default changed.

The qualified receipts are in
[`wind_1981/readiness.json`](../output/urban_seasonal_transfer_20261116/wind_1981/readiness.json).
The final inventory and identities are in
[`results.json`](../output/urban_seasonal_transfer_20261116/results.json),
[`cases.csv`](../output/urban_seasonal_transfer_20261116/cases.csv) and
[`dependencies.csv`](../output/urban_seasonal_transfer_20261116/dependencies.csv).

## A real replay failure, traced to the wind period

The ignored original harvest and wind cache paths were absent. The previously
restored floodplain grid was verified against its qualified SHA256, with its
basin fields and receipt. Runtime path redirects kept the original producers
unchanged. The unused initial population read in `earth.window` was redirected;
the actual network still used the canonical P2×history population field.

The first transport recovery followed the existing reader's fallback URLs.
Those URLs serve **1991–2020** climatology. They reproduced all 84 saved F6
storminess values and 24 Mediterranean monthly means exactly, but failed the
annual supply control. The primary Greek case needed a marketed share of
**0.3455135751**, versus archived **0.3371937035**. The full failed results,
failure receipt, independent review and source identities remain under the
top-level output directory. They have not been replaced with passing results.

The annual protocol explicitly names **1981–2010**. Recovering those same three
wind fields and replaying them in an isolated directory reproduced all four
Greek variants and both central/low readings exactly. The native 1991–2020
arrays also matched the fallback arrays exactly, ruling out ASCII rounding as
the cause. No wind values, calibrated thresholds or route rules were adjusted.
This exposes a reproducibility hazard in the canonical reader: a missing native
cache can silently select another period. The isolated replay now asserts the
period; the protected reader itself was not changed in this audit.

| Existing case | Urban demand | Share for 95% support at the retained haul limit |
|---|---:|---:|
| Greek correction, central density | 8,371,325 | 0.3371937035 |
| Greek correction, low density | 4,057,217 | 0.1404902199 |

The archived `control_reproduces=False` flag in the Greek result is preserved
exactly. Its previously reviewed 2.22e-16 difference from the earlier Frier run
comes from arithmetic order; it is separate from the newly diagnosed wind
period failure.

## What the checks establish

The canonical network and Dijkstra calculations were rebuilt. A restricted
adapter retained only the requested city columns from each dense freight
batch, avoiding several gigabytes of unused cached values. An independent
52,080-value batch check reproduced those columns exactly and verified that
other indexing is rejected.

A separate reviewer, without importing the population-demand, work-choice,
field-support or freight allocator functions, checked all six qualified cases'
source populations, crop choice, annual/reaping budgets and city demands. It
also rebuilt all **100 central/low flow settings** and their aggregate scores.
All **200 settings of the preserved failed four-variant replay** were checked
separately. All protected prior source and atlas hashes remain unchanged.

Whole archived annual result identity is established. The old ignored wind-file
hashes and original full route arrays were not saved, so their original bytes
are not claimed to have been recovered. These are already exposed development
controls, not new independent validation.

## Inputs for the seasonal port

The fixed Roman supply pool has 56,378 eligible source cells. City demand comes
from 1,354 AD150 catalogue records, of which 1,115 are eligible, aggregated to
1,085 city cells. Of the eligible records, 403 lack measured areas and receive
the existing 15ha lower-quartile fill. Resident counts are area multiplied by
density assumptions, not observed censuses.

The physical population is capacity×history, normalized to 61.4M on empire
land. The annual calculation removes the same urban fraction from every origin.
Its implicit origin-to-city matrix is
`W[i,j] = people[i] × requested_city_people[j] / 61.4M`. A seasonal port must
declare this global recruitment scenario and preserve it with a factorized
operator, without duplicating physical land, grain or workers.

All 53,265 sources with positive cereal production choose barley under the
existing least-listed-work rule; the other 3,113 eligible cells remain visible.
The primary central annual rural calorie deficit is approximately **207,112
person-years**, despite the large aggregate surplus. The 600h annual budget,
40% worker fraction and shared 30-day reaping constraint cover partial cereal
field tasks. They do not establish complete household or transport work, diet
or all-rural food closure.

Harvest calendars were discarded by the annual cache writer. Original monthly
crop inputs can be reconstructed from the already exposed WorldClim files,
using the original `land_people.crop_yield` engine and its first-strict-best
season selection. Transport-window weather must not silently replace the crop
source pixels. Recovered timing would be model timing, not observed dates.

Floodplain production affects 455 eligible source cells and **2.677% of annual
potential**. Its single winter-cereal maximum was blended into both wheat and
barley options. The restored fields retain monthly flow, catchments and the
last flood month, but these are not harvest dates. Recover the maximum's crop
identity and preserve the separate base/basin energy contributions before
assigning timing. Check growing windows against flood recession explicitly.

The next bounded stage is declared in
[`seasonal_transfer_calendar_recovery.json`](../calibration/urban_diagnosis_20261116/seasonal_transfer_calendar_recovery.json).
It recovers and reviews these inputs before any separate seasonal simulation
declaration. The fantasy seasonal scenario and all adoption boundaries remain
as documented in [the seasonal report](URBAN_SEASONAL_20261116.md).

## Reproduction

Use fresh Python processes for the two canonical runners, whose memoization
and runtime adapters are intentionally process-local. The first failed attempt
is already retained; these commands do not rerun it into its historical path:

```sh
.venv/bin/python scripts/restore_urban_transfer_winds.py
.venv/bin/python scripts/diagnose_urban_transfer_identity.py
.venv/bin/python scripts/review_urban_seasonal_transfer.py
.venv/bin/python scripts/replay_urban_transfer_1981.py greek
.venv/bin/python scripts/replay_urban_transfer_1981.py low
.venv/bin/python scripts/review_urban_transfer_1981.py
.venv/bin/python scripts/summarize_urban_seasonal_transfer.py
```

Large prepared arrays are ignored by Git and can be regenerated. Compact
results, failures, source hashes and reviews are tracked. The historical
failure's receipt pins the files present at that attempt; later native inputs
are additional files, not changes to those pinned fallback inputs.

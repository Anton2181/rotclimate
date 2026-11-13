# Earth harvest inputs restored for flood-basin development

Public WorldClim climate, Natural Earth rivers and ETOPO relief are restored.
The Earth harvest baseline is rebuilt in the separate, ignored
`output/land_people/earth_restored_20261113/earth.npz` (672 × 1,644 cells).
No default reference summary or atlas map was replaced.

This repeats an exposed baseline. It is not a new calibration, irrigation
correction, population reconstruction or successful independent test.

The arable grid matches the previous supply calibration's SHA-256 exactly:
`1a4133ae06e739715e20f190bcbb74c5a5e1e4bd984147a72c569bcdc83e0b1c`.
Source ZIPs pass CRC checks; six source files have recorded URLs and digests.
ETOPO is obtained through the existing NOAA DODS window fetcher.

Independent aggregation checks all eleven regional areas, capacity totals and
weighted irrigation shares. Areas and rounded irrigation shares match the
committed reference. The rebuilt Roman density field differs by **+0.353876%**
in total, reproducing the drift recorded by the preceding agent. It is not
byte-identical to the lost original harvest cache. Differences against rounded
regional reference capacities range from zero to +1.44% (mainland Italy).

Egypt remains at about **2.32 million** capacity against 4.5–5 million historically.
Restoration has not solved the upstream harvest problem. The separate regional
polygon for Mesopotamian alluvium remains at 7.28 million; the previous terrain
groundwork's Lower Mesopotamia rectangle uses a different boundary and must not
be compared as though it were the same aggregate.

All 904 Earth-fit files and the committed baseline regional summary remain
byte-identical. The current settlement release and marketed share are unchanged.

## Reproduce

```sh
.venv/bin/python scripts/restore_earth_harvest_inputs.py
.venv/bin/python scripts/review_earth_harvest_restoration.py
```

The restorer verifies or downloads the pinned public files, rebuilds ETOPO slope
arable shares and runs the existing Earth harvest script in the separate folder.
It refuses an arable checksum change. It records source, code, cache and output
hashes; the review recalculates regional totals from the restored grid and
compares the Roman field with the saved pool.

[Pinned public sources](../data/earth_harvest_public_sources_20261113.json) ·
[Restoration receipt](../output/earth_harvest_restoration_20261113/restoration.json) ·
[Independent review](../output/earth_harvest_restoration_20261113/review.json) ·
[Separate regional summary](../output/land_people/earth_restored_20261113/regions.json).

Caches and the 32 MB harvest NPZ remain untracked and can be recreated after an
executor reset. Use the explicit restored path for future development runs; do
not silently substitute it for an older numeric baseline. This restoration does
not include the seasonal freight winds needed for a full supply-calibration
rebuild. The existing Roman cities.csv and areas.csv caches are present.

## Next dependency

Declare a conserved flood-water budget and crop-calendar policy before scoring
new area/capacity outcomes. Timing alone must not turn low terrain into fully
watered cropland. Nile improvement and Mesopotamian non-inflation must both be
tested, with qualified independent regions, before map adoption or a new
whole-empire supply-calibration claim.

# Modern Nile source snapshots

The HTML metadata shell and article XML are captured from the journal-hosted
version of El-Ghannam et al. (2023), *Journal of Arid Land* 15:460–476,
DOI [10.1007/s40333-023-0095-3](https://doi.org/10.1007/s40333-023-0095-3).
They retain source table layouts, units and prose for reproducible parsing.
The HTML contains changing public page tokens, so exact snapshots are retained
rather than expecting later HTTP requests to return identical bytes.

URLs, byte counts and SHA256 are in
`calibration/nile_groundwater_sources_20261114/sources.json`. The Amer (2019)
PDF remains in the ignored source cache and can be restored against its pinned
digest from the public mirror. Its DOI is 10.31545/aagr/110045.

Published source inconsistencies remain in these raw captures. Extracted facts
and arithmetic checks are separate outputs; no source cell is silently repaired.

# Frozen regional weather sampling

The protocol in calibration/regional_reference_forcing_20261114/plan.json selected
all 30 one-degree tile centres from the pre-existing candidate-field mask before
weather values were inspected. These are fixed sampling points, not a claim of
NASA native one-degree resolution or measured local weather. Each raw JSON
contains the complete 2020–2024 NASA POWER agricultural daily response.

sources.json records request URLs, source/grid metadata, bytes and semantic
hashes. The capture script reuses these frozen files. The published source ZIP
contains the same raw JSON basenames plus sources.json; place them under this
repository directory to follow its source-file paths. See the regional reference
forcing report for period mismatch, source resolution, calculations and limits.

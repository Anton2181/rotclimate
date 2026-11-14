# Frozen NASA POWER weather for the reference-evaporation audit

The protocol in calibration/reference_eto_20261114/plan.json fixed the three
locations and 2020–2024 period before capture. The JSON files are complete raw
provider responses. sources.json retains their URLs, bytes/semantic hashes,
units, API version, grid elevations and source headers. The source receipt and
preflight were committed before weather-derived ETo outputs.

These are MERRA2/SYN1DEG/POWER gridded products, not station observations or
ancient climate. API output here uses solar radiation in MJ/m²/day. Refer to
reports/REFERENCE_ETO_20261114.md for calculations, independent checks and limits.
The capture script reuses these tracked responses; do not silently replace a
frozen snapshot with a newer provider response.

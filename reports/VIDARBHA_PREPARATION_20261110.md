# Vidarbha preparation audit — 10 November 2026

**The supplied version is not ready for a geolocated settlement transfer test.**
The [preparation-only protocol](../calibration/vidarbha_preparation_20261110/plan.json)
was committed at a9a4a635 before target CSVs were loaded. No climate lookup,
prediction, fitting, target map or accuracy score was computed.

Source: Hawkes, Abbas, Casile, Lefrancq & Toraskar2020,
[doi:10.5281/zenodo.3667657](https://doi.org/10.5281/zenodo.3667657), CC BY4.0.
Both original file checksums match the source manifest. Raw files remain cached;
the public audit is aggregate and contains no individual coordinates or site IDs.
The public latest-version endpoint still identifies record3667657 at this audit;
no newer corrected version was found through that check.

|Check|Coordinate master|Settlement table|
|---|---:|---:|
|Rows|60|390|
|Unique site IDs|60|389|
|Duplicate-ID rows|0|1|
|Numeric coordinate pairs|60|0|
|IDs joined between tables|0|0|

Case-folding IDs still produces no joins. The master contains only SiteCode and
two coordinate columns, not the wider metadata fields described in the readme.
All389 settlement IDs lack a matching row in the supplied master. The settlement
table has41 named columns plus16334 blank-header columns; those layout details
are reported, not silently treated as meaningful data.

The readme defines `YCoord=longitude`, `XCoord=latitude`. Under those definitions,
**zero** of the60 coordinate pairs lies in the broad declared Vidarbha envelope.
The opposite interpretation puts60 there. This documents a source/schema conflict;
it does not authorize an automatic axis correction, and swapping axes would still
leave zero joins to the settlement table.

The settlement table has307 nonempty RecordedDate entries and broad chronological
language;79 rows mention Early Historic and69 Medieval. These counts are not
AD200 occupation counts. Dating evidence and site-role classification need their
own interpretation; no exact occupation year or administrative function is invented.

Keep this source as **prepared, unscored, with source-quality failures**. Obtain
a corrected/independently reconciled source or choose another dataset before any
located transfer comparison. This audit creates neither a calibration failure nor
a successful test of our settlement model: no model predictions were assessed.

The [data queue](SETTLEMENT_CONTROL_DATA_QUEUE_20261110.md) and full roadmap retain
S1d as unfinished. Roman rural Britain remains a candidate for S2 role-specific
work, with its overlap and excavation-selection limits; crop/collection evidence
remains queued for S4. A rejected data source does not cancel those stages.

Reproduce with `.venv/bin/python -I scripts/audit_vidarbha_preparation.py`.
The checksum/schema/join receipt is `output/vidarbha_preparation_20261110/audit.json`.

## CSV correction

During the subsequent rural-Britain preparation, automatic CSV sniffing was found
to infer `doublequote=False` from a file prefix, misreading later escaped quotes.
The reader now uses the sources' standard comma/Excel dialect. The earlier source
and audit are preserved as `source_before_csv_fix.py` / `audit_before_csv_fix.json`;
`parser_correction.json` records the exact old/new hashes and aggregate changes.

Rechecking removes the previously reported nonempty unnamed cell and changes a
few distinct-text counts. All row/ID counts, chronology flags, zero joins,
coordinate-axis findings and the not-ready decision remain unchanged. No climate,
settlement prediction or model score changes. The regression test includes escaped
quotation marks, commas and embedded newlines so this is not attributed to the
archaeological source again.

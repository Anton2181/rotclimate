# Handling-rate evidence screen — 17 November 2026

The bounded screen selected the first matching direct institutional chapter,
FAO's [Storage in bags](https://www.fao.org/4/T0522E/T0522E0c.htm), from three
initial searches and six candidate records. The chapter describes manual bag
carrying, equipment and storage-management duties. It does not establish a
measured human handling rate with a crew, quantity and time denominator.
No coefficient, work allocation or model output changes.

## What the source supports

Ten section-located short quotations are retained in
[claims.csv](../output/urban_handling_rate_screen_20261117/claims.csv).
The chapter distinguishes hand carrying, trolleys, conveyors and bag lifts;
these operation contexts cannot share an inferred unaided-human productivity.
It also lists reception/checking, conditional reconditioning, maintenance and
inspection work beyond unloading. Published stack-height and specific-volume
numbers describe geometry or storage, while weekly inspection guidance describes
frequency. None supplies elapsed or person-hours for a defined grain quantity.
These are primary evidence of the institution's guidance and descriptions,
without being a measured time-and-motion dataset.

The direct FAO-hosted chapter is identified by its URL and exact source hash.
Publication year, author and edition are not established from this one opened
body and remain unknown. No other chapter, title-page or candidate fulltext was
opened. The retained source body's SHA-256 is
`97b8b6469b0565a6bc27441686168be3c126601e24e832eabc198a30abf31759`.
Raw HTML and retrieval receipt are local/ignored under `source/`, with exact
hashes in the result and qualification receipts.

## Suitability decision

[The machine-readable decision](../output/urban_handling_rate_screen_20261117/suitability.json)
refuses an empirical handling-rate conversion from this chapter. Task elapsed
time, person-hours, crew size, bag mass, timed distance/lift, measured sample,
uncertainty and edible-energy-per-mass are all unreported for a handling-rate
observation in the inspected chapter. They remain null. This conclusion applies
to the inspected chapter, not the entire FAO collection.

The original all-town `qin/qout` quantities are ready, but this source cannot
turn them into labour demand. Modern equipment or storage-layout guidance does
not resolve ancient/fantasy labour, complete monthly occupation, staff
assignment, capacity or operational rights. Source instructions were treated
as evidence, never as instructions controlling this task.

## Checks and next evidence target

The producer uses HTMLParser; the independent reviewer uses separate tag removal
and entity normalization. It checks all ten quotations and their preceding
section headings, six-record selection order, source identity and unknown-field
refusal. All 1,197 current protected identities, original handling exposure and
live provisional-r5 atlas remain unchanged. Zero model/food/stock/graph/work or
staff-allocation calls occur. See
[qualification](../output/urban_handling_rate_screen_20261117/qualification.json).

A direct-journal search lead is **Physiological and Subjective Assessment of
Food Grain Handling Workers in West Godavari District, India**, Industrial
Health 45(1), starting page 165:
https://www.jstage.jst.go.jp/article/indhealth/45/1/45_1_165/_pdf .
Its full text has not been opened or qualified in this screen. The next frozen
plan is `calibration/urban_diagnosis_20261117/handling_observation_primary.json`:
inspect this one observational paper's operation/crew/mass/time denominator and
measurement protocol. Search snippets are not measurements, and truck elapsed
time cannot become person-hours without the missing operation and crew facts.
No numerical rate adoption is authorized by finding an apparently relevant paper.

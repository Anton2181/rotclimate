# Archaeological store capacity: what the source supports — 17 November 2026

The full methods article supports separating physical storage from annual
production, marketed throughput and edible-energy budgets. It supplies no
qualified replacement for the model's 90/365-day stores or five-percent loss.
The current store settings remain scenarios. An archaeological store needs
material, usable-space, function, location and phase evidence before it can be
attached to a modeled commercial origin.

Source: Javier Salido Domínguez (2018), *Sobre la capacidad de almacenaje de los
horrea rurales romanos: teoría del Escepticismo Cuantitativo*, Gerión 36(1),
79–94, [DOI/publisher](https://doi.org/10.5209/GERI.60294). The
[unchanged publisher PDF](../output/urban_storage_methods_20261117/source/salido2018.pdf)
is retained under the publisher's **CC BY 4.0** license, with attribution and
access metadata. Translations and model-interface deductions below are ours.
PDF SHA256: `a4374b2b23e7cbfea88b3abe2ebb26fd71515a6ea2adb82bedf09c31d4608424`.

## Page-located findings

The [methods ledger](../output/urban_storage_methods_20261117/methods.csv)
records twelve fields, including all nine factors in §7. Each short Spanish
anchor matches both independent `pdftotext -layout` and `-raw` extractions.
Printed pages 88–90 were also checked against the PDF images. These checks
authenticate locators; they do not independently verify the cited excavations.

| Printed pages | Source statement | Consequence for this model |
|---|---|---|
| 88, §7.1–4; 84–87 | Cereal identity, other commodities, containers and grain state are often unresolved | Match density and edible conversion to the stored material; allocate cereal space explicitly |
| 88, §7.5 | Author argues turnover and owner needs decouple retained stocks from agricultural output | Keep stock, capacity, production and dispatch separate; do not treat the interpretation as a measured schedule |
| 88–89, §7.6–8 | Working space, ventilation, floor support and safe pile geometry limit a simple footprint conversion | Gross area alone cannot establish an operational grain budget; competing height proposals remain estimates |
| 90, §7.9 | Residence time is unknown and need not be a full year | No universal annual buffer follows; days require a justified flow denominator |
| 81/84, §2; 87–88, §6 | Function can vary by phase; preservation has multiple interpretations | Align chronology and function; germination is not a measured annual energy-loss rate |

These are review statements, author interpretations or reported disagreements,
not newly authenticated primary site measurements. The density table and
competing height estimates are explicitly attributed to earlier works; those
works were not opened or adopted. No site dimensions, capacities, density or
height proposals were transcribed into a measurement/fit table. Numerical
examples and figures were visible and are recorded as development exposure.

## Explicit conversion contract

For a future single-commodity bulk store, our dimensional bookkeeping is:

`usable volume = allocated usable area × effective fill depth`

`stored mass = usable volume × density of that stored material/state`

`net-edible energy equivalent = stored mass × net-edible yield × edible energy/kg`

This is **our unit relation**, not an equation presented by Salido and not a
historical capacity estimator. Gross footprint is not allocated usable area.
Sacks, containers and mixed stores require appropriate volume/packing evidence;
an effective depth cannot be guessed. Structural floor support and preservation
may make a geometrically possible fill unusable. A known floor-load limit can
reject a fill; an unknown limit cannot be treated as unlimited support.

Stored husked material and the existing model's already-net edible grain are
different accounting states. Seed, processing and other deductions must be
assigned once at the correct boundary. Physical volume occupied by another
commodity or inventory cannot also fund this cereal store. We have not supplied
any new density, fill height, edible fraction, floor load or loss coefficient.

Only an explicit compatible flow permits a day-equivalent:
`days = energy / daily flow`, or `365 × energy / annual flow` for a declared
365-day year. Zero or unknown flow leaves days undefined. Original marketed
flow depends on modeled work, rural need and policy; it is not an archaeological
observation. Historical capacity must not silently resize when those outputs
change. Physical ownership, access and route association also need evidence;
the rural methods review does not locate every commercial store in an origin
cell or demonstrate that each belongs to an exporter.

## Decision and checks

Keep the rural/commercial/town budgets as disclosed scenario infrastructure.
Do not fit one global capacity coefficient from this review or infer a loss
rate from preservation symptoms. Next, implement the
[declared isolated capacity contract](../calibration/urban_diagnosis_20261117/storage_capacity_contract.json)
with manufactured unit/definition controls and missing-data behavior. It must
label conditional arithmetic separately from empirical qualification and leave
the food producers disconnected. This makes the new evidence distinctions
usable without inventing archaeological measurements.

The [qualification](../output/urban_storage_methods_20261117/qualification.json)
records the committed declaration, 16-page source identity, twelve dual-path
anchor checks and all 1103 protected parent identities. The full article is now
development evidence, including incidentally visible examples. Van Oyen's
chapter and Rickman's monograph remain unread-body leads. No new food case,
phenology/climate run, population/staff change, fit or atlas/default adoption
occurred. Full diet/work, rights and independent transfer gates remain open.

Reproduce from retained PDF/access metadata with
`scripts/qualify_urban_storage_methods.py`, then
`scripts/seal_urban_storage_methods.py`. Completed outputs refuse overwrite;
redirect OUT consistently to an empty location for fresh extraction/review.
Uncookied publisher requests initially looped on locale redirects; the retained
access receipt records the resolved cookie/session request. No secondary source
was substituted. The PDF and raw text extractions preserve the source, not a
site measurement dataset.

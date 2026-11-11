# Primary Vidarbha field survey, 11 November 2026

The separate 2016 field-survey archive supplies a coherent located settlement
cohort. All 134 settlement records join exactly to the all-sites table; every
coordinate pair is finite, geographically valid and within the published broad
Vidarbha envelope. This does not repair the earlier literature-census export.

Protocol 5d7d0b00 preceded opening the record archive. Sources: Abbas, Toraskar
and Hawkes (2020), *The Archaeology of Vidarbha, Maharashtra: 2016 Regional Survey
Data*, version [10.5281/zenodo.3670055](https://doi.org/10.5281/zenodo.3670055),
CC BY 4.0; Hawkes, Abbas and Toraskar (2020), *Multi-Period Regional Survey Data
from Vidarbha, Maharashtra, India*, [10.5334/joad.61](https://doi.org/10.5334/joad.61).
Relevant primary article methods and the source readme were checked. Only the
139,013-byte record archive and readme were downloaded, not the multi-GB photos
and plans. Raw survey rows and coordinates remain in the private cache.

|Table|Records|Unique keys|Exact all-site joins|Review|
|---|---:|---:|---:|---|
|AllSites|268|268|—|All documented North/East coordinates valid|
|Settlements|134|134|134|127 uppercase and 7 lowercase settlement labels|
|Megaliths|18|18|18|Separate source context|
|Religious|25|25|24|One missing parent; no fuzzy repair|
|Others|22|22|22|Separate source context|

The all-sites table additionally contains 69 spot-find contexts. They are not
automatically settlements or negative evidence of settlement absence. There are
no malformed rows or duplicate keys in these five tables. The religious join
failure remains visible; it does not invalidate the exact settlement-only joins.

Among matched settlements, the EH-S flag is yes for 82, no for 41, unknown (`?`)
for 9 and blank for 2. The published chronology places the Satavahana phase broadly
in the first century BCE to second century CE. Phase-compatible finds are not
proof of continuous occupation or a settlement census at exactly AD200. Other
phase flags and all missing/uncertain states remain in the preparation download.

## Coverage and interpretation

Three purposefully centred survey frames have nominal radius 13 km: Chammak
(the dataset spells the zone Chamak), Mandhal and Pauni. The authors report about
7.5% area coverage and discuss alluvial burial, surface visibility and discovery
methods. This is a selected field-survey record, not a complete urban inventory.
Unobserved land cannot be labelled true absence, and every archaeological entity
cannot become an administrative town. Models may be assessed for conditional
location support; these data alone cannot validate city counts or populations.

The readme explicitly calls North latitude and East longitude. No coordinate
swap, nearest-land rescue, source-name fuzzy join or physical-place merge occurs.
The datum is not independently certified here; a comparison must report its
operational geographic interpretation and grid/offset sensitivity.

Eight ID strings overlap the old master and 20 the old census settlement table.
None of the eight old-master coordinate pairs exactly equals the new field pair
under either documented order. Shared local ID strings do not establish shared
physical sites, and no cross-source coordinate transfer or reconciliation is
performed. The older failed-source audit remains byte-identical. Prior broad
geography/source exposure is acknowledged; a new DOI alone does not make a test
blind. Reba/Modelski's ancient-city data was also already used elsewhere in the
project and is not a fresh validation source.

The independent review reconstructs five CSVs, 268 coordinate records, 134 exact
settlement joins and 2,412 phase-record cases, including old-source overlap.
Thirteen relevant parser/source tests pass. No environmental or model prediction
lookup, fit or score has occurred in this preparation milestone.

Next freeze the exact finalist, controls, source cohorts, frame conditioning,
grid scales, metrics and decision margins before first prediction lookup, then
run the regional transfer comparison. Keep the partial coverage and village/town
role distinction explicit. This serves the four-milestone settlement-map release;
detailed institutional/control calibration remains on the longer roadmap.

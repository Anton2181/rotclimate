# Local Nile groundwater evidence: measurements and inferred fluxes separated

Two modern Delta studies supply useful water-table and soil observations, but
neither supplies a complete, consistent boundary/input set for the regional
groundwater model. Their reported groundwater contributions are inferred, not
direct measurements of capillary flux. No regional groundwater rate, aquifer
capacity, root-zone capacity, yield or settlement change is adopted.

Declaration `5b3b3af6` preceded full-table extraction and derived arithmetic.
Search snippets/abstracts and their broad contribution estimates were already
exposed and declared as known development evidence, not independent holdouts.
This source audit continued after the finite-budget checkpoint `5ca4ae91`.

## Amer 2019: actual water-table depths, empirical contributions

Source: Amer, *Acta Agrophysica* 26(1):79–92,
[DOI 10.31545/aagr/110045](https://doi.org/10.31545/aagr/110045).
The DOI/repository route was unavailable; a valid 840,298-byte PDF was recovered
from a public mirror. Its bytes, URL and SHA256 are pinned in
[sources.json](../calibration/nile_groundwater_sources_20261114/sources.json).

The study concerns the 2014–2015 managed middle Delta: four cultivated locations
in Menoufia and an uncultivated Ebshan profile. Wheat/clover in winter, maize
in summer and citrus at Talla are distinct systems. The cultivated sites used
furrow irrigation. Piezometers measured depths; soil properties, saturated
conductivity and field infiltration were investigated. Printed p85/PDF7 gives
the methods; printed pp88–89/PDF10–11 discuss the depths and fitted crop factor.

All forty Table3 depths and forty corresponding fitted factors are retained in
[water_tables.csv](../output/nile_groundwater_sources_20261114/water_tables.csv):
four sites × ten months, November2014–August2015. The associated prose discusses
before-irrigation depths; before/after irrigation measurements do not constitute
a continuous daily groundwater boundary. Talla's values describe citrus, not
wheat. These modern monthly depths are not observations of an ancient basin.

|Site|Minimum published monthly depth cm|Maximum cm|
|---|---:|---:|
|El-Baghour|111|135|
|Berket El-Saba|110|139|
|Talla|89|123|
|Shebin El-Kom|91|136|

The crop factor m is fitted, and ETa and seasonal contributions are empirically
estimated. Thus the broad winter20–40% / summer≤20% conclusion is not a measured
upward-flux boundary or independent ET validation. Equation1 is a static
capillary-height relation; printed p88 discusses calculated rise rates. Height
alone cannot determine a rate. No such rate is adopted here.

## El-Ghannam et al. 2023: controlled drainage and a residual estimate

Source: *Journal of Arid Land* 15:460–476,
[DOI 10.1007/s40333-023-0095-3](https://doi.org/10.1007/s40333-023-0095-3).
Journal-hosted HTML metadata and article XML retain Tables1/2 and the methods.
Both exact captures are tracked under
[data/source/nile_groundwater_sources_20261114](../data/source/nile_groundwater_sources_20261114/README.md)
because the live HTML includes changing public page tokens. Several PDF routes
returned HTTP errors or HTML; no response was accepted as a PDF. The numerical
finding below concerns the captured HTML/XML, not an inspected printed PDF.

The experiment is at Sakha/Motobus (31°15′51″N,30°47′06″E), on three separately
drained 0.6ha fields. Drain burial is 1.2m in all treatments. Controlled-drainage
labels0.4/0.8m identify outlet/weir elevations, not buried drain depths or fixed
measured groundwater levels. Cultivar replicates occur within each field;
there is one field per drainage treatment. Modern wheat cultivars, fertilizer
and irrigation are part of the experiment's context.

The sowing/harvest dates are 15Nov2018–25Apr2019 and20Nov2019–27Apr2020 (§2.3).
The study reports flow-meter irrigation, tank/stopwatch drainage, TDR field
moisture, monthly well observations, roots measured before irrigation and
harvested yield (§§2.4–2.7). These support studying a managed local system.

All three Table1 layers are retained in
[sakha_soils.csv](../output/nile_groundwater_sources_20261114/sakha_soils.csv),
including bulk density, salinity, printed saturated conductivity, particle
fractions and texture. Particle fractions sum to100% for every layer.
The source's conductivity header is m/h in both representations; it is retained
as printed and is not used as a recharge allowance.

Section2.4 reports FC39.98%, WP21.70% and half depletion30.84%, but does not
explicitly identify the FC/WP mass/volume basis or layer assignment in the
retained methods. TDR is stated for field moisture monitoring. We therefore do
not multiply these percentages by a layer thickness or bulk density to invent
a root-zone storage capacity. Likewise, §2.6 Equation3 describes storage change
as moisture percent beside water depths in mm, without the needed depth/basis
conversion there.

Groundwater uptake is inferred as a water-balance residual using estimated ETc
(§2.6); §3.3 assumes common actual ET from the free-drainage control for all
treatments. That assumption does not provide an independently measured upward
flux. Salinity changes under shallow control also prevent treating short-term
water availability as a complete long-term crop response.

## Captured percentage discrepancies remain unresolved

Section3.3 gives actual ET396.7mm and385.3mm for the two seasons. The captured
Table2 has the following values, preserved without repairing their layout:

|Treatment|Season|Inferred uptake mm|Table percentage|100×uptake/stated ET %|
|---|---:|---:|---:|---:|
|CD-0.4|1|95.0|23.1|23.948|
|CD-0.4|2|105.7|12.8|27.433|
|CD-0.8|1|52.7|26.4|13.285|
|CD-0.8|2|40.5|10.1|10.511|

All four differ beyond0.1-percentage-point printed rounding. In addition, the
prose associates12.8% with CD-0.8 season1 and26.4% with CD-0.4 season2, unlike
the middle cells' captured table positions. Swapping those cells would still
not reconcile them with the stated ET. We cannot choose the table, prose or a
different denominator as a calibrated input. Full checks are in
[sakha_flux_checks.csv](../output/nile_groundwater_sources_20261114/sakha_flux_checks.csv).

## Independent verification and next evidence

The reviewer imports no producer. PDFplumber word geometry checks all80PDF
table cells against the producer's pdftotext extraction. Standard-library
HTMLParser/ElementTree independently checks both captured representations of
the selected Sakha tables against lxml, including all24soil numeric cells.
Fifty-digit Decimal arithmetic checks each percentage discrepancy. Four fresh
exports reproduce byte for byte; all942protected files remain unchanged,
including the paid-groundwater numeric results, controls and review.

Reproduce with system Python (lxml/pdfplumber installed), plus pdftotext:

```sh
python scripts/nile_groundwater_sources.py
python scripts/nile_groundwater_sources.py --out output/nile_groundwater_sources_20261114/fresh
python scripts/review_nile_groundwater_sources.py
```

Before a local groundwater experiment, obtain a consistent layer retention/
conductivity definition, FC/WP basis, full water-table/root development/suction
history and matched weather, irrigation/drainage and storage changes. Accessible
aquifer storage/specific yield, finite recharge boundaries/losses and transient/
oxygen/salinity constraints remain missing. The printed PDF or another primary
version is needed to distinguish a digital conversion problem from a source
table problem; arithmetic and residual-method limitations remain either way.

The immediate modelling path is to keep groundwater disabled in regional fields
until those inputs are qualified. Work on consistent regional weather and crop
inputs can proceed independently. No Dutch-soil transfer, free groundwater or
parameter selection from Egypt's deficit follows from these studies. Tigris,
shared Earth/fantasy flow, independent regions and frozen harvest/whole-empire
checks remain required. Latest regional water maps and release3 settlements
remain unchanged; Egypt calibration still fails.

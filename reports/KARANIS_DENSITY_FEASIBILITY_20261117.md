# Karanis cannot yet anchor the AD200 density conversion

17 November 2026. The bounded screen found useful demographic and archaeological
leads, but **no matched population/occupied-area observation**. Keep both current
density scenarios explicit. There is no defensible new number to substitute into
the atlas from this screen.

The [declaration](../calibration/roman_benchmark_20261117/karanis_density_feasibility.json)
allowed three targeted searches and three source bodies. Exactly those limits
were used; no papyrus record, new census dataset or additional source body was
opened. Institutional search-result metadata helped identify the tax chapter;
search snippets and third-party population estimates are not adopted evidence.

## What the three sources establish

| Source and exact location | Useful evidence | Missing link |
| --- | --- | --- |
| Uri Yiftach (2020), *Reconstructing Karanis*, pp.243–247, especially p.246 n.36 | AD174/175 payment records; reconstruction of roughly120 collection units; census returns with and without within-village location. Two cited declarations date201/2. | Taxpayer entries are not all inhabitants; units lack mapped locations. Neither a complete AD200 count nor a matching residential footprint is established. |
| Motta et al. (2024), *Antiquity*98:954–972, “The level system”, “Results” and “Dating the late occupation” | Thirteen crop specimens test the lettered excavation chronology. Local building histories overlap; letters cannot simply be synchronized across the village. | These dates concern later occupation, not an AD200 residential-area map. |
| Kelsey Museum, “Karanis, Egypt”, excavation history | Prior destruction and complicated stratigraphy qualify how surviving houses represent the settlement. | Excavated plans are not a contemporaneous complete inhabited extent. |

Read [Yiftach's chapter text](https://www.academia.edu/43805468/Reconstructing_Karanis_Tax_Collection_and_Administrative_Innovation_in_an_Arsinoite_Town_of_the_Second_Century_CE),
the [radiocarbon study](https://doi.org/10.15184/aqy.2024.69) and the
[museum's excavation account](https://lsa.umich.edu/kelsey/research/past-field-projects/karanis-egypt.html).
The first is an original scholarly analysis of documents, rather than direct
inspection of the papyri here. The museum account describes the older chronology;
the 2024 study supplies the explicit caution about its use. No wholesale redating
of every house follows from the selected specimens.

## Decision and what would change it

The required observation is a numerator with stated household/person inclusion
and coverage, linked to an occupied residential area at a compatible date and
spatial support. This screen supplies neither a complete numerator nor the
matched denominator. A tax collector's unit count cannot become households or
total people through an assumed multiplier. Likewise, total mound dimensions,
an excavated subset or the union of houses used across centuries cannot supply
the missing occupied hectares. Village evidence alone would also not establish
the atlas's density law for large cities.

The near-target documents **BGU I97 and BGU II577 (201/2)** are specific follow-up
leads cited by Yiftach, not newly inspected or qualified records. A future attempt
would need their actual inclusion rules and an authenticated archaeological link
to dated houses and occupied area. Repeating published village population
estimates without that link will not close the gap. This is a failed match in
this finite screen, not a claim that no suitable evidence exists anywhere.

The [annual impact assessment](ANNUAL_ASSUMPTION_IMPACT_20261117.md) therefore
stands: town population conversion remains an explicit, influential uncertainty.
The next implementation work should constrain the annual agricultural budget
and preserve these density alternatives, rather than delay all progress until
one universal density estimate appears. Climate remains deferred.

## Evidence record and checks

`output/karanis_density_feasibility_20261117/source_receipt.json` records URLs,
retrieval routes, cache hashes and the three search queries. Original HTML/text
and web-extracted scholarly text stay local under ignored `source/`. In this
session the directly downloaded Academia HTML contains preview/AI material but
not the relevant chapter body. That material is **not** used as the chapter:
the separate web extraction contains the printed-page text and footnotes used
above. No PDF-byte or facsimile identity is claimed for that extraction.

The verifier checks cache identities, locates the relevant source sections,
checks the declared three-search/three-body bound, and verifies the previous
annual assessment's source, output and protected atlas identities. These are
provenance and scope checks, not an independent papyrological interpretation or
new demographic validation. No model, parameter, population or atlas is changed.

```sh
.venv/bin/python scripts/check_karanis_density_feasibility.py
```

The script preserves completed receipts. Reacquiring a changed web page does not
authorize replacement of the pinned source identity or interpretation.

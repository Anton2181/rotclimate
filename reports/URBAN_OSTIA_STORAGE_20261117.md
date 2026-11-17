# A primary port-warehouse source, with its limits retained — 17 November 2026

The selected chapter supplies archaeological evidence for a physical warehouse
at Ostia, but its capacity figures remain reconstructions. It does not qualify
an operational grain budget or a replacement for the model's store settings.
The evidence also motivates keeping the identity of a port store separate
from the agricultural origins supplying it; no origin-to-port mapping or
allocation right is inferred here.

Source: G. Boetto, É. Bukowiecki, N. Monteix and C. Rousse (2016),
[*Les Grandi Horrea d'Ostie*](https://books.openedition.org/efr/32815?lang=fr),
in *Entrepôts et trafics annonaires en Méditerranée*, CEFR 522, pp.177–226,
[chapter DOI](https://doi.org/10.4000/books.efr.32815), HAL `halshs-01441802`.

## Source identity and evidence

Publisher HTML and a public mirror of the HAL author deposit agree on the
chapter identity. The mirror supplies printed-page locators and the PDF image
check of p.217. The publisher citation modal identifies the chapter DOI;
its generic `citation_doi` metadata instead contains the book DOI ending
`32730`. Secondary catalogue snippets also vary in collection/page metadata;
the retained title page and publisher pagination establish 522/177–226.

The full chapter's 81 numbered paragraphs were read. The public ledger keeps
[61 numerical source statements](../output/urban_ostia_storage_20261117/numeric_claims.csv),
[18 contextual assessments](../output/urban_ostia_storage_20261117/context.csv),
[seven capacity-estimate rows](../output/urban_ostia_storage_20261117/capacity_estimates.csv)
and [complete paragraph coverage](../output/urban_ostia_storage_20261117/coverage.csv).
Each quantity retains a unit, source locator, statement kind and limitation.
Measurements, reconstructions, modern analogies and author conventions are
separate. No quantity becomes a model input.

The authors assume wheat rather than positively identifying the contents.
Their calculations select the first Severan phase, reconstruct pile geometry
and extrapolate an upper storey. Sack height/angle are conventions; storage
duration bounds use modern analogies. Ownership/destination and actual
residence time remain unresolved. Gross dimensions are not usable cereal area.
The authors' Rome demand-day equivalent is a stock/consumption ratio, not
warehouse residence time or days of modeled export flow. These distinctions
are retained, including their conditional and estimated numerical statements.

## Unresolved numerical checks

Our [source-column diagnostics](../output/urban_ostia_storage_20261117/source_column_checks.csv)
apply only the chapter's own unit conventions. They do not calculate a new
operational capacity or repair the source. For example, the north row prints
349m³ alongside 30,772 modii. At the source's 8.76 litres/modius, the latter is
269.56272m³, a difference of **79.43728m³**. The central sack endpoint also
differs: 753m³ versus 83,904 modii implies a difference of **18.00096m³**.
Published approximate totals and all original columns remain unchanged.

There is a separate dimensional issue in the expression printed in p.217,
note114, confirmed in both publisher HTML and PDF image: the prism term has
length dimension three, but the added term as printed has dimension two.
The expression is not implemented, corrected or used to reconstruct an
unprinted capacity. These findings are preserved in the
[issue receipt](../output/urban_ostia_storage_20261117/source_issues.json).
They do not invalidate every architectural observation, but they prevent
treating the printed formula/table as a qualified conversion without further
source clarification.

## Interface outcome

The [contract record](../output/urban_ostia_storage_20261117/interface.json)
keeps physical location and the selected phase, while leaving commodity/state,
allocated usable geometry, net-edible conversion, structural-load bound,
operational preservation and access qualification incomplete. Its geometric
net-energy result is unset; operational/historical capacity is unqualified.
Even the source's proposed bulk density remains labelled author estimate and
is not adopted. No model flow denominator, city node, origin or population was
crossed with this source.

The next useful implementation is therefore a
[declared shared-warehouse accounting primitive](../calibration/urban_diagnosis_20261117/shared_warehouse_primitive.json):
several explicitly permitted origins can fund one identified store, whose
capacity is charged once. It will use manufactured scenarios plus four exact
existing source-store reduction controls. It will not assign real ports,
infer rights, adopt the Ostia estimates or launch a new Earth meal scenario.
This is a bounded structural step towards later food/work/occupancy coupling.

## Review and preservation

A separate extraction uses HTML paragraph/footnote and table structure,
compares the seven rows with the PDF, checks 81 numerical tokens and
independently recomputes ten column diagnostics with Decimal. The source's
numeric consistency remains explicitly **unresolved**. The positive review
qualifies transcription and source classification, not the capacity estimates.
See the [qualification](../output/urban_ostia_storage_20261117/qualification.json).

The initial before-reading
[registration](../output/urban_ostia_storage_20261117/exposure.json) remains
unchanged. The chapter and incidentally visible comparison examples are now
development exposure, not an independent validation pool. Out-of-scope Portus,
Vienne and other comparison examples were not extracted as additional sites.
The mirrored file also includes front matter, references and indexes; only
its target chapter pages 177–226 support this evidence ledger.

The source license is recorded as stated by the publisher: text under the
OpenEdition Books license; illustrations/annexes reserved unless stated
otherwise. Raw HTML/PDF/text caches stay local/ignored. Public artifacts retain
facts, source locations and our diagnostics. The
[identity/access receipt](../output/urban_ostia_storage_20261117/source_identity.json)
pins bytes and semantic paragraph identity; web wrappers may change on replay.
Some web/HAL landing requests returned bot-protection pages. An ordinary
publisher HTML request and the public author-deposit mirror succeeded; no
challenge bypass or secondary summary was substituted for the chapter.

Reproduction: restore the identified source caches, run
`scripts/qualify_ostia_store.py`, `scripts/review_ostia_store.py`, then
`scripts/seal_ostia_store.py` in `.venv`, using an empty consistent OUT for
fresh replay. All 1103 protected parent identities remain unchanged. Zero
new food cases, fits, climate/phenology runs or actual population/staff changes
occurred. Main atlas/defaults remain unchanged; reserved pools and the
site-survey workbook were not opened.

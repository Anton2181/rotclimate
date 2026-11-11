# Settlement roles may be successive: change dates and record identity

11 November 2026. The source authors document phase dates as **major settlement
changes**, and explain that a farmstead developing into a villa can receive both
labels. Multiple source labels therefore do not establish contemporaneous roles.
An executable audit now separates consistent change order from dated functions,
and strengthens future validation blocks without merging physical places.

Source: Smith and colleagues2016, *The Rural Settlement of Roman Britain*,
Britannia Monograph29, [Chapter1](https://archaeologydataservice.ac.uk/catalogue/adsdata/arch-3299-1/dissemination/brit_29/disc_1_-_ch_1-11/Romanch1.pdf),
printed page10/right column and page11/right column; and
[Chapter2](https://archaeologydataservice.ac.uk/catalogue/adsdata/arch-3299-1/dissemination/brit_29/disc_1_-_ch_1-11/Romanch2.pdf),
printed page20, discussion of palimpsests and investigation strategies.
The underlying [ADS archive](https://doi.org/10.5284/1030449) is selected excavated
evidence, not a complete census. Original collectors are not responsible for this
model's interpretation. PDF bytes were streamed to text extraction; locally
recorded PDF/text hashes and URLs are retained. Raw PDFs/text/CSV are not
redistributed. These are local content identities, not archive-published checksums.

## What the new evidence resolves

The generic purpose of phase-date fields is documented. Successive roles and
occupation hiatuses are explicitly possible; the authors discuss large variation
in dating precision. The original inspected DDL still omits PHASE_DATE1/2, so a
complete direct export-column dictionary and a role-to-change mapping remain
unavailable. Do not automatically treat a slot as the start/end of a particular
role, assume continuity between endpoints or assign every source role to AD200.

`polity/settlement_phase_evidence.py` preserves source order and flags nonnumeric,
zero, reversed, out-of-span or unbounded changes. It never sorts/clips dates into
plausibility or assigns role intervals. Consistent dates are useful chronology
constraints, not a qualified functional timeline.

|Source check|Records|
|---|---:|
|No recorded change dates|2611|
|Consistent recorded changes|1031|
|Change-bearing records requiring review|10|
|Both farm and villa labels|146|
|Specific role intervals assigned|0|

Among1041 change-bearing records, the10 requiring review comprise4 with missing
site bounds,3 with reversed change order and3 with a change outside the recorded
span. No recorded change is not proof of no change; all3652 records still lack
role-specific intervals in this compiler. The aggregate all-record flags also
retain117 unknown site spans and2 zero-endpoint cases, even where no change is
recorded. These denominators are kept distinct.

## Place evidence and validation blocks are different

The same numeric XY occurs at16 shared keys/32 records; normalized county+name
at4 keys/8 records. Shared points and names are useful leakage warnings, not proof
of duplicate population units. Exact numeric notation is canonicalized without
rounding or nearest-neighbour merging; names are case/whitespace normalized with
county namespaces, without fuzzy matching.

The new review blocks preserve every original exact-association component and
add these point/name links. Nontrivial blocks increase from65/153 records to
83/189 records; total blocking components become3546, largest8. **Every source
record is retained.** These are not physical-place IDs or independent spatial folds.
The archive's approximate2500-settlement statement is not imposed as a merging
target; the difference from record totals does not quantify duplicates by itself.

Three declared review cases illustrate why:

* Records3018/3069 share a name and centroid but have different investigation
  areas/date spans and inconsistent association namespaces. Block them together;
  exact physical observation overlap still needs source review.
* Records43004/43054 share county/name but describe villa and nearby cemetery
  evidence. The summary identifies an offset between features. Keep the distinct
  observations and role histories even if a later complex-level grouping links them.
* Record1010 has two change dates in a long site span and describes changing
  building phases. Generic date slots alone do not associate every observed role
  with a precise interval.

The review manifest records interpretations/IDs, without publishing original
coordinates or source passages. No name/centroid collision creates residents,
staff, actor affiliation or political authority.

## Next calibration contract

Do not wait for a perfect global gazetteer or treat unresolved evidence as absence.
First declare which question each evidence unit can answer: broad Roman-period
role footprints, a dated residential nucleus, or an institution with its own timing.
Use broad-period/undated observations only for questions they support. Define
grouped/spatial coverage and positional-uncertainty sensitivity before scoring;
association/point/name blocks alone do not establish independent transfer.

The next role-specific experiment should compare the appropriate conditional
evidence units rather than fit all farms to county seats or treat excavation
frequency as a census. Physical grouping and function intervals remain explicit
uncertainties. Qualified settlement/role allocations must then enter the SAME
resident, seasonal food, staffing and differentiated-control chain. No production
map changed in this source audit; the [full S1–S5 programme](SETTLEMENT_CONTROL_ROADMAP_20261110.md)
remains open.

Reproduce: `.venv/bin/python -I scripts/audit_settlement_phase_evidence.py`.
The five pinned source CSVs and private cached methodology text/scope HTML are
required; source identities and extraction details are in
`calibration/settlement_phase_evidence_20261111/semantic_sources.json`. The protocol
explicitly discloses that source rows/integrity examples had already been inspected:
this is an exposed source audit, not a preregistered model test or sealed data.

Verification:89 focused tests pass. The boundary study independently passes all
100 count/eligibility/intensity/pair checks and20 exact overlapping controls. The
new source audit replays byte for byte; all seven previous source-audit/numerical
artifacts remain unchanged against32ca2173. Served-browser checks pass for both
new panels,10 aggregate/document links, the figure, keyboard controls and
344/390px light/dark layouts; previous rural/coordinate panels and evidence
filters/download/error handling also pass. An existing narrow-screen card overflow
was fixed with scoped text wrapping. Full portable ZIP/site copies are not rebuilt
under the disk quota; packaging recipes include the new artifacts.

Focused Windows-style checkout preserves 70 critical files byte for byte;
all 652 local page dependencies resolve. Standalone publication is idempotent
and the standard launcher verifies the refreshed release.

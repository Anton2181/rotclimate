# Earth reference date scopes, 11 November 2026

The documented Seshat parent-scope convention recovers reference coverage needed
for the next settlement-map release: at positive year 200, settlement-hierarchy
polity/variable groups increase from 0 with complete explicit row dates to 26;
largest-settlement population groups increase from 4 to 18. The corresponding
numeric source rows are 24 and 14. Missing values and competing observations remain
visible. These are source-reference counts, not model accuracy or independent sites.

Protocol f0f3b892 was committed before the new scope counts. Both policies and
all ten variables are retained; no model predictions, parameter fitting or chosen
policy is reported. Initial preparation and atlas inputs are unchanged. The
full four-milestone map-release path is on the [roadmap](SETTLEMENT_CONTROL_ROADMAP_20261110.md).

## Documented policy and conservative limits

The official Seshat data page links
[SeshatDatasetAnalysis](https://github.com/matildaperuzzo/SeshatDatasetAnalysis).
At pinned commit `292b042cef3dde3d43b2c7723dec41a173c2a163`, its README describes
undated single values and disputed undated alternatives as spanning the parent
polity duration. `Template.py`, including `check_dataframe`, implements that
convention and rejects mixtures of dated and fully undated values.

Our limited adapter compares complete explicit intervals against that documented
scope. Multiple undated rows require an explicit uncertainty/dispute flag and
stay separate. Unflagged multiples, mixed-date groups, partial dates, invalid or
reversed bounds and intervals outside the parent span retain review reasons.
No date clipping, point-date extension, nearest-year rescue, random sampling,
range midpoint, interpolation or value-code conversion is copied from the author
package. Third-party code was inspected as text and never executed.

Parent-scoped values are labelled as such, with original bounds preserved. This
is a documented source-analysis convention, not proof of continuous operation,
directly dated institutional roles or a staff count. Positive year 200 is tested
against exported bounds without rewriting BCE/zero-year conventions. Unknown,
inferred, missing and conflicting values do not become ordinary observed absence.

## Reference coverage and next gate

The input retains 5,007 source rows in 4,675 polity-variable groups. All row
eligibility and year-200 value-state summaries are downloadable for both policies.
Reference support may contain alternatives rather than independent observations;
small sample sizes and regional/historical relatedness still matter.

The independent reviewer reconstructs all 10,014 row-policy cases and both
year-200 summaries directly from the pinned workbook. Five scope tests cover the
documented cases, nonmutation and refusal to fill partial/outside dates. No
third-party raw rows or workbook are redistributed.

This advances milestone 1's dated reference work. A located geographic transfer
pool and frozen comparison rules remain necessary: Seshat polity attributes do
not provide settlement coordinates. Milestones 2–4 then fit/test placement and
sizes, rebuild fantasy settlements on one resident/food ledger, and publish the
normal atlas. Detailed institutional roles and de-facto control remain on the
longer S2–S5 queue, rather than blocking the first settlement-map release.

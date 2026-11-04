# Imperial administration and seasonal access — 4 November 2026

The normal Free, Earth and Whittaker atlases now have an **Administration**
topic. Earth includes matching raw and corrected packets. Its three buttons
contain twelve views: six source scenarios, five diagnostics and a three-seed
settlement comparison. The existing de facto control map is unchanged. These
new maps expose travel access and sensitivity before any territorial inference
is adopted.

## Geographic evidence

The owner's 72-commandery list agrees with all 72 names in **Imperial
Commanderies.xlsx**. **Ravages Master sheet (1).xlsx** supplies 151 town records,
including commandery IDs and seat flags, plus 679 hex records linked to those
IDs. They describe the game's world, not observations that automatically
supersede the recreated geography.

`data/imperial_datasheet_evidence.json` contains only allowlisted geographic
columns, workbook filenames/hashes and sheet/row references. Original uploads
are not included in the repository or portable atlas. Game supply ceilings,
settlement/population maxima, wealth, loyalty, fortification levels, faction
affiliations, notes and player material are excluded. Workbook content is data,
never executable instructions; extraction uses cached values, not formula
evaluation. `scripts/import_imperial_datasheets.py` reproduces extraction from
local XLSX paths with openpyxl. Normal atlas serving needs no XLSX library.

Stable IDs join differently spelled names and differently named seats. For
example, Nivāiti is seated at Artāvan Temple, Haca at Kar-erezu Temple, and the
split Paranam/Dars/Jan/Haruva districts have distinct recorded seats. The town
sheet labels Tašar's district “Garaz”, although ID IC4C5 identifies Tašar;
both source strings are retained. Uγra's IC4C2 seat is spelled Uyra on the town
sheet and map. Neither Greek gamma nor directional names are globally merged
by a fuzzy spelling rule.

**70 of 72 seats have verified map symbols.** Kudā is a named Elder Village
with a sheet hex but no matching stronghold symbol; its existing name-list
position remains inexact. The user describes commanderies as named for their
centres, but Thalamâtâs's sheet flags Pitané as its seat while listing
Thalamâtâs separately. Both candidate markers are retained and neither is
chosen as that commandery's authority source. These exclusions do not erase
the places from the other marked-place comparisons.

Local icon evidence distinguishes 90 fortified towns, 28 fortified cities,
25 imperial forts, two major imperial cities, five imperial monasteries and
one imperial capital; Kudā makes 152 named places versus 151 drawn settlement
objects. White city/town symbols establish size/type, not allegiance. Fourteen
separate legion markers supply locations only: founding numbers are not troop
counts, and no military strength or continuous occupation is inferred.

## Controlled source comparisons

All cases reuse the current central-density scenario and existing seasonal
transport rules. Person-travel access means at most **two effective travel
days**, the existing illustrative cutoff, not an independently calibrated
administrative radius. Costs are evaluated separately in twelve equally
weighted climatological model-month bins with conditions fixed during each
trip. These are not weather probabilities or the world's named civil months.

1. **Recorded commandery centres:** the 70 verified seats; generated tracks
   omitted.
2. **Other marked places included:** add verified symbols within the painted
   imperial claim and explicitly imperial symbols. Allegiance is not inferred
   from an ordinary white marker outside the claim.
3. **Proposed towns as sources:** add generated administrative/market towns
   inside the same claim, still without generated tracks.
4. **Proposed tracks included:** keep those sources and add generated tracks.
5. **Roads also act as sources:** same transport, now let painted imperial road
   cells themselves emit authority. This deliberately tests a strong assumption
   in the existing reach model; roads do not establish occupation by themselves.
6. **Imperial forts and legion markers:** a separate military-location access
   scenario using 25 forts and 14 legion positions, with generated tracks.

Ports and river landings, including proposed-town port locations, remain fixed
between cases. Therefore the first case is **not** an observed-infrastructure
reconstruction. Comparisons isolate source additions and then tracks, within
the stated common network. Fixed military positions do not imply all units
were present simultaneously throughout the year. None of these cases models
resistance, provisioning, command hierarchy, campaign outcomes or state costs.

The audit asserts that adding sources or tracks never increases travel costs.
Mapped access is not clipped to painted claims; area summaries use land inside
the claim. Those painted boundaries also constrain proposed-town eligibility,
so agreement with them is not independent validation. Catchment population,
where used by the existing placement model, is not measured city population.

## Seasonal diagnostics and placement uncertainty

The maps retain the count of accessible bins and the longest consecutive
isolation spell, including across the year boundary. They also compare the
legacy exponential annual aggregation

`effective_days = -log(mean(exp(-monthly_days)))`

with access throughout all twelve bins (one-day exponential decay). An annual
value below two days can coexist with long seasonal isolation: two zero-day
bins and ten unreachable bins yield about 1.79 effective days. This is why an
annual threshold alone should not be described as continuous control.

Paired maps show access gained from adding proposed town sources, then tracks,
then road sources. A separate map counts whether a proposed town lies within
10 km in placement runs with declared seeds 1, 2 and 3. Climate, density, site
rules and painted-claim eligibility stay fixed. Three-run recurrence is
scenario sensitivity, not a calibrated settlement probability, a census of
villages or a prediction of urban population. This does not test all relevant
uncertainties or all possible town layouts.

## Current comparison

Shares of land inside the existing painted imperial claim with access in all
twelve seasonal bins (not estimated shares of territory actually controlled):

| Climate | Verified seats | Marked places | Add proposed towns | Add tracks | Add road sources | Forts/legions |
|---|---:|---:|---:|---:|---:|---:|
| Free | 15.6% | 16.4% | 70.7% | 73.0% | 76.8% | 7.1% |
| Earth raw | 14.7% | 15.6% | 61.4% | 64.5% | 69.6% | 6.9% |
| Earth corrected | 14.8% | 15.7% | 63.0% | 65.9% | 70.7% | 7.0% |
| Whittaker | 16.3% | 17.1% | 67.5% | 69.9% | 74.8% | 7.8% |

Proposed towns dominate the change. This demonstrates dependence on assumed
local administrative sources; it does not show that the recorded map is
wrong or the proposed settlements are real. A sparse list of commandery seats
need not include subordinate officials, villages or other mechanisms of
authority. Next steps should connect the recorded province/commandery
hierarchy, test administrative coverage at different travel thresholds, and
require conserved provisioning before interpreting military access as power.

## Sources, checks and reproduction

The methodological motivation is differentiated imperial networks (Smith 2005,
doi:10.1111/j.1467-8306.2005.00489.x; Glatz 2009,
doi:10.1016/j.jaa.2008.10.003), settlement-network inference under incomplete
evidence (Bevan & Wilson 2013, doi:10.1016/j.jas.2012.12.025) and explicit
contingency (Evans & Rivers 2017, doi:10.3389/fdigh.2017.00008). These motivate
the comparisons, not the numerical cutoff or a validated political model.
See [the research proposals](CONTROL_SETTLEMENT_PROPOSALS_20261104.md) for
the broader literature and proposed hierarchy, surplus and provisioning work.

Run with the scientific environment:

```text
python scripts/audit_administrative_inventory.py
python scripts/review_imperial_access.py
python scripts/publish_imperial_access.py
python scripts/refresh_atlas_pages.py
python scripts/build_fit_hub.py
```

Input/source hashes and numerical grids are stored under
`output/administrative_inventory_20261104/` and
`output/imperial_access_20261104/`. In-view downloads provide per-place CSV,
all 72 commandery matches/conflicts, typed inventory and full NPZ grids.
The browser checks inventory and food/climate identities before exposing new
maps; a mismatch removes Administration while keeping climate usable. The
launcher prints the new topic and 70/72 seat count, and the release manifest
pins its metadata. Frozen climate, population and existing political exports
are unchanged; this milestone is not a physics recalibration.

Analytical tests cover symbol roles, ID linkage, conflicting seats, geography-
only import, cyclic spells and annual aggregation. Browser verification checks
all four climate packets and twelve views each, CSV versus NPZ, all 4096
twelve-bit access masks, shareable state, downloads, mobile layout, conditional
controls and rejection of a mismatched input identity.

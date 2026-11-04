# Worldwide pasture and seasonal feed resources — 4 November 2026

**Livelihoods** adds three buttons/six views to every normal atlas, including
matching Earth raw/corrected packets: annual usable forage and feed equivalents;
lean-bin new growth, minimum zero-loss reserve and a 90-day-buffer test; mapped
water proximity. Production is evaluated across all land, without a political
claim eligibility mask. No people, actual herd size or livelihood identity is
assigned by these maps. Existing climate, farming/population and control exports
remain unchanged.

## Research basis

[FAO (2012), Conducting national feed assessments](https://www.fao.org/4/i3043e/i3043e.pdf)
motivates feed inventories that distinguish supply, requirements, seasonal
availability and access to water. Water restrictions vary by animal and local
conditions; incomplete water information cannot establish a universal grazing
boundary. This implementation therefore publishes water proximity separately.

[FAO's Kenya livestock assessment, chapter 7.4](https://www.fao.org/4/t0828e/T0828E09.htm)
specifies a reference 250 kg tropical livestock unit with maintenance intake
of 6.25 kg dry matter/day and additional requirements for production. Here the
intake defines a **feed-equivalent unit only**, not an adequate diet, a locally
appropriate animal, or an estimate of milk/meat output.

[Mottet & Assouma (2024), doi:10.3389/fanim.2024.1354728](https://doi.org/10.3389/fanim.2024.1354728)
shows why dry matter, energy and protein need separate seasonal accounting;
DM abundance can coexist with nutritional deficits. Its Feed Balance Sheet is
not reproduced here. The present model lacks the evidence needed for a global
multi-nutrient herd simulation.

[Illius & O'Connor (2000), resource heterogeneity and ungulate population dynamics](https://www.gov.uk/research-for-development-outputs/resource-heterogeneity-and-ungulate-population-dynamics-oikos-89-283-294)
provides abstract-level motivation for seasonal key resources. The publisher
full text was unavailable; no equations or parameters from that model are used.

## Annual resource and land budget

Use each atlas's published Miami NPP in its existing g dry matter/m²/year
convention. Multiply by 1,000 to obtain kg DM/km²/year. Reuse current Harvest
assumptions for aboveground allocation (0.5), biome-dependent edible share and
usable fraction (0.25). Exclude the area already assigned to crops:

```text
cropped_share = published_arable_share × current_farmed_share (0.6)
remaining_share = 1 − cropped_share
usable_annual_DM = NPP × 1000 × aboveground × edible × usable × remaining
```

These annual allocation coefficients remain inherited assumptions, not new
empirical estimates or a calibrated response to grazing. Remaining land also
contains woods and other uses; its entire productivity is not automatically
edible. Crop residues and imports are not added. Annual feed equivalents divide
this DM by `6.25 ×365` in a reference accounting year; they cannot be added to existing farming, pastoral or
FORGE population scenarios. A complete joint human/animal budget remains future
work. Quantities are per km² **of land**, with partial coastal land fractions
retained for totals.

## Seasonal allocation and conserved inventory

An explicit proxy distributes each annual resource across twelve equal bins:

```text
weight[m] = clip(T[m]/15, 0, 1) × P[m]/(P[m]+50)
supply[m] = annual_DM × weight[m]/sum(weight)
```

The 0/15 °C and 50 mm scales are uncalibrated scenario choices, reusing the
project's simplified seasonal-resource approach. They are not observed pasture
phenology or a reproduction of a vegetation model. Annual DM is conserved
exactly. If all weights vanish while annual DM is positive, seasonality remains
unresolved; a uniform growing season is not fabricated. Zero annual forage is
distinct from unresolved seasonality.

The lean-growth map shows minimum new production divided by average new
production. It deliberately omits standing forage and reserves; low new growth
alone does not imply animals starve. A separate inventory test consumes **half
the annual usable DM**, evenly through the year. This is a specified demand,
not observed stocking. The maximum cyclic cumulative deficit gives the minimum
zero-loss reserve required to meet that demand indefinitely. Units are days of
the declared demand, not civil-calendar dates or days of food for people.

The 90-day-buffer view uses storage capacity equal to 90 days of that same
demand and solves the smallest repeating inventory. Supply is grazed/withdrawn
or stored once; excess over capacity is explicit overflow. Initial stocks must
be replenished by the repeating year. Stock/consumption/overflow ledgers close.
Bins with unmet demand are counted; they are not famine, mortality or weather
probabilities. Standing forage, cut fodder and hay are not distinguished.

Zero loss is an optimistic inventory reference. Preservation/harvest labour,
quality deterioration, energy/protein, herd age/reproduction, body condition,
movement, access rights and drought years remain unmodelled. Twelve-bin
production/demand accounting also omits within-bin timing. The result identifies
resource questions for stationary or mobile scenarios, not sustainable herd
carrying capacity or the merits of a particular social system.

## Water and geographic examples

Water distance is mean land distance to existing mapped rivers/lakes. It does
not establish routes, seasonal permanence, salinity, sufficient volume, wells
or species-specific watering itineraries. Distance thresholds in the legend
are reference bins, not imposed exclusions or a prediction of nomadic routes.

Four geographic examples use fixed drawing-fraction anchors and eligibility
from previously published Earth-raw fields: an agricultural-resource site in
the Kingdom of Tarani; a nonimperial grassland patch; a mixed-resource patch
outside named claims; and a site labelled Tribes of the Neck. The protocol
retains coordinates, source claim labels, selection rules and input hashes.
The examples are illustrative, not withheld validation or ethnographic cases.
Source-map claims themselves remain provisional. Neither grassland nor an
unclaimed patch establishes a population's mobility or absence of institutions.
The tribal label does not imply pastoralism.

## Current comparison

Median minimum zero-loss reserve among cells with a defined positive-resource
test, and known share of total land area requiring over 90 demand-days:

| Climate | Median reserve, demand-days | Land area requiring >90 |
|---|---:|---:|
| Free | 33.5 | 12.8% |
| Earth raw | 37.2 | 14.6% |
| Earth corrected | 35.6 | 15.3% |
| Whittaker | 47.0 | 19.3% |

All current positive resources have a resolved allocation under this proxy;
the analytical unknown-season fixture is nevertheless retained. In corrected
Earth, roughly 25% of annual modelled DM lies outside named mapped claims.
These figures describe the stated resource assumptions, not historical herd
distribution, population density or political organization. Maximum per-cell
annual inventory residual is below 5e−11 kg DM in these runs.

## Reproduction and delivery

`harvest/pasture.py` implements the allocation/diagnostics and reuses the tested
cyclic food-inventory kernel. `data/pasture_model.json` and
`research_notes/pasture_20261104.json` distinguish sources from assumptions.
Run `python scripts/build_pasture_maps.py`, then refresh atlas pages and build
the fit hub. Input/source hashes and geographic examples are saved under
`output/pasture_maps_20261104/` and in each public `data/pasture.json` manifest.

All four climate packets have matching maps, a compact readout binary and full
float32 NPZ downloads. Annual DM stays float32 to retain small positive values;
lean fractions use 1/60,000 steps, reserve days 0.01, water distance 0.1 km and
shortfall bins exact integers. Missing values have explicit nodata encodings.
Point CSV records units and the demand scenario. The browser checks its loaded
Harvest identity and the resource binary before exposing readouts. Failure
removes only this topic, keeping the underlying atlas usable.

Tests cover disjoint cropped/grazing area, DM units, annual conservation,
unresolved phenology, equal annual supply with different seasonality, calendar
rotation, scaling, explicit reserves and mass closure. Browser checks cover
all packets/views, numerical CSV/NPZ agreement, points outside named claims,
missing identity/data, controls, URLs, downloads and mobile layout. This
milestone extends the [worldwide scope](WORLDWIDE_PROVISIONING_SCOPE_20261104.md)
without adopting a new population, livelihood assignment or climate calibration.

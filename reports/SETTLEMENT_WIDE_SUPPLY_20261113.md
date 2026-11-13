# Wider grain supply for the release-3 towns

**Outcome.** With grain allowed to travel and one third of the rural surplus
marketed, 1,012 of the 1,053 release-3 towns are fully fed and 85% of town
residents eat. The 41 largest cities stay short; the capital is 37% fed. At 10%
marketed only 35% of residents are fed. A first Roman pilot supports the
one-third level ([Earth pilot](SETTLEMENT_SUPPLY_EARTH_20261113.md)).

Protocol: [plan and amendment](../calibration/settlement_wide_supply_20261113/plan.json).

![Grain supply, corrected climate, one third of surplus marketed](figures/settlement_wide_supply_20261113.png)

Green: fed by its own freight hinterland. Blue: fed with shipments from other
towns. Red: still short. Lines: the 400 largest shipments.

## Results (corrected climate, 600 field hours a worker; raw is within two points)

| Town sizes | Surplus marketed | Own hinterland | With imports | Short | Residents fed |
|---|---|---:|---:|---:|---:|
| **Sliding density (headline)** | **one third** | **832** | **180** | **41** | **85%** |
| Sliding density | 10% | 651 | 106 | 296 | 35% |
| Sliding density, 300 field hours | one third | 632 | 98 | 323 | 35% |
| Flat 100/ha | one third | 982 | 70 | 1 | 100% |
| Flat 100/ha | 10% | 730 | 261 | 62 | 93% |

Grain ledger for the headline, in millions of person-years of food: 127.9
grown; 39.8 eaten by rural people; 29.4 marketed. Of the marketed grain, 6.0
never leaves cells beyond any town's reach, 9.9 is consumed by transport, 11.5
is eaten in towns and 2.0 is excess nobody can use. The ledger closes exactly.

- **The largest cities are the ones that stay short.** The 41 short towns hold
  4.3 M of the 13.6 M town residents and have a median of 95,000 residents.
- **Field labour matters as much as the marketed share.** Halving field hours
  has the same effect as cutting the share from one third to 10%.
- **Most towns need no imports**: 832 are fed by their own freight hinterland.

## Correction after the first published build

The first build (commit `87d19b43`) took the full cereal *potential* above rural
needs as surplus: 240 M person-years, which the 40 M rural people could not have
grown. It reported every town fed at one third. Production is now limited by the
published field-work rule (40% of rural people work the fields, 600 listed hours
a year, 30-day reaping window), which gives 128 M. The numbers above replace the
earlier ones.

## How it works

1. **Grain grown** per cell: cereal potential, limited by the field hours of the
   rural people who remain after towns are populated.
2. **Grain marketed**: a share of what is grown beyond rural needs.
3. **Transport is paid in grain.** A path costing c road-km equivalents delivers
   1 − c/270 (road haulage eats a staple's whole value at about 270 km,
   Duncan-Jones 1982). Sea, downstream river and road cost 1 : 5 : 28 per km
   (Diocletian's Price Edict). Costs come from the atlas's seasonal freight
   network on the release-3 towns and tracks, averaged over four trade months.
4. **Hinterland.** Every cell sends its grain to the town it reaches most cheaply.
5. **Between towns.** Towns with excess ship to towns in need, cheapest link
   first. Imported grain is not shipped on.

## In the atlas

- Settlements options "grain supply" at one third (headline) and 10%.
- On the default settlement maps the white centre means "fed, including grain
  shipped in" at one third. **Town sizes on the map are not reduced** where a
  city is short; the shortfall is shown, not applied.
- The supply-supported reach now takes its staffed towns from these fed
  residents ([downstream report](SETTLEMENT_DOWNSTREAM_20261113.md)).

## Limits

- A scenario on existing coefficients. The Earth pilot tests only the overall
  marketed amount, with a proxy for production.
- 600 field hours covers listed field tasks only, not threshing, transport or
  other household work, so labour is if anything too generous.
- The shipment plan is feasible, not optimal.
- Wheat and barley only. No fish, livestock, other crops, prices, shipping
  capacity, storage through the year, or state grain fleets.
- The independent review recomputes production, allocation and ledgers, not the
  freight costs, which come from the atlas network.

## Reproduce

```sh
.venv/bin/python -I scripts/build_wide_supply_release3.py
.venv/bin/python -I scripts/review_wide_supply_release3.py
.venv/bin/python -I scripts/publish_wide_supply_release3.py
```

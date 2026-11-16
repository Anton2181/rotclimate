# Forest in travel cost (C2): Earth test, 16 November 2026

**Outcome: adopted under the declared gates, but the effect on Earth is about zero.**
Walking cost now comes from the Earth-fitted forest share (the new "Forest (AD 200
potential)" layer) rather than the Whittaker biome lookup. Control territory stays as
accurate, and borders fall on forest as often as before. The rule mainly makes the
model consistent: the biome lookup counted most of central Europe as open shrubland.

Protocol: [plan](../calibration/forest_travel_20261116/plan.json), committed before any
C2 result. Nothing was fitted. Development used the two seen pools. The blind run was
made once, on three pools never used for a control test.

## Rule

walking coefficient = open × (1 − f) + forest × f

* f is the C1b forest share (0–0.6).
* "open" is the biome coefficient with forest biomes set to 1.2.
* "forest" is the forest biome's own coefficient, or 1.5 elsewhere (Soule & Goldman,
  as already used).
* Swamp and snow are unchanged.

## Results

| Pool | Accuracy, biome lookup | Accuracy, C2 | Forest on border: real | Lookup | C2 | Cells changed |
|---|---:|---:|---:|---:|---:|---:|
| Rome AD 150 (dev) | 0.848 | 0.849 | ×1.14 | ×0.77 | ×0.78 | 203 |
| Han AD 2 (dev) | 0.663 | 0.661 | ×0.99 | ×1.11 | ×1.10 | 1,920 |
| Ming AD 1600 (blind) | 0.377 | 0.381 | ×1.03 | ×1.12 | ×1.12 | 978 |
| Sui AD 609 (blind) | 0.705 | 0.704 | ×1.05 | ×1.14 | ×1.13 | 925 |
| Europe AD 1700 (blind) | 0.581 | 0.578 | ×1.14 | ×1.19 | ×1.19 | 755 |

Gates:
* **G1 passes.** Accuracy is within 0.01 of the lookup in all three blind pools.
* **G2 passes, narrowly.** The forest pattern is closer to Earth's in two of three pools,
  by about 0.002 in log distance.

The margins are far below what anyone could see on a map. C2 changes 1–4% of territory
cells and slightly shrinks territory in forested regions.

## What adoption means

* By the plan, the map's walking cost takes the forest layer, and the reach chain is
  rebuilt as a new release.
* Because the Earth effect is near zero, the map impact is measured first.
* The owner is told before anything is published.
* The Ming 1600 pool scores low for both rules (0.38). As with Qing 1820, the AD 200
  chain holds far less than a late-imperial state space.

## Reproduce

```sh
.venv/bin/python -I scripts/forest_travel.py prep rome   # likewise han, T9, T10, T11
.venv/bin/python -I scripts/forest_travel.py dev
.venv/bin/python -I scripts/forest_travel.py blind       # run once
```

## Map probe (control step only)

`scripts/forest_travel_map_probe.sh` reruns control v2 and v2.1 with `ROTCLIMATE_FOREST_TRAVEL=1`.
Release-4 towns, supply and staffing are kept fixed; only the control step's walking cost
changes.

| Climate | Held land, release 4 | Held land, C2 | Owner changed |
|---|---:|---:|---:|
| Raw | 66.6% | 66.2% | 1.0% of land |
| Corrected | 66.8% | 66.4% | 0.8% of land |

The map changes little: under 1% of land changes owner. Republishing waits for the
owner's decision.

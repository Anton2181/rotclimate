# Storage constraints after the first field-water experiment

Source qualification after checkpoint `e1d88d57` identifies a specific model
dependency: separate surface drying, root-zone storage and inundation/drainage
timing. The 96 published sensitivity runs remain unchanged; no capacity is
selected from their crop-water scores.

## Generic soil and cereal constraints

FAO-56 Chapter 7 uses a shallow evaporation layer, typically 0.10–0.15 m, with
evaporation declining as it dries. Table 19 gives clay surface-layer REW of
8–12 mm and TEW of 22–29 mm at 0.10 m. The deeper root store is not simply
available for bare-surface evaporation at full PET throughout a dry interval.
The experiment's zero/full-PET cases remain sensitivity endpoints.
[FAO-56 Chapter 7, Table 19 and equations 73–74](https://www.fao.org/4/x0490e/x0490e0c.htm).

Chapter 8 defines TAW as `1000 × (field-capacity − wilting-point) × rooting-depth`.
Table 22 lists maximum effective root-depth ranges of 1.0–1.5 m for barley and
1.5–1.8 m for winter wheat. Both have depletion fraction 0.55 at crop ET near
5 mm/day; it changes with demand. Combining the published soil and root ranges
gives generic upper envelopes of **300 mm for barley** and **360 mm for winter
wheat**. These are not measurements of Nile soils. Stress starts before total
available water is exhausted; groundwater supply is a separate balance term.
[FAO-56 Chapter 8, Table 22 and equations 82–85](https://www.fao.org/4/x0490e/x0490e0e.htm).

The reference export retains all nine published soil classes and both cereals:
18 derived envelopes. It uses Table 19's published available-water difference,
not subtraction of unrelated field-capacity/wilting-point range endpoints.
The soil classes are not assigned geographically or fitted to Egypt's deficit.
The next model needs observed or independently qualified local soil inputs.

## Inundation timing is different from root storage

Butzer's historical synthesis describes field inundation around 1.5 m deep for
6–10 weeks, extending into mid-November in the north, followed by a winter with
moist soils and a high water table. Flood depth must not be relabelled as
plant-available root-zone capacity. These broad Pharaonic seasonal descriptions
also do not establish a universal exact cereal calendar for Roman Egypt.
[Butzer (1984), printed p.105 / PDF page 4](https://sites.utexas.edu/butzer/wp-content/uploads/sites/6106/2017/07/Butzer-1984-LongTermNile.pdf).

Our fixed experiment stops capture after October and represents November–March
as five whole climate bins. Inference: before estimating actual basin farming,
the model needs a drainage/sowing clock capable of representing partial months
and ponded water. Moving capture after evaporation or changing crop length just
to improve the Nile score would introduce an undeclared model choice.

## Concrete next implementation

1. Declare a separate surface-evaporation and root-zone ledger, with water
   stress and explicit drainage/percolation. Neither store may duplicate water.
2. Verify it against FAO's drying examples and independent conservation checks
   before new Earth field outputs. Keep floodwater/groundwater separate from
   root-zone TAW and require explicit, paid transfers.
3. Qualify drainage, crop dates and local soil profiles before spatial parameter
   selection. Add Tigris and independent-region evidence, and a shared
   Earth/fantasy flow adapter before any harvest rule is adopted.

The generic source tables support the model structure. They do not validate
local parameters, a groundwater rate, irrigated hectares or resident capacity.
In particular, the successful 600 mm sensitivity case is not qualified as an
ordinary cereal root-zone store by these references.

## Provenance and reproduction

```sh
.venv/bin/python scripts/qualify_flood_storage_sources.py
```

Publisher downloads are cached with pinned SHA-256 digests. Independent
HTMLParser and raw-regex extraction agree on the selected table rows; Decimal
and float calculations agree on every envelope. A fresh reference export is
byte-identical. Raw pages/PDF remain in ignored cache; small numeric facts,
citations and source hashes are committed.

[Source facts and derived envelopes](../atlases/earth_evidence/flood_storage/soil_reference.json) ·
[Replay receipt](../output/flood_storage_sources_20261114/replay.json) ·
[Unchanged field experiment](FLOOD_BASIN_STORAGE_20261114.md).

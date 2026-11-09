# Carry delta irrigation into cereal calendars — 9 November 2026

The v2.2 release stopped at its cereal-work consistency check: wheat production recomputed for calendar
selection differed from the published Harvest packet by up to 78,096.6 kcal/ha. The check was retained.

Harvest's `derive()` adds discharge-dependent delta fans to the terrain/distance irrigation returned by
`geometry()`. The calendar producer still called `geometry()` alone. It therefore reconstructed a different
crop response at the river mouths, despite using the same climate and crop coefficients.

`scripts/build_cereal_work_maps.py` now obtains its unquantized geometry from the same complete `derive()`
calculation as the Harvest exporter. Reading packed irrigation instead would introduce another rounding
step before computing the crop response. No irrigation equation, fan parameter or crop coefficient changed.

The full producer then passed its existing per-cell checks for **both wheat and barley** across 245,031
analysis-land cells in each climate mode. Maximum differences from the packed energy fields were
20.8878 kcal/ha (raw) and 20.9099 (corrected), within the declared packet-quantization tolerance. Every
productive selected cereal retained at least one calendar. These are integration checks, not new Earth
agronomic validation.

The original run's failed log and input identity remain in `output/atlas_v22`. The continuation uses
`output/atlas_v22_calendar_fix`: its reuse receipt verifies that only this previously uncompleted stage's
CLI producer changed. Already completed physics, correction, export, coverage and pasture inputs are
byte-identical; their stage results are reused explicitly. Downstream food/work, supply and control
publication continues under the new identity rather than rewriting the old one.

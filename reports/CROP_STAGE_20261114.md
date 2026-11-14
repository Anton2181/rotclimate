# Crop-stage source constraints and exact coefficient curves

The supplied four-stage basal-coefficient component now reproduces FAO56
Example 30 and integrates arbitrary fractional intervals exactly. This prepares
a later crop-stage comparison without selecting a new Earth calendar, changing
field water outputs, or adopting a new harvest or settlement rule.

The continuation first fetched the latest remote handoff, `3e649793`, which had
already completed the rain-timing sensitivity. The overlapping local draft was
preserved in a Git stash rather than replacing that completed work. Protocol
`e470de0a` declared this component and source review before its code and outputs.
The published example was already known and is not an independent regional test.

Open [the normal evidence page](../atlases/earth_evidence/crop_stage/index.html)
for the curve, all source contexts and downloadable results.

## Source findings

[FAO56 Chapter 7](https://www.fao.org/4/x0490e/x0490e0c.htm), Table 17, gives
barley initial/mid/end basal coefficients 0.15/1.10/0.15. The initial cell
inherits the cereal heading; a blank cell does not mean zero. Spring wheat
similarly inherits 0.15 initially, with mid 1.10 and end 0.15–0.3. Winter wheat
has contextual initial alternatives 0.15/0.5, mid 1.10, and end 0.15–0.3.
Footnote 11 distinguishes sparse ground cover from a fully covered nonfrozen
winter dormancy period. Footnote 10 says the higher final value is for hand
harvesting. These are conditional source values, not unrestricted fit ranges.

The table assumes minimum relative humidity 45% and wind 2 m/s. Equation 70
requires climatic adjustment of mid/end values above 0.45 outside those
conditions. The current legacy constant crop coefficients are not such a curve.

FAO defines Kcb × ETo as primarily transpiration, but explicitly includes
residual diffusion from below the dry surface and beneath dense vegetation.
Therefore, substituting a published Kcb curve into the existing root-uptake
operator would require an explicit, reviewed approximation for that residual
component. All basal ET cannot be described as measured root transpiration.
This does not retroactively change the prior scenarios' declared metric.

[Chapter 6](https://www.fao.org/4/x0490e/x0490e0b.htm), Table 11, provides
11 stage-duration examples across Barley/Oats/Wheat, Winter Wheat and Grains
(small). Every original planting/region label is exported. For example:

|Source crop group|Initial/development/mid/late days|Total|Planting|Source region|
|---|---|---:|---|---|
|Barley/Oats/Wheat|15/25/50/30|120|November|Central India|
|Barley/Oats/Wheat|20/50/60/30|160|December|California Desert, USA|
|Winter Wheat|30/140/40/30|240|November|Mediterranean|
|Grains (small)|25/35/65/40|165|October/November|Pakistan; Arid Region|

No row establishes an ancient Nile barley calendar. Unspecified source regions
remain unspecified. Superscript footnotes are kept separate: `20` followed by
footnote `2` is 20 days, not 202. Table 11 footnote 2 states that winter-wheat
initial/development stages lengthen with frozen conditions and dormancy.

Raw HTML is digest-pinned in the protocol and restored by the producer into
`data/cache/crop_stage_20261114/`. Two independent parsing paths agree on all
11 duration/context rows and three cereal coefficient rows. The previous
Chapter 7 cache is reused when available. HTTP requests use a browser user-agent;
the no-header request was rejected with 403, while the public source then loaded.

## Component and checks

`harvest/crop_stage.py` defines `StageCurve`: four strictly positive supplied
stage durations and three finite nonnegative basal coefficients. Initial and
mid-season segments are constant; development and late-season segments are
linear. `value` evaluates supplied crop age; `integral` gives coefficient-days;
`mean` divides by the actual positive interval duration. Intervals may cross
stage boundaries. Inputs outside the supplied crop period, reversed intervals,
nonfinite parameters and zero-length mean intervals are rejected. There is no
inferred planting date, thermal progression, climate correction or root growth.

The published dry-bean example uses 25/25/30/20 days and coefficients
0.15/1.14/0.25:

|Day|Unrounded component value|FAO printed value|
|---:|---:|---:|
|12|0.15|0.15|
|37|0.6252|0.63|
|65|1.14|1.14|
|90|0.695|0.70|

Its integral is 67.975 coefficient-days; its mean over 100 days is 0.67975.
These are dry-bean component results, not a Nile cereal demand estimate.

137 controls pass, including 20 new component controls and the existing 117.
Independent 40-digit Decimal arithmetic verifies point values, half-up printed
rounding, all 277 exported intervals and 4,000 intervals across 100 synthetic
curves. Largest exported interval discrepancy is 1.10e-14 coefficient-days;
largest synthetic discrepancy is 7.67e-14. Both fresh numeric files reproduce
byte for byte. All 917 protected numeric/atlas files remain unchanged.

The normal page retains all 18 source/benchmark rows, with six viewport/theme
checks, five byte-checked downloads, an actual CSV download, image/keyboard/width
and hub/evidence/return-link checks. Receipts and the staged Windows-style
checkout/release check live under `output/crop_stage_20261114/`.

## Reproduce and continue

```sh
.venv/bin/python -m pytest -q tests/test_crop_stage.py
.venv/bin/python scripts/crop_stage_benchmarks.py
.venv/bin/python scripts/crop_stage_benchmarks.py --out output/crop_stage_20261114/fresh
.venv/bin/python scripts/review_crop_stage.py
.venv/bin/python scripts/publish_crop_stage.py
.venv/bin/python scripts/build_fit_hub.py --date 2026-11-14
python scripts/check_crop_stage_browser.py
```

The browser runner expects the repository served on port 8766. Stage the final
site before running `scripts/check_atlas_checkout.py --out
output/crop_stage_20261114/windows_checkout.json`. Numeric/source outputs are
tracked; the fresh duplicate directory and browser screenshots are ignored.
The normal evidence publisher runs this new publisher after rain timing.

Next qualify local phenology and reference ETo/climatic adjustment, distinguish
basal diffusion from crop uptake, and specify canopy exposure/root development
and inundation/drainage. Declare any Earth comparison before its outputs. Do
not scale generic stage ratios or choose among regional examples because they
improve Egypt. The completed rainfall experiment excludes a large rain-timing
effect only for its eight fixed illustrations and declared patterns.

Tigris, shared Earth/fantasy flow, independent regional evidence and a frozen
harvest translation remain required before Nile gain/Mesopotamian non-inflation
and whole-empire calibration. Current release-3 settlements and marketed share
0.3923 remain adopted: 850 self-fed, 174 importers, 29 short, 91% fed; reach
staffing 1042. Egypt calibration still fails. Actual occupancy/provider evidence,
S3–S5, complete resources/diets/work, mobile actors and political authority are
separate unresolved programme obligations.

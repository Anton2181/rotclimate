# Finite pond–groundwater–soil accounting verified

Groundwater transfer now spends an explicit accessible stock in the same ledger
as pond capture, soil and river delivery. Separate scalar replay agrees with
every saved synthetic history. This completes the accounting component;
hydraulic permissions and capacities remain supplied inputs. There is no Earth
groundwater field, harvest or settlement adoption.

Open [the demonstration and downloads](../atlases/earth_evidence/groundwater_budget/index.html).
Declaration `6e7490d2` preceded implementation. Fixed demonstrations were
committed in `2a072eb8` before their outputs. These are synthetic component
checks, not independent regional validation or locally measured rates.

## Budget and timing

`harvest/groundwater_fields.py` wraps the unchanged field kernel one actual step
at a time. Stocks are top/deep available soil water, surface water below wilting
point, pond and accessible aquifer above a supplied inaccessible floor. Default
initial stocks are empty; supplied initial stocks are accounted and bounded.

1. Supplied external aquifer loss is debited, limited by stock.
2. Upward transfer is limited by permission × actual duration, remaining aquifer
   stock and soil deficit. It fills deep available water, then surface water
   below wilting point, then top available water. Actual increments are debited
   once. Roots retain their restriction to available water.
3. Recharge draws only from previous pond stock, while recharge and pond
   permissions are open. Pond stock, aquifer room, recharge rate and the shared
   infiltration allowance bound it. Recharge consumes the same allowance as
   soil infiltration.
4. The original field/river kernel handles remaining infiltration, river
   rationing, delivery loss, evaporation, drainage and uptake. Fresh delivery
   may refill the pond but cannot recharge until a later step.

Recharge and upward flux are internal transfers, not new joint-balance inputs.
Percolation, overflow, pond release and downstream flow receive no duplicate
credit or instant return-flow reuse. All five periodic stocks must converge
within 1e-6 mm in at most 50 cycles; nonconvergence remains explicit.

This budget does not solve transient Richards flow, infer depth or hydraulic
permission, apply Dutch O8 to the synthetic soil, or represent high-water-table
oxygen/salinity constraints.

## Fixed synthetic demonstrations

A 1,000 m² field has twenty flood days followed by forty crop days. Flood river
supply is 30 m³/day; crop supply and all rain are zero. ETo is 4 mm/day, Kcb is
0.75, bare background is 0.15, pond capacity is 40 mm, shared infiltration is
20 mm/day and delivery efficiency is one. Soil θFC=0.25, θWP=0.10, root depth
1 m, evaporation depth 0.1 m and REW 9 mm are illustrative. Aquifer loss is zero.

|Case|Recharge mm|Upward mm|Final aquifer mm|Root uptake mm|Root demand mm|River delivery m³|
|---|---:|---:|---:|---:|---:|---:|
|Groundwater disabled|0|0|0|105.416|120|271|
|Stored, no upward permission|40|0|40|105.416|120|311|
|Finite groundwater transfer|40|40|0|119.140|120|311|

The storage cases use 40 mm accessible capacity and a 5 mm/day recharge limit.
Finite transfer permits at most 3 mm/day upward during the crop; the other
permits zero. Empty first-cycle results are displayed. Separately, all five
periodic stocks converge in two cycles for every case. No member is adopted.

Storing 40 mm costs 40 m³ of extra river delivery here. Water stored without
permission adds no uptake. Permission allows the stock to empty; root uptake
increases by 13.724 mm, less than the 40 mm transferred. This is root uptake,
not total-crop ET or grain. It cannot directly replace total ET in legacy Ky.

## Independent verification and publication

223 controls pass, including fifteen new groundwater controls. Ten synthetic
zero-groundwater forests reproduce every original field array exactly, with
fractional durations, delivery efficiency and multiple nodes retained. Other
controls cover empty starts, exhaustion, below-wilting restrictions, shared
infiltration, closed pond permissions, loss ordering and nonconvergence.

100 synthetic forests / 4,680 field-steps include explicit bounded initial
stocks as well as empty starts. The reviewer imports neither the new component
nor producer. Scalar soil/pond/forest accounting checks all 105,552 history
values, infiltration/capacity bounds, fixed demo inputs, 180 CSV rows and all
five-stock periodic states. Maximum history difference is 1.60e-13; maximum
scalar field residual is 6.76e-14 mm and joint residual is 3.70e-13 m³. Terminal
outlets are counted once.

Three fresh numeric files reproduce byte for byte. The canonical test-runtime
receipt is pinned separately and reused by fresh exports. All 937 protected
files remain unchanged, including prior hydraulic and regional forcing results.
Six viewport/theme cases verify all three numerical rows, eight downloads,
actual CSV download, image/keyboard/width and navigation. Staged Windows-style
checkout and complete release verification receipts accompany the page.

## Reproduce

```sh
.venv/bin/python scripts/paid_groundwater_benchmarks.py
.venv/bin/python scripts/paid_groundwater_benchmarks.py --out output/paid_groundwater_20261114/fresh
.venv/bin/python scripts/review_paid_groundwater.py
.venv/bin/python scripts/publish_paid_groundwater.py
.venv/bin/python scripts/build_fit_hub.py --date 2026-11-14
python scripts/check_groundwater_browser.py
```

The browser runner expects port 8766. Stage final assets before
`scripts/check_atlas_checkout.py --out output/paid_groundwater_20261114/windows_checkout.json`.
Primary numeric archives are explicitly tracked despite the NPZ ignore rule.

## Next dependency

Recover and qualify local hydraulic/soil profiles, seasonal water-table depth,
root development/suction and recharge/drainage evidence. Separate measurements
from model-derived fluxes. Managed modern Delta plots cannot silently become
ancient basin defaults. Declare an internally consistent soil/root/hydraulic
definition and finite water inputs before scoring regional groundwater fields.

Weather period/grid consistency, local phenology/canopy, transient and high-water-
table crop constraints, shared Earth/fantasy weather/river inputs, Tigris and
independent regions remain open. Freeze harvest translation before Nile gain,
Mesopotamian non-inflation and whole-empire supply checks.

Release-3 / marketed share 0.3923 remain adopted: 850 self-fed, 174 importers,
29 short, 91% fed; reach staffing 1042. Egypt calibration still fails. S3–S5,
empirical occupancy/provider/size, complete diets/resources/work, mobile actors
and political authority remain separate programme obligations.

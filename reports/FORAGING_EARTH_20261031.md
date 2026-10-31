# The foraging scenario against Binford's hunter-gatherers, 31 October 2026

The atlas's adapted FORGE scenario (`reports/FORAGING_20261027.md`) had only
numerical verification. This is its first empirical test: Binford's (2001)
table of ethnographically documented hunter-gatherers (CRAN package
`binford` 0.1.0, 339 groups; Marwick, Johnson, White, Eff; GPL-3),
population density against the model run at each group's location with
**observed** WorldClim 2.1 climate (so this tests the forager model, not the
climate model). Plan frozen and committed before any run:
`calibration/forager_binford_20261031/plan.json`; runner
`scripts/forager_earth_test.py`; results `output/forager_binford_20261031/`.

**Sample.** Binford's normal cases with a positive density and WorldClim
land within 25 km: 280 groups. Fit set (where anything is fitted): the North
American culture areas, 214 groups. Test set: the rest of the world
(Australia 47, South America 8, Africa 7, Asia 4), 66 groups.

## Result

| configuration | set | density rank correlation | median abs log10 error | median bias | animal share vs observed |
|---|---|---:|---:|---:|---:|
| A, current atlas (300 y, mean of last 50) | fit | 0.682 | 0.366 (×2.3) | +0.14 | 0.53 |
| | test | **0.701** | **0.483 (×3.0)** | +0.48 | 0.45 |
| B, long-window median (600 y, last 300) | fit | 0.671 | 0.374 | +0.16 | 0.52 |
| | test | 0.697 | 0.508 (×3.2) | +0.51 | 0.44 |
| C, B + food storage (capacity fitted on the fit set) | fit | best capacity 0 MJ (storage only worsens the fit) | | | |
| | test | = B | | | |

* **The model ranks forager densities well and transfers:** rank
  correlation 0.70 on continents it never saw. It is too dense by a factor
  of ~3 outside North America (Australia +0.51, Africa +0.51 in log10) and
  6–8× in the Subarctic and the interior west (+0.88, +0.75), while it is
  right on the Arctic coast (−0.08) and the Northwest Coast (−0.12), whose
  people lived mainly on fish and sea mammals, which the model does not
  have. Terrestrial food is therefore too generous, and the coasts come out
  right for the wrong reason.
* **B (long-window median) fails the frozen rule** by a hair: test error
  +0.025 against an allowed +0.02 (medians sit above means in cycling
  cells). The atlas keeps its summary.
* **Storage (C) only hurts** on the fit set (median error 0.374 at 0 MJ,
  0.393 at 250, 0.457 at 2,000): it adds people where the model already has
  too many. Not adopted; the option stays in the kernel (off).

## Why the atlas's foraging map is speckled

On 400 cells of the Earth-fit atlas over 1,000 years, the annual population
of many cells oscillates with a 2-year period (the once-a-year population
step overshoots) and about a third have no clear period. The year-to-year
variation is 7.7 % for the median cell and 34 % at the 90th percentile.
The median cell's mean changes by 0.2 % between consecutive 50-year
windows, but 10 % of cells change by more than 11 %, so a small change of
input (such as the Earth corrections) moves those cells' 50-year means by
±20 %. The kernel now also returns long-window robust statistics (median,
10th and 90th percentiles, lag-1 autocorrelation of the annual density)
and an optional food store (`storage_capacity_mj`, off by default), with
the published configuration unchanged (17 foraging tests pass).

## Next

The addendum to the plan, frozen before its runs, tests (B2) the long-window
*mean* (the same statistic as the atlas's, with six times the sample, to
remove the speckle) and (D) aquatic foods: coastal and freshwater fish as a
third food source, with any scale fitted on North America only and judged
on the rest of the world, including whether it predicts which groups
depended on fishing.

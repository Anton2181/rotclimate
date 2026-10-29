# Three-day land-water sensitivity — 29 October 2026

All nine declared72-hour runs completed. Initial land water remains a dominant
source of rainfall and surface-temperature uncertainty after three days. Wet
baseline land produces much more rain than initially dry land, even though the
atmospheric initial state, external forcing and planetary parameters are fixed.
This is not evidence of two stable climates or a local optimizer trap: storage
and rain are still changing, and no parameters were optimized.

The two literal plans were committed in `5afa26b` before any new integration.
Wet land starts with50 kg/m² liquid and uses900/450 s; dry land starts with0
and uses900 s as a coarse initial-condition screen. Initial conversion rain is
returned before the clock starts in both branches. Initial water affects both
evaporative availability and surface heat capacity. Ocean storage and every
physical forcing parameter remain fixed. No observed climate/wind fields are used.

## Daily land rainfall,900-second cases

| Region | Initial water | Day1 mm | Day2 mm | Day3 mm | Final land liquid kg/m² | Final land T K |
|---|---|---:|---:|---:|---:|---:|
| North India | wet | .845 | 1.236 | 1.318 | 40.11 | 301.99 |
| North India | dry | .291 | .184 | .065 | .43 | 307.98 |
| Mexico | wet | 1.809 | 1.488 | 1.353 | 46.23 | 301.04 |
| Mexico | dry | 1.426 | .989 | .403 | 2.35 | 305.13 |
| Pacific Northwest | wet | .387 | 1.254 | 1.635 | 41.42 | 293.85 |
| Pacific Northwest | dry | .015 | .174 | .183 | .32 | 298.29 |

The48–72-hour window is fixed in advance. At450 s the wet day-three land means
are1.314/1.325/1.647 mm. Thus the initial-state effect is much larger than the
wet-branch difference in regional means between timesteps. That does not prove
the dry branch numerically converged, nor does it establish local rainfall skill.

Wet soil still loses water over the final day and the dry cases are accumulating
small amounts. The data do not support a steady-state claim. A fit to one wet
initialization would confound a guessed water store with climate-process skill.
Future calibration must declare its initial-state/spinup treatment and evaluation
window; it should not hide the uncertainty by selecting whichever start rains more.

## Numerical and reproducibility checks

Every wet day-one checkpoint reproduces the preceding24-hour experiment at the
same timestep: all six comparisons are **byte-identical in the saved arrays**.
That checks the longer-run orchestration without changing the underlying physics.

After72 hours, wet-case atmospheric T RMS timestep differences are .119/.140/
.068 K, and surface T differences are .065/.096/.034 K. Day-three spatial rain
RMS differences are .822/.479/.428 mm. Local rain is not declared converged merely
because regional means differ by only a few percent.

The existing356 focused physics tests remain applicable: no physical source file
changed for this experiment. The publisher checks frozen sources and reconstructs
every saved daily gas + kinetic + surface energy and atmospheric + surface water
budget against recorded radiation/lateral supply. Maximum errors are7.14e−15
relative for energy and3.45e−16 for water. Daily surface rain/evaporation identities
close to8.52e−13 kg/m². This is independent final-state accounting, not an
independent flux solver.

## Water-budget maps

For each fixed daily window, actual net evaporation is

`rain − change in surface liquid`.

Net horizontal column-water input is

`change in atmospheric vapor + change in surface liquid`.

All rain/evaporation is internal to that combined column, and there is no runoff
or water flux through the top. Thus its storage change measures integrated net
horizontal input. The maps compare these daily budgets between wet and dry starts.
They are **not moisture-origin tags**, and cannot identify an individual rain
drop as locally recycled versus ocean-sourced.

## Next practical step

Longer spinup and broader calibration are computationally expensive. A synthetic
profile identifies repeated liquid-equilibrium roots and sparse tracer solves
as substantial costs. The next useful implementation milestone is to accelerate
those numerical operations while preserving the same equations, conservation
checks and reference trajectories. That is groundwork for assessing longer
initial-condition convergence and a wider parameter search, not a substitute
for Earth validation or a claimed global optimum.

The grey/neutral forcing remains exploratory, with an explicit partial380 hPa
upper boundary. Terrain, nonlinear momentum, cloud/spectral radiation, stability,
ice, runoff and deep-ocean supply are still omitted. Earth r39 and all normal
world/biome/population fields remain unchanged. There is no monthly skill score,
recalibration or production adoption.

The prototype record is now **75 starts /71 completions /four retained earlier
numerical failures**, separate from legacy1934 attempts /1929 strict passes /
four historical failures /one interruption. The `.bat`-served research atlas
includes all nine cases, daily checkpoints, water maps and time series.

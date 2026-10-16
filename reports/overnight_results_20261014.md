# First overnight run: atlas published; sweep incomplete

Historical first-session report. The resumed sweep has since finished; see
[the final review](overnight_final_20261014.md) and [current plan](near_term_plan.md).

14 October 2026. Analysis of user-run results. No new climate simulations were
launched by the assistant. The original runner and model sources are unchanged,
so all verified completed cases remain reusable.

## What actually completed

The batch finished in 6.53 hours. Its 46 completed case records include reused
results and identical-setting aliases; they are not 46 new parameter trials.
There were no recorded numerical failures.

- 34 of the 64 planned sweep settings completed; 30 remain.
- Both endpoints completed for 16 of 24 controls. Evaporation has only its
  lower endpoint completed. Precipitation timescale, humidity threshold,
  orographic rain, instability, wet cooling, warmer SST and land-offset bounds
  are still untested in this sweep (the incumbent SST lower bound was reused).
- None of the 16 joint probes ran. A conclusion about parameter interactions
  would be premature.
- Both starting profiles completed one- and two-year warm-up checks.
- The narrower-storm candidate completed all three development worlds.
- The higher-seasonality candidate completed only development world 1.
- Fresh surroundings 401/402 and paired finer-grid checks did not run.

The unused time was a consequence of conservative stage admission/reserves,
not a crash. One late world 301 case took 101.7 minutes. After it completed,
the estimated next long cases no longer fit ahead of the fixed one-hour atlas
reserve, so the runner deferred them. Export actually took about 2.6 minutes.
The eight-hour command is a soft budget, not a promise to fill every minute.

## Numerical result: seasonal warm-up is sufficient for these two profiles

One versus two full warm-up years agree very closely on world 1:

| Monthly change across painted land | Broad anchor | Starting shortlist |
|---|---:|---:|
| 95th percentile absolute temperature change | 0.000099°C | 0.000100°C |
| Maximum absolute temperature change | 0.000380°C | 0.000386°C |
| 95th percentile absolute monthly-rain change | 0.0103 mm | 0.0101 mm |
| Maximum absolute monthly-rain change | 0.0695 mm | 0.0713 mm |

Both pass the stated continuous-field limits, including separate Mediterranean
and dry-zone regions. Eight-step versus two-year warm-up changes the broad
anchor's world 1 dry Mediterranean area only 12.02% → 11.59%. Initialization
does not explain most of the remaining dry strip in this configuration.
This does not establish warm-up adequacy for every new parameter set or grid.

## Stronger candidates: promising Mediterranean response, regional constraint

The retained broad anchor and narrow-width trial, with matched two-year warm-up:

| World | Med dry, anchor → narrow | Cold-dry recall | Hot-dry recall | Overall strict agreement |
|---|---:|---:|---:|---:|
| 1 | 11.59% → 6.71% | 68.05% → 67.44% | 56.27% → 68.82% | 48.87% → 50.63% |
| 302 | 1.54% → 0.84% | 53.54% → 56.17% | 34.31% → 50.29% | 50.32% → 52.11% |
| 301 | 3.67% → 1.90% | 69.16% → 65.57% | 64.22% → 65.69% | 54.14% → 53.82% |

Storm width 4.8° is rejected under the declared per-world limit: cold-dry world
301 loses 3.59 percentage points, versus the allowed 2. The gains on worlds 1
and 302 cannot compensate under that rule. Do not silently relax the limit.

Offline comparison of world 301's same cold-dry cells finds 118 lost correct
labels and 47 gains. Among lost cells, 79 become Csa and 28 remain BSk but lose
the exclusive painted label. Median paired annual rainfall rises 19.51 mm;
mean temperature changes only +0.008°C. Wetting/aridity and fuzzy membership,
rather than substantial warming, account for this damage.

On the original world 1 Mediterranean dry patch, the narrower storm pattern
changes annual rain by a median of just +0.16 mm, with winter +19.18 mm and
summer -18.94 mm. The seasonal redistribution is physically relevant and its
classification effect is amplified by the already documented winter-share
threshold. It should not be described as a large increase in annual water supply.

Seasonal contrast 0.85 achieves 7.82% dry Mediterranean land and 68.25% cold-dry
recall on world 1. Its worlds 302/301 were deferred, so it is **incomplete**, not
rejected. The partial sweep also shows storm asymmetry 0.1 improves world 1
agreement while preserving both dry-zone scores; its other worlds are untested.
Complete the remaining sweep before selecting new parameter combinations.

The long world 301 narrow-storm run converged, but required 11,219 coupled
temperature iterations, versus 1,933 on world 1 and 3,074 on world 302. Twelve
seasonal steps needed damping retries; one step used 1,153 iterations. This
explains a real cost increase, not a hung file writer or broken moisture solve.

## Atlas status

The published atlas uses the broad seasonal anchor, with strict temperature,
linear and moisture convergence and two full warm-up years. It is a fallback
to the verified starting fit, not a newly accepted parameter-sweep winner.

- Strict model-grid agreement: 48.87%.
- Mean fuzzy rule agreement: 0.4623 (a different measure).
- Dry Mediterranean land on its displayed surrounding world: 11.59%.
- Model grid setting: 8, with 25 seasonal steps/year.
- Exported map images: 3x source resolution. This is image rendering scale,
  not evidence of a verified finer simulation grid.

Verified the live atlas metadata, packed-array bounds and image files against
the selected parameters. Current climate animations and layers were regenerated.
The previous atlas data are preserved at
`output/overnight_mediterranean/atlas_previous_20261014_071517/`.
The published run metadata explicitly records that fresh-world validation is
incomplete. The <=5% Mediterranean target remains unmet.

## Next: finish the existing experiment

Repeat the unchanged command to resume:

```sh
caffeinate -i .venv/bin/python -u scripts/overnight_mediterranean.py --run --hours 8 --workers 3
```

The assistant verified exact cache matching for all 34 completed sweep settings.
Warm-up and development results also remain saved. The resume therefore spends
its search window on the 30 pending settings, rather than repeating completed
climate runs. Fresh/fine checks remain subject to the budget, and can still be
deferred if unusually stiff cases dominate. The runner reports actual coverage
and keeps the atlas backup when it builds a later accepted result.

Do not change model or runner sources before resuming: the experiment's source
fingerprint currently matches. No new parameter nudge, classifier change or
replacement calibration is introduced while this broad sweep is unfinished.

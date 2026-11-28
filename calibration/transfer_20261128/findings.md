# M1 transfer score, r58 -> r64b (28 Nov 2026)
World-legal (ROTCLIMATE_WORLD_LEGAL=1, world parameter sets r58w vs r64bw, 97 dev regions):
  S97 0.9869 [0.9748, 0.9982] (T -1.0 %, P -1.7 %)
Earth (observed fields on), chained dev6 r59..r64b: 0.884.
Transferable share ~ (1 - 0.9869) / (1 - 0.884) = 11 %: almost all of the gain since the last rebuild rests on the
Earth-only NCEP fields (r60/r61 omega cap, r63 wet PW nudge, r64/r64b 500 hPa RH gates). Caveat: the Earth number is a
chain of paired steps, the world number one direct comparison.
Priority before the r70 rebuild: model-diagnosed stand-ins for observed 500 hPa omega and RH (and PW), so the r60-r64b
mechanisms reach the world.

## Note: e49 monsoon descent on Earth grids comes from WorldClim OBSERVED rain (the rain target)
earth.monsoon_descent() builds the 1-deg descent field from WorldClim land rain; world grids compute theirs from their
own simulated rain (model._descent). The world-legal mode keeps the Earth field as the stand-in for the world's
globally computed one (a regional window would miss remote sources: Iran's descent comes from India), but it is a mild
target leak in the Earth harness (rain input -> rain score). Candidate fix for r65/r70: build the Earth descent field
from a global model rain climatology (e.g. the r70 world-style run on Earth) instead of WorldClim.

## What r64b rests on (single fields withheld, vs r64b; ROTCLIMATE_WITHHOLD)
obs_omega 1.0524 [1.017, 1.106] (P +10 %, arid 1.167) > obs_rh500 1.0360 (tropical_wet 1.078) > obs_slp_fall 1.0000 (unused).
obs_pw: crashed (r64b's edge_pw_source "observed" requires it; measure with the world parameter set instead).

## e154 WTG own-rain omega stand-in: REJECTED (obs_omega withheld; baseline without stand-in 1.0524)
w30 1.1305, w20p2 1.0599, w30k2 1.1596: a within-run feedback (no rain -> sinking -> no rain) dries the Congo
(s 3.0-3.7). Lesson: a stand-in must not read the same run's rain. Next design: two-pass - derive a FIXED omega
climatology from a completed global (world-style) run's rain, then rerun with it, as the Earth descent field is built
once. Needs a global Earth run (the regional harness has no global rain); natural on the world grid.

## T10 option A: two-pass omega from a global MODEL rain climatology - REJECTED
scripts/global_model_rain.py: 27 tiles (6,000 x 5,000 km, 112 km cells, rows 22 S / 0 / 22 N, every 40 deg) run
world-legal with r64bw -> data/cache/earth/model_rain_r64bw.npz (1 deg, 40 S - 40 N covered; ~8 min). Fixed WTG omega
from it (0.03 Pa/s x clip(1 - P_1000km / 3 mm/day)). Screen (obs_omega withheld, convective_omega_source "model") vs
r64b: S97 1.0811 [1.034, 1.138] - worse than no stand-in (1.0524). Sahel/northern boxes improve (0.85-0.92), but S Somalia
s 2.10 and Congo/Gabon 2.3-2.4: the model's own rain errors (Somalia 11 mm/day in July, Congo 1.8) are exactly what
the observed omega corrects, so any rain-derived field inherits them.
Conclusion: a world-legal omega must come from the model's circulation, not its rain (e.g. low-level divergence of the
model's winds, or the Hadley/monsoon pressure pattern), or the world accepts these terms do not transfer.
The global model-rain map is still useful: it can replace WorldClim in the Earth e49 descent field (the target leak).

## T10b: omega from the model's low-level divergence - not attempted as a screen (diagnostic says no)
3e4 Pa x 500 km-smoothed surface divergence vs NCEP 500 hPa omega, land means (months 1/4/7/10):
S Somalia -0.05..-0.08 (convergent) vs +0.02..+0.04 (sinking); Algeria +0.09 / -0.08 vs +0.04 / +0.01;
Sahel -0.12 in April vs +0.02; Gabon -0.08 vs -0.04. No sign agreement where it matters: the model's monsoon inflow
converges where the real 500 hPa air sinks. Option "div" kept in code (off).
OVERALL: no model-internal field (own rain, fixed two-pass rain, low-level divergence) reproduces the observed
descent that e141 relies on. Remaining world-legal route: Earth ANALOGS - give each world cell the NCEP omega / RH500
of Earth cells in the same climatic position (latitude, side of continent, distance from coast, elevation, season),
as rotclimate/analogs.py does for other fields; or accept that the r60-r64b Earth gains do not transfer.

# Mid-latitude maritime winter: diagnosis (22 Nov 2026, r50; no candidate scored)

r50's largest temperature error is the BC coast (monthly MAE 3.48 C, annual -3.2; Feb-Mar -7). Its cells 50-100 km
from the sea (median 227 m) model -6.8 C in February against +1.3 observed; July is right (+12.3 vs +12.6).

* Not the sea: against WOA18 (scripts/compare_sea_surface.py, now with SST_EXTRA_SPECS for retired regions) the open
  sea off BC is 1.2-2.4 C TOO WARM in winter (+5 to +6 in summer); only the fjord channels (enclosed) follow the cold land
  (-5 in Feb). British Isles' open sea is 3-4 C too cold Feb-Apr; Nova Scotia's and Hokkaido's open seas are ~1-2 C too warm in winter.
  (sst_coasts_r50.json)
* Not elevation (bias -3.0/-3.2/-3.4 by elevation tercile), not e98c sea damping (BC MAE unchanged).
* The winter air over BC is continental: desert/continental share chi 0.70-0.75 Jan-Mar (0.41 in summer), wind
  easterly (u -0.8 m/s) i.e. offshore. Probes (scripts/monsoon_trace.py bc_coast, in-map land mean):
  land_stable_rate 0 -> Jan +2.4, Feb +1.1, Mar 0 C; eddy_rate x2 -> Jan +0.5, Dec +0.1 C; a prototype oceanic subpolar
  low wind (e99, mirror of e3's subtropical highs, 3 m/s, centred 57 N) makes the flow more southerly but, friction-turned
  toward the low, also more offshore (u -1.8): T unchanged. e99 reverted, not kept.
* Conclusion: the coast's winter warmth in reality comes from the Coast Mountains blocking interior Arctic air and from
  storm-borne Pacific air, neither of which the zonal land column + mean-wind advection represents; the land equilibrium
  at 56 N in February (the latitude's mean land, ~-15 C) dominates. A fix needs a barrier-aware cold-air term (the
  interior's cold pool should not reach a coast behind a high crest) — not attempted yet.

## e100 terrain-weighted eddy heat (plan_e100.json): STOP at stage A
E1 (H 1.0 km) S49 1.078 (T +15.8 %, P -0.2 %); E2 (0.4 km) 1.193 (T +38.7 %). Both over the 1.03 stop.
Helps Bengal, North India (bias -2.55 -> -1.32), BC coast (-3.21 -> -2.49), Mexico, Victoria; but East Asia warms
1.3-1.8 C on biases already +1 to +1.6 (Korea +3.4, East China +3.1, North China Plain +2.9, Tibet +2.8, Manchuria
+2.8, Japan +2.0): taking high ground out of the eddy mean removes the Tibetan / Mongolian cold that the eddies
carry east. A weight on the SOURCE's elevation is not a barrier; a barrier needs the crest BETWEEN the cells
(directional, as e75 does for eddy water). Code kept, default off; not adopted.

## e101 directional cold-air damming (probe only, not scored; code reverted)
Eddy heat cut where the eddy mean is colder and a crest stands up to 300 km toward the colder side (full at +1 km):
BC coast in-map land Jan +0.5, Feb +0.2 C; North India +0.2-0.4 C. Too small to matter. So e100's gains in BC and
North India came from weighting the warm SEA more in the eddy mean, not from blocking a cold source; the eddy mixing
is not what holds those coasts cold (eddy_rate x2 on BC: +0.5 C). Their cold is the latitude-mean land equilibrium
itself. Candidate next: a land equilibrium that knows its own setting (coastal/maritime cloud and longwave for
BC; the dry clear subtropical plains for North India) rather than the latitude's mean land.

## What explains r50's annual temperature bias (all dev49 cells, 15,232)
OLS on standardised cell features, R2 0.58: Tann_obs -3.56, |lat| -2.75, elevation -1.50, log coast distance -0.33,
log P_obs -0.29, T range -0.13 (C per s.d.). By observed annual mean: < -5 C +2.0; -5..18 C ~0; 18..24 -0.4; > 24 -2.2.
Read: at a given latitude and height, cells warmer than their latitude are modelled too cold and colder ones too warm;
the model compresses each place's departure from the latitude-mean land column. Every campaign today nudged one
cause of that departure (sea, dry ground, eddies) and none moves it enough. The next design should give the land
equilibrium its own local departure (cloud / humidity longwave, surface dryness, continentality) fitted as one
term against this residual, rather than one more gated switch.

## A fitted local-departure term is not recoverable from model fields (checked, not built)
OLS of the annual bias on model-internal predictors only (|lat|, elevation, log coast distance, the model's own annual
rain, annual mean and range), fitted on dev31 cells: dev31 MAE 1.18 -> 1.02 (R2 0.23) but retired a/b/c 1.48 -> 1.72
(R2 -0.39). The departure that matters is carried by the observed climate itself (cloud regimes, local circulation),
not by anything the model already knows; a statistical term would overfit. Dropped.

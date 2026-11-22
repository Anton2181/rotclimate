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

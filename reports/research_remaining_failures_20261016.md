# Literature review: fixes for the remaining Earth failures

16 October 2026. A research pass (code reading plus literature) on the five
failures left after the Earth fit r4 (`reports/earth_mode.md`). Numbers about
the model below were derived by reading the code and the r4 parameters, not
by running it; they are hypotheses to test.

## Four code facts behind most of the failures

1. **Land air is held to a latitude mean all year.** Air over land relaxes
   to Tl(lat) with `land_tau_days` ≈ 1.4 d in every season: at 5 m/s that is
   a memory of only ~600 km. Cold surges cannot travel (East China), and
   warm-water peninsulas stay continental.
2. **Rain is spread too evenly.** rain = A_dyn · gate · instab · W / τ with
   A_dyn = 1 + storm + conv + oro: the "1 +" is ascent everywhere and the gate
   is gentle, so every column above r ≈ 0.33 drizzles (deserts too wet). Wet
   convective columns rain only ~12× faster than r = 0.4 columns; observed
   ~30× (Bretherton et al. 2004).
3. **Land evaporation recycles too efficiently** (0.77 of recent rain,
   re-entering the same column), stretching the inland decay of ocean moisture
   ~4×; with wet cooling (wet → cooler → higher RH → more rain) it is a
   positive loop that can keep an interior humid with little ocean supply.
   Observed regional recycling: ~9 % at 500 km, < 20 % at 1,000 km
   (Trenberth 1999; van der Ent & Savenije 2011).
4. **Converging winds cannot concentrate moisture**: the transport is u·∇W
   with no W∇·u term, so monsoon convergence cannot pile water up.

## Mechanisms and simple parameterizations

**East China winter (Oct–Apr 3–6 °C too warm).** East/west coast winter
contrasts come from advection by the stationary-wave flow (Seager et al.
2002; Kaspi & Schneider 2011); cold-outbreak air keeps much of its cold for
days (Hartig et al. 2023). *Fix A:* make land coupling seasonal,
λ_land = 1/τ_rad + (1/τ_s)(S/S_ref)^n with S the daily insolation
(τ_rad ~30 d, S_ref ~480 W m⁻², n ~1.5): ~1.2 d in summer, 3–6 d in winter
(as in Held & Suarez 1994, whose relaxation lengthens poleward). Expected
winter cold-advection offsets grow from ~−3.5 K to ~−10 K.

**Meiyu too weak.** The rain band sits on the poleward-flow west flank of the
North Pacific high under the jet off Tibet (Sampe & Xie 2010; Rodwell &
Hoskins 2001); monsoon reach is limited by ventilation (Chou & Neelin 2003).
*Fix B:* let the Sverdrup factor carry summer subsidence instead of a zonal
band; a bounded, water-conserving convergence source c·W·max(0, −∇·u_thermal)
(Lindzen & Nigam 1987; Kuo 1974); do not let wet cooling weaken the thermal
low (latent heating deepens it; Gill 1980).

**Chile's coast (summer ~8 °C too warm).** A 0.5–1 km marine boundary layer
under the subsidence inversion with stratocumulus and upwelling (Lilly 1968;
Garreaud 2009; Rutllant et al. 2013); low cloud rises ~6 % per K of
lower-tropospheric stability (Klein & Hartmann 1993; Wood & Bretherton 2006).
*Fix C:* a trapped marine layer: land cells below an inversion height
(~800 m) connected to the sea, weighted by distance from the coast (~30 km)
and gated by stability, relax toward the nearby SST; no eddy/diffusive heat
exchange across the inversion.

**Dry continental interiors turning humid.** Mountains are the first
control: without them the mid-latitude deserts and steppes of Central Asia
and western North America largely vanish (Manabe & Broccoli 1990; Broccoli &
Manabe 1992). Column water barely falls inland; interiors are dry from low
relative humidity, absent ascent and low rain efficiency (Byrne & O'Gorman
2013). Strong soil-moisture–rain coupling only in transition hotspots
(Koster et al. 2004); afternoon storms favour drier soils (Taylor et al.
2012). *Fix D:* squeeze moisture at the crest (dividing streamline, h_eff =
min(h, U/N), thinning the saturation with height) so rain shadows persist
downwind (Galewsky et al. 2005; Smith & Barstad 2004); land evaporation from a
Budyko curve (Fu; Zhang et al. 2004); storms decaying over land (Hoskins &
Valdes 1990). **A dry interior at 40–45° with no upwind range of 1.5–2 km
within ~2,000–3,000 km of a windward coast is not what Earth physics makes:
do not tune the physics to force it dry.**

**Swamps and Florida's summer rain (−50 %); deserts too wet.** Monthly rain
rises exponentially with column relative humidity, P ≈ exp[11.4 (r − 0.522)]
mm/day (Bretherton et al. 2004; Peters & Neelin 2006); sea breezes from both
coasts converge over peninsulas (Byers & Rodebush 1948; Pielke 1974);
desert rain partly evaporates below high cloud bases (z_LCL ≈ (20 + T/5)
(100 − RH) m; Lawrence 2005). *Fix E (rain closure):* exponential convective
rain (gated by temperature), large-scale rain without the background "1 +",
and sub-cloud evaporation exp(−z_LCL/3 km) with the evaporated water left in
the column. *Fix F:* sea-breeze convergence from the curvature of the
smoothed land fraction. *Fix G:* moist static energy matching of wet land to
the upwind sea instead of wet cooling (Byrne & O'Gorman 2018).

## Priorities

1. **E, rain closure** (~10 lines): deserts, Florida/swamps, part of the
   humid interiors and the Meiyu.
2. **A, seasonal land coupling** (3–5 lines): East China's winter, the
   Florida/swamp annual mean, maritime vs continental contrast.
3. **C, trapped marine layer** (~20 lines): Chile, probably the Cape, SW
   Australia and California.

Avoid: anything tied to place (fixed Siberian High, Tibet heating,
longitude tests), raising already-large multipliers (signs of compensating
errors), more wet cooling, calibrating physics against the painted classes
(circular), more than 1–2 new parameters per mechanism, each with a
literature prior.

## References

Bretherton, Peters & Back 2004, J. Climate 17:1517 · Peters & Neelin 2006,
Nature Physics 2:393 · Frierson 2007, JAS 64:1959 · Kuo 1974, JAS 31:1232 ·
Lawrence 2005, BAMS 86:225 · Seager et al. 2002, QJRMS 128:2563 · Kaspi &
Schneider 2011, Nature 471:621 · Ding & Krishnamurti 1987, MWR 115:2428 ·
Hartig, Tziperman & Loughner 2023, J. Climate · Held & Suarez 1994, BAMS
75:1825 · Sampe & Xie 2010, J. Climate 23:113 · Chou & Neelin 2003,
J. Climate 16:406 · Rodwell & Hoskins 1996, QJRMS 122:1385; 2001, J. Climate
14:3192 · Lindzen & Nigam 1987, JAS 44:2418 · Gill 1980, QJRMS 106:447 ·
Lilly 1968, QJRMS 94:292 · Klein & Hartmann 1993, J. Climate 6:1587 · Wood &
Bretherton 2006, J. Climate 19:6425 · Garreaud 2009, Adv. Geosci. 22:3 ·
Rutllant, Muñoz & Garreaud 2013, ACP 13:3409 · Manabe & Broccoli 1990,
Science 247:192 · Broccoli & Manabe 1992, J. Climate 5:1181 · Smith &
Barstad 2004, JAS 61:1377 · Galewsky, Sobel & Held 2005, JAS 62:3353 ·
Trenberth 1999, J. Climate 12:1368 · van der Ent & Savenije 2011, ACP
11:1853 · Savenije 1995, J. Hydrol. 167:57 · Zhang et al. 2004, WRR 40 ·
Koster et al. 2004, Science 305:1138 · Taylor et al. 2012, Nature 489:423 ·
Hoskins & Valdes 1990, JAS 47:1854 · Byers & Rodebush 1948, J. Meteor. 5:275 ·
Pielke 1974, MWR 102:115 · Emanuel 1995, JAS 52:1529 · Privé & Plumb 2007,
JAS 64:1417 · Byrne & O'Gorman 2013, J. Climate 26:4000; 2018, PNAS 115:4863

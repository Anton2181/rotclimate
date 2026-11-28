# Spring timing (G3) under r63 — 28 Nov 2026

Spring-minus-autumn monthly bias (MAM - SON) over all 107 r63 reference cases: rms 2.0 C.
- Interiors cold in Apr-May (Volga -5.2/-5.5, Kazakh -4.8, E Europe -2.8, prairies, 56-58 N Siberia, BC).
- East-Asian coasts warm Mar-May (Japan +3, Hokkaido +4, E China +4).

Volga land budget (r63, lb.py): zonal column Apr 3.5 ~ Oct 4.3 (observed Apr 7.2 > Oct 5.4);
continental centre/amplification -3.5 in Apr; snow albedo -1.4; sea-air mixing ~-1.3.
Snow is gone by May, yet May-Jun stay 4-5 C cold: wet_cooling (-2..-6 C) under a spring rain
excess (May 61 vs 34 mm). Toggles on Volga: snow_albedo 0 +1.1 C Apr; wet_sun 0 +0.7; dry_coupling 0 nil.

Japan: land equilibrium Mar 9.8 vs observed 6.2 (sea-level) with the sea warmer still (13.7):
only continental cold-air advection can hold it; not a local land term.

e151 land_phase_cont_days (one-sided e121: deep-continental land cycle earlier; default off):
  ph10        S97 1.0422   ph10 + continental_mean 5.0  1.0458   ph18 + cm 4.5  1.1295
  Helps Volga/BC/E Europe/prairies, hurts Mongolia, Tibet, 40N94E, Hokkaido, Canadian Shield
  (already on time). REJECTED: same east-west trade as e121/e130/e138.
Conclusion: the spring error is not a phase or snow-albedo term. Leads: the spring rain excess
over western Eurasia (storm band too far north in May) and lacking cold advection to east coasts;
both need transport-level changes, deferred to the r65 recalibration.

## Tropical transition seasons (same session)
Across r63 references the land rain belt sits too far NORTH in both transition seasons:
- northern dry tropics (r_11n_2w, Sahel) start early in April and run too wet to October
  (r_11n_2w Oct 162 vs 47 mm) -> too cold (C1 cold side);
- southern Amazon/cerrado (s3_15s_65w, gg2_14s_56w, u3_11s_55w, t_10s_66w) start 1-2 months late
  (Sep-Nov 0/0/18 vs 108/163/237 mm) and end early (May-Jun) -> +3..+8 C pre-onset (C1 hot side).
Southern pre-onset column water 12-16 vs NCEP 27-35 mm; land evaporation 0 Jul-Oct (bucket empty).
Probes: obs_pw_nudge_wet lat 10-25 adds wet-season rain only (onset still dry; north floods further).
Snow-free NCEP albedo does NOT separate the warm-south / cold-north boxes (0.17-0.22 both): no
vegetation-gated root store. Perihelion is correctly shifted for mirrored regions.
Diagnosis: a hot-dry-land feedback (no rain -> Ws rises -> rh falls -> no rain) that the model's
moisture/convection scheme cannot break before the belt arrives; one land ITCZ (W5) cannot be both
early-north and early-south. Needs a forest-initiated onset term (shallow convection moistening, Wright
et al. 2017) or hemispheric land belt asymmetry, fitted in r65.

## Sahel May cold under r64b (same session)
sahel_niger May T 28.3 vs 32.3 C. Budget (lb.py, sea-level): land_eq 32.6 vs observed 33.9 (dry heating falls
2.3 -> 0.8 C Apr -> May as early rain wets the soil; wet cooling/wet_sun -0.5..-1); air 30.5 = ~half-way from
land_eq toward the Gulf of Guinea sea air (28.1) 1,000 km inland: the monsoon inflow's sea-air share is the larger
term. Column water May 39 vs NCEP 29 (early), Jul-Aug 31 vs 38-42 (late).
Probes with no useful effect: obs_pw_nudge_excess 0.2/0.05 (nudge gated by rh0), e136 itcz_land_sharp alone
(needs e134), e134 lag 30/43 + sharp 2 (Sahel May-Jun rain -0..-14 mm, T +0.2; southern Amazon onset later).
Lead: inland heating of monsoon sea air (air-mass modification over hot land), not the rain belt.

## Kalahari / inland Australia after r64b (same session)
With the wet nudge reaching the plateau (lat 25-30, h fade 2-3 km) the Kalahari column holds NCEP's water (24 mm)
and still rains ~5 mm/month: the convection caps (e93 gate, chi0 cut, e94 descent, e141 omega) are redundant; only all
off gives 154 vs 237 mm. e152d (rh500 release of chi0/descent/omega caps on heat and rate, off) screen vs r64b:
d1 S97 1.0139 [1.0005, 1.0295] FAIL: Kalahari 0.863, inland Australia 0.954, but Algeria 1.963, Libyan desert 1.738,
Sudan 1.266, Tripolitania 1.258 (arid 1.059). NCEP 500 hPa RH cannot separate them: Kalahari summer 30-35 %, inland
Australia 34 %, Libya/Tripolitania spring 33-36 %, Algeria summer 24-26 %. A stricter own ramp (27-33 %) loses the
Kalahari gain and keeps Sudan/Algeria wet. LINE CLOSED for rh500: needs a discriminator for the Sahara's deep dry
boundary layer / heat-low capping inversion (e.g. NCEP 700 hPa temperature or omega profile), deferred to r65.
e152f (off): gate the e152d release by NCEP 700 hPa omega (rising) and 500 hPa omega (not sinking); caches
ncep_omega700.npz (scripts/build_ncep_omega700.py) + existing omega500. 700 hPa separates the Sahara core (+0.04..+0.08
Pa/s) from Kalahari/inland Australia summers (-0.02..-0.04), but the southern Sahara heat low also rises at 700 hPa;
with both gates (700 lo -0.02 hi 0; 500 lo -0.005 hi 0.01) the Kalahari gain vanishes (Dec-Mar 11-9 vs 6-8 mm) while
Algeria May-Jun stays +4-5 mm. Not screened. Kalahari rain needs a structural heat-low convection term (r65).

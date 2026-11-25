# e128 snow surface inversion (25 Nov 2026, vs r55)

Largest remaining r55 temperature errors (97 dev regions): subarctic NE Asia / Canadian interiors too warm
Oct-Jan by 4-7 C (u2_56n_135e, u_53n_92w, u2_49n_93w, s3_56n_124e, Manchuria); western Eurasia too cold, mostly
in SPRING (Mar-May -4 to -6 C: Middle Volga, Kazakh steppe, Krasnoyarsk, E Europe, British Isles).
Okhotsk (u2_56n_135e) diagnosis with WOA: model sea is colder than WOA in autumn, so the sea is not the cause;
land_eq is 3-6 C too warm Nov-Jan and the air another ~3.5 C warmer than land_eq.

e128: 2 m air under full snow cover in darkness is cooled by snow_inversion K x cover x clip(1 - S/snow_inversion_s).
v1 (inversion also seen by the snowpack), screen_inv.log:
  inv3 S97 0.9991 [0.9943, 1.0038]; inv6 1.0032 [0.9938, 1.0129]; inv5s100 0.9997.
  inv6 helps u2_56n_135e 0.844, s3_56n_124e 0.880, u_53n_92w 0.901, Manchuria 0.932; hurts BC coast 1.148,
  Kazakh steppe 1.158, Middle Volga 1.142, Krasnoyarsk 1.141 (already cold-biased; colder air also delays the melt).
  Neither model nor observed winter precipitation separates helped from hurt regions (no clean clear-sky gate).
v2: the offset is diagnostic (snowmelt sees the mixed air): see screen_inv2.log.
  v2 result (screen_inv2.log): identical to v1 (dinv3 0.9991, dinv6 1.0032): the melt path was not the cause.
  The hurt regions are too cold in midwinter too (Middle Volga Jan -1.6), so one inversion strength cannot serve
  both: e128 alone is not adoptable.

## Canada east-west dipole (r55 annual bias)
Eastern interior too warm: w1_48n_79w +3.0, u2_49n_93w +2.4, u_53n_92w +3.2, w2_54n_85w +4.7, u2_59n_76w +3.3.
Western interior too cold: w1_54n_116w -4.3, w2_57n_116w -3.1, canadian_prairies -1.8, bc_coast -3.0.
Ungava stage breakdown (land_budget, r55): the ZONAL land column is already 22.0 C in July (obs 11.5); the air
follows land, not the 5 C sea; the summer excess is set before any regional stage. Hudson Bay lowlands: land_eq
3-4 C too warm in summer and 4-7 C in winter. Candidate structural causes (not yet tested): the zonal land column
is a Eurasia-dominated mean; the Shield's lakes and wetlands are counted as land.

## W12 (plan_W12.json) declared: e128 jointly with continental-season knobs on r55; gates vs r55, sealed X.
W12 CLOSED after wave 1 (49 points): no point beat the r55 base (best w1_001 1.0014); wave-2 proposals predicted
0.9959 (gain 0.004 < 0.005) with snow_inversion -> 0.2-1.3 and land_coupling_insolation / snow_albedo at the lower
range edges. e128 is not the binding error; no candidate, sealed X stays UNOPENED. r55 remains adopted.

## Global levers on the dipole (all vs r55, 97 dev regions) — none adoptable
- land_coupling_insolation 1.2 / 0.9 / 0.6: S97 0.9982 / 0.9994 / 1.0042 (0.6: Hudson/Ontario 0.89-0.90, E Europe
  1.21, Kazakh 1.19, mediterranean 1.042). screen_lci.log.
- e129 pole_frozen_sea (WOA-derived winter-frozen sea counts in the poleward cold-air source; Hudson Bay, Foxe,
  Kara, Okhotsk frozen; Barents SW, Baltic, Labrador, Bering open at the -1.0 C criterion): 0.5 -> 0.9996, 1.0 ->
  1.0027; Hudson lowlands 0.82, Ontario 0.85, Ungava 0.91; Krasnoyarsk 1.27, Kazakh 1.23, BC coast 1.18. screen_pfs.log.
- e130 continental_mean_season (cold-pool shift weighted to the dark months, same annual mean): 0.5 -> 1.0073,
  1.0 -> 1.0320, 1.0 + e129 1.0 -> 1.0575 (Kazakh 1.75, Krasnoyarsk 1.64: winters too cold). REJECTED.
Middle Volga stage breakdown (r55): April air 0.9 C vs obs 6.7: the continental stage drops April 3.5 -> -0.1;
wet_cooling takes 5.7-6.7 C off June-July (0.43 x soil wetness x (Tl - annual mean), largest where the swing is
largest). Every global lever trades the warm east (E Canada, Okhotsk) against the cold west (Volga, Kazakh,
Krasnoyarsk, BC/Alberta). The dipole needs a regional discriminator that none of chi, pole_land, frozen sea,
elevation or winter precipitation supplies. Leads not tried: spring snowmelt timing vs observed snow cover;
wet_cooling energy-limited (sunshine) instead of anomaly-scaled.
- Seasonal phase (phase_lag.py, r55): the cold west runs LATE (British Isles +19.8 d, BC coast +11.6, E Europe +7.7,
  Middle Volga +5.4, Krasnoyarsk +4.7, Kazakh +3.5); the warm east is on time (u_53n_92w -1.1, u2_49n_93w -2.1).
- land_radiative_days 4: S97 0.9982 [0.9931, 1.0036]: same trade (east 0.93-0.96, Volga 1.05, Kazakh 1.08, BC 1.08).
  land_radiative_days 0 crashed in dev31 (benchmark error; not pursued).
CONCLUSION (25 Nov): six levers (e128, W12, coupling, e129, e130, radiative days) all move the continental interiors
together. Parked: the dipole needs a regional discriminator. The most specific remaining lead is the west's late
phase (maritime lag, task C4: British Isles +20 d), i.e. the sea-air share of western coasts/interiors.

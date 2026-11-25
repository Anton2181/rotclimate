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

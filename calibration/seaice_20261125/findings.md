# Sea ice (e127) — 25 Nov 2026, reference r54

r54's worst continental regions sit by freezing seas: u2_59n_76w (Ungava) T 5.2 C, bias +4.9; u_53n_92w +2.8;
u2_56n_135e (Okhotsk) +2.0. Ungava stage check: model sea -1.9 C Nov-May; air January -14.3 against -24.2,
land equilibrium -21: the air relaxes to -1.8 C water all winter. The model had no ice surface (only the
freezing clamp).

e127 (sea_ice, sea_ice_melt_days): where the sea is at freezing (cover 0 at -1.0 C, full at -1.8 C) the air
relaxes to the ice surface = min(land equilibrium, 0 C); moisture keeps the water. Ungava January -14.3 -> -21.7.

| run | S97 | temperate | continental | notes |
|---|---|---|---|---|
| ice100 | 1.0045 | 1.044 | 0.986 | Ungava 5.20 -> 3.73; British Isles 1.91 -> 2.62, S Chile 2.91 -> 4.55, BC coast, Patagonia worse |
| ice60 | 1.0009 | 1.022 | 0.987 | |
| ice100m30 | 1.0045 | 1.045 | 0.985 | melt memory changes nothing |
Diagnosis: the model's zonal sea freezes the open subpolar ocean (Norwegian Sea, Southern Ocean), which in
reality overturns and stays ice-free. e127b gates the cover on the air over the sea (sea_ice_air_c: none above,
all 10 K below): ice where land-chilled air keeps drawing heat out. Ungava with gate -5: January -21.1,
November -9.5 (ungated -12.7, obs -7.5). Screen: screen_iceg.log.

## Gated ice (e127b), reference r54
| run | S97 [90 %] | continental | others |
|---|---|---|---|
| ig5 (air gate -5 C, melt 30 d) | 0.9940 [0.9836, 1.0000] | 0.973 | all other regimes 1.000 |
| ig10 (-10 C) | 0.9945 [0.9849, 1.0000] | 0.976 | 1.000 |
| ig3 (-3 C) | 0.9943 [0.9843, 1.0001] | 0.974 | 1.000 |
A clean, local gain (Ungava 5.20 -> 3.53 C, Okhotsk, Hudson Bay lowlands); too concentrated to clear the
90 % upper bound alone. Carry ig5 into the next candidate. Container restart interrupted ig5m60 (rerun).

## Next lead: band snow albedo in spring (r54)
British Isles r54: land equilibrium April 3.8 C (obs air 7.4), air Mar-May 2-3.5 C cold, Oct-Nov +1 warm.
BC coast: land equilibrium March -12 C, air Feb-Mar 3-4 C cold, Oct-Nov +3-4 warm; its sea is now 1.5-4 C warm
in summer (NE Pacific, r54 damping + currents). ebm_land_ice (e65, 0.47) leaves half the latitude band's
continental snow albedo on every land cell. Screen: screen_eli.log (0, 0.2, 0 + ig5).

## Band snow albedo (ebm_land_ice), reference r54
| run | S97 [90 %] | continental | temperate | mediterranean | tropical_wet |
|---|---|---|---|---|---|
| ig5m60 | 0.9941 [0.9836, 1.0002] | 0.973 | 1.001 | 1.000 | 1.000 |
| eli0 | 0.9997 [0.9899, 1.0095] | 1.017 | 0.986 | 0.975 | 1.024 |
| eli20 | 0.9979 [0.9919, 1.0038] | 1.005 | 0.990 | 0.983 | 1.014 |
| eli0 + ig5 | 0.9936 [0.9832, 1.0040] | 0.990 | 0.986 | 0.975 | 1.024 |
eli0 helps the cold-biased (Kazakh steppe 1.51 -> 1.08, Middle Volga 2.26 -> 1.80, W Siberia, Alps, BC coast,
Pacific NW) and hurts the warm-biased snowy lands (US Midwest, Korea, Nova Scotia, N China, Hudson Bay lowlands
+0.5-0.7 C). The cells' own snowpack (e16 snow_albedo 0.21 K per 480 W m-2) is too weak to carry the snow the
band no longer imposes. Screen eli0 + ig5 + snow_albedo 3 / 6: screen_snow.log.

## Cell snowpack (e16 snow_albedo) with eli0 + ig5, reference r54
| run | S97 [90 %] | regimes |
|---|---|---|
| es3 (snow_albedo 3) | 0.9926 [0.9834, 1.0011] | arid 0.994, continental 0.980, highland 0.995, med 0.988, temperate 0.988, tropical_dry 1.001, tropical_wet 1.024 |
| es6 | 0.9996 [0.9885, 1.0087] | highland 1.022, med 1.012 |
es3 = best combination; tropical_wet 1.024 breaks the regime gate (the band column change warms Amazon land
~0.1 C). plan_W11 declared on es3 (calibration/ppe_20261123/plan_W11.json), gates vs r54, sealed W13.

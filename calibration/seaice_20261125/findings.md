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

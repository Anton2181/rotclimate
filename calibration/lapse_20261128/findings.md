# Tropical lapse (e146) and relief lapse (e147), 28 Nov 2026, vs r63

r63 bias vs elevation, within-region (region mean removed), all r63 reference parts:
| 0-12 deg | +1.44 K/km | 12-24 | +0.57 | 24-36 | +0.53 | 36-48 | +0.33 | 48-70 | +0.07 |
Pooled tropical (12-24) bias at sea level -1.46 C: tropical highs too warm vs their own lowlands.
Fitted lapse_rate is 4.35 K/km (plus lapse_seasonal 0.15).

e146 lapse_tropical (uniform extra K/km, latitude fade), screen_e146.log, all FAIL:
| lt1 1.0 K/km, 12-30 deg | S97 1.0100 [1.0013, 1.0189] | highland 1.033 |
| lt2 1.5 K/km, 12-30 deg | S97 1.0252 | |
| lt3 1.0 K/km, 20-40 deg | S97 1.0191 | highland 1.154 |
Zambia/Tanzania/Congo rim improve (r_14s_32e +1.09 -> +0.37 C), but whole basins and the Andes cool
(s2_23s_67w +0.20 -> -1.22/-3.10, r_4s_79w -1.12): the error is relative relief, not absolute height.
-> e147 relief_lapse: extra K/km on height above the 150 km-smoothed surrounding land.

# e138 radiation snowmelt under r57 (26 Nov 2026) - NEUTRAL, parked

Symptom (r57, April): Volga -4.6, Kazakh steppe -4.0, Canadian prairies -3.5, BC -3.7 C. Snowmelt was degree-day only
(3.5 mm/C/day). e138 snow_melt_sun adds radiation melt (mm/day per 480 W m-2 of sunshine) from snow_melt_sun_c.
| set | S97 [90 %] | notes |
| 3, from -6 C | 1.0000 [0.9989, 1.0010] | Kazakh 0.977, Volga 0.985; Korea / Midwest / Tibet 1.01-1.02 |
| 6, from -6 C | 0.9999 [0.9987, 1.0012] | |
| 10, from -6 C | 1.0000 | saturates: bias moves ~0.1 C |
| 6, from -3 C | 0.9999 [0.9992, 1.0005] | |
Reading: snow persistence is not what holds the interiors' spring cold (the snow is already gone or the land column
is cold without it). Next suspects: the zonal land column's spring phase over large continents and cold-air drainage
(e31 continental_mean's season shape, e130 rejected at r55). Code default off.

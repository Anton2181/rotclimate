# South Asia cold bias (r52), 23-24 Nov 2026

Diagnosis (land_budget taps, plains cells < 300 m): the Ganges plain is 3.4-3.6 C too cold in every month (north_india
cells: bias -3.6 at sea level, shrinking with height, so not a lapse-rate problem). Same latitude, same observed January
(15 C) as the Sahara plains, which the model gets right. Two parts:
1. local land column too cold: Jan -1.3, Apr -2.7 (observed pre-monsoon April is hotter than the Sahara's), Oct -1.4;
2. the air step (transport) cools a further 1-2 C every month (Sahara: -1 to +1).
Deccan: -3 C through the dry season (Jan-May), fine in the monsoon. Bengal: no pre-monsoon rain (Apr 0.3 mm vs 96),
monsoon ~60 % of observed, winter -2.5 C, May +3.5 C.

Tried (all default off in code):
- e108 heat_barrier_km (face exchange x exp(-|dh|/scale)): north India +0.2 C only -> transport is not via neighbours.
- e100 eddy_heat_terrain_km (absolute, existing): plain fixed but Tibet +2-4 C.
- e100b eddy_heat_terrain_relative (only ground above the receiver blocks): 61-region S 1.033 / 1.066 / 1.109 at
  1.0 / 0.5 / 0.25 km - FAILS: Korea, Japan, north China +1.5-3 C (the Mongolian ramp's winter cold air is real).
- e100c eddy_heat_terrain_offset_km (block only ground > offset above): offset 2 km S61 0.9994 [0.992, 1.008],
  1.5 km 1.0010. Neutral: Bengal -13 %, north India -6 %, Deccan -3 % against Tarim side (r_40n_94e) +27 %,
  Kazakh steppe / central Asia / Mongolia +1-5 % (they were kept warm by the plateau's sea-level-equivalent air).
PARKED. The transport fix fights the sea-level-reduction framing; the larger, cleaner target is the local column
(part 1: pre-monsoon heat over dry South Asian soil).

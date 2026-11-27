# Hot dry land cold bias under r58 (27 Nov 2026): dry_heating re-screen REJECTED
r58 bias: north India -2.7, Najd -2.8 (Aug -5.9), Iran -2.3, Deccan -2.2, Sahel -2.1, Nigeria coast -3.0 C.
dry_heating (r58 1.50) vs r58: 2.5 -> S97 1.0071; 3.5 -> 1.0285; 3.5 + mean_c 15 -> 1.0262; 5 + mean_c 15 -> 1.0656.
Targets improve (Najd 0.88-0.92, Iran 0.89-0.94, Deccan 0.89-0.94, north India 0.89) but the Altiplano, NW Australia,
Zambia overheat (highland 1.04-1.13, tropical_dry 1.02-1.11). The r58 interior-rain fix moved the trade-off from the
wet tropics to dry highlands / plateaus; it did not remove it. Still needs a discriminator between hot lowland deserts
and dry high / southern plateaus.

## Continental-air gate (e54b dry_heating_chi0) vs a LOCAL r58 reference (27 Nov 2026) - REJECTED
| set | S97 [90 %] | highland | targets / costs |
| dry_heating 3.5, chi0 0.6 | 1.0016 [0.992, 1.012] | 1.077 | Iran 0.92; NW Australia (u_24s_124e) 1.39 |
| dry_heating 3.5, chi0 0.75 | 1.0004 [0.991, 1.011] | 1.069 | Iran 0.93; NW Australia 1.36 |
| dry_heating 5, chi0 0.75 | 1.0091 | 1.167 | north India 0.89, Iran 0.89; NW Australia 1.43, Sahara 1.44, Tarim side 1.64 (+1.9 C) |
The continental share of the air does not separate the cold lowland deserts (Najd, Iran, north India) from dry high
basins and NW Australia. Still needs a different discriminator (e.g. column water / cloud state, or the season).

Reference note: screens must pair with reference runs made in the SAME container caches. The stored current-source
reference (output/climate_reference_20261127/ref58) was made with WOA in data/cache/earth (sea_depth) and without the
e129 frozen_sea_1deg.npz; a remaining case-hash difference could not be traced. scripts/make_local_reference.py builds a
local reference (output/ppe_20261127/ref58local). WOA now stays in the cache (sea_depth is an r58 input).

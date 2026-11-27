# World-legal edge forcing for r58 (e116z)

r58's e116 blends each land-edge column toward the observed NCEP precipitable water at that point: Earth-only.
e116z (`edge_pw_source: "zonal"`) uses the globe's land-mean NCEP column water at the cell's latitude and month
(rotclimate/earth.py `zonal_land_pw`), which needs only latitude and season.

Earth dev pool (scripts/screen_v6.py vs ref58local, 97 regions; >1 is worse):

| variant | S97 | 90 % interval | S49 |
|---|---|---|---|
| zonal (r58w) | 1.0098 | 1.0012–1.0187 | 1.0063 |
| edge off | 1.0265 | 1.0106–1.0449 | 1.0228 |

Zonal costs 1 % of r58's Earth skill against 2.7 % for no edge forcing, so the world uses r58w. Earth keeps r58.

## World zone agreement by physics release (r58 world geometry = r51 world, ds16, layout 1, one run each)

| physics | strict | Med recall | Med dry share | Med Cs share | hot-dry recall | warm-wet recall |
|---|---|---|---|---|---|---|
| r51 | 0.244 | 0.346 | 0.073 | 0.371 | 0.588 | 0.146 |
| r57 | 0.160 | 0.077 | 0.047 | 0.086 | 0.256 | 0.156 |
| r58 edge off | 0.180 | 0.117 | 0.211 | 0.126 | 0.784 | 0.021 |
| r58w (atlas) | 0.181 | 0.145 | 0.214 | 0.157 | 0.804 | 0.001 |

The painted Mediterranean was lost between r51 and r57 (Earth-adopted physics), not by the world edge forcing:
e116z is the best of the r58 options on the world too. At ds8 layouts 1-3 (selection.json) r58w gives strict 0.219,
Med recall 0.191 against r51's 0.350 / 0.645. Owner rule: the atlas uses the latest Earth physics regardless.

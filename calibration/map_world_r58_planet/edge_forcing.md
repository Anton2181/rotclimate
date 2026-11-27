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

# River cap (owner 26 Nov 2026): drawn rivers in full; undrawn catchments < smallest drawn river (403 km2)

Atlas display: rotclimate/routing.segments now always includes drawn-river pixels (27 % -> 99.6 % shown on r51).
Height map v2.2 retrofits (capped tree imposed on the eroded surface) need 2.3 km gorges and break the tier-3 gate,
so the erosion is regenerated on a capped tree (scripts/terrain_capped.py).

Attempt 1 (tree on the tier ramps, uphill weight 0.2/m): tree over-cap 1,713 cells (0.18 % of land, max 1,377 km2).
Build gates: drawn rivers PASS, lowland slope PASS (0.175), tier bands 2/3/4 0.941/0.547/0.866 vs v2.2 0.984/0.516/0.862
(tier 2 FAIL), climate scale 68 m vs 45 m (FAIL). The final fall-along-tree fill raised cells p99 585 m (28 % of tree
links climb the ramps). Attempt 2: uphill weight 5.

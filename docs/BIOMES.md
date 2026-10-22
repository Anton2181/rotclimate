# Whittaker biome maps

The active climate atlases now include a **Whittaker biomes** layer, a legend with land-pixel shares, a temperature–precipitation diagram, and biome names in station cards and the downloadable places CSV.

The classifier uses mean annual surface temperature in °C and total annual precipitation in mm. Temperature includes the same seasonal elevation correction as the simulator. Classification is independent of the painted target zones. The published atlases were fitted using the original seasonal zone objective; adding the biome layer does not change that score.

A separate experimental objective now maps painted zones to allowed biome envelopes using `data/biome_target_crosswalk.json`. `--objective whittaker` selects the restrictive profile and `--objective whittaker-broad` selects a broader interpretation. Each gives equal weight to painted zones and combines categorical coverage with continuous distance to the allowed envelopes (5°C and 500 mm distance scales). Outside-envelope climates receive partial optimization credit but remain unclassified on the biome map. These scores measure a different hypothesis from the original zone rules and must not be compared numerically with `zonefit`. See [the target-crosswalk experiment](../reports/WHITTAKER_TARGETS_20261022.md).

The nine climate envelopes are digitized from Ricklefs, *The Economy of Nature* (2008), figure 5.5, by Valentin Stefan's [plotbiomes](https://github.com/valentinitnelav/plotbiomes) project. Coordinates are retained in `data/whittaker_biomes.csv`; its original precipitation unit is cm, converted to mm in the classifier. Source metadata and the MIT license are adjacent to the CSV and copied into atlas downloads.

These are potential climate biomes. They do not resolve seasonality, drainage, wetlands, soils, fire, farming or actual vegetation. In particular, a swamp is not a separate Whittaker climate envelope. A Mediterranean climate may plot within woodland/shrubland, grassland or a forest envelope depending on its annual means.

Climates outside the digitized envelopes remain **Outside diagram**, shown in grey. They are never extrapolated into the nearest biome. Ocean is separately masked. Exact shared boundaries choose the lowest numeric polygon ID consistently; a tiny tolerance includes boundary points and the digitization's zero-area spike.

`atlas.bin` stores biome IDs on the same half-source-resolution grid as Köppen IDs:

| ID | Class |
|---|---|
| 0 | Outside diagram / invalid climate |
| 1 | Tropical seasonal forest / savanna |
| 2 | Subtropical desert |
| 3 | Temperate rainforest |
| 4 | Tropical rainforest |
| 5 | Woodland / shrubland |
| 6 | Tundra |
| 7 | Boreal forest |
| 8 | Temperate grassland / desert |
| 9 | Temperate seasonal forest |
| 255 | Ocean |

Legend shares use full-source-resolution land pixels, including the outside-diagram class, and sum to one. They are map-area shares rather than spherical Earth-area estimates. High-resolution layer boundaries can differ slightly from the coarser click grid because classification follows interpolation of climate and terrain.

`rotclimate/biomes.py` contains the classifier. `tests/test_biomes.py` covers representative climates, units, masks, outside-envelope cases and boundaries. `scripts/verify_atlas_export.py` checks the exported binary layout and assets. `scripts/check_atlas_browser.py` exercises layer switching, station lookup and seasonal maps in Chromium.

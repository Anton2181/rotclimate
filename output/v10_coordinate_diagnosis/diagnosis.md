# Completed coordinate-path diagnosis

Four cases / sixteen cycles completed in 10.00 minutes. All settle; none qualifies.

| Region / path | Rain MAE | Annual rain / reference | Wet-reference coverage | Highest-layer rain, mm/year |
|---|---:|---:|---:|---:|
| california_sigma | 64.26 | 1.70 | 50.9% | 299.75 |
| california_hybrid | 30.26 | 0.43 | 52.0% | 0.00 |
| iberia_sigma | 37.71 | 0.46 | 59.0% | 77.31 |
| iberia_hybrid | 32.84 | 0.21 | 58.6% | 0.00 |

The hybrid path removes high-level mountain rain but leaves most land too dry. Its lower MAE partly reflects suppression of excessive rain, not adequate wetting. Its unchanged face fluxes also imply excessive speeds in thin layers.

Next: convert prescribed velocities to flux using actual face mass, then apply a weighted column-continuity projection. Compare the unchanged rare-storm/humidity anchor first; separately test reference humidity and nested zero/one/four/eight-storm forcing. Keep geometry and thermodynamic closure fixed. No unconstrained search or atlas update.

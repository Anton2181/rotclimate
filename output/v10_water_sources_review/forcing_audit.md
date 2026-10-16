# Cached forcing audit after the source-water batch

No climate integration or download. No-storm monthly flow constructions and partial-column profile integrals.

| Region / wind mode | Maximum projection velocity correction | Mean monthly land low-level direction reversal |
|---|---:|---:|
| california_uniform | 0.894 m/s | 0.00% |
| california_spatial | 0.558 m/s | 0.00% |
| iberia_uniform | 0.722 m/s | 0.00% |
| iberia_spatial | 0.736 m/s | 0.00% |

Corrections use consistent face velocities. Raw unprojected flow is not a valid closed-mass seasonal control. Small corrections alone cannot validate the circulation, but a huge projection-induced mean-flow reversal is not seen here.

| Region / partial pressure window | Local midpoint / native water | Operational boundary / native water | Split-top quadrature / native water |
|---|---:|---:|---:|
| california / common_925_300_hpa | 0.832 | 0.826 | 0.970 |
| california / upper_60795_300_hpa | 0.267 | 0.267 | 0.955 |
| iberia / common_925_300_hpa | 0.848 | 0.840 | 0.963 |
| iberia / upper_60795_300_hpa | 0.274 | 0.274 | 0.945 |

These are partial-column q dp/g comparisons, not complete atmospheric water, vapor import or rainfall. The local midpoint comparison isolates vertical quadrature; the operational boundary adds offshore averaging and saturation capping. Both use observed monthly means; no subdaily covariance is measured. No extrapolation beyond the native humidity pressure coverage.

The proposed quadrature splits the original upper cell at 300 hPa and samples its lower portion at 453.975 hPa. This is a profile-only calculation, not a new five-layer climate or its rainfall prediction. Temperature, winds, microphysics and the unobserved humidity above 300 hPa still need an explicit consistent treatment before a five-layer simulation is prepared.

Diagnose the pressure windows separately. A missing upper-partial moisture store does not by itself identify the cause of regional rain failure, and increasing upper humidity without consistent temperature/vertical resolution could simply trigger spurious saturation.

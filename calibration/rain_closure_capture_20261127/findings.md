# Excess rain comes from both base and exponential convection, not overflow

All6 exact endpoint replays pass original numerical certificates/local equations
and reproduce every shared parent physical/monthly/raw/budget/sea-temperature
field byte-exact. The private wrapper returns the original solve result and
copies actual solved water/saturation/dynamics/instability/full closure inputs.
Independent algebra reconstructs total rain within1.1e-14mm/day. Four known-
answer helper tests pass. No physical source/parameter/numerical change or retry.

| Case | Base rain mm/year | Exponential convection | Overflow |
|---|---:|---:|---:|
| Somalia baseline |2300.80|1247.13|0|
| Somalia joint observed |1481.43|1109.00|0|
| Sahara baseline |182.19|32.85|0|
| Sahara joint observed |1.18|1.24|0|
| North India baseline |302.57|244.85|0|
| North India joint observed |624.33|252.62|0|

In Somalia's July baseline, base rain is10.27mm/day and exponential convection
4.65. Joint observed winds/SST give4.90 and4.36mm/day respectively, still far
above the observed total~0.84mm/day. Zero supersaturation rules out simply
raising the saturation capacity to remove a numerical overflow as the main
solution in these cases. Component magnitudes are identities, not effects of
removing them: water, drying, export and the other component will respond.

Somalia's baseline July RH is0.775, effective exponential threshold0.321,
dynamics1.393 and instability3.056. Joint values0.626/0.366/2.360/2.236.
The exponential term reaches95% of its configured5mm/day cap in59.3%/54.8%
of annual scored samples BEFORE subcloud attenuation. Both inherited warm-
instability amplification of the base and the explicit heated-land exponential
closure are active. The result motivates testing consolidation of those two
warm-convection treatments; it does not prove they are duplicate physical fluxes.

Next physical intervention: fixed instability=0 with everything else retained,
so the older bulk warm-moist boost is removed while explicit exponential
convection, its cap/heating threshold, storm/slope effects and all moisture
transport remain. Pair with already completed, exact/current-source controls
rather than integrate identical controls again. Test native Somalia/Sahara/
North India and joint-observed Somalia, prospectively declare four candidate
runs and guard criteria before execution. Report failures without tuning.
No such candidate run occurred in this6-replay packet.

The inspected stacked figure shows all six endpoints and fixed rain observations.
Raw actual saturation includes the model's actual ice adjustment where active;
this is not inferred from a generic temperature-only saturation. Full scored
trace and full closure inputs are preserved. Worker19223 exited. W18c CLOSED,
AAUNOPENED,r58retained,atlasr51unchanged; no current97pairedreference or adoption.

# Climate progress and remaining priorities — 27 November 2026

There are verified correctness fixes and useful local accuracy gains. There is
still no newly adopted, broadly validated climate or settlement atlas from this
work. Retained Earth parameters are r58; the published atlas still uses r51.
An experimental improvement in one region is not an adopted global improvement.

## Work that is finished

- Signed marine moisture exchange is now included in the diagnostic ledger.
  This corrected accounting; it did not change the actual rain solution.
- The warm-sea inflow mechanism requires actual modeled water. All-land padded
  domains no longer acquire a fictitious sea source from a distance transform.
- Empirical coastal Ekman cooling now respects hemisphere and rotation.
  The directional correction is tested; it was not a universal accuracy gain.
- Literal observed-SST experiments no longer add the modeled SST anomaly back
  into the moisture and convection calculations. The modeled heat-only damping
  behavior remains covered by its own coupled test.
- A current-source97-region r58 reference is complete and independently checked:
  mean regional monthly temperature MAE **1.6297 C**, mean rainfall loss
  **0.46164**. All97 original numerical certificates passed. Three recent
  independent native repeats are byte exact. These are exposed development
  regions and modern WorldClim normals, not independent global validation.

Reference: [current qualification](../../output/climate_reference_20261127/qualification.json)
and [baseline findings](../current_climate_reference_20261127/findings.md).

- Southern westerly and polar background belts are now present. Eleven
  symmetry checks failed before;39 relevant tests now pass. An ordinary coupled
  run is byte exact and a wider native run passes unchanged strict criteria.
  The correction is provably inactive on all97 full r58 reference grids.
  [Source qualification and compatibility proof](../../output/southern_zonal_belts_fix_20261127/qualification.json)
  explicitly link the original reference; it was not reintegrated.

## Outstanding physical issues

| Priority | Evidence | Decision it supports |
| --- | --- | --- |
| Wet-land temperature forcing and continental biases | Volga, western Canada and western Europe are too cold or late; parts of eastern Canada are already too warm. The existing summer-anomaly cooling can remove 5–7 K from the land target. | Test physically stated thermal hypotheses across both groups, rather than a global warming/cooling knob. The fixed shared-solar-bound experiment completed all97: local gains but full development rejection. |
| Circulation depends on unavailable surrounding context | Padding changes Sahara rain from215 to7 mm/year with identical scored geography. Native summer winds have the wrong direction in Somalia and Sahara. Replacing the pressure filters' unknown exterior by zero improves these rain targets but damages North India. | The completed finite native-parent pilot improved Somali July wind RMSE22.6% but worsened its rain loss53.8% and badly wetted the deserts. That fixed candidate is closed. Work next on precipitation/stability; wider pressure context alone is not the climate fix. |
| Tropical precipitation triggers are too active | With observed winds and SST, Somalia's water column is close to reanalysis but rain remains2590 versus457 mm/year. Both ordinary and exponential pathways are large; overflow is not the explanation. | A valid convection change must preserve the Indian monsoon and dry interiors. Neither deleting the warm instability boost nor algebraically consolidating its cap is an established solution. |
| Dry interiors are also too dry | Namibia/Kalahari19 versus237 mm/year; inland Australia17 versus240. | Broad global drying is a poor response to wet Somalia and Sahara. Include these deficits in development assessments. |
| Calibration depends on Earth-only conditioning | r58 uses observed lateral precipitable water and some observed-rain-derived circulation conditioning. The fantasy world has no such observations. | A separate transfer configuration and matched world validation are required before an Earth gain can become a new atlas. No planetary fit can substitute for this check. |

The solar-bound thermal hypothesis explicitly assumes the existing EBM composite
atmosphere+soil heat capacity for the regional temperature relaxation. Its bound
is absorbed ice-free TOA sunlight. This is a stated modeling assumption, not a
closed surface/latent-heat budget or a proven estimate of the regional column.
See its [prospective protocol](../wet_energy_budget_20261127/README.md). Its [complete findings](../wet_energy_budget_20261127/findings.md) report the full97 rejection, gains and harms.

## Avoid repeating unsuccessful work

- The instability=0 experiment reduced native Somalia rainfall error by33.5%
  but worsened North India's by11.2%; closed, unapplied.
- Zero pressure-anomaly exterior reduced Sahara rainfall error by54.5% and
  Somalia's by15.2%, but worsened North India's by47.4%; closed, unapplied.
- The offline shared-convection-cap prototype has no coupled validation and
  gives no convincing monsoon protection. It is not an adopted physical fix.
- Earlier conservative column/reservoir and environmental-profile studies are
  not untried ideas. For example, both environmental6 and6.5 K/km candidates
  passed their numerical checks but failed accuracy/humidity protections under
  r39. Read the actual archived failures before proposing a new vertical model.
- W18/W18c remain permanently closed after fine failure. AA remains unopened.

Useful records: [instability findings](../instability_consolidation_20261127/findings.md),
[pressure findings](../pressure_zonal_exterior_20261127/findings.md),
[closure decomposition](../rain_closure_capture_20261127/findings.md),
[wind/SST findings](../wind_sst_diagnostic_20261127/findings.md),
[old environmental result](../../output/environmental_partition_20261027/review.json).

The fixed solar-bound candidate is closed after full development failure.
The native-parent test has now isolated wider pressure context and failed its rainfall protections. Further local boundary blends should give way to the precipitation/stability problem. The new [small global/context reference](../spherical_pressure_context_20261127/README.md)
preserves constants, spherical distances/areas, longitude rotation and hemisphere
reflection; one spherical harmonic converges under refinement. It still needs
scalable agreement, a justified global thermal field and nested sampling; it cannot be presented as
better climate before actual coupled evaluations. There is no promised date
for a new atlas until a candidate passes development and subsequent validation.

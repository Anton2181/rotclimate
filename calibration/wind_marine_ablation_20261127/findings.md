# Marine relaxation compensates wind changes but deleting it is not a fix

All12 fixed integrations finished without retries or numerical changes. All
original certificates pass. Six controls reproduce BOTH completed wind arms,
including every shared physical/raw/budget array byte-exact. All observed
heat/moisture wind samples remain exactly prescribed; all six disabled arms
have zero marine term. Source/input/library/forcing/attempt parameter checks
and complete signed local equations pass independent review. Original0.01
criteria remain; largest exported scaled residual is0.009974 in a control.

| Region | Wind | Marine on → off rain mm/year | T MAE C on → off | Rain loss on → off |
|---|---|---:|---:|---:|
| Somalia | Model |3556.41 →3593.46|1.2981 →1.2849|3.6634 →3.7000|
| Somalia | Observed |4097.36 →3423.01|1.5149 →1.5056|4.2022 →3.5271|
| Sahara | Model |215.04 →202.39|2.3639 →2.3295|1.6858 →1.6103|
| Sahara | Observed |12.31 →0.85|1.9901 →1.9278|0.1411 →0.0254|
| North India | Model |547.42 →460.87|3.2063 →3.1591|0.4900 →0.5709|
| North India | Observed |748.02 →668.70|2.9523 →2.8917|0.6654 →0.6933|

The wind effect on Somalia's rain changes from+540.95mm/year with e91 active
to−170.46 with it disabled: a−711.41mm/year interaction. Source compensation
therefore changes even the sign of this model's response to prescribed wind.
It does not explain the remaining~2966mm/year excess or fix summer seasonality.
The same interaction is only+1.19mm/year in Sahara and+7.22 in North India;
regional mechanisms differ. These are coupled model responses, not a tagged
moisture fraction or isolated natural causal contribution.

With observed winds in Somalia, removing the1662.56mm/year marine source
reduces rain only674.36mm/year. Advection rises817.16mm/year and storm exchange
rises138.98, among other changes. With modeled wind, e91 had been a small net
sink at the scored cells, so removing it raises rain37.05mm/year. Sahara's
modeled scored marine term is zero in both arms but rainfall still falls12.65,
showing off-footprint/coupled effects. Do not interpret local source magnitudes
as independent rain reduction estimates.

North India's rain loss worsens16.52% under modeled wind and4.20% under
observed wind when e91 is removed. Its annual amount becomes more deficient.
Small temperature improvements do not justify adopting this ablation. No score
screen was declared; report the result rather than inventing a new gate.

All four-arm regional T/P curves are retained in inspected wind_response.png.
Both observed-wind North India cases still require the parent spatial warning:
regional mean totals/seasonal curves hide large per-cell mountain errors. No
mean-total substitution, tuning, global accuracy claim or adoption follows.

## Next work

The simple e91 deletion line is closed as a proposed general fix. Keep the
completed12-run packet immutable. Moisture transport/boundary state, coastal
SST and conversion to precipitation remain unresolved Somali leads; additional
ablations cannot be treated as individually additive fractions. Before any
observed-SST test, account explicitly for sst_damping_heat_only, which adds a
modeled undamped seasonal anomaly back for moisture even in observed mode.

A separate source audit found that the active coastal upwelling Ekman rotation
uses planetary spin but omits latitude's Coriolis sign (model.py upwelling block).
A prograde southern west coast with northward/equatorward wind should transport
water westward/left, but the current right-turn expression gives eastward flow.
The existing NH test hardcodes a right turn and never exercises that southern
case. Verify/fix this generic directional error with known-answer hemisphere/
spin/rotation tests and a separately declared changed-source regression. Do not
change source until all old-source workers have exited and this packet is saved.
The audit alone does not show a major Somali rainfall effect or justify an
accuracy claim. Native map/NH interiors may be unaffected; southern padding can
still influence the coupled sea.

Worker17070 has exited. Main source/retained params unchanged by this ablation.
W18c CLOSED, AA UNOPENED, r58 retained, atlasr51 unchanged. A new current-source
paired reference remains necessary before calibration or a new map.

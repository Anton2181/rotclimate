# Six native pressure-exterior candidates

Commit before preparation/integration. Replace ONLY the two broad/local thermal-
anomaly pressure filters' nearest continuation with constant-zero anomaly outside
the actual padded grid. Keep pressure coefficients/scales, Pa units, signed
momentum/friction/drag and all other filters/params/grid/numerics. No observed
forcing. New pressure feeds all original last_pres uses(turning/drying/feedback).

This is a hypothesis about unknown exterior context, not a proven correction
or observed pressure. A uniform finite warm patch has gradients against its
prescribed zero exterior; that is intended, not a globally uniform atmosphere.
No kernel-mass normalization or boundary truth inferred. Three known-answer
zero/kernel-mass/signed-momentum tests pass.

Exactly6 new candidates: Sahara target, Somalia/NIndia/Algerian Sahara/Najd/
California guards, reusing qualified current97-source native controls. Target
rain-loss ratio<=.90; all6temperature and rain-loss ratios<=1.01. Passing only
permits broader exposed development, never adoption. Failure closes this fixed
alternative with no blend-strength rescue or relaxed guards.

Production89files unchanged. Private228regularfile model uses explicitly hashed
in-memory pressure_wind override; protocol includes actual helper/runner source
and intervention. Recorder returns original result and saves actual winds;
restore both methods even on exception. Same56km/1100km, original strict solver
criteria. One worker nice10,all4thread vars1,literalvenvPython. Fixed6-run limit,
preserve/stop on failure/interruption, no automatic retry/tolerance change.

scripts/run_pressure_zonal_exterior.py prepares, --run executes6 once. Independent
review checks qualification/source/input/params/masks/cells/certificates, original
scores within archive rounding and actual geographic winds. W18cCLOSED,
AAUNOPENED,r58retained,atlasr51unchanged; no fine28 or global fitting in this pilot.

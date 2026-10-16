# Completed source-water diagnosis: pursue vertical structure

15 October 2026. All twenty user-run cases complete and settle after four
cycles: eighty cycles, 112.1 saved integration minutes, 112.3 minutes elapsed
for the invocation. Protocol, settings, inputs, annual field hashes, source
budgets and recomputed physical/source summaries agree. All four seed-41
physical controls reproduce their saved original arrays exactly. No new
seasonal integration or download was launched by the assistant.

## The drought survives every tested storm catalogue

| Region / wind background | Annual scored-land rain, five-seed range | Reference |
|---|---:|---:|
| California / uniform | 465.9–476.7 mm | 401.8 mm |
| California / spatial | 37.7–40.9 mm | 401.8 mm |
| Iberia / uniform | 175.5–178.4 mm | 424.2 mm |
| Iberia / spatial | 21.2–23.1 mm | 424.2 mm |

Spatial minus uniform rainfall is −425 to −436 mm in California and −154 to
−156 mm in Iberia. Coastal winter differences are −268 to −274 mm and −121 to
−125 mm. These matched differences are much larger than variation among the
five tested catalogues. More seed selection will not resolve this observed
contrast. This is generator sensitivity, not a confidence interval for real
climate; repeated settling years are not independent weather years.

California uniform cases still lose to the zero-rain monthly-MAE baseline.
Their roughly correct regional amount conceals coastal underprediction and
interior excess. Spatial cases beat zero-rain MAE by small amounts while
remaining far too dry. Existing broad screens are preserved and do not justify
an atlas promotion.

![Paired rainfall and full-domain source removals](../output/v10_water_sources_review/source_comparison.png)

## Water enters, but most leaves without precipitation

| Region / winds | Boundary share of scored-land rain | Gross boundary supply exported again | Locally evaporated ocean water exported |
|---|---:|---:|---:|
| California / uniform | 92.3% | 89.9% | 89.8% |
| California / spatial | 91.3% | 98.2% | 99.3% |
| Iberia / uniform | 83.1% | 92.0% | 90.1% |
| Iberia / spatial | 63.9% | 98.7% | 98.1% |

The first column is scored-land rain ancestry at its latest vapor entry. The
last two columns are full-domain atmospheric source balances. They include
water and rain over both ocean and land, rather than an efficiency for useful
land rain. Soil evaporation resets ancestry to land recycling. Initial vapor
has decayed to negligible levels; land recycling contributes below 0.4% of
scored-land rain in all these cases.

Changing to spatial winds reduces gross boundary supply by a mean 22.4% in
California and 21.4% in Iberia. Boundary-sourced precipitation anywhere in the
domain falls by 86.2% and 87.0%. Local ocean evaporation increases from a mean
358.9 to 453.0 mm per domain area in California and 255.1 to 314.2 mm in Iberia,
while its precipitation removal collapses. Per-source stores, gross supply,
rain, export and tiny explicit numerical adjustments close; maximum final-year
source residual is 2.19e-11 mm.

This establishes a strong conversion/placement issue alongside the supply
reduction. It does not identify a unique cause: moisture distribution, ascent,
thermal structure, missing fronts and instantaneous rainout remain separate
hypotheses. A larger humidity or ocean-evaporation multiplier alone is not a
justified next calibration. The circulation can still carry additional water
through the region without creating the desired winter rain.

Full verification, source amounts, coast/interior season responses and paired
contrasts are in
[`output/v10_water_sources_review/review.json`](../output/v10_water_sources_review/review.json)
and [its summary](../output/v10_water_sources_review/review.md).

## Cached checks narrow two structural questions

Forty-eight independent no-storm monthly flow constructions measure the actual
mass-projection adjustment using consistent face velocities. Maximum adjustment
is 0.56–0.89 m/s across the four region/wind combinations. No low-level land
direction reversals occur for raw speeds >=0.5 m/s under the declared test.
Thus a huge projection-induced reversal of the monthly mean flow is not
supported. This does not validate its vertical circulation, real storms, or
what a different pressure/mass closure would do in a climate integration.

The second check compares specific-humidity pressure integrals in the shared
native 925–300 hPa window. It separates four-layer midpoint quadrature from
the operational offshore profile and local saturation cap. No humidity outside
the cached native pressure coverage is extrapolated.

| Region / pressure band | Local four-layer midpoint / native water | Operational profile / native | Split-top quadrature / native |
|---|---:|---:|---:|
| California / 925–300 hPa | 83.2% | 82.6% | 97.0% |
| California / 608–300 hPa | 26.7% | 26.7% | 95.5% |
| Iberia / 925–300 hPa | 84.8% | 84.0% | 96.3% |
| Iberia / 608–300 hPa | 27.4% | 27.4% | 94.5% |

The current top cell spans 607.95–0 hPa, about 60% of atmospheric mass at sea
level, but uses one representative pressure near 304 hPa. That value is much
drier than the lower portion of the cell. The partial-profile check captures
only about 27% of native-reference water between 608 and 300 hPa. Offshore
averaging/capping explains little of that specific deficit because the local
midpoint and operational numbers nearly coincide.

The proposed quadrature splits the top cell at 300 hPa and samples its lower
portion at 453.975 hPa. In a **profile-only calculation**, the known upper
band improves to 94.5–95.5% of reference water and the full shared window to
96.3–97.0%. No new model state, upper humidity outside the observed window or
rainfall prediction is inferred. A model's actual transported vapor is not
identical to its prescribed reference profile; these numbers do not measure
all of its vapor stores or prove the rainfall cause.

See [cached forcing audit](../output/v10_water_sources_review/forcing_audit.md)
and its full monthly/area [data](../output/v10_water_sources_review/forcing_audit.json).

## Next development target

The [separate five-layer mechanism test](v10_split_column.md) is now implemented
and prepared for the user. Twelve cases compare zero/retained-RH incoming
upper humidity and an old-column-water matched control, in both regions and
wind backgrounds. It splits the large upper cell at 300 hPa and uses pressure-consistent local
temperature/height targets. Treat the missing humidity reference above 300 hPa
explicitly: any dry-lid or retained-RH assumption must be labelled and checked
for sensitivity, rather than claimed as observed upper-air forcing.

Keep the old circulation comparison controlled. A useful first hypothesis can
split the old upper face flux in proportion to the new dry masses, preserving
its aggregate horizontal transport and lower-layer flows, then reconstruct
interface exchange from continuity. It is a controlled coarse-circulation
experiment, not new reference winds at both upper pressures. A later test of
their separate reference winds must remain distinct.

Measure supplied column water as well as its vertical distribution, and include
a matched-water control where it is compatible with local saturation. This
distinguishes better vertical placement from bulk wetting. Changing humidity
alone in the cold old upper cell risks spurious saturation; temperature,
pressure conversion and moisture must be treated together.

The implementation passes resolved-layer shape checks, exact four-layer step/
manufactured-year regression, dry pressure-law/continuity limits, water/work/
energy ledgers and serialized resume. Sixty focused tests and forty-eight
independent <=60-second regional probes pass; no seasonal integration was
started. The user-run command and 45–75 minute estimate are in the new protocol.
Evaluate coast/interior winter/summer rain,
zero-rain skill, source balances and thermal departures together. The current
profile calculation earns the prototype; it does not earn a claim of improved
climate or publication.

The six-hourly real-weather covariance audit remains without data after the
NOAA access failure. Real front forcing is still an unresolved avenue. These
synthetic-source results do not replace it. The fantasy forcing bridge and
Mediterranean/cold-dry/hot-dry safeguards remain outstanding requirements; the
atlas stays unchanged.

## Reproduction and verification

Saved-field / operator analysis only:

```sh
.venv/bin/python scripts/review_v10_water_sources.py --write
.venv/bin/python scripts/audit_v10_source_forcing.py --write
```

Twenty-two focused tests pass across source tags, source fates and new audit
helpers. New checks use independent constant/linear-q pressure integrals,
variable clipped bounds, exact partial-layer mass, refused extrapolation,
whole-domain source storage/removal balances and face-mass velocities over
uneven terrain. Figure layout was visually inspected. Frozen experiment,
weather-audit and production source identities remain unchanged.

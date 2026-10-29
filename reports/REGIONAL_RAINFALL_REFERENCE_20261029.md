# Verified r39 reference for the regional calendar-month benchmark

All three new r39 controls pass strict numerical checks and exactly reproduce
the archived monthly float32 temperature and rainfall fields. Their new raw
annual output permits Gregorian interval-overlap reaggregation on the fixed
common footprints. These are reference controls, not new prototype accuracy
results. The month-long wet/dry prototype trials are running separately.

| Region/month | Eligible cells | Observed mm/day | r39 mm/day | Area-weighted MAE mm/day | Bias mm/day |
|---|---:|---:|---:|---:|---:|
| north india/7 | 24 | 8.092 | 2.408 | 5.955 | -5.684 |
| mexico/8 | 23 | 3.023 | 1.591 | 2.088 | -1.433 |
| pacific nw/7 | 12 | 0.681 | 0.838 | 0.205 | 0.158 |

India and Mexico show substantial monsoon-month underprediction in the qualified
baseline. These selected region/month footprints are not its annual development
score or an independent held-out validation. Prototype comparisons must use the
same masks, area weights and calendar. No incomplete month is substituted.

The source inputs and complete test were frozen in `f48a02a7` before forecasts.
Reference and model values share centered 224-km footprints aggregated over
56-km cells with projection-area weights and explicit valid land coverage. Fine
edge pixels contribute half widths. The primary masks require at least 80%
valid reference land area and an interior model-land center. They are unchanged
by any forecast outcome. WorldClim 2.1 monthly normals are the scoring reference. The r39 controls retain
the qualified legacy model’s fixed climatological background fields, and the
new prototype inherits simulated initial/lateral states. This is a conditional
regional comparison, not an independent global climate forecast.

The seven prototype trajectories use a fixed fourteen-day prelude followed by
complete July or August, with wet and dry starts scored separately. The primary
objective averages six 900-second branch losses with equal region/scenario
weight; extra Mexico wet450 is numerical sensitivity only. A pooled candidate
score is withheld if a primary trajectory is incomplete or budget-invalid, or
its reference fails reproduction. Initialization uncertainty is not removed by
choosing the branch that rains more.

The completed reference stage adds three legacy attempts and three strict
passes, bringing that separate record to 1937/1932. Publication and scoring add
zero further integrations. Prototype counts remain separate; active month-long
trajectories are not labelled failures while still running. Normal atlas
climate/biome/population fields and qualified physical parameters stay unchanged.

All three raw annual controls, numerical receipts and frozen case plans are
retained in `output/regional_rainfall_benchmark_20261029/*_r39`. Published reference
fields retain WorldClim means, fixed masks/areas and Gregorian r39 rainfall.
The new prototype full-month comparison remains pending at this reference milestone.

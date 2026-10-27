# Shared westerly-amplitude comparison — 27 October 2026

The Pacific Northwest reference audit found excessive eastward moisture winds
in four eligible native ocean footprints. This experiment tests whether a
smaller globally shared background westerly amplitude reduces that bias without
sacrificing monsoon delivery, temperature, ocean state or humidity structure.
The amplitude is not an observed column speed: it sets the peak background belt,
its fixed0.15poleward component and its fixed seasonal modulation, before terrain
drag, temperature-driven pressure winds, thermal shear and mass projection.
Coupled temperatures, sea state, circulation and water can respond.

The frozen plan `calibration/westerly_fit_20261027/plan.json` declares exactly
three amplitudes:5.0,6.25and7.5m/s versus the current8.76025m/s. These are within
the existing shared2–12m/s calibration bounds. Planet, other wind coefficients,
corrected rain/recycling law, independent no-mixing moisture, capacities, boundary
humidity, land/ocean exchanges, drying and storms remain fixed. There is no
regional coefficient, humidity reset, imposed observed wind or planetary retune.

Forty-two actual coupled Earth runs cover the same seven development regions:
21historical controls (r39, fixed-profile transport, corrected no-mix), then
21candidate cases. All archived control arrays must reproduce exactly. The new
PNW native diagnostic lives in JSON so it cannot change old NPZ fieldsets; r39
must also reproduce the independent native-vector audit exactly.

All original local rainfall/temperature, ocean, wind, humidity, branch/mass and
layer-equation safeguards remain. Added PNW guards require at least10% lower
native partial-column vector RMSE versus the corrected control and no more than
2% worse partial water or vertical-shape MAE. Footprints and areas must match.
The four ocean footprints remain a small, reused, model-assisted development
sample, not global or land circulation validation. The reference is925–300hPa
whereas modeled wind diagnoses the whole moisture column; transient covariance,
coarse geometry and different climate-normal periods limit interpretation.

This stage has no automatic promotion. Any screening qualifier requires a new
frozen full31/ocean/fine/established comparison preserving all original release
guards and repeating PNW circulation/humidity at56/28km before adoption. Fantasy
world transfer remains separate. No headline or normal atlas climate changes
on the basis of a seven-region screening score.

Status: complete; no amplitude qualified.

## Completed coupled comparison

Source `1d706fd`;42/42actual integrations passed strict numerical checks,21historical controls were exact, and runtime was480.6seconds. None passed every screening safeguard, so no full31/ocean/fine/established/world stage or adoption followed.

| Background amplitude | Combined error / r39 | Rain loss / r39 | Temperature MAE / r39 |
|---|---:|---:|---:|
|8.7602m/s|1.13100|1.27291|0.98909|
|5m/s|1.05937|1.11810|1.00064|
|6.25m/s|1.08084|1.16792|0.99375|
|7.5m/s|1.10496|1.21977|0.99015|

The5.0m/s trial reduces experimental rain loss by12.16% and combined error by6.33% relative to the corrected original-westerly control. It still has11.81% higher rain loss than adopted r39. These are gains over a failed experimental model, not an adopted accuracy improvement.

| Background amplitude | PNW annual land rain mm | PNW ocean wind RMSE m/s | PNW mean vector speed m/s | PNW extra guard |
|---|---:|---:|---:|---|
|8.7602|2394.06|4.1259|9.9546|Control|
|5|1700.09|2.1545|7.1448|Fail: vertical humidity|
|6.25|1936.34|2.5909|8.0734|Fail: vertical humidity|
|7.5|2167.17|3.2903|9.0081|Pass|

Observed PNW rain averages897.46mm/year; mean native reference vector speed is6.355m/s. The5.0m/s trial cuts vector error47.78%, yet still rains1700.09mm/year and worsens partial-humidity-shape MAE5.78%. The6.25m/s trial improves wind but worsens shape3.56%. The7.5m/s trial improves wind error20.25% and keeps both humidity errors within2%, so it passes the added PNW guard. None passes all protected rainfall and Iberia humidity checks. Wind improvement alone is insufficient.

| Region | Observed mm/year | Corrected8.76 |5.0 |6.25 |7.5 |
|---|---:|---:|---:|---:|---:|
|north_india|760.83|272.46|270.70|271.25|271.84|
|iran_plateau|232.39|212.69|168.61|183.00|197.78|
|iberia|391.83|737.34|597.37|644.09|690.72|
|japan|1601.36|1114.75|969.98|1017.07|1066.25|
|pacific_nw|897.46|2394.06|1700.09|1936.34|2167.17|

All three candidates fail the protected Iberia, Japan, Mexico and PNW local-error checks and the Iberia vertical-humidity check. No original threshold is relaxed. All seasonal/primer layer and column equations, mass/branch constraints, conservative precipitation transfer and existing native circulation checks remain recorded. Separate PNW native NPZ companions preserve original main climate NPZ fields exactly.

The fixed map shows6.25m/s, the middle declared amplitude; it was not chosen by score. Four native ocean cells remain a small reused development sample. A shared amplitude changes several coupled processes, so this experiment does not attribute every rainfall change to incoming vapor alone.

The unresolved regional opposition matters: weaker winds reduce PNW excess but further weaken Japanese rain. PNW modeled partial humidity remains bottom-heavy while Iberia is top-heavy. A universal upper-q adjustment or a region-specific wind coefficient is not justified. The next separately declared reference audit examines vertical thermal and humidity profiles rather than selecting another amplitude after outcomes.

After this comparison the series contains899actual Earth attempts,895passes and4preserved earlier failures. Figure work and synthetic guard tests add no Earth runs. Science Earthr39, fantasy Earthr38, normal atlas climate/economy packets and headline accuracy remain unchanged.

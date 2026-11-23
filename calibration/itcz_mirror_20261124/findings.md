# ITCZ mean in mirrored southern regions (24 Nov 2026, r53)

Southern regions run mirrored into the northern hemisphere (earth.py region_case / earth_params) but itcz_mean
(+7.0 N, Earth's ocean ITCZ) is NOT mirrored: in the mirrored frame the belt's mean sits 7 deg on the region's own
side instead of 7 deg away. Symptom: the rains end late (Zambia April 210 mm vs obs 44; southern Tanzania
October 180 vs ~25; run-calendar months shown below rolled by six).

Probes (rainprobe, r53, monthly P in the RUN calendar, mm/month):
- itcz_mean -7 everywhere: the wet season vanishes (Zambia peak 23, Queensland 60) - the land belt's whole
  range (7 +- 11.6) was fitted with the +7 offset.
- ocean-only flip (itcz_mean -7, itcz_mean_land +7 or +4): the late tail is cut (Zambia April 210 -> 90 / 45)
  but the wet-season peak falls too (Queensland Jan 235 -> 126 / 97 vs obs 202; Tanzania 226 -> 122 / 106 vs 261).
  See probes_ocean_flip.txt.

Conclusion: a real defect of the Earth harness, but fixing it means re-fitting the ITCZ's land range for both
hemispheres together (land mean + land shift separate from the ocean's), i.e. a PPE over itcz_mean_land,
itcz_shift, circulation_lag_days and the rain-gate knobs, scored on the v5 pool. Parked as lead B4b; no code
change. Note it only affects Earth calibration cases; the atlas world is a northern-hemisphere map.

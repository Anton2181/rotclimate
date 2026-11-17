# The seed-to-area link is supported for two conditional cereal cases

17 November 2026. The same retained Columella bookII witness links the four-to-five
modii wheat task quantity and the five-modii barley quantity to one iugerum.
That closes the specific area-denominator gap in the earlier resource screen.
It does **not** make the prescribed work universal or establish an eight-hour
Roman working day. No existing coefficient or atlas output changes.

| Case | Sowing quantity per iugerum | Task-count quantity | Decision |
| --- | --- | --- | --- |
| Common wheat |4 or5modii (2.9.1,5)|4 or5modii (2.12.1)|Conditional match;10.5 prescribed days|
| Named hexastichum barley |5modii (2.9.14–15)|5modii (2.12.2)|Conditional match;6.5 prescribed days|
| Distichum/Galatian barley |6modii (2.9.16)|5modii in the task example|No direct same-quantity match|

Read the [sowing discussion](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Columella/de_Re_Rustica/2%2A.html#9)
and [task counts](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Columella/de_Re_Rustica/2%2A.html#12).
The author varies seed rates with soil, place, season, weather and tree planting.
The barley cases have distinct variety/conditions; the model's generic barley
and least-work choice do not qualify as an observed regional crop mixture.
Do not rescale task days by6/5 for the other variety: that linear relation is
not supplied here.

The prior scenario conversion remains10.5×8/0.25 =336 listed hours/ha for wheat
and6.5×8/0.25 =208 for the matched barley case. The approximate hectare conversion
and eight-hour assumption remain separate from the text-supported seed/area
link. These prescribed coefficients are inputs, not fitted empirical annual
farm productivity. Human/operator/draft availability, competing occupations,
postharvest work and usable windows remain uncalibrated.

The declared screen analyzed11 selected paragraphs within chapters9/12 of the
same original cached English witness. No new source family, Latin/scan collation
or model run occurred. Slice-based and streaming extraction agree on every
selected paragraph digest; quantities, both arithmetic conversions and the
unmatched variety are checked. Fresh crosswalk/digest/result exports are byte exact.
Artifacts: `output/cereal_seed_area_link_20261117/`.

```sh
.venv/bin/python scripts/cereal_seed_area_link.py
.venv/bin/python scripts/cereal_seed_area_link.py --out output/cereal_seed_area_link_20261117/fresh
.venv/bin/python scripts/cereal_seed_area_link.py --review
```

This finishes the declared unit check. The next work package must select an
explicit calibration baseline, free parameters and eligible observations.
Another source transcription or manufactured scheduler test alone is not a
calibration result.

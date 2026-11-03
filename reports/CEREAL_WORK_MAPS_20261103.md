# Cereal field-work maps — 3 November 2026

The normal Free, Earth and Whittaker atlases now have a **Food and work** topic. Earth offers the maps on both its raw and Earth-corrected climate. The topic contains two map buttons: **Cereal field work**, with five views, and **Calendar alternatives**. These are partial field-work scenarios on the current crop model, with place readouts and downloads. They do not replace climate, crop yields or population estimates.

## Views and units

* Listed field work: hours needed for a target of one million modeled net edible kcal, using the less work-intensive of wheat and barley.
* Cropped land required: hectares of that same least-work cereal for the target. This is not an independently optimized minimum-land crop mix or total landscape land including fallow.
* Harvest staffing: reaping worker equivalents for that target, over a supplied10,20or30day window at8hours/day. These windows are explicit sensitivity scenarios; no climate-based harvest deadline or actual workforce is estimated.
* Calendar alternatives: the number of distinct harvest-boundary climate bins across all equal maximum-energy seasons of the selected cereal. These bins are alternatives, not probabilities, successive harvests or observed dates.

Every map uses common classes across fits and raw/corrected climate. Gray land means no positive modeled wheat/barley output. It is not zero work, zero population, or evidence that other crops, grazing, fishing or imported food are impossible. A missing workload is retained as NaN in grid downloads and as a blank selected-place CSV value. The target is standardized food energy, not a person, household, town demand or complete diet.

## Historical work input

[Columella, De re rustica2.12.1–2](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Columella/de_Re_Rustica/2%2A.html#12) gives wheat10.5 and barley6.5 listed workdays per iugerum, including reaping1.5and1day respectively. These are prescriptive task counts to the threshing floor, not a census of Roman farm work or universal200AD coefficients. [The existing labour report](FARM_LABOUR_20261103.md) records the task breakdown and limitations.

Using the explicitly assumed8-hour workday and approximate0.25ha/iugerum conversion gives336listed hours/ha for wheat and208for barley; reaping48and32hours/ha. The calendar windows and all grain yields still come from the current atlas model. The archaeological [Bogaard et al.2025 labour/land framework](https://doi.org/10.1073/pnas.2400694122) motivates examining work constraints but supplies neither these rates nor a biome-level societal-development classification.

## Calculation and accounting

For cereal c with exported crop energy E_c in net edible kcal per cropped hectare, the target requires A_c=1,000,000/E_c hectares and H_c=A_c×listed_hours_c. Choose the positive-output cereal with least H_c; ties deterministically prefer wheat. Reaping work uses the same selected area and crop, not an independently selected faster cereal. The staffing view divides that reaping work by the chosen number of days and8hours/day.

The input energies are decoded from each atlas's own `harvest.bin` with its own metadata, including the same quantization as the browser. Seed and edible-processing fractions have already been applied. There is no second seed deduction, half-weight second crop, occupation, malaria, arable-land fraction or fallow adjustment. This is a standardized single-cropped-hectare calculation, not a food-support or landscape-population calculation. Current crop assumptions include low-input yield limits, a river-access irrigation proxy and reliability modifiers on cold/dry margins; these limitations carry through to the new maps. Work per hectare is assumed independent of realized yield, without modeling the work saved or wasted in failed crops.

In these four packets, barley always has lower listed work per target under the current crop and work assumptions. The chosen cereal is therefore reported in place readouts; no uniform crop-choice map is presented as new spatial information. This result is conditional on the supplied crop alternatives, current yield response and historical work-rate scenario, not a recommendation that every ancient farmer should plant barley.

For calendars, regenerate all current wheat/barley windows with the current temperature, rain, evaporation and reference soil bucket. Check each crop's maximum against exported energy, allowing only the recorded packing precision. Among tied maxima retain the union of their harvest-boundary bins; multiple windows reaching the same boundary count once. The mask rotates with a rotated calendar, preserving calendar-origin invariance. It is the current monthly crop response, **not** the experimental daily phenology clock or an independently validated crop calendar. The reference bucket is not a continuous crop-sequence soil-water budget.

The calculation agrees with the shared minimum-work LP for unconstrained single-crop controls. The full scheduler's land, seasonal work, task and animal limits are **not jointly imposed on the maps**. A staffing ratio is not a demonstration that a household can complete every required operation or consume enough food in every season. Threshing, processing work, storage, water/fuel collection, animal feed/care, irrigation work, equipment, rest and other duties remain outside the partial budget. There is no claim of total subsistence work, leisure, surplus labour, inequality, famine frequency or validated population.

## Data integrity and downloads

Each atlas has a separate `data/farm_work.json` extension manifest. It records the exact input hashes, work coefficients, calendar grid, image hashes and source identities; existing frozen `atlas.json`, climate and Harvest inputs remain unchanged. The viewer adds the new layers only when explicitly enabled for an atlas with this packet. It checks the selected climate's Harvest fingerprint, metadata bytes, calendar bytes and loaded Harvest binary before exposing readouts. Earth raw/corrected views use their matching packets.

The grid NPZ contains listed work, cropped land and reaping work per million kcal, cereal code(0unavailable,1wheat,2barley), a twelve-bit harvest-boundary mask and the land mask. Bit0is the boundary at the beginning of the solstice-aligned model year; the other bits advance by equal climate bins. The selected-place CSV records the climate, grid location, status, target, crop, partial workload, area, reaping work, all three staffing scenarios and count of calendar alternatives. No calendar probabilities are supplied.

Analytical tests cover units, food balance, equivalence to the minimum-work LP, zero output, scaling, the distinction between work-minimum and land-minimum crops, retained calendar ties and calendar rotation. Full-grid regeneration checks published crop maxima. Browser checks exercise every view, both Earth climates, state restoration, irrelevant-control hiding, downloads and numerical agreement with the independently read grid arrays. Windows-checkout and portable-bundle checks cover byte integrity and launcher delivery.

## Reproduction

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/build_cereal_work_maps.py
.venv/bin/python scripts/refresh_atlas_pages.py
.venv/bin/python scripts/build_fit_hub.py
.venv/bin/python -m pytest -q tests/test_cereal_work_maps.py tests/test_farm_labour.py
```

New map values and source checks are recorded in `output/cereal_work_maps_20261103/review.json`. Rebuilding does not run climate calibration. Better work maps next require crop-specific evidence for omitted tasks, locally appropriate rates, actual cultivar calendars, soil workability and finite water supply before integrating seasonal food storage, labour and provisioning.

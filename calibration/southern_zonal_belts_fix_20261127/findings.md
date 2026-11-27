# Southern extra-tropical background winds corrected and verified

The main model now supplies the missing southern westerly and polar-easterly
belts, with reversed seasonal strength and meridional direction. Existing
friction, retrograde reversal and map rotation still apply afterward.
This is an unfitted source correction; no coefficient or parameter profile was
selected from climate outcomes. It does not complete the model's global
circulation or cure the Somali rain bias.

Before the fix, a symmetric equinox case gave7m/s at45N and0 at45S,−3 at75N
and0 at75S. Eleven known-answer/reflection checks failed, with the rotation
check passing. Afterward all13 new regressions pass, and the combined relevant
suite passes **39 tests** without skips/errors. Twenty pre-edit golden
northern profiles on a mixed-hemisphere grid reproduce ALL saved northern
u/v/ITCZ/Hadley values byte-for-byte after the source change.

## Explicit reference compatibility

The source-scope checker verifies every actual input ID for all97 existing
r58 reference cases and their FULL grid latitudes, including padding. The new
guard can activate only below−27.562666degrees for ANY seasonal index in[-1,1].
The minimum latitude over those97 grids is−10.489706degrees, so the guard
cannot run in any of their steps or primer. Exact file comparison proves
the guarded block is the ONLY model.py addition; the other88 model sources
are unchanged.

This is an explicit inactive-branch compatibility proof for FIXED r58 Earth
parameters and those actual grids. Their original numerical certificates,
protocols and source hashes remain intact. It is not97 new integrations,
a guarantee for different parameters/geography, or new independent validation.
The new engineering qualification links the old97 reference and this proof.

## Two prospective coupled source checks completed

Both original strict numerical certificates passed, with unchanged r58
parameters, data, solver settings, calendar, primer and domain.

| Native Somalia domain | Result |
| --- | --- |
|1100km padding |Every saved T/P/observation/coordinate array and scored monthly wind is byte exact. New branch active in0 steps.|
|4012km padding |New branch active in14 of25 scored steps, up to2051 cells. All input/observation identities and score-rounding checks pass.|

In the wider native run, rain changes **3587.62 →3579.78 mm/year** and T MAE
**1.364457 →1.363049 C**. Maximum scored monthly changes are.01439 C,
3.4885 mm rain and.06862m/s for a wind component. These are source regression
measurements, not a general skill gain. Somalia remains severely too wet.

The wider reference is the ordinary native parent from the finished14-run
experiment. No nested intervention was rerun, rescued, retuned or reopened.
The source was changed only after that worker exited and its failed result
was archived. Among those six finite parent domains, only Somalia reaches the
newly covered southern belts; the Sahara/Algeria failures cannot be excused by
this source gap.

Raw before/after/regression XML and logs, the20-profile golden, exact-source/
all97-case scope proof, two attempts/protocols/numerical certificates, T/P arrays,
actual full winds and the inspected seasonal comparison are preserved.
No scientific retry or changed tolerance occurred.

Use output/southern_zonal_belts_fix_20261127/qualification.json for the current
engineering source and explicit97-reference compatibility; keep the original
output/climate_reference_20261127/qualification.json as its historical parent.
Retain r58 parameters. Atlasr51 is unchanged. W18/W18c remain closed, AA
unopened; no fine/world fit or new climate-accuracy adoption.

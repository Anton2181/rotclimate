# Next physics work after the v2.2 atlas release — 9 November 2026

The adopted physics remains **r44**. Rebuilding its lost Earth-correction artifacts reproduces the recorded
rounded cross-validation scores; that is recovery, not a new improvement or independent validation.

## What the latest experiment actually tells us

P8a's four air–sea coupling candidates passed the 49-region development and 28 km gates. The selected C3 scored
S49 = 0.990966, but S = 1.001360 on the then-unseen eight-region set h and was rejected. Temperature worsened
1.72% on h while rainfall loss improved 1.45%. Its tropical coastal failures join the development evidence.
See `calibration/maritime_p8_20261108/plan.json` and `reports/AUTUMN_PHASE_20261101.md`.

This is evidence of incomplete transfer across climates, not evidence that r44 is a global optimum. Nor does
the recovered correction score establish that another parameter search will improve the physical model.
The adoption rule already permits regional tradeoffs: the aggregate temperature and rain scores, numerical
checks, resolution check and independent milestone test decide adoption. Reinstating an every-region veto
would change the owner's policy and make the search more restrictive.

## First diagnose the heat exchange

Use the **actual model SST recording hook**, not simulated marine air labelled as SST. Keep the comparisons
separate: WOA18 for sea temperature, the appropriate atmospheric reference for marine air, and land observations
for the coastal temperature error. The existing autumn-phase report already distinguishes these quantities.

A physically useful audit starts from the bulk sensible heat relation

    Q_H = rho_air cp C_H U_relative (T_surface - T_air).

For a uniform atmospheric slab of thickness h, this implies

    lambda = C_H U_relative / h;  tau = h / (C_H U_relative).

These are a dimensional diagnostic, not a complete boundary-layer model. Model wind height, temperature
representativeness, stability and the effective layer thickness have to be specified before inserting a bulk
coefficient into the solver. A surface flux in W/m² cannot be substituted for a temperature tendency in K/day.
Test the implied flux across a disclosed range of slab depths rather than fitting a separate depth to each
region. A future coupled ocean budget would also need the opposite heat tendency in the ocean; the current
prescribed equilibrium-temperature framework does not provide that conservation claim.
Record the tendency and its inputs at the solver's actual sampling steps before aggregating by month;
the product of monthly mean wind and monthly mean temperature contrast generally differs from their mean product.

The academic starting point is [Fairall et al. (2003), COARE 3.0](https://journals.ametsoc.org/view/journals/clim/16/4/1520-0442_2003_016_0571_bpoasf_2.0.co_2.xml).
[NOAA's implementation notes](https://www.pmel.noaa.gov/ocs/flux-documentation/) document wind-relative-to-current,
measurement heights and stability corrections. This supports auditing the exchange mechanism; it does not
validate a simplified replacement in Rotclimate. No new scheme or coefficient is adopted by this note.

The diagnostic must cover the existing Mediterranean autumn benefit, East Asian cold outbreaks and the now-seen
tropical coastal failure together. A warm-pool or seasonal mask is a hypothesis needing physical support,
not an automatic fix for the regions that failed.

## Then test whether the search is trapped

Freeze a small candidate family, realistic parameter bounds and computational budget before calibration.
Keep Earth's orbital/radiative forcing and benchmark geography fixed, and use modeled SST and winds for
candidate scores. Observed-forcing substitutions remain explicitly separate attribution diagnostics.
The existing regional monsoon-descent benchmark still has an observed large-scale rainfall driver;
these remain conditional regional scores, not validation of a fully coupled Earth simulation.
Compare multiple dispersed starts against a local refinement from r44 using the same objective and paired
reference. Report the distribution of final scores and which bounds the solutions reach, including failures.
Agreement between several starts would increase confidence only within that parameter family and budget;
it would not establish a global optimum or exclude a missing physical process.

Keep the historical S49/S31 and 28 km scores comparable, and report sensitivity on all additional spent
regions used in development. Name the datasets explicitly; previously spent f/g/h results cannot become
unseen again. A new milestone requires a separately declared independent test after selecting the finalist.
Do not open a new pool merely to keep trying variants. Only adopted physics triggers another Earth-correction
retraining and atlas rebuild.

## Keep the atlas release separate

Finish the pending v2.2 lake routing and delta release with the recovered r44 corrections, then check the full
food → settlements → control chain, the Windows launcher and the extracted portable bundle. This preserves
the physical baseline while making the already-tested geography available in the browser.

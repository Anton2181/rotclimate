# Beyond a short multistart refit — 10 November 2026

This is a development proposal, not a change to the running P8d campaign, its budget,
score, selection, or adoption rule. Complete and report that campaign first.

Two CMA generations from three starts compare attainable candidates under a small,
equal budget. They cannot establish convergence, distinguish starting-point effects
from random-seed effects, or exclude other minima. C3 also changes the fixed exchange
operator, so its points must not be treated as samples of the same response function.

Three useful academic approaches suggest a more informative next campaign:

* [Petrov, Will & Geyer (2025), LiMMo](https://gmd.copernicus.org/articles/18/6177/2025/gmd-18-6177-2025.html)
  approximate monthly model fields with linear parameter responses and optimize the
  resulting error function within specified bounds. This suggests saving monthly
  fields during a designed ensemble, rather than retaining only aggregate errors.
  A cheap emulator is useful only after testing its predictions with actual runs.
* [Williamson et al. (2013), history matching](https://nora.nerc.ac.uk/id/eprint/503735/)
  retain parameter regions consistent with observations after accounting for
  observational, emulator and model-discrepancy uncertainty. This addresses feasible
  parameter space, rather than treating a single optimizer result as uniquely true.
* [Couvreux et al. (2021), process-based calibration](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2020MS002217)
  compare single-column parameterizations with reference large-eddy simulations.
  Their work supports separating process calibration from whole-climate tuning,
  helping identify shortcomings that parameter adjustment cannot resolve.

For Rotclimate, the proposed adaptation is:

1. Freeze a space-covering design within documented response-parameter bounds and
   fixed Earth forcing. Include paired seeds across dispersed starts and seed
   replicates within starts if the question is dependence on initialization.
2. Keep exchange branches separate. Save monthly land fields and actual modeled
   SST, together with numerical and input-identity receipts. Preserve the canonical
   cell/month rainfall loss; regional-mean curves can hide large spatial errors.
3. Test emulator predictions on withheld simulation profiles before using them to
   choose new runs. This tests the emulator, not independent Earth generalization:
   the underlying 49 regions are still development data. Reject unreliable
   approximations and disclose extrapolation rather than trusting a predicted gain.
4. Examine sea and land errors together. WOA SST can constrain the sea process;
   NCEP sigma0.995 air remains a separate diagnostic with a different period and
   vertical reference. Neither their difference nor a conditional air-slab flux is
   an observed coupled ocean heat budget. Any new process constraint and uncertainty
   allowance must be declared before that future search, not fitted to its failures.
5. If physically plausible parameter combinations cannot resolve the observed
   conflicts under an adequate design, investigate the process formulation. Failure
   of a small search alone does not establish structural impossibility. Keep the
   existing aggregate v3 adoption policy; do not restore every-region improvement
   requirements under another name.

This proposal adapts the papers' methods; it is not a claim to have implemented
LiMMo, a Gaussian-process history-matching system, or a validated LES-calibrated
boundary layer. No new coefficients, uncertainty tolerances or independent test
pool are selected here. The eventual climate finalist still needs the declared
development/finer checks and a separately declared independent milestone; f/g/h
cannot become unseen again.

# Calibration methods for rotclimate's ~45-parameter, noisy, 11 s/eval calibrator

Method note: WebFetch could not resolve any host in this session (DNS failure on arxiv.org and agupubs.onlinelibrary.wiley.com), so every finding below comes from search-engine summaries of the cited pages, not from reading the full papers. Exact numbers (CPU times, cut-offs, budgets) should be checked against the originals before they are quoted in a final report. Cost figures for rotclimate assume 11 s per evaluation and 4 evaluations running in parallel on 4 cores: about 22 evals/min, so 320 evals take about 15 min and 1000 take about 46 min. If the 11 s is already the wall-clock time with all 4 cores busy, multiply those times by 4.

## Q1. History matching with GP emulators in climate model tuning: how it works and whether it is useful at ~45 dims with 300–1000 runs

### Takeaway
History matching (HM) does not look for one best parameter vector. It fits a Gaussian-process (GP) emulator to the runs made so far, and then rules out every region whose implausibility (the distance between the emulated output and the target, scaled by all known uncertainties) is above a cut-off, usually 3. It repeats this in "waves", adding about 80 new runs per wave inside the region that has not yet been ruled out (the "NROY" space). Groups have made it work on climate models with tens of parameters and a few hundred runs per study. For rotclimate it is most useful as a way to find and map the acceptable region and to handle discrete hypotheses (spin) honestly. It is less useful as a replacement for the optimiser at finding the single best score.

### Cited Findings
- Williamson et al. 2013, "History matching for exploring and reducing climate model parameter space using observations and a large perturbed physics ensemble", *Climate Dynamics* 41(7-8):1703–1729, DOI 10.1007/s00382-013-1896-4. They applied HM to the HadCM3 coupled model with a 10,000-member perturbed-physics ensemble and used emulators to rule out implausible regions. — [Southampton ePrints](https://eprints.soton.ac.uk/359716); [NERC NORA](https://nora.nerc.ac.uk/id/eprint/503735/)
- In that study HM ruled out about half of parameter space using only a few historical observations. The shape of what remained (NROY) depended mainly on cloud parameters and one ocean-mixing parameter. Global mean surface air temperature was the dominant constraint, and the other metrics added little once temperature was matched. — [Southampton ePrints](https://eprints.soton.ac.uk/359716); [ResearchGate](https://www.researchgate.net/publication/260726780_History_matching_for_exploring_and_reducing_climate_model_parameter_space_using_observations_and_a_large_perturbed_physics_ensemble)
- A follow-up (Williamson, Blaker, Hampton & Salter, *Climate Dynamics* 2015) used HM to remove a structural bias in HadCM3's Antarctic Circumpolar Current. The acceptable region was about 1% of the original parameter space. — [Southampton ePrints 373159](https://eprints.soton.ac.uk/373159/)
- Couvreux et al. 2021, "Process-Based Climate Model Development Harnessing Machine Learning: I. A Calibration Tool for Parameterization Improvement", *JAMES* 13, e2020MS002217 (DOI 10.1029/2020MS002217), with Hourdin, Williamson, Roehrig, Volodina, Villefranque, Rio, Audouin, Salter and Bazile. It is based on the HM technique of Williamson et al. 2013. HM "differs from traditional optimization methods by identifying the range of acceptable ('tuned') model configurations rather than a single best-fit solution." The IPSL and CNRM teams built the htexplo tool to calibrate single-column model runs against large-eddy simulations. — [ResearchGate (paper)](https://www.researchgate.net/publication/347411749_Process-Based_Climate_Model_Development_Harnessing_Machine_Learning_I_A_Calibration_Tool_for_Parameterization_Improvement); [Météo-France job posting describing ht-explo](https://careers.flatchr.io/company/meteofrance/vacancy/adyjo9mxwbznkr0r-researcher-on-strategies-for-climate-model-calibration-f-m/); [WGNE workshop slides (Roehrig)](https://events.ecmwf.int/event/241/contributions/3398/attachments/1994/3610/WGNE-WS_Roehrig.pdf)
- Hourdin et al. 2021 (Part II, "Model Calibration From Single Column to Global"): the implausibility cut-off that defines NROY was 3 for the first 4 waves, 2.5 for the next 3, and 2 from wave 8 onward. The same list of metrics was used in every wave. The paper also mentions a 30-wave single-column HM with an extended parameter set. The authors stress that HM is "not an optimization method providing in the end a single set of parameters, but a method ruling-out a non-plausible part of the initial parameter space." — [Hourdin 2021 Part II PDF](https://web.lmd.jussieu.fr/~hourdin/PUBLIS/Hourdin2021ItuneII.pdf)
- A cut-off of 3 is usually justified by Pukelsheim's 3-sigma rule: any continuous unimodal distribution has at least 95% of its mass within 3 standard deviations. One guidance source recommends keeping T = 3 until the process has converged. — [OSTI-hosted paper](https://www.osti.gov/pages/servlets/purl/1767954); [Lguensat et al. 2023, JAMES](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2022MS003367)
- When to stop waves: when NROY is empty, when emulator uncertainty is smaller than the other uncertainties, when the run budget is spent, or when NROY stops shrinking noticeably. — [Lguensat et al. 2023 (NOAA repository copy)](https://repository.library.noaa.gov/view/noaa/53825/noaa_53825_DS1.pdf); [OSTI](https://www.osti.gov/pages/servlets/purl/1767954)
- A related LMDZ tuning study sampled 80 new parameter vectors inside NROY at each wave. This is a different paper from Hourdin 2021 Part II, so the number may not match. — [search summary of LMDZ HM work, Hourdin 2021 Part II PDF](https://web.lmd.jussieu.fr/~hourdin/PUBLIS/Hourdin2021ItuneII.pdf)
- A land-surface model study using HM shrank NROY to 0.01% of its original size, which shows how far iterative refocusing can go. — [GMD 17, 5779, 2024](https://gmd.copernicus.org/articles/17/5779/2024/)
- Related work: Lguensat et al. 2023 ("Semi-automatic tuning of coupled climate models with multiple intrinsic timescales", Lorenz96) and Hourdin et al. 2023 *Science Advances* ("Toward machine-assisted tuning avoiding the underestimation of uncertainty in climate change projections"). — [Lguensat 2023 JAMES](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2022MS003367); [Science Advances](https://www.science.org/doi/10.1126/sciadv.adf2758)

### Inferences
- How HM works, with the standard implausibility form from the Williamson/Vernon line of work (not re-verified in this session): I(θ) = |z − E[f̂(θ)]| / sqrt(Var_emulator(θ) + Var_obs + Var_discrepancy + Var_internal). Any θ with I > 3 is ruled out. For rotclimate:
  - z: a per-zone target, such as each painted zone's F1 or area fraction.
  - Var_obs: uncertainty in the painting itself, e.g. fuzzy zone boundaries.
  - Var_discrepancy: "tolerance to error", meaning how well a cheap simulator could ever match a hand-drawn map.
  - Var_internal: the spread across random surrounding worlds. This lets the 3-world ensemble noise enter in a principled way instead of through racing.
- The multi-metric version takes the maximum (or the 2nd or 3rd largest) implausibility over all zones. This is a natural multi-objective alternative to the 0.5·mean + 0.5·softmin weighting (see Q4).
- Feasibility at 45 dims: Williamson 2013 used 10,000 runs, which is far more than rotclimate's budget. The htexplo/LMDZ studies used about 80 runs per wave over many waves, typically with fewer parameters (exact counts not retrieved). With 300–1000 runs at 45 dims, a wave-1 GP will be crude unless only a handful of parameters matter, which is plausible here: latitude, tilt, spin and land fractions probably dominate. Waves of about 100–150 runs would be practical, at about 5–7 min per wave on 4 cores.
- Recommended use: HM as a front end. Run 1–2 waves of about 150 space-filling runs each, with spin as a factor or one wave per spin. Rule out implausible regions such as wrong-hemisphere latitude or rainfall regimes that cannot match. Then start CMA-ES or TuRBO inside NROY. It also gives a principled spin comparison (see Q3): compare how much NROY volume, or what fraction of runs, survives under each spin.
- Main caveat: HM needs one emulator per output metric. With many zones that means many GPs, which is cheap at n ≤ 1000. HM also targets "good enough" rather than "best". If the goal is the highest possible F1, HM alone will not deliver it.

### Gaps
- I could not retrieve the full texts of Hourdin et al. 2017 ("The art and science of climate model tuning", BAMS) or Williamson et al. 2017 (tuning to the present climate). Their specific claims are not in these notes.
- I did not retrieve the exact parameter counts, runs per wave, or final NROY fractions for Couvreux 2021 or Hourdin 2021 Part II.
- I found no published example of HM at about 45 parameters with fewer than 1000 runs, and no direct HM-vs-CMA-ES comparison.

## Q2. Bayesian optimisation and surrogate-assisted evolution at 30–50 dims with small budgets

### Takeaway
Independent BBOB benchmarks at 10–60 dims find that trust-region BO (TuRBO) beats CMA-ES at small budgets. At 60 dims, CMA-ES catches up or wins as the budget grows. SAASBO is strong but too slow to compute beyond a few hundred points. lq-CMA-ES is a low-risk drop-in for the existing CMA-ES setup in pycma. At 300–1000 evaluations the expected gain is moderate (a better result earlier in the run), not a different order of magnitude, and noise reduces the surrogates' advantage.

### Cited Findings
- TuRBO (Eriksson et al., NeurIPS 2019, "Scalable Global Optimization via Local Bayesian Optimization") runs several local BO searches at once, each in a trust region with its own GP. CMA-ES was among the baselines, and the authors report that TuRBO beats BO, evolutionary, and stochastic-optimisation baselines. — [NeurIPS paper PDF](https://proceedings.nips.cc/paper_files/paper/2019/file/6c990b7aca7bc7058f5e98ea909e924b-Paper.pdf); [arXiv 1910.01739](https://arxiv.org/pdf/1910.01739)
- A third-party summary (not the paper) says CMA-ES and BOBYQA were consistent runners-up behind TuRBO on robot-pushing and rover-trajectory tasks. — [Liner review](https://liner.com/review/scalable-global-optimization-via-local-bayesian-optimization)
- Independent benchmark: Santoni et al., "Comparison of High-Dimensional Bayesian Optimization Algorithms on BBOB" (ACM TELO 2024; arXiv 2303.00890). It compared 5 high-dimensional BO methods, vanilla BO and CMA-ES on the 24 BBOB functions at 10–60 dims. Findings:
  - BO is better than CMA-ES at limited budgets.
  - Trust regions are the most promising way to improve BO, and TuRBO did well across many function, dimension and budget combinations.
  - At 60 dims, CMA-ES did better, especially at larger budgets.
  - TuRBO was the most promising method on both convergence and CPU time.
  - Code: IOH-Profiler-HDBO-Comparison on GitHub.
  - [arXiv 2303.00890](https://arxiv.org/pdf/2303.00890); [ACM TELO](https://dl.acm.org/doi/10.1145/3670683); [GitHub code](https://github.com/BayesOptApp/IOH-Profiler-HDBO-Comparison)
- CPU overhead in that study, as reported in a snippet with the dimension unclear: average total CPU time was about 9.8 s for TuRBO1, 35.5 s for TuRBO-m, 168 s for vanilla BO, and about 5285 s for SAASBO. SAASBO's runtime was called "prohibitive", and at 20 dims SAASBO was run only on f15–f24 for that reason. — [arXiv 2303.00890](https://arxiv.org/pdf/2303.00890); [HAL earlier version](https://hal.sorbonne-universite.fr/hal-04184969v1/document)
- SAASBO (Eriksson & Jankowiak, UAI 2021) targets problems with hundreds of variables and a few hundred evaluations. It uses a GP with a sparsity-inducing prior on per-dimension lengthscales, fitted by Hamiltonian Monte Carlo (NUTS). It beat strong baselines on problems up to 388 dims. On a 124-variable vehicle design problem, the effective dimension it identified grew from about 2 to about 10 during the run. — [PMLR v161](https://proceedings.mlr.press/v161/eriksson21a.html); [UAI PDF](https://auai.org/uai2021/pdf/uai2021.207.pdf); [arXiv 2103.00349](https://arxiv.org/pdf/2103.00349)
- The Ax SAASBO tutorial warns that more than about 100 evaluations "may not be feasible", because SAASBO's overhead grows cubically with the number of data points (NUTS). — [Ax SAASBO tutorial](https://ax.dev/docs/0.5.0/tutorials/saasbo/)
- A later paper found that adding the SAAS prior can hurt when the low-effective-dimension assumption does not hold. — [arXiv 2208.02704](https://arxiv.org/pdf/2208.02704) (via search summary; attribution not fully verified)
- lq-CMA-ES (Hansen, GECCO 2019, "A global surrogate assisted CMA-ES", DOI 10.1145/3321707.3321842) works as follows:
  - It fits a global linear, diagonal-quadratic, or full-quadratic surrogate, chosen by how much data is available.
  - It uses the surrogate in place of the true objective only when the surrogate's rank correlation with recent true evaluations is high. Otherwise it spends more true evaluations.
  - Hansen concludes that a global quadratic model is a viable way to enhance CMA-ES.
  - The code is in pycma.
  - [ACM DOI](https://dx.doi.org/10.1145/3321707.3321842); [GECCO 2019 TOC](https://sig.sigevo.org/TOC-GECCO-2019-ENUM); [pycma advanced-optimization docs mirror](https://tessl.io/registry/tessl/pypi-cma/4.3.0/files/docs/advanced-optimization.md)
- A related but different method (multi-objective CMA-ES with a linear-quadratic surrogate, Gharafi, Hansen, Brockhoff & Le Riche 2023) converged 6–20× faster than without the surrogate on the double-sphere function. Do not read this as the speedup for single-objective lq-CMA-ES. — [IP Paris research portal](https://researchportal.ip-paris.fr/en/publications/multiobjective-optimization-with-a-quadratic-surrogate-assisted-c/)
- Py-BOBYQA (Cartis, Fiala, Marteau, Roberts) is a model-based trust-region derivative-free optimiser with bound constraints. Features relevant to noise:
  - Restarts trigger when all interpolation-set values are within a user-given noise level. A restart pairs model-improving steps with a large increase in the trust-region radius.
  - Restarts are on by default for noisy problems, with a default cap of 10 consecutive unsuccessful restarts.
  - The `nsamples` option averages repeated evaluations.
  - The authors report restarts as "a cheap and effective mechanism for achieving robustness". That statement may come from the DFO-LS paper.
  - [Py-BOBYQA user guide](https://numericalalgorithmsgroup.github.io/pybobyqa/build/html/userguide.html); [Advanced usage](https://numericalalgorithmsgroup.github.io/pybobyqa/build/html/advanced.html); [arXiv 1804.00154](https://arxiv.org/pdf/1804.00154); [Escaping local minima with DFO, arXiv 1812.11343](https://arxiv.org/pdf/1812.11343)
- Nevergrad's NGOpt is an algorithm-selection "wizard" that picks an optimiser from the problem's properties (dimension, budget, noise, discrete variables, parallelism). It was tested across noisy, discrete, mixed-integer and large-scale problems. The source snippet was garbled, and I found no budget- or dimension-specific results for NGOpt. — [ResearchGate: Improving NGOpt via automated algorithm configuration](https://www.researchgate.net/publication/363478831_Improving_Nevergrad's_Algorithm_Selection_Wizard_NGOpt_through_Automated_Algorithm_Configuration)

### Inferences
- Python options for rotclimate:
  - `cma` (pycma): CMA-ES, lq-CMA-ES, and NoiseHandler (UH-CMA-ES).
  - BoTorch: has a TuRBO-1 tutorial implementation; the original `turbo` repository also exists.
  - Ax/BoTorch: SAASBO.
  - `Py-BOBYQA`.
  - `nevergrad`: NGOpt, and it can wrap CMA-ES and BO.
  - `cmaes`: lightweight, with IPOP/BIPOP-style restarts via the Optuna hub sampler.
  - Package names come from the sources above; exact API names should be checked.
- Sizing: at 11 s per evaluation, TuRBO's GP overhead (seconds per step) is negligible, and batched TuRBO (q = 4) fits 4 cores naturally. SAASBO's overhead (minutes per step at n of several hundred) would be large relative to the 11 s evaluation and does not fit a 1000-eval budget. At most, use it once on a few hundred archived points to see which parameters matter (see Q5).
- Expected gains vs plain CMA-ES at about 45 dims and 300–1000 evals: the BBOB results suggest TuRBO reaches a given quality earlier. At 45 dims (between the tested 20 and 60) with 1000 evals, CMA-ES is likely to be roughly as good, so expect improvement mostly in the first few hundred evals. No source gives a number specific to rotclimate's noisy, partly discrete problem, so this is uncertain.
- lq-CMA-ES's rank-correlation gate interacts with noise. With a 3-world noisy objective, the surrogate's rank correlation will be lower, it will be trusted less often, and gains shrink. It is still low-risk because it falls back to plain CMA-ES behaviour.
- Py-BOBYQA needs about 2n + 1 = 91 points just to build its initial interpolation model at n = 45. It is a local method, best used for polishing the best CMA-ES result within the last 100–200 evals.
- The discrete spin choice does not fit TuRBO/SAASBO/BOBYQA cleanly. Keep spin outside the optimiser (separate runs per spin, see Q3) or use a mixed-variable method. Nevergrad and Ax support categorical choices, but performance is not verified here.

### Gaps
- I could not get the exact evaluation-count speedups of lq-CMA-ES over CMA-ES on BBOB from the 2019 paper (full text not accessible).
- I found no benchmark of TuRBO or lq-CMA-ES on noisy objectives at 30–50 dims with about 300–1000 evals.
- I found no NGOpt performance data by budget or dimension.

## Q3. Fair comparison of discrete hypotheses (Earth-like vs reversed spin) with a stochastic optimiser

### Takeaway
One run per hypothesis, with both runs still improving, cannot show that 0.427 is better than 0.421. These are best-so-far values from a stochastic optimiser on a noisy objective, and best-of-run values are biased upward. A defensible comparison needs:
- several independent runs per spin, with budgets fixed or run to convergence;
- every run's final incumbent re-evaluated on the same, larger set of held-out random worlds;
- an interval estimate of the difference.

How many runs are needed depends on the run-to-run spread σ, which has to be measured first.

### Cited Findings
- Benchmarking best practice (Bartz-Beielstein et al. 2020, "Benchmarking in Optimization: Best Practice and Open Issues", arXiv 2007.03488): randomised search heuristics vary from run to run, so performance must be assessed over several independent runs and compared with appropriate statistical tests. The paper includes a test-selection flowchart from Eftimov et al. 2020. — [CIplus 2/2020 PDF](https://d-nb.info/1214641016/34); [ResearchGate](https://www.researchgate.net/publication/342763159_Benchmarking_in_Optimization_Best_Practice_and_Open_Issues)
- Eftimov & Korošec (GECCO 2025) proposed adaptive estimation of the number of runs needed. A 2026 follow-up examines how reliable those estimates are; its arXiv ID is 2605.28309, so treat it as very recent and not verified in detail. — [arXiv 2605.28309](https://arxiv.org/html/2605.28309v1)
- A *Physical Review Applied* paper on per-instance evaluation of stochastic optimisers argues that the accuracy of estimated performance metrics depends on the number of runs and must be checked statistically. It gives experiment-design guidelines. — [Phys. Rev. Applied](https://journals.aps.org/prapplied/abstract/10.1103/2fpj-t663)
- Non-parametric option: trial-based dominance (Price, Kumar & Suganthan 2023) allows standard tests such as Mann-Whitney U to compare both speed and final accuracy. — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2210650223000603)
- Restart strategies for budget fairness and robustness:
  - IPOP-CMA-ES (Auger & Hansen 2005) doubles the population at each restart and ranked first at CEC 2005.
  - BIPOP-CMA-ES (Hansen 2009) alternates large-population restarts with small-population restarts that use a random initial step size. At each restart it picks the regime that has used fewer evaluations. It was among the best on BBOB 2009/2010.
  - The default population size is tuned for unimodal functions and is "hardly large enough for multi-modal functions".
  - [Loshchilov, Schoenauer & Sebag, arXiv 1207.0206](https://arxiv.org/pdf/1207.0206); [Optuna hub restart CMA-ES sampler](https://hub.optuna.org/samplers/restart_cmaes/); [cmaes on PyPI](https://pypi.org/project/cmaes/0.7.0)
- A "time-fair" restart protocol for fixed-time comparisons of metaheuristics has been proposed (arXiv 2509.08986, not read in detail). — [arXiv 2509.08986](https://arxiv.org/pdf/2509.08986)

### Inferences
- Run counts from standard power analysis (two-sample, α = 0.05 two-sided, 80% power): n per arm ≈ 2(1.96 + 0.84)²σ²/δ² ≈ 15.7·σ²/δ². For δ = 0.006:
  - σ = 0.003 → about 4 runs per spin
  - σ = 0.005 → about 11 runs per spin
  - σ = 0.010 → about 44 runs per spin
  - σ = 0.020 → about 175 runs per spin

  Here σ is the run-to-run SD of the re-evaluated final score. A paired or CRN design (same seeds and worlds in both arms) reduces the effective σ. Estimate σ from 3–4 pilot replicates per spin first. Each replicate at 320 evals is about 15 min on 4 cores, so 8 runs per spin is about 4 h.
- Re-evaluate on held-out worlds. The reported 0.427 and 0.421 are the best values over hundreds of noisy 3-world evaluations, so both are biased upward by selection (the "winner's curse"). The longer or more exploratory run gets a bigger bias. Re-evaluate each run's final incumbent (or top 3) on a fixed set of, say, 20–30 new random worlds that is identical for both spins (common random numbers, see Q4), and compare those scores.
- Budget equalisation and convergence: both runs were "still improving", so the comparison measures speed of progress, not the attainable optimum. Either run both arms to a convergence criterion (e.g. BIPOP restarts until K restarts give no improvement) or report best-so-far curves (median and interquartile range over seeds) against evaluations, so readers see whether the curves cross.
- Bayes factors / model evidence: a formal Bayes factor needs the marginal likelihood of the painted map under each spin, integrated over the other ~44 parameters. That requires a likelihood for fuzzy F1, which does not exist, plus heavy sampling. It is not practical here. Pragmatic proxies:
  - Compare the HM NROY fraction (how much of the prior space stays plausible) under each spin.
  - Compare the distribution of scores from a shared space-filling design under each spin.

  These capture "how easily" each hypothesis fits, which is closer to evidence than "best attainable fit". The "best fit" comparison favours the more flexible configuration.
- Report the decision as a difference with a 95% bootstrap CI over seeds, plus an equivalence statement. If the CI lies within ±0.01 (a smallest effect of interest chosen in advance), call the hypotheses indistinguishable under this simulator and objective instead of declaring a winner.
- Alternative design: put spin into a single search as a categorical variable (e.g. Nevergrad, or CMA-ES on a continuous relaxation with rounding). This avoids splitting the budget but gives a less clean comparison. Separate replicated runs remain the more transparent method.

### Gaps
- I found no published guidance specific to comparing discrete structural hypotheses (as opposed to algorithms) by replicated optimisation runs. The design above is adapted from algorithm-benchmarking practice.
- I found no source on computing Bayes factors with a fuzzy-F1 objective. The formula above is a textbook power calculation, not taken from a retrieved source.

## Q4. Handling noisy objectives, and multi-objective calibration

### Takeaway
The cheapest large win is common random numbers (CRN): evaluate all candidates in a generation (and the incumbent) on the same random surrounding worlds. Then add periodic re-evaluation of the incumbent, or pycma's UH-CMA-ES noise handler, instead of trusting single 3-world scores. A full Pareto front across many zones is hard to use. Better options are HM-style per-zone implausibility, or keeping the scalarisation while looking at per-zone trade-offs among the final candidates.

### Cited Findings
- UH-CMA-ES (Hansen et al. 2009): measures the noise level by re-evaluating part of the population and counting how much the ranking changes. If the noise is too large, it either increases evaluation effort (more samples per point) or increases the step size. One source gives a re-evaluated fraction of about 0.3 and a rank-change threshold θ = 0.2. — [Hansen et al. GECCO 2011, Using the UH-CMA-ES for robust optima (PDF)](http://www.cmap.polytechnique.fr/~nikolaus.hansen/proceedings/2011/GECCO/proceedings/p877.pdf); [ACM DL](https://dl.acm.org/doi/10.1145/2001576.2001696); [ResearchGate: UH-CMA-ES for reinforcement learning](https://www.researchgate.net/publication/220743287_Uncertainty_handling_CMA-ES_for_reinforcement_learning)
- Newer re-evaluation work:
  - RA-CMA-ES (Uchida et al. 2024) estimates how reliable the update direction is by splitting the evaluations into two groups and correlating the two update directions. It was motivated by population-size and learning-rate adaptation becoming unreliable under multiplicative noise.
  - An adaptive re-evaluation method for evolution strategies under additive noise appeared at GECCO 2025.
  - [arXiv 2405.11471](https://arxiv.org/html/2405.11471); [arXiv 2409.16757](https://arxiv.org/html/2409.16757); [DOI 10.1145/3712256.3726352](https://doi.org/10.1145/3712256.3726352)
- Confidence-based ranking with adaptive sampling for noisy black-box optimisation (2026 preprint, not read in detail). — [arXiv 2607.14936](https://arxiv.org/html/2607.14936)
- What CRN does and its limits:
  - CRN tests the alternatives against the same random inputs, so differences reflect the alternatives rather than sampling noise. This is the standard way to sharpen difference estimates in simulation optimisation. — [Simulation-based optimization with SA using CRN, Management Science 1999](https://pubsonline.informs.org/doi/10.1287/mnsc.45.11.1570); [On the Effectiveness of CRN, Management Science 1979](https://pubsonline.informs.org/doi/10.1287/mnsc.25.7.649)
  - Reusing a seed only helps if each random draw maps to the same modelled event. A single central random generator can cause execution-path dependence, so key each draw to its event or give each stochastic input its own stream. — [arXiv 2603.11084](https://arxiv.org/pdf/2603.11084)
  - Gains vary a lot: full CRN gave a 93.6% variance reduction in a health-economics microsimulation, while partial CRN gave 5.6%. CRN can also backfire by inducing negative correlation in some models, and it tends to increase the MSE of stochastic-kriging metamodels. — [PMC 3725537](https://pmc.ncbi.nlm.nih.gov/articles/PMC3725537/); [arXiv 1802.00677](https://arxiv.org/pdf/1802.00677)
- Py-BOBYQA averages repeated samples (`nsamples`) and has noise-triggered restarts. — [Py-BOBYQA advanced usage](https://numericalalgorithmsgroup.github.io/pybobyqa/build/html/advanced.html)
- Multi-objective calibration (hydrology):
  - Gupta, Sorooshian & Yapo (1998, WRR) argue for multiple, noncommensurate criteria. Structural model error can be as large as or larger than measurement error and lacks probabilistic properties to build a single objective on, so a single aggregated objective is poorly defined.
  - Yapo et al. (1998) introduced MOCOM-UA, which brought Pareto-based automatic calibration into hydrology.
  - Vrugt et al. (2003, MOSCEM-UA) frame calibration as finding the nondominated set over complementary criteria.
  - [Hydrological Sciences Journal review: one decade of multi-objective calibration](https://www.tandfonline.com/doi/full/10.1080/02626660903526292); [Vrugt et al. 2003, WRR](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2002WR001746); [Vrugt 2003 PDF](https://bpb-us-e2.wpmucdn.com/faculty.sites.uci.edu/dist/f/94/files/2016/04/9.pdf)
- Picking final parameter sets from an NSGA-II trade-off surface is itself a separate decision problem. — [Water Resources Management 2010](https://link.springer.com/article/10.1007/s11269-010-9668-y)

### Inferences
- CRN for rotclimate: use the same 3 surrounding-world seeds for every candidate in a CMA-ES generation, and change them between generations so the search does not overfit to 3 specific worlds. This turns the racing comparison against "best − 0.06" into a paired comparison and makes the 0.06 margin far less likely to throw away good candidates.
  - Caveat: the incumbent's "best" score was measured on old seeds, so it is not directly comparable. Re-evaluate the incumbent on the current generation's seeds, or keep a running mean of its scores across generations.
  - Make sure the world generator draws per-feature random streams, so a parameter change does not shift which random draws later features receive. This matters if land fraction changes how many random numbers are consumed.
- Racing threshold: the 0.06 abort margin should be tied to measured noise. Re-evaluate a few points about 10 times each, estimate the SD of a single-world score, and set the margin to about 2–3 SDs of the paired difference after one world. With CRN the paired SD should be much smaller than the unpaired one.
- pycma's noise handling (`cma.NoiseHandler`, the UH-CMA-ES mechanism) can replace the hand-written racing, or complement it by adapting the number of worlds per evaluation. The cost is roughly a 20–30% increase in evaluations, which is affordable.
- At the end of each 320-eval round, re-evaluate the top 5–10 distinct candidates on about 10–20 worlds (50–200 evals, about 3–9 min) and choose the winner from those means. This removes the winner's curse inside a round.
- Multi-objective: with about 8–15 zones, a Pareto approach becomes "many-objective". Nearly every point is nondominated and the front cannot be shown or used. This reflects general many-objective EMO behaviour and was not directly sourced here. Better options:
  - (a) Keep the 0.5·mean + 0.5·softmin scalarisation for search, then show the per-zone F1 of the top candidates as a trade-off table.
  - (b) Use HM-style "every zone within tolerance" constraints (max implausibility), which is a principled multi-criteria acceptance rule.
  - (c) If a front is wanted, use 2–3 aggregated objectives (e.g. mean F1, worst-zone F1, rainfall realism) with a multi-objective CMA-ES or NSGA-II.

### Gaps
- I found no source measuring how much CRN reduces variance in climate or terrain random-world ensembles specifically. The benefit must be measured in rotclimate.
- I found no direct head-to-head published comparison of weighted-sum vs Pareto calibration outcomes.
- I did not retrieve the UH-CMA-ES original paper (Hansen, Niederberger, Guzzella & Koumoutsakos 2009, IEEE TEC) itself. Its parameters are as given by secondary sources.

## Q5. Sensitivity analysis to reduce dimensionality (Morris, Sobol), and whether to fix insensitive parameters

### Takeaway
Morris screening costs r(k+1) runs. For k ≈ 44 continuous parameters and r = 10 that is about 450 runs (about 20 min on 4 cores), which is affordable and would show which parameters barely affect the objective. Sobol indices computed directly are not affordable at 45 dims; they are only feasible through a GP emulator. Fixing insensitive parameters is reasonable, but only after checking that they are insensitive in the good region, not just over the full prior box.

### Cited Findings
- A Morris design is r one-at-a-time trajectories, each of k + 1 runs, for a total cost of N = r(k + 1). Iooss & Lemaître (2015) recommend r between 2 and 10. — [Campolongo, Cariboni & Saltelli 2007, "An effective screening design for sensitivity analysis of large models"](https://www.asc.ohio-state.edu/statistics/comp_exp/jour.club/CamCarSal_EngModellingSoftware-2007.pdf); [arXiv 1901.05566](https://arxiv.org/pdf/1901.05566); [Saltelli, "From screening to quantitative sensitivity analysis" (2011)](https://www.andreasaltelli.eu/file/repository/Screening_CPC_2011.pdf)
- SALib's Morris sampler takes `num_levels` (default 4) and can optionally choose optimised trajectories. It warns that searching over all combinations of trajectories can be expensive. — [SALib.sample.morris docs](https://salib.readthedocs.io/en/latest/api/SALib.sample.morris.html)
- Morris indices cannot separate nonlinearity from interactions; a high σ could mean either. — [arXiv 1901.05566](https://arxiv.org/pdf/1901.05566)
- Example: a 30-parameter study used classical Morris with 310 samples as its benchmark. — [Raj 2024, PAMM](https://onlinelibrary.wiley.com/doi/10.1002/pamm.202400104)
- In climate HM practice, the plausible region is often controlled by a few parameters (in HadCM3, cloud parameters plus one ocean mixing parameter). This supports the idea that the effective dimension is low. — [Southampton ePrints, Williamson 2013](https://eprints.soton.ac.uk/359716)
- SAASBO's sparsity prior found low effective dimension (about 2–10) in a 124-variable problem, which is evidence that such structure is common in real engineering problems. — [PMLR v161](https://proceedings.mlr.press/v161/eriksson21a.html)

### Inferences
- A practical recipe at 11 s/eval and 4 cores:
  - (1) Free first pass: fit a GP with per-dimension (ARD) lengthscales, or the SAAS prior, to the existing CMA-ES archive (hundreds to thousands of points). Rank parameters by inverse lengthscale. Caveat: CMA-ES archives concentrate around the search path, so this ranks sensitivity locally.
  - (2) Morris with r = 10 (k = 44, about 450 runs, about 20 min), run separately for each spin direction or with spin fixed at the current best. Use CRN (the same surrounding-world seeds along each trajectory), otherwise ensemble noise inflates μ* for every parameter. Screen per-zone F1 and the rainfall penalty as well as the total score, because a parameter can matter for one zone and still look flat on the aggregate.
  - (3) Fix only parameters with low μ* on every output, at the current best value, not the prior mid-point.
  - (4) Run a second Morris pass, or check GP lengthscales, inside the region CMA-ES has converged to, since sensitivity there can differ from sensitivity over the full prior box.
- Expected benefit: if, say, 15 of 44 parameters can be fixed, CMA-ES's default population and adaptation rates improve. Its covariance learning scales roughly as O(n²) parameters, so learning becomes much faster. This is a standard property of CMA-ES and was not sourced here.
- Sobol: the standard Saltelli scheme costs N(k + 2) runs, e.g. N = 512 gives about 23,500 runs at k = 44. This figure is from general knowledge and was not verified in this session. It is infeasible directly. Compute Sobol indices on a GP emulator fitted to about 500–1000 runs instead, which is exactly what the HM workflow already provides.
- Risk of fixing parameters: some parameters may matter only together with others (e.g. a terrain tier height only matters at certain latitudes). Morris's σ flags that, so keep any parameter with high σ even if its μ* is modest.

### Gaps
- I found no climate- or rotclimate-specific guidance on Morris trajectory counts, and no source on screening with a noisy stochastic simulator. The CRN advice is inferred.
- The Sobol cost formula and emulator-based Sobol practice were not verified from sources retrieved in this session.

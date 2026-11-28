# W26 — CLOSED, no adoption (2026-11-28)
Joint refit of e150 surface albedo with its compensating knobs (dry_heating,
subsidence_warming, land_offset), base r63, 33 points (wave 1).
- Every observed point is worse than r63 on S55 (best w1_031 1.0025, land_albedo 1.19 i.e. ~off).
- Emulator (LOO rmse 0.0038, corr 0.992) proposes best 0.9987: predicted gain 0.0013 < 0.005 close rule.
- No wave 2, no dev6/fine28/sealed spend. r63 remains adopted.
Finding: the dev set gains in the eastern Sahara/Tibet from albedo are cancelled by
Arabia/Algeria/central-Australia cooling and Amazon warming even after refitting
compensators; the albedo term needs a structural partner (e.g. clear-sky LW / dust) before
it can be adopted. Deferred to the r65 recalibration.

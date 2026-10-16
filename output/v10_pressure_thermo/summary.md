# Pressure-based thermodynamic transport check

Status: complete. Four fixed cases; no search or atlas export.

| Case | Old → theta rain MAE | Old → theta rain/reference | Old → theta coverage | Settled | Broad screen |
|---|---:|---:|---:|---|---|
| california_uniform | 41.66 → 40.07 | 1.28 → 1.18 | 85.9% → 82.9% | True | True |
| iberia_uniform | 32.07 → 32.20 | 0.46 → 0.42 | 79.2% → 76.0% | True | False |
| california_spatial | 29.88 → 30.33 | 0.12 → 0.10 | 59.1% → 54.3% | True | False |
| iberia_spatial | 34.91 → 35.02 | 0.05 → 0.05 | 34.9% → 34.2% | True | False |

Dry potential temperature is advected with the same dry-air fluxes as water. Pressure conversion replaces passive approximate-MSE transport. Diagnosed prescribed-flow work is an explicit energy exchange; the kinetic/momentum system is unsolved, so this is not a claim of complete total-energy conservation.

Water transport, microphysics, geometry, boundaries, winds and weather remain paired. All old broad screens are retained in separately fingerprinted evidence. Review physical rainfall, target departure and work magnitude together; temperature is observation-informed. No automatic atlas promotion.

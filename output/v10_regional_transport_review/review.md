# Saved regional transport review

Experiment **needs_diagnosis**, 6/8 cases; 16 annual records independently checked. Atlas unchanged.

Stopped error: Ascending parcel condensate exceeds transported water.

| Case | Winter coast mm | Reference mm | Monthly MAE mm | Target Med now arid | Settled |
|---|---:|---:|---:|---:|---|
| control_california_bulk | 56.91 | 534.82 | 30.508 | 92.75% | True |
| control_iberia_bulk | 33.26 | 439.18 | 33.527 | 97.47% | True |
| control_california_parcel_lower | 92.96 | 534.82 | 27.074 | 78.26% | True |
| control_iberia_parcel_lower | 61.28 | 439.18 | 32.850 | 94.44% | True |
| candidate_california_bulk | 90.23 | 534.82 | 28.607 | 79.71% | False |
| candidate_iberia_bulk | 59.15 | 439.18 | 32.258 | 93.94% | False |
| candidate_california_parcel_lower | incomplete | | | | |
| candidate_iberia_parcel_lower | incomplete | | | | |

Candidate rows describe the last **unsettled** cycle, not accepted climates.

All four controls reproduce the parent physical fields and ledgers exactly. Each saved annual budget, signed thermal change, incoming monthly vapor target, evidence hash and reconstructed case summary was checked. The JSON contains cycle histories, layerwise endpoint changes and protected-file fingerprints.

The California parcel candidate has only its configuration file; the failing state/time was not saved. The Iberia parcel candidate did not start. The original parcel dose uses donor-cell vapor, whereas the new corrected transport can leave a different amount in the recipient. This is a compatibility failure, not evidence that adding water or clipping rain is an acceptable fix.

![Saved convergence and rainfall](convergence.png)

No integration, forcing download or atlas publication is performed by this reviewer.

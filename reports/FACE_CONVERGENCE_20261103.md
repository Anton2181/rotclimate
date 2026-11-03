# Fixed-state advection diagnosis: column circulation is a structural constraint

The verified raw r43 world checkpoint is observed without integration. Its
stored vapor and wind arrays are used only after checking the exact saved
scientific source identity and explicit settings that make stored surface winds
equal to moisture-transport winds. No Earth observations or held-out regions are
opened. The diagnostic does not alter the checkpoint, model, calibration or atlas.

At fixed W/u/v, compute the exact discrete vapor supply difference between
shared-face upwind flux divergence and the production point-advection stencil.
Decompose that difference into `-W div(u)` using the same face winds, plus the
exact algebraic remainder. Annual weights use the original model calendar;
statistics cover mapped model-grid land cells. Constant-water and constant-wind
analytic tests verify the decomposition independently of climate outcomes.

The annual mean absolute difference is **6,109.6 mm water equivalent**. The
compression component has mean absolute6,103.0 mm; the remainder is19.74 mm.
The signed means are −26.10, −42.71 and+16.61 mm/year respectively, so a small
domain-average change hides very large opposite local terms. Map arrays and
unclipped percentiles are retained. The large-term maps share a symmetric log
scale; the remainder uses a separate linear scale of±250 mm/year.

These figures are NOT rainfall predictions. Water, winds and all other terms
are held fixed. The full flux experiment changes the solved humidity and
feedbacks and removes the old positive-only, smoothed, warm-column import
closure. This diagnosis neither reconstructs that full switch nor proves the
same magnitude or distribution on Earth regions.

The mechanistic implication is nevertheless specific: stationary column vapor
transport needs compatible dry-air circulation. Surface convergence cannot be
treated as whole-column inflow without upper outflow, vertical exchange or air
storage. The existing mass-projected counterflow experiment substantially
reduced excess wetting but still had S8=1.4562, so that implementation is not
yet accurate enough. Conservative storms alone show a promising reused-region
gain and are undergoing the separate declared61-region comparison.

The fitted face operator addresses numerical diffusion; it cannot by itself
provide the missing column mass/vertical circulation. Its declared climate
screen will finish independently. Future physical development should prioritize
compatible circulation and vertical moisture exchange while preserving the
regional/boundary water ledger, rather than interpreting a lower aggregate
error or a conservation certificate as a complete physical solution.

Observer: scripts/diagnose_face_convergence.py. Reproducible arrays, source
hashes, figure and scope: output/face_convergence_20261103. The normal launcher's
Climate accuracy companion includes the same data, clearly labelled as a
zero-integration diagnostic.

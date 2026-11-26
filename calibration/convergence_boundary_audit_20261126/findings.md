# Convergence-filter boundary sensitivity

The current convergence calculation is substantially sensitive to regional
boundary continuation. About **77.8% of the nominal Gaussian kernel weight**
at scored cells lies beyond these saved regional domains. With production's
reflect mode, that weight samples reflected copies of the available field.
Independent explicit-kernel calculations confirm the result.

This is a concrete numerical-domain issue to investigate before changing
physical coefficients. It is **not** evidence that 77.8% of moisture is false,
that reflection causes the rainfall bias, or that another extension is correct.

## Fixed calculation

All three existing cases use 45×45 cells at 56 km, with a roughly 1,100 km
padding around their scored region. r58's convergence filter has sigma
2,000 km (35.714 cells). SciPy's default truncate=4 produces a radius of
143 cells, approximately 8,008 km. Its nominal support therefore extends
well beyond the regional wind field. The mean exterior kernel fraction is
77.8124% for both Somali variants and 77.8137% for Sahara; all scored cells
fall between 77.7832% and 77.8441%.

The declared stress calculation holds the full saved monthly wind field
fixed. It computes centred divergence with the production row-south sign,
then filters that field under three explicit extension assumptions. It does
not supply the unknown real wind outside the domain. r58's monsoon-heating
and column-shear branches are inactive here, so no unrecorded velocity
subtraction is attributed to these cases.

| Case | Reflect, production | Nearest edge value | Zero exterior divergence |
|---|---:|---:|---:|
| Somalia r58 | 0.097399 | 0.044400 | 0.025019 |
| Somalia minimum turning | 0.039645 | 0.031009 | 0.010534 |
| Sahara r58 | 0.055877 | 0.022974 | 0.013334 |

Values are scored-cell/model-month means of the **clipped convergence proxy**,
in 1/day. They omit the temperature gate and multiplication by column water.
They are not actual instantaneous gain or predicted changes in rain. In the
baseline Somali frozen-field proxy, nearest-edge extension is about 54% lower
and zero exterior divergence about 74% lower than reflection. These are
stress comparisons, not improvements or admissible boundary selections.

Nearest-edge extension changes the sign of smoothed divergence in 54/288
Somali baseline cell-months, 107/288 turning cell-months and 41/300 Saharan
cell-months. Zero exterior divergence changes signs in 0/288, 18/288 and
0/300, respectively. The full table retains signed divergence and positive
proxies for every cell/month and every extension. Sign changes are reported
without an outcome-tuned threshold.

## Checks and scope

An independent reviewer constructs normalized finite Gaussian kernels from
explicit exponential weights and maps each exterior index by hand. It uses
matrix multiplication for separable convolution, with no SciPy filtering
or boundary helper, and independently reconstructs centred divergence.
All **2,628 cell/month/extension filter values** pass, with maximum absolute
difference **2.55e-21/s** (rounded upward). Including support mass, raw
divergence and clipped proxies gives **7,884 independent scalar checks**.
All 876 unique cell-months are present; sources and prior qualifications
remain unchanged, and the scientific figure was inspected.

Filtering a domain of ones with zero exterior independently agrees with
the product of explicit one-dimensional in-domain kernel sums. Reflect and
nearest kernel rows each sum to one. These checks verify the weighting and
stress calculations, not atmospheric truth.

No new climate integration, physical source edit, cache change, score fit,
fine/sealed target access or atlas update occurred. Previous gate, import
and historical failed-transport findings remain intact. Monthly clipping
cannot reconstruct the mean of actual instantaneous clipped convergence.
The result is not a conservative vapor budget or observational attribution.

## Next physical check

Prioritize a bounded **padding-sensitivity experiment** with unchanged r58
physics, after W18c's active source/input freeze is resolved. Include Somalia,
Sahara and a previously exposed wet-monsoon protection case such as North
India; compare the same scored footprint at fixed 56 km spacing under a few
declared padding sizes. Require strict numerical certificates and unchanged
control reproduction, and retain every failure. Trace the actual gain and
water state so domain sensitivity can be distinguished from this frozen-field
proxy. A larger domain can also change pressure, heat, marine access and other
operators, so its rainfall response is not isolated convergence causality.

Do not select reflect/nearest/zero or a Gaussian scale by matching Somali
rain, and do not restart the already failed wholesale flux campaigns. If
larger-domain results fail to stabilize, report that uncertainty rather than
promoting the largest attempted domain as truth. Any candidate change needs
a separate physical declaration and all current validation gates. W18c
continues unchanged, r58 remains adopted, and the atlas is unchanged.

Artifacts: `output/convergence_boundary_audit_20261126/` contains the complete
table, provenance, independent review, qualification and `boundary_support.png`.

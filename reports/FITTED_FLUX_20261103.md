# Conservative fitted vapor transport: experimental numerical operator

The existing first-order upwind flux adds approximately |u| dx/2 of numerical
diffusion in each coordinate. At 56 km and 5 m/s this is about 140,000 m²/s,
compared with the specified vapor diffusivity of 60,000 m²/s. The extra term
can blur coastal and rain-shadow gradients and changes with resolution.
It is a numerical error, not a physical mixing coefficient to calibrate away.

An opt-in `moisture_flux_scheme="exponential"` now applies the conservative
Scharfetter–Gummel face solution. For each face with signed speed a, distance h
and physical diffusivity K, its flux is the upwind drift plus
`-Kfit (Wright-Wleft)/h`, where `Kfit=|a|h/expm1(|a|h/K)`.
The combined flux exactly balances `W=A+B exp(a x/K)` for constant coefficients;
Kfit alone is not a replacement estimate of physical diffusion. Both adjacent
cells use the same face flux. At zero wind it reduces to centered diffusion;
at zero diffusion it reduces to pure upwind transport. Nonnegative inputs
remain compatible with the existing monotone M-matrix solve.

The option affects vapor only. Heat retains its existing transport operator;
planet/orbit, modeled winds/SST and physical closures are unchanged. It requires
single-column flux form, zero separate positive-only convergence import, and
no independent or mass-weighted layers. Unsupported combinations fail before
grid construction. The residual observer and regional boundary ledger use the
same fitted operator as the solve; standalone Fickian diffusion would report
the wrong equation. All defaults retain their previous arithmetic.

Analytic tests cover both wind signs and two spacings; variable-flow tests
compare the matrix stencil with an independently assembled shared-face ledger,
including telescoping boundary exchange and coefficient signs. Limits, an
integrated strict seasonal moisture run, existing upwind/mass/layer operators,
and solver recovery are tested. The first two focused suites pass 64 and70
checks respectively. These numerical results do not establish better climate.

The existing global storm-family comparison and r43 atlas build run from their
own pinned sources and do not use this new option. A separate declared regional
screen will compare unchanged r43, conservative upwind flux and fitted flux on
the eight already-used development regions before any broader assessment.
No reserved observations, adoption or normal atlas publication follow from
this numerical implementation alone.


## Complete coupled climate screen

All three eight-region profiles finish with passing strict numerical checks;
the fresh default r43 control reproduces the original monthly fields within
the declared drift limits. Every raw packet is retained and pushed inb1691d33.

| Fixed operator | S8 / production r43 | T error change | Rain-loss change |
|---|---:|---:|---:|
| Conservative upwind vapor + storms |2.111305|+3.0939%|+219.1672%|
| Conservative fitted vapor + storms |2.186141|+2.8569%|+234.3714%|

Relative to conservative upwind flux itself, fitting worsens the combined
score2.2669% and rain loss4.7637%, while temperature MAE falls0.2299%.
The new stencil is not adopted. No reserved region is opened. Its analytic
conservation and exact constant-coefficient face solution remain valid, but
reducing numerical smearing does not repair the incompatible column circulation
or improve this coupled climate. This is a reused development screen, not a
new global score or a tuned conservative model.

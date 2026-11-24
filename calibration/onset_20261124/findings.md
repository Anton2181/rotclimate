# Southern-tropics wet-season onset (24 Nov 2026, r53) - cause found, fix open

Cause: e93's cap on heated-land convection poleward of the rain belt (convective_rh_gate 1.0, ramp from ITCZ -
onset_gap_deg). It stands for the Saharan dry layer aloft, but it also holds back the southern Amazon's spring
convection, which on Earth starts 1-2 months before the rain belt arrives.

Screens vs r53 (v5 pool), logs screen_gates.log, screen_e117.log:
| set | S61 [90 %] | notes |
| convective_rh_gate 0 | 1.0330 [0.996, 1.075], P +6 % | southern Amazon 0.72, south Brazil 0.74, central Amazon 0.79, Rondonia 0.81, Kalahari 0.90; Sahel, Sahara, Tripolitania, E Australia, N Queensland, Darfur 1.56-1.72 |
| convective_rh_chi0 0 | 1.0004 | the land-crossed-air gate is inactive here |
| e117 gate x chi_dry/0.2 | 1.0000 | Amazon unchanged; Sahel 1.13, E Australia 1.16 |
| e117 /0.35 | 1.0073 | |
| e117 /0.5 | 1.0128 | Sahel 1.49, E Australia 1.60 |

southern Amazon (t_10s_66w) rain, run months (real + 6):
  r53     0  0  0   8  50  94 100 139 146 126   9  0
  gate 0  6 13 17  59 154 147 133 142 145 139  42  7   (T Apr 32.1 -> 30.2, MAE 1.66 -> 1.35)
  e117    unchanged
  obs    23 37 84 139 196 229 265 247 230 160  92 36

e117 (scale the cap by the advected dry-land share chi_dry) is circular: the model's Amazon soil is dry because the
spring rain is missing, so its air counts as dry-land air and keeps the cap; the Sahel's wet-season soil opens it.
e117 stays in the code, default off.

Lead: a non-circular discriminator for the dry layer aloft - static geography (the size / poleward extent of the
land upwind under the subtropical descent: Sahara, Arabia, the Australian interior vs the Chaco-Amazon), or
the model's own subsidence field (descent_cap / the subsidence branch) rather than soil water.

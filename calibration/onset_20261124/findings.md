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

## e118 wind-direction gate (screen_e118.log) - no gain
Cap x clip(1 - poleward low-level wind (500 km smoothed) / v0, 0, 1):
| v0 1 m/s | 1.0177 [0.999, 1.040] | Sahel 1.75, Darfur 1.44, Mali 1.35 |
| v0 3 | 1.0137 | |
| v0 6 | 1.0071 | |
Southern Amazon rain, run months 4-5 (real Oct-Nov): r53 8 / 50, vw1 9 / 91 (gate off 59 / 154, obs 139 / 196).
The model's spring flow over the southern Amazon is not poleward in Sep-Oct (the opening only comes in Nov), while
the Sahel's wet-season monsoon inflow is, so the gate opens in the wrong place. e118 stays, default off.
Both soil- and wind-based discriminators fail; B6 PARKED. Remaining idea: a static, geography-only measure of the
desert upwind (the land area under the subtropical descent poleward of the cell), computed once per map.

## e119 poleward-desert gate (screen_e119.log, screen_e119b.log) - no adoption
Cap x clip(dry land (one-year soil) averaged 1,500 km poleward / pole0, 0, 1); with e117 on too, the larger of the two.
| pole0 0.3 | 1.0031 [0.988, 1.021] | |
| pole0 0.5 | 1.0028 [0.986, 1.023] | south Brazil 0.76, central Amazon 0.90; E Australia 1.71 |
| pole0 0.7 | 1.0057 | |
| pole0 0.5 + e117 0.35 (max) | 0.9983 [0.988, 1.011] | S49 0.996; E Australia 1.50 |
| pole0 0.5 + e117 0.6 (max) | 1.0005 | |
The Sahel / Darfur / Mali are protected (the Sahara lies poleward), but the southern Amazon still does not open:
the model's Chaco is dry too (the same southern-tropics deficit one step removed). Eastern Australia has the
Tasman Sea poleward and floods. The small gains (Japan, Korea, SE US, US Midwest 0.89-0.95) are mid-latitude summer
convection, not the target. Best 0.998 is noise; B6 stays PARKED. e117/e118/e119 in code, default off.

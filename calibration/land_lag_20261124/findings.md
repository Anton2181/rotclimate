# Seasonal phase diagnosis and land-lag tests (24 Nov 2026, policy v6, base = W7 finalist w1_049)

Diagnostic (scripts/phase_lag.py: amplitude-weighted annual-harmonic lag, sim vs obs, per region):
temperate +9 d (maritime NZ +35, British Isles +28, Patagonia +26, W Europe +21, S Chile +43),
continental +2, mediterranean +2, highland -4, arid -7.5, tropical regimes dominated by rain-onset errors.
Observed SST (WOA18) in place of the model sea leaves the maritime lag at +16 to +30 d: the lag sits in the
land/air response, not only in the sea.

| run | change | S97 [90 %] | notes |
|---|---|---|---|
| base w1_049 | - | 0.9872 [0.972, 1.002] | fails dev6 upper bound |
| lhc070 | land_heat_capacity 0.94 -> 0.7 | 0.9943 | all regimes ~4 d earlier; arid/highland/med worse |
| lhc050 | 0.5 | 1.0238 | |
| lhc035 | 0.35 | 1.0577 | 6-region maritime/inland test had shown T 2.01 -> 1.68: did not generalise |
| lhc070la88 | + land_amplitude 0.927 -> 0.881 | 0.9958 | |
| lhc050la83 | + land_amplitude 0.835 | 1.0274 | |
| e121 ph20 | land_phase_days +20 (shift by 0.5 - chi) | 1.0219 | continental 1.10, highland 1.14 |
| e121 ph40 | +40 | 1.0978 | |
| e121 phm20 | -20 | 1.0209 | |

Verdict: PARKED. A global heat capacity moves every regime the same way; the errors have opposite signs.
Shifting phase by the advected land share (e121, default 0) hurts continental and highland land in both
directions. The maritime lag needs a different discriminator (distance to an open, deep-mixed sea; winter
mixed-layer depth) or an explanation in the sea-air exchange; boreal autumn warmth (Siberia, Hudson Bay
5-9 C) looks like missing sea ice / bay ice and snow-cover timing.

# Moisture supply to deep continental interiors (24 Nov 2026, r53) - PARKED

The southern tropics' warm bias (+1.26 C mean at 5-20 S) is a rain / column-water deficit: southern Amazon
~750 mm/yr vs ~1,900, column water 28-32 mm in the wet season vs ~45-55 observed. Their sea (Atlantic) is beyond
the 1,100 km map pad, so their water enters through the land edge at land_edge_rh 0.5.

Screens vs r53 (v5 pool):
| set | S61 [90 %] | gains | losses |
| edge_inner 0.5 (e81) | 1.0101 [1.004, 1.017] | Tripolitania, Amazon | Mongolia 1.15, r_40n_94e 1.14, Volga, Kazakh |
| edge_inner 1.0 | 1.0670 | Amazon 0.79-0.88 | Kazakh 2.57, Mongolia 2.04, Volga 1.46 |
| land_edge_rh 0.65 | 1.0682 | t_10s_66w 0.75, Amazon 0.80, Congo 0.84, Anatolia 0.80 | Kazakh 1.90, r_40n_94e 1.80, Sahara 1.79 |
| e115 (e81 only on warm, wet inner ground) 20 C | 0.9985 [0.992, 1.004] | Amazon 0.87-0.91 | Tanzania, Zambia, Queensland 1.03-1.05 (dry-season rain back) |
| e115 23 C | 0.9998 | | |
| e115 17 C | 0.9993 | | |

e115 removes the steppe / desert damage but nets to noise: the warm-wet gate also re-wets the winter-side
tropical dry seasons that r53 dried. Not adoptable on the v5 gate. Code kept, default off.
Next structural option (owner decision, changes what calibration means): drive Earth regional cases with observed
lateral humidity (reanalysis precipitable water climatology) - the regional-climate-model convention - so the
interior physics is fitted without the edge artefact. The atlas world has no such data at its edges.

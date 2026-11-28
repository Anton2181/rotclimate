# W21 closed (2026-11-28)

Refit of e138 sst_zonal_obs with the five SST knobs tuned on the old too-cold baseline.
Wave 1 (25 pts): best = base (0.9926 vs r58). Wave 2 (12 pts, predicted gain 0.0077): best w2_001 0.9844.
Finalist by dev objective only: w2_001 (sst_zonal_obs 0.312, sst_offset -3.77, current_strength 5.64,
subpolar_current 6.38, sst_damping 0.561, inland_sea_warming 4.96).

dev6 paired vs r59 (output/ppe_20261127/ref59 = r59's own gate runs, wc3_12): S97 0.9974 [0.9887, 1.0063] -> FAIL (q95 > 1).
Wins: British Isles 0.85, s3_7n_10w 0.85, Gulf of Guinea 0.87, Alps 0.88, Tierra del Fuego 0.91.
Losses: tropical Brazil coast (t_2s_45w 1.40, s_0s_50w 1.34), Victoria 1.17, SW Australia 1.16, east Australia 1.10.
Reading: a uniform blend warms the tropics/subtropics, where the model SST was already right; the bias it fixes is subpolar.
Sealed BB stays UNOPENED. Next: latitude-gated blend (e138b).

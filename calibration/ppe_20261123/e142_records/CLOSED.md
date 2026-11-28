# e142 (tropics-only monsoon descent) — CLOSED, not adopted

- W23 wave 1 (25 pts, 4 knobs, base r61 + {md_tropics 0.8, lat0 20, lat1 25}).
- Best observed = w1_base: S 0.9892 [q05 0.9691, q95 1.0048].
- Emulator (LOO rmse 0.0007, corr 0.96) best proposal 0.9867: predicted gain 0.0025 < 0.005 -> no wave 2 (proposed once).
- Finalist w1_base dev6 vs r61: FAIL (q95 1.0048 >= 1; temperate 1.0054, tropical_dry 1.0036).
- Gains Sudan/Tibesti/Mali/Sahel; losses Mexico, Nicaragua, Najd, N India, Algeria — the drying is
  not region-selective enough. Next idea would need an obs-based selector (e.g. NCEP PW/omega ratio),
  not a latitude band. r61 remains current. No sealed set spent.

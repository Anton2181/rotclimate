# e150 observed land albedo (28 Nov 2026), vs r63

The model had no land-surface albedo apart from snow: every snow-free surface absorbed sunshine alike.
scripts/build_ncep_albedo.py: snow-free albedo = lowest monthly NCEP R1 uswrf/dswrf (months >= 80 W m-2), 2 deg.
Sahara 0.32, Arabia 0.32, Thar 0.29, Sahel 0.26, Ganges 0.22, Zambia 0.22, Kalahari 0.20-0.26, Amazon 0.16.
e150 land_albedo (K per unit albedo x sunshine / 480 W m-2, ref 0.2), screen_e150.log - FAIL alone:
| al10  10, ref 0.20 | S97 1.0156 [1.0072, 1.0241] |
| al20  20, ref 0.20 | S97 1.0413 | Tibesti box +1.81 -> +0.13 C, Libya u2_27n_23e +1.65 -> +0.40, Tibet +1.02 -> +0.03 |
| al20r 20, ref 0.22 | S97 1.0414 | but Algeria -0.47 -> -2.10, Najd -2.60 -> -3.98, interior Australia, Amazon warmer |
The physics is right for the warm eastern Sahara and Tibet, but 63 releases of fitted knobs compensate for the
missing albedo (the cold-biased bright deserts Algeria/Najd were tuned warm by dry heating/subsidence warming).
Albedo must enter a JOINT refit, not be added alone -> candidate for the r65 big recalibration (with tilt scaling).

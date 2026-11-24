# plan_W5 verdict (24 Nov 2026)

65 Sobol points (0 failed; resumed once after a container restart at 51/65) over 6 ITCZ knobs with e112 on
(itcz_mean mirrored for southern Earth regions), scored against r53.

- Base (r53 + e112 only): S 1.109, T +7.7 %, P +14.1 %, S49 1.020.
- Best evaluated w1_048: S 1.0245, P +4.2 %, S49 1.011 (itcz_mean_land -2.9, itcz_shift 19.2, itcz_shift_ocean 10.3,
  lag 38.6 d, itcz_mean 5.1, gate_lat 17.9). It wrecks the Sahel (t_13n_7w rain loss 0.22 -> 0.43, r_12n_22e
  0.26 -> 0.50) and the southern Amazon.
- Emulator LOO RMSE 0.0019 (r 0.998): it is reliable here, and its best predicted objective is 1.34. Every point
  in the box is worse than r53, so W5 closes after wave 1; the proposed wave 2 was dropped unrun.
- Sensitivity: itcz_mean_land 0.29, itcz_shift 0.25, circulation_lag_days 0.20.

Reading: with one land ITCZ for both hemispheres, the land mean that would let the southern rains end on time
(south of the equator) moves the Sahel's rains out of place. The model's southern tropical land is fitted
around the unmirrored mean (other knobs compensate). e112 stays in the code, default off; not adopted.
V18 stays UNOPENED. r53 remains adopted.

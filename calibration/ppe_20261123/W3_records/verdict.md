# plan_W3 verdict (23 Nov 2026)

65 Sobol points + one emulator wave of 16 (81 evaluations, 0 failures) over 10 knobs: dry heating (e54: strength,
chi0, warm_c), terrain-blocked eddy heat mixing (e100c: scale, offset) and five rebalancing knobs, base r52.
Emulator LOO rmse 0.0013, corr 0.996. Wave 1 best other than base: 1.0003; wave 2 predicted best 0.9978,
evaluated best w2_013 S61 0.9986 (T -0.0 %, P -0.2 %, S49 0.9991).

The best points all drive dry heating to near zero (0.05-0.14 of a 0-3 range) and e100c to weak blocking. Its
regional gains (Najd, Iran, north India, Deccan, Bengal) are cancelled by losses elsewhere (Namibia, Chile, the
Tarim / Central Asian basins). A 0.1 % gain cannot clear the v5 dev gate (bootstrap sd ~0.005): the search is CLOSED
early (2 of 4 waves). r52 stays adopted. Sealed U18 stays UNOPENED.

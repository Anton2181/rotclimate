# Separating rainfall transport mechanisms on r42

This is an eight-region development diagnosis, with no adopted change and no
unseen validation. The source plan, raw monthly cell packets and strict numerical
receipts are under `output/r42_conservative_replay_20261102`. At this snapshot,
the numerical control and two physical profiles are complete; both independent
reservoir profiles remain unscored. The figures and machine-readable review in
`output/r42_transport_review_20261102` retain those pending outcomes explicitly.

| Complete profile | Temperature ratio | Rain-loss ratio | Combined ratio |
| --- | ---: | ---: | ---: |
| r42 with damped numerical control | 1.0000 | 1.0000 | 1.0000 |
| Conservative vapor flux and symmetric storms | 1.0213 | 3.2075 | 2.1144 |
| Plus dry-mass-balanced counterflow | 1.0019 | 1.9105 | 1.4562 |

Ratios use equal-region means over the same eight complete footprints. These
substantial aggregate regressions are not evidence that conservation is wrong;
the tested changes alter the circulation and unresolved transport closures
without retuning their inherited strengths. Conversely, local conservation
certificates alone do not establish realistic circulation or rainfall.

The first change raises California's footprint-mean annual rain from about
502 to 2,609 mm, against 392 observed. Counterflow lowers that to 1,375 mm.
It raises North India's monsoon, but the counterflow also removes much of that
gain. Tripolitania's false summer rainy season becomes stronger. The regional
figures show why a change to annual rain alone cannot solve the seasonal errors.

## Next prospective operator comparison

The combined flux profile changes two operators together. Before drawing a
mechanism conclusion, `calibration/r42_storm_factorial_20261102` declares:

1. Conservative mean-wind vapor flux with the original storm scheme.
2. Symmetric conservative storm exchange with original concentration transport.
3. Symmetric storm hops with local condensate retained and counted as rainfall.
4. Conservative vapor flux plus that accounted storm condensation.

The first two, with the existing control and completed joint change, separate
the operators and their interaction. The latter two test an additional physical
closure. **R42 has `eddy_rainout=0`**; the new condensation profiles explicitly
set it to 1, corresponding to the local crest-saturation capacity. They do not
pretend that condensation was already active in the baseline. No strength is
selected from the new results. Earlier accounted-condensation work under r31
is historical development evidence, not independent confirmation on r42.

All four parameter sets construct with the same Earth planet and model-generated
winds/SST. They retain the verified damped solver control, work cap and strict
residual checks. The maximum is 32 new regional integrations. This follow-up is
queued behind completion of the original screen, so its existing failures and
remaining reservoir outcomes cannot disappear. Every outcome is retained and
only a complete matched profile receives an aggregate score.

Neither experiment can adopt physics or replace atlas fields. A useful closure
would still need full 49-region calibration, paired finer-grid checks, independent
wind/SST assessment and a prospectively fixed unseen evaluation.

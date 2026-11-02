from scripts.run_calibration_portfolio import select_finalist


def row(chain=1, n=1, S=.99, **fields):
    return dict(chain=chain, n=n, S=S, T_relative=-.01, P_relative=-.01, **fields)


def test_finalist_uses_overall_score_and_deterministic_ties():
    a = row(chain=2, S=.98, groups={'holdout': 1.2})
    b = row(chain=1, S=.99)
    assert select_finalist([b, a]) == a
    assert select_finalist([a, row(chain=1, S=.98)])['chain'] == 1


def test_failures_controls_small_gains_and_individual_metric_regressions_cannot_win():
    invalid = [row(n=0, S=.9), row(S=.996), row(S=.8, failed=['region']),
               {**row(S=.9), 'T_relative': .011}, {**row(S=.9), 'P_relative': .011}]
    assert select_finalist(invalid) is None
    valid = row(S=.994)
    assert select_finalist(invalid + [valid]) == valid

from scripts.continue_climate_work import matches,process_start


def test_only_the_actual_driver_with_its_exact_plan_matches():
    args=['/repo/.venv/bin/python','-u','-I','scripts/run_atlas_snapshot.py','--plan','calibration/plan.json']
    assert matches(args,'run_atlas_snapshot.py','calibration/plan.json')
    assert not matches(args+['--train-only'],'run_atlas_snapshot.py','calibration/plan.json')
    assert not matches(args,'run_atlas_snapshot.py','calibration/another.json')
    assert not matches(['/bin/bash','-c',' '.join(args)],'run_atlas_snapshot.py','calibration/plan.json')


def test_pid_identity_uses_start_time_after_the_complete_process_name():
    # Fields 3..22, after a name containing spaces and a right parenthesis.
    assert process_start('123 (python (worker) x) '+' '.join(str(i) for i in range(3,23)))=='22'

from dataclasses import asdict

from scripts.validate_mediterranean import finalists,jobs_for,comparison


def test_new_worlds_only_change_surroundings_seed_and_remain_paired():
    profiles=finalists()
    assert all(p.t_require_convergence and p.t_adaptive_retries==2 for p in profiles.values())
    jobs=jobs_for(profiles,[301,302])
    assert len(jobs)==4
    assert [s for _,s,_ in jobs]==[301,301,302,302]
    for name,seed,p in jobs:
        changed={k for k,v in asdict(p).items() if v!=asdict(profiles[name])[k]}
        assert changed=={'beyond_seed'}
        assert p.beyond_seed==seed and p.moisture_require_convergence


def test_incomplete_pair_does_not_create_an_unpaired_candidate_gap():
    profiles=finalists();jobs=jobs_for(profiles,[301,302])
    a=dict(accuracy=.5,mediterranean=dict(dry_share=.1,cs_share=.4),zone_recall=dict(cold_dry=.68))
    b=dict(accuracy=.49,mediterranean=dict(dry_share=.02,cs_share=.5),zone_recall=dict(cold_dry=.48))
    rows={('strong_seasonal',301):a,('focused_seasonal',302):b}
    assert comparison(rows,jobs)['paired']==[]
    rows['focused_seasonal',301]=b
    report=comparison(rows,jobs)
    assert len(report['paired'])==1 and report['completed']==3
    assert abs(report['paired'][0]['focused_minus_strong_cold_dry']+.2)<1e-12

"""Run the independent audit on the protocol-period replay and isolate its cause."""
import json
from pathlib import Path

import numpy as np
import review_urban_seasonal_transfer as R


def main():
    root=R.OUT;qualified=root/'wind_1981'
    wind=R.read(qualified/'wind_restoration.json')
    for source in wind['sources'].values():
        assert R.sha(R.ROOT/source['path'])==source['sha256']
        assert '1981/01/01 - 2010/12/31' in source['period']
    assert wind['producer_sha256']==R.sha(R.ROOT/'scripts/replay_urban_transfer_1981.py')
    equal_fields=0;route_changes={}
    for name in ['control','greece','greece_and_asia_minor','greece_hansen_150']:
        old=dict(np.load(root/'prepared'/f'greek_{name}.npz'))
        new=dict(np.load(qualified/'prepared'/f'greek_{name}.npz'))
        assert old.keys()==new.keys()
        for key in old:
            if key in ['dist','owner','between']:continue
            np.testing.assert_array_equal(old[key],new[key]);equal_fields+=1
        if name=='greece':
            route_changes={key:int((old[key]!=new[key]).sum()) for key in ['dist','owner','between']}
            assert all(n>0 for n in route_changes.values())
    R.OUT=qualified;R.main()
    readiness=R.read(qualified/'readiness.json')
    assert readiness['annual_archived_result_bytes_exact'] and readiness['annual_cases']==6
    receipt=dict(status='passed_exact_annual_controls_and_independent_primary_flow_audit',
                 reviewer_sha256=R.sha(Path(__file__)),base_reviewer_sha256=R.sha(R.ROOT/'scripts/review_urban_seasonal_transfer.py'),
                 readiness_sha256=R.sha(qualified/'readiness.json'),wind_restoration_sha256=R.sha(qualified/'wind_restoration.json'),
                 identical_nonroute_arrays_across_periods=equal_fields,
                 different_greece_route_array_entries=route_changes,
                 annual_cases=6,independent_primary_flow_settings=100,
                 diagnosis='Only the wind-period input changes the four captured cases: all nonroute arrays are exact. The1981–2010 product named in the protocol restores the full archived outputs.',
                 seasonal_trial_ready=False,new_fit=False,new_validation_claim=False,adopt=False)
    (qualified/'review.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['status'],flush=True)


if __name__=='__main__':main()

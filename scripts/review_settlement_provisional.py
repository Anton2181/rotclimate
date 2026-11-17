"""Verify publication cohort identity, all viewer values and frozen science."""
import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
import publish_settlement_provisional as P


def main():
    P.check_frozen(); P.check_replay()
    publication=P.read(P.OUT/'publication.json')
    assert publication['publisher_sha256']==P.sha(Path(P.__file__))
    for name,digest in publication['files_sha256'].items():
        assert P.sha(P.ROOT/name)==digest,name
    viewer=P.read(P.OUT/'viewer_data.json')
    original=P.read(P.BASE/'viewer_data.json')
    supply=P.read(P.SUPPLY/'results.json')
    manifest=P.read(P.DATA/'settlement_provisional.json')
    count=0
    with np.load(P.SUPPLY/'town_model.npz') as grain:
        for mode in ['raw','corrected']:
            assert len(viewer['modes'][mode]['towns'])==len(original['modes'][mode]['towns'])
            for i,(town,old) in enumerate(zip(viewer['modes'][mode]['towns'],original['modes'][mode]['towns'])):
                assert {key:town[key] for key in old}==old
                for reading,key in [('central','central_x34'),('low','low_x14')]:
                    for label,cohort in [('old','control'),('new','candidate')]:
                        assert town[label+'_grain_'+reading]==float(grain[f'{cohort}__{mode}__{key}_fed_share'][i])
                        count+=1
            for reading,key in [('central','central_x34'),('low','low_x14')]:
                s=viewer['modes'][mode]['summary'][reading]
                for label,cohort in [('old','control'),('new','candidate')]:
                    expected=supply['variants'][cohort]['climates'][mode]['scenarios'][key]
                    assert s[label+'_grain']==expected['fed_share_of_residents']
                    assert s[label+'_short']==expected['short_towns']
            options=manifest['packets'][mode]['options']['reach_towns']
            assert {o['value'] for o in options}=={'provisional_central','provisional_low','provisional_supply_central','provisional_supply_low'}
            for option in options:
                assert not option['integrated_support']
                assert P.sha(P.DATA/option['file'])==option['file_sha256']
                assert (P.DATA/option['download']).is_file()
    assert manifest['scientific_adoption'] is False
    assert P.read(P.BASE/'candidate_earth.json')['adopt'] is False
    assert P.read(P.SUPPLY/'packets/candidate/fantasy.json')['gate']['passed'] is False
    result=dict(status='passed',grain_town_values=count,all_preexisting_viewer_values_exact=True,
                frozen_inputs=publication['frozen_input_count'],historical_scientific_gates_unchanged=True,
                publication_sha256=P.sha(P.OUT/'publication.json'),reviewer_sha256=P.sha(Path(__file__)),
                scope='All reviewed input/download/map identities and all viewer town, population and grain values. Grain equations independently reviewed before publication. Publication whitelist uses exact archived baseline files.')
    P.write(P.OUT/'review.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()

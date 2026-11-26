"""Qualify a fresh paired r58 reference without asserting historical exactness."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash, write_json


def main():
    out=ROOT/'output/climate_runtime_20261126'
    ref=ROOT/'output/ppe_20261126/ref58'
    old=ref/'restoration_review.json'
    assert old.exists(), 'Wait for the full historical comparison'
    historical=json.loads(old.read_text())
    for n,h in historical['sources_sha256'].items():assert file_hash(ROOT/n)==h,n
    restoration=out/'restoration.json';r=json.loads(restoration.read_text())
    assert file_hash(ROOT/'scripts/restore_climate_inputs.py')==r['producer_sha256']
    for n,h in r['cache_sha256'].items():assert file_hash(ROOT/n)==h,n
    archives=json.loads((ROOT/'output/climate_restore_20261120/trial/protocol.json').read_text())['sources']
    for row in r['sources']:
        assert file_hash(ROOT/row['path'])==row['sha256']
        if 'worldclim' in row['path']:assert archives[row['path']]==row['sha256']
    params=ROOT/'calibration/local_accuracy_20261023/r58_params.json'
    adoption=json.loads((params.parent/'r58_adoption.json').read_text())
    assert file_hash(params)==adoption['params_sha256']
    protocols={};regions={};expected_sources=None
    for folder in sorted(ref.glob('r58_*')):
        protocol=json.loads((folder/'protocol.json').read_text())
        if expected_sources is None:expected_sources=protocol['sources']
        assert protocol['sources']==expected_sources
        for n,h in protocol['sources'].items():assert file_hash(ROOT/n)==h,n
        assert protocol['params']==json.loads(params.read_text())
        summary=json.loads((folder/'summary.json').read_text());assert summary['complete']
        protocols[str(folder.relative_to(ROOT))]=file_hash(folder/'protocol.json')
        for name,row in summary['regions'].items():
            assert name not in regions and row['status']=='passed' and row['numerics']['all_checks_passed']
            regions[name]=row
    archived=ROOT/'calibration/ppe_20261123/W18_records/results.jsonl'
    expected=next(json.loads(s)['regions'] for s in archived.read_text().splitlines() if json.loads(s).get('ok'))
    assert set(regions)==set(expected) and len(regions)==97
    control=out/'r58_california_repeat'
    repeat=json.loads((control/'cases/california.json').read_text());reference=regions['california']
    assert repeat['case_identity']==reference['case_identity']
    with np.load(control/'cells/california.npz') as a,np.load(ref/'r58_dev31/cells/california.npz') as b:
        assert set(a.files)==set(b.files)
        for k in a.files:np.testing.assert_array_equal(a[k],b[k])
    for k in ['temperature','rain','numerics']:assert repeat[k]==reference[k],k
    amendment=ROOT/'calibration/ppe_20261123/W18c_runtime_amendment.json'
    producers=[Path(__file__),amendment,params,old,restoration,archived,
               ROOT/'scripts/local_benchmark_protocol.py',ROOT/'scripts/restore_r58_reference.py']
    deltas=historical['comparisons']
    write_json(out/'qualification.json',dict(status='passed_fresh_paired_r58_reference_historical_replay_not_exact',
        sources_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in producers},reference_protocols_sha256=protocols,
        shared_inputs_sha256=r['cache_sha256'],reference_regions=97,strict_numeric_certificates=97,
        raw_WorldClim_archives_exact=4,same_runtime_repeat_arrays_exact=True,
        historical_score_replay_exact=historical['passed'],historical_score_replay_overridden=False,
        historical_temperature_mean_abs_delta=float(np.mean([x['temperature_abs_delta'] for x in deltas])),
        historical_rain_loss_mean_abs_delta=float(np.mean([x['rain_loss_abs_delta'] for x in deltas])),
        candidate_runs_performed=0,sealed_AA_opened=False,adoption_gates_changed=False,atlas_changed=False))
    print('Fresh97-region paired r58 baseline qualified; non-exact historical comparison retained.')


if __name__=='__main__':main()

"""Replay actual CMA proposals from the declared seeds, without climate solves."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from report_joint_ocean_land_refit import CAMPAIGN,SOURCE,summarize


def main():
    import cma
    import numpy as np
    snapshot=summarize();campaign=json.loads(CAMPAIGN.read_text());checks={}
    for name,chain in snapshot['starts'].items():
        plan=json.loads((ROOT/campaign['starts'][name]).read_text())
        base=json.loads((ROOT/plan['start']).read_text())
        bounds=plan['knobs'];lo=np.array([p[1] for p in bounds]);hi=np.array([p[2] for p in bounds])
        center=np.array([(base[k]-l)/(h-l) for k,l,h in bounds])
        es=cma.CMAEvolutionStrategy(center,plan['sigma'],dict(bounds=[0,1],popsize=plan['popsize'],
            seed=plan['seed'],verbose=-9))
        rows=chain['records'];maximum=0.;verified=0;generations=0
        for start in range(1,len(rows),plan['popsize']):
            proposals=es.ask();completed=rows[start:start+plan['popsize']]
            expected=lo+np.clip(np.asarray(proposals[:len(completed)]),0,1)*(hi-lo)
            actual=np.array([[r['knobs'][k] for k,l,h in bounds] for r in completed])
            delta=float(np.max(np.abs(expected-actual)));maximum=max(maximum,delta)
            if delta>1e-12:raise ValueError('Seeded population does not replay: '+name)
            verified+=len(completed)
            if len(completed)==plan['popsize']:
                es.tell(proposals,[r['cost'] for r in completed]);generations+=1
        checks[name]=dict(proposals_verified=verified,complete_generations=generations,
            maximum_parameter_difference=maximum,seed=plan['seed'],records_sha256=chain['records_sha256'])
    result=dict(status='passed',search_status=snapshot['status'],starts=checks,
        campaign_sha256=file_hash(CAMPAIGN),
        scope='Numerical reproducibility of actual proposal streams only; no new climate evaluation, fit or global-optimum claim.')
    write_json(SOURCE/'sampling_replay.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

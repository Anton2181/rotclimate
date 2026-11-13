"""Audit the water-routing primitive using node balances and complementarity.

Synthetic inputs only. No observed irrigation area, crop yield or population
is scored and no irrigation field rule is selected by this audit.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from harvest.flood_water import route_water_budget
OUT=ROOT/'output/flood_water_budget_20261113'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    controls=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_flood_timing.py','tests/test_flood_gauge_quality.py','tests/test_flood_water.py'],cwd=ROOT,text=True,capture_output=True,check=True)
    assert '37 passed' in controls.stdout
    protected=json.loads((ROOT/'output/flood_basin_seasonality_20261113/results.json').read_text())['unchanged_atlas_sha256']
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    rng=np.random.default_rng(20261113);nodes=0;monthly_nodes=0;digest=hashlib.sha256()
    for case in range(200):
        n=int(rng.integers(1,65));receiver=np.array([-1]+[int(rng.integers(-1,c)) for c in range(1,n)])
        order=np.arange(n);source=rng.uniform(0,1000,(12,n));demand=rng.uniform(0,900,(12,n));eff=rng.uniform(.2,1,n)
        r=route_water_budget(source,demand,order,receiver,efficiency=eff)
        # Independently reconstruct incidence balances from returned edge fluxes.
        # No recreation of the producer's greedy traversal or withdrawal formula.
        incoming=np.zeros_like(source)
        for c,parent in enumerate(receiver):
            if parent>=0:incoming[:,parent]+=r['downstream_m3'][:,c]
        np.testing.assert_allclose(r['available_m3'],source+incoming,rtol=2e-14,atol=1e-10)
        np.testing.assert_allclose(source+incoming,r['downstream_m3']+r['delivered_m3']+r['delivery_loss_m3'],rtol=2e-14,atol=1e-10)
        np.testing.assert_allclose(r['delivered_m3']+r['delivery_loss_m3'],r['delivered_m3']/eff[None,:],rtol=2e-14,atol=1e-10)
        np.testing.assert_allclose(r['unmet_m3'],demand-r['delivered_m3'],rtol=2e-14,atol=1e-10)
        assert np.max(np.minimum(r['unmet_m3'],r['downstream_m3']))<1e-10,'Unmet local demand while water passes unused'
        outlet=receiver<0
        np.testing.assert_array_equal(r['outlet_m3'][:,outlet],r['downstream_m3'][:,outlet])
        assert not r['outlet_m3'][:,~outlet].any()
        np.testing.assert_allclose(source.sum(1),(r['delivered_m3']+r['delivery_loss_m3']+r['outlet_m3']).sum(1),rtol=2e-14,atol=1e-10)
        fresh=route_water_budget(source,demand,order,receiver,efficiency=eff)
        for name,value in r.items():
            assert np.isfinite(value).all() and np.all(value>=0)
            np.testing.assert_array_equal(fresh[name],value);digest.update(value.tobytes())
        nodes+=n;monthly_nodes+=12*n
    paths=[Path(__file__),ROOT/'harvest/flood_water.py',ROOT/'tests/test_flood_water.py']
    result=dict(status='passed',scope='synthetic_water_routing_accounting_only',producers={str(p.relative_to(ROOT)):sha(p) for p in paths},controls_output=controls.stdout,
        random_forests=200,nodes=nodes,monthly_node_balances=monthly_nodes,numeric_repeat_sha256=digest.hexdigest(),
        checks=['independent edge incidence balances','useful delivery plus paid loss','demand complementarity','separate outlet accounting','global monthly conservation','exact repeated numeric outputs'],
        unchanged_earth_atlas_files=len(protected),irrigation_area_or_harvest_computed=False,default_adoption=False,
        limitations='Monthly instantaneous routing, upstream-first demands, no storage, return flow, flood access or crop-calendar selection; no empirical efficiency fitted.')
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'review.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Passed:37 controls,200 synthetic forests,',monthly_nodes,'monthly node balances; Earth atlas unchanged')


if __name__=='__main__':main()

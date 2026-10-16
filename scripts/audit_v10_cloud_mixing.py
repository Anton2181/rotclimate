"""Saved winter-stage diagnostics and a tiny mixing counterexample; no climate year."""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scripts import check_v10_cloud_mixing as run
from rotclimate_v10.earth import atomic_json


def analyse():
    p=run.SOURCE;state=json.loads((p/'state.json').read_text());winter=[10,11,0,1,2,3];rows={}
    for region in ('california','iberia'):
        for name in ('lift1_steady','lift16_aligned'):
            key='reference_'+region+'_'+name;folder=p/'cases'/key
            run.previous.verify_completed(folder,state['cases'][key])
            with np.load(folder/'year1.npz',allow_pickle=False) as a:
                rain=a['trace_actual_layer_rain_cell_mm'];opp=a['trace_stage_condensation_cell_mm']
                removed=a['trace_relaxation_removed_opportunity_cell_mm'];added=a['trace_relaxation_added_opportunity_cell_mm']
                h=a['trace_joint_time_cell_seconds'][winter,2].sum(0)
            rising=h[:,5:,:].sum((1,2));moist=h[:,5:,4:].sum((1,2))
            rows[key]={'winter_upward_recipient_RH90_fraction':np.divide(moist,rising,out=np.zeros(4),where=rising>0).tolist(),
                'winter_net_relaxation_opportunity_change_over_realized_rain':float((removed[winter,2]-added[winter,2]).sum()/rain[winter,2].sum()),
                'winter_opportunity_before_over_after':float(opp[winter,2,0].sum()/opp[winter,2,1].sum()),
                'caution':'Time-weighted receiver humidity conditional on upward exchange >=.01Pa/s, not observed parcel omega. Condensation opportunities on one realized trajectory may recount vapor; their ratio is not rainfall from disabling heating.'}
    b=run.model.base;unit=np.ones((1,1));z=np.zeros((1,1));p0=100000.;p1=np.full((1,1),80000.)
    t0=20.;q0=.7*b.saturation(np.array([[t0]]),np.full((1,1),p0))
    dry=(t0+273.15)*(p1/p0)**(287.05/b.CP)-273.15
    env=10.;qe=.2*b.saturation(np.full((1,1),env),p1)
    energy=lambda t,q:b.CP*(t+273.15)+b.LV*q
    _,parcel,_=b.adjust(q0,energy(dry,q0),unit,z,p1)
    mixq=.2*q0+.8*qe;mixT=.2*dry+.8*env
    _,mixed,_=b.adjust(mixq,energy(mixT,mixq),unit,z,p1)
    counterexample={'donor_temperature_c':t0,'donor_RH':.7,'source_pressure_pa':p0,'recipient_pressure_pa':80000.,
        'parcel_fraction':.2,'environment_temperature_c':env,'environment_RH':.2,'lifted_dry_temperature_c':float(dry.item()),
        'separate_weighted_condensate_g_per_kg_mixture':float(.2*parcel.item()*1000),
        'mixed_RH':float((mixq/b.saturation(mixT,p1)).item()),'mixed_condensate_g_per_kg_mixture':float(mixed.item()*1000),
        'caution':'Constructed two-population limit, not real regional cloud validation. Same liquid latent-heat convention as parent.'}
    preflight=json.loads((run.PREFLIGHT/'manifest.json').read_text())
    if preflight['protocol']['code_sha256']!=run.source_id():raise ValueError('Cloud preflight sources changed.')
    return {'winter_replay_analysis':rows,'manufactured_mixing_counterexample':counterexample,
        'regional_probe_evidence':preflight['checks'],'preflight_source_sha256':preflight['protocol']['code_sha256'],
        'new_real_annual_integrations_started':0,'atlas_updated':False}


def main():
    result=analyse();out=ROOT/'output/v10_cloud_mixing_audit';atomic_json(out/'audit.json',result)
    example=result['manufactured_mixing_counterexample']
    lines=['# Cloud-mixing audit, 16 October 2026','',
        'Saved evidence and tiny independent probes only. No real annual integration launched; atlas unchanged.','',
        '| Saved reference case | Net heating-stage opportunity difference / realized winter rain | Humid upward receiver fraction, lower three interfaces |',
        '|---|---:|---|']
    for key,r in result['winter_replay_analysis'].items():
        humid=', '.join(f'{v:.1%}' for v in r['winter_upward_recipient_RH90_fraction'][:3])
        lines.append(f'| {key} | {r["winter_net_relaxation_opportunity_change_over_realized_rain"]:.1%} | {humid} |')
    lines+=['', 'Opportunity differences follow the realized state sequence; they can recount vapor and are not the rainfall of a different climate. They do not prove heating is unimportant after climate feedbacks.', '',
        f'A constructed 70%-RH parcel at 20°C rising from 1000 to 800hPa condenses. With a 20% parcel fraction, separately adjusted condensate is {example["separate_weighted_condensate_g_per_kg_mixture"]:.3f} g/kg mixture. Mixing first with dry environmental air gives {example["mixed_RH"]:.1%} bulk RH and zero condensate. This demonstrates sensitivity to unresolved variability, not regional skill.', '',
        'The 24 independent Jan-1 regional steps reproduce the bulk operator exactly and preserve water/energy under the parcel bound. Their increased per-probe rainfall cannot be extrapolated to annual totals.', '',
        'Primary context: [ECMWF cloud-cover lecture](https://www.ecmwf.int/sites/default/files/elibrary/2005/16958-parametrization-cloud-cover.pdf) explains why subgrid humidity/temperature variability can form cloud below grid-average saturation. It does not validate this prototype or immediate rain fallout.', '',
        'Next: [staged cloud-mixing experiment](../../reports/v10_cloud_mixing.md).']
    (out/'audit.md').write_text('\n'.join(lines)+'\n');print('Saved audit: '+str(out/'audit.md'))


if __name__=='__main__':main()

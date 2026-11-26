"""Rank the fresh r58 development errors; weak seasonal cycles have no phase claim."""
import csv
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json


def main():
    out=ROOT/'output/climate_runtime_20261126';ref=ROOT/'output/ppe_20261126/ref58'
    qualification=out/'qualification.json';q=json.loads(qualification.read_text())
    assert q['reference_regions']==97 and q['same_runtime_repeat_arrays_exact']
    regimes=json.loads((ROOT/'calibration/regimes_20261124/regimes_v2.json').read_text())['regimes']
    rows=[];sources={str(qualification.relative_to(ROOT)):file_hash(qualification)}
    phase=np.exp(-2j*np.pi*np.arange(12)/12)
    for part in sorted(q['reference_protocols_sha256']):
        folder=ROOT/part;summary=folder/'summary.json';sources[str(summary.relative_to(ROOT))]=file_hash(summary)
        for name,record in json.loads(summary.read_text())['regions'].items():
            path=folder/'cells'/f'{name}.npz';assert file_hash(path)==record['cells_sha256']
            with np.load(path) as z:Ts,To,Ps,Po=[z[k].astype(float) for k in ['Ts','To','Ps','Po']]
            sim=(Ts*phase[:,None]).sum(0);obs=(To*phase[:,None]).sum(0);amp=np.abs(obs)
            lag=None
            if amp.mean()/6>=2:
                valid=amp>1e-10
                angle=np.angle(np.sum(np.exp(1j*(np.angle(sim[valid])-np.angle(obs[valid])))*amp[valid]))
                lag=float(-angle*365/(2*np.pi))
            rain_sim=float(Ps.sum(0).mean());rain_obs=float(Po.sum(0).mean())
            rows.append(dict(region=name,regime=regimes[name],scored_cells=record['cells'],
                temperature_monthly_mae_C=record['temperature']['monthly_mae_C'],
                annual_temperature_bias_C=record['temperature']['annual_bias_C'],
                seasonal_range_error_C=record['temperature']['range_error_C'],
                seasonal_phase_lag_days=lag,observed_harmonic_amplitude_C=float(amp.mean()/6),
                rain_loss=record['rain']['loss'],annual_rain_sim_mm=rain_sim,annual_rain_obs_mm=rain_obs,
                annual_rain_ratio=rain_sim/rain_obs if rain_obs>0 else None))
    assert len(rows)==97
    t=np.mean([r['temperature_monthly_mae_C'] for r in rows]);p=np.mean([r['rain_loss'] for r in rows])
    for r in rows:
        r['temperature_score_burden_percent']=50*r['temperature_monthly_mae_C']/t/len(rows)
        r['rain_score_burden_percent']=50*r['rain_loss']/p/len(rows)
        r['total_score_burden_percent']=r['temperature_score_burden_percent']+r['rain_score_burden_percent']
    rows.sort(key=lambda r:-r['total_score_burden_percent'])
    with (out/'error_inventory.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    sources[str(Path(__file__).relative_to(ROOT))]=file_hash(Path(__file__))
    sources['calibration/regimes_20261124/regimes_v2.json']=file_hash(ROOT/'calibration/regimes_20261124/regimes_v2.json')
    write_json(out/'error_inventory.json',dict(status='descriptive_fresh_r58_development_inventory',
        source_sha256=sources,regions=97,mean_monthly_temperature_mae_C=float(t),mean_rain_loss=float(p),
        source_table_sha256=file_hash(out/'error_inventory.csv'),leaders=rows[:15],
        phase_note='Positive=simulation lags observations. Circular observed-amplitude-weighted phase; omitted when observed mean harmonic amplitude<2C. Southern run calendars are mirrored.',
        burden_note='Each region contributes equally to the policy objective; burdens sum to100%. These are error shares, not causal parameter importance or independent validation.',
        new_fit=False,sealed_AA_opened=False))
    for r in rows[:12]:
        print(f"{r['region']:22s} burden {r['total_score_burden_percent']:.2f}% T {r['temperature_monthly_mae_C']:.2f}C bias {r['annual_temperature_bias_C']:+.2f}C rain ratio {r['annual_rain_ratio']:.2f}")


if __name__=='__main__':main()

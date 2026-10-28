"""Exploratory archived seasonal water evidence; no new fit or model run."""
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from local_benchmark_protocol import file_hash,identity,write_json
from audit_column_drying import check_source_closure


def diagnose(source,target):
    protocol=json.loads((source/'protocol.json').read_text());review=json.loads((source/'review.json').read_text())
    verification=json.loads((source/'scientific_verification.json').read_text())
    if (not review['complete'] or review['identity']!=identity(protocol) or verification['status']!='passed'
            or verification['review_sha256']!=file_hash(source/'review.json')):raise ValueError('Need completed verified source')
    valid={n:s for n,s in review['scores'].items() if s.get('physical_admissible')}
    selected=dict(retained_legacy='global01',best_mean_rain=min(valid,key=lambda n:(valid[n]['mean_rain_ratio'],n)),
                  best_objective=min(valid,key=lambda n:(valid[n]['objective'],n)))
    names=list(dict.fromkeys(selected.values()));regions=['north_india','mexico','pacific_nw']
    result={};hashes={}
    for region in regions:
        result[region]={}
        for name in names:
            path=source/name/(region+'.json');row=json.loads(path.read_text());raw=path.with_suffix('.npz')
            if row['status']!='passed' or file_hash(raw)!=row['arrays_sha256']:raise ValueError('Changed source climate')
            hashes[name+'/'+region]=dict(row_sha256=file_hash(path),arrays_sha256=file_hash(raw))
            with np.load(raw,allow_pickle=False) as z:
                fields={k:z[k] for k in z.files};mask=fields['valid']
                if int(mask.sum())!=row['rain']['scored_land_cells']:raise ValueError('Diagnostic crop differs from full scoring mask')
                closure=check_source_closure(fields,mask)
                monthly={k:np.asarray(fields[k],float)[:,mask].mean(1) for k in ['simulated','observed','evaporation','advection','diffusion','storm_exchange','column_drying','convergence_import']}
            seasons={}
            for season,months in [('annual',np.arange(12)),('JJA',np.array([5,6,7])),('SON',np.array([8,9,10])),('wet_half',np.array([9,10,11,0,1,2]))]:
                seasons[season]={k:float(v[months].sum()) for k,v in monthly.items()}
            report=row.get('extra_circulation') if region=='pacific_nw' else row.get('circulation')
            group='ocean' if region=='pacific_nw' else 'land'
            native=report['humidity']['scores'][group] if report else None
            result[region][name]=dict(full_scored_land_cells=int(mask.sum()),seasons=seasons,
                observed_peak_month=int(np.argmax(monthly['observed']))+1,simulated_peak_month=int(np.argmax(monthly['simulated']))+1,
                monthly={k:v.tolist() for k,v in monthly.items()},closure=closure,native_humidity_separate_footprint=native)
    if target.exists():raise ValueError('Preserve the earlier exploratory diagnostic')
    target.parent.mkdir(parents=True,exist_ok=True)
    meta=dict(status='passed_exploratory_diagnostic',selected=selected,regions=result,source_records=hashes,
        source_protocol_sha256=file_hash(source/'protocol.json'),source_review_sha256=file_hash(source/'review.json'),
        script_sha256=file_hash(Path(__file__)),helper_sha256=file_hash(ROOT/'scripts/audit_column_drying.py'),
        new_earth_integrations=0,new_fit=False,physics_or_atlas_adoption=False,
        limitations=['Three northern full-score crops; equal model-month water totals. No East Australia crop/calendar ambiguity.',
            'Native humidity samples and scored land rain masks differ; no rain/PW efficiency ratio or observed closed water budget is inferred.',
            'Signed modeled terms are equation balances, not independent causal shares. Observed evaporation and exact submonthly vapor covariance are unavailable.',
            'Actual branch winds and donor fluxes were not saved by this archive. Monthly column means cannot reconstruct their instantaneous transport.',
            'Exploratory case diagnosis, not a new acceptance rule or independent validation. All old outcomes remain unchanged.'])
    write_json(target,meta)
    print(json.dumps({region:{n:{k:round(v,1) for k,v in r['seasons']['JJA'].items()} for n,r in profiles.items()} for region,profiles in result.items()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();diagnose(args.source.resolve(),args.out.resolve())

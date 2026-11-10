"""Publish the integrated implementation's equivalence and limited timing evidence."""
import hashlib
import inspect
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from organize_climate_accuracy import organize
from rotclimate import moisture


def main():
    pilot=ROOT/'output/moisture_mix_reuse_20261110'
    expanded=ROOT/'output/moisture_mix_reuse_20261110_expanded'
    full=ROOT/'output/moisture_mix_reuse_20261110_all49_float_resolution'
    integrated=json.loads((pilot/'integration.json').read_text())
    check=json.loads((full/'summary.json').read_text());protocol=json.loads((full/'protocol.json').read_text())
    if integrated['status']!='integrated_and_verified' or check['verified_regions']!=49:
        raise ValueError('Incomplete integration/equivalence checks')
    if file_hash(ROOT/'rotclimate/moisture.py')!=integrated['new_module_sha256']:
        raise ValueError('Integrated model source changed')
    if hashlib.sha256(inspect.getsource(moisture.solve_moisture).encode()).hexdigest()!=protocol['proposal_sha256']:
        raise ValueError('Integrated function does not match the verified proposal')
    if file_hash(full/'summary.json')!=integrated['full49_equivalence_summary_sha256']:
        raise ValueError('Changed equivalence evidence')
    first=json.loads((pilot/'summary.json').read_text());more=json.loads((expanded/'summary.json').read_text())
    assert first['status']==more['status']==check['status']=='passed'
    rows=[dict(label='Japan · r44',baseline_cpu_seconds=sum(r['cpu_seconds'] for r in first['rows'] if r['mode']=='baseline')/2,
        reuse_cpu_seconds=sum(r['cpu_seconds'] for r in first['rows'] if r['mode']=='reuse')/2,cpu_ratio=first['cpu_ratio'])]
    labels={'bengal':'Bengal · r44','north_queensland':'North Queensland · r44',
        'patagonia':'Patagonia · r44','japan':'Japan · warmer-sea/C3'}
    for r in more['records']:
        rows.append(dict(label=labels[r['region']],**{k:r[k] for k in ['baseline_cpu_seconds','reuse_cpu_seconds','cpu_ratio']}))
    cases=[]
    for r in check['rows']:
        assert r['all_field_bytes_and_numerics_equal'] and r['exact_reference_monthly_climate']
        cases.append(dict(region=r['region'],case_sha256=r['case_sha256'],fields=r['field_bytes'],
            numerical_diagnostics_sha256=hashlib.sha256(json.dumps(r['numerics'],sort_keys=True,allow_nan=False).encode()).hexdigest()))
    payload=dict(status='integrated',physical_model='r44',climate_accuracy_gain=False,
        atlas_climate_fields_changed=False,verified_regions=49,integration=integrated,
        counterbalanced_cpu_checks=rows,case_equivalence=cases,
        limit='CPU timing on five known profiles only; no general speedup, new climate accuracy or independent validation claim.')
    data=ROOT/'atlases/climate_accuracy/data';write_json(data/'moisture_mix_reuse.json',payload)
    table=''.join(f'<tr><th>{r["label"]}</th><td>{r["baseline_cpu_seconds"]:.3f}</td>'
        f'<td>{r["reuse_cpu_seconds"]:.3f}</td><td>{r["cpu_ratio"]:.3f}</td></tr>' for r in rows)
    section=f'''<!--moisture-mix-reuse-start--><h2>Less duplicate mixing work; identical climate</h2>
<p>The moisture solver now reuses a storm-mixing target already computed by its preceding residual check at the identical water state. It retains the vapor target before adding condensate. Forcing, coefficients, equation, tolerances and reported numerical diagnostics stay unchanged.</p>
<p><strong>All 49 development regions pass exact byte comparisons</strong> for temperature, sea-level temperature, rain, water, winds, evaporation, snow and sample days, with identical reported numerical diagnostics and original-reference monthly climate. The integrated function exactly matches the tested proposal; an integrated Japan replay and 64 focused regression tests pass.</p>
<div class="table"><table><thead><tr><th>Known profile</th><th>Baseline CPU, s</th><th>Reuse CPU, s</th><th>CPU ratio</th></tr></thead><tbody>{table}</tbody></table></div>
<p>After warmup, each profile uses baseline/reuse/reuse/baseline order. The four expanded cases use 4.6% less pooled CPU; the first Japan pilot uses 6.5% less. This small timing sample does not establish a general speedup. Concurrent calibration affects wall time, which is not used for these ratios. These are reused development cases, not independent climate validation.</p>
<p><strong>r44 climate accuracy and all adopted map fields are unchanged.</strong> The optimization was integrated only after the frozen 51-profile calibration, coastal diagnostics and publication completed. To resume those historical optimizer checkpoints, use their recorded pre-integration source revision.</p>
<p><a href="data/moisture_mix_reuse.json" download>Timing, per-field hashes and integration lineage</a> · <a href="../../reports/MOISTURE_MIX_REUSE_20261110.md">Implementation and verification report</a></p><!--moisture-mix-reuse-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';html=page.read_text()
    pattern=r'<!--moisture-mix-reuse-start-->[\s\S]*?<!--moisture-mix-reuse-end-->'
    html=re.sub(pattern,lambda m:section,html) if re.search(pattern,html) else html.replace('</main>',section+'\n</main>')
    html,_=organize(html);assert organize(html)[0]==html;page.write_text(html)
    register=ROOT/'calibration/earth_components_20261105/dataset_usage.json'
    exposure=json.loads(register.read_text());exposure['date']='2026-11-10'
    entry=dict(id='moisture_mix_reuse_20261110',status='numerical_equivalence_on_development_cases',
        evidence='reports/MOISTURE_MIX_REUSE_20261110.md',
        note='49 known regions used for exact-output/numerical replay; five known profiles for CPU timing. No climate fit, accuracy gain or new independent validation.')
    exposure['datasets']=[r for r in exposure['datasets'] if r['id']!=entry['id']]+[entry]
    write_json(register,exposure)
    (ROOT/'atlases/earth_evidence/data/dataset_usage.json').write_bytes(register.read_bytes())
    print('Published integrated cache:49 exact regions; adopted physical climate remains r44.')


if __name__=='__main__':main()

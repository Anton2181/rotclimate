"""Publish development settlement evidence without replacing production map fields."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from settlement_locations_earth import OUT,PLAN,sha,write


def main():
    results=json.loads((OUT/'results.json').read_text())
    if results['status']!='development_only' or results['adopt'] or results['plan_sha256']!=sha(PLAN):
        raise ValueError('Wrong study status or changed protocol')
    for name,digest in results['sources'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Changed experiment source: '+name)
    for name,receipt in results['pools'].items():
        if sha(OUT/(name+'_inputs.npz'))!=receipt['input_sha256']:
            raise ValueError('Changed prepared input')
    if sha(OUT/'positions.npz')!=results['positions_sha256']:
        raise ValueError('Changed candidate locations')
    lead=next(r for r in results['ranking'] if r['variant']==results['development_lead'])
    if not lead['feasible'] or len(results['pools'])!=2 or len(results['rows'])!=72:
        raise ValueError('Incomplete declared comparison')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    data.mkdir(exist_ok=True)
    for src,name in [(OUT/'results.json','settlement_locations.json'),(PLAN,'settlement_locations_plan.json'),
                     (ROOT/'reports/figures/settlement_locations_20261110.png','settlement_locations.png')]:
        shutil.copyfile(src,data/name)
    table=[]
    for pool,label in [('han','Han AD2'),('rome','Rome AD150')]:
        for title,row in [('Current',results['baseline'][pool]),('Candidate · five-seed mean',lead['pools'][pool])]:
            table.append(f'<tr><th>{label}</th><td>{title}</td>'+''.join(f'<td>{row[k]:.3f}</td>' for k in ['F1','M1','M3','unique_F1'])+'</tr>')
    section='''<!--settlement-locations-start--><section id="settlement-locations" aria-labelledby="settlement-locations-h"><h2 id="settlement-locations-h">Settlement locations: fixed counts, better clustering, transfer still pending</h2><div class="panel">
<p><strong>Development experiment · no main-map adoption.</strong> The complete five-stage settlement/control programme is tracked in the repository: location and occupancy → settlement roles and hierarchy → local versus central authority → surplus-supported institutions → mobile and nonstate communities.</p>
<p>We tested 12 placement variants on two exposed Earth pools (72 pool/variant/seed evaluations). Counts stay fixed at 1,202 Han and 1,292 Roman proposals. Old-heartland weights change location scores, never the requested count or population. All draws meet their budgets.</p>
<div class="table"><table id="settlement-locations-results"><thead><tr><th>Pool</th><th>Placement</th><th>Proximity F1 ↑</th><th>100km block rank ↑</th><th>Spacing KS ↓</th><th>Unique-site F1 ↑</th></tr></thead><tbody>'''+''.join(table)+'''</tbody></table></div>
<p>The candidate improves clustering in both pools and Han location matching substantially. Roman proximity improves modestly, but unique-site matching is slightly worse. Proximity can count several observed centres near one proposal; unique matching cannot. This is not independent validation or a demonstration that every location improves.</p>
<p>A retained alternative, deterministic18km placement with the same historical prior, improves unique-site F1 in both pools (Han0.591, Rome0.422) but matches spacing less closely. The predeclared composite still selects the candidate in the table; next work will examine this location-versus-spacing tradeoff.</p>
<figure><img src="data/settlement_locations.png" alt="Han and Roman observed centres, current regular placement, and a more clustered fixed-count development candidate"><figcaption>Always seed1, fixed before selection; table shows five-seed means. Newly reconstructed current-source Earth inputs have paired baselines; old November7 numbers are not comparable controls. These are administrative seats and urban sites, not every village.</figcaption></figure>
<p><strong>Next unfinished step:</strong> resolve historical occupancy and grid/site-resolution assumptions, then freeze prospective transfer checks. Only a qualified candidate will rebuild settlements, tracks, shared food/staffing and control together. Settlement roles, differentiated authority, institutional resources and mobile communities remain on the roadmap. Existing atlas settlement/control defaults are unchanged.</p>
<p><a href="../../reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md">Full programme and completion checklists</a> · <a href="../../reports/SETTLEMENT_LOCATIONS_20261110.md">Methods, ablations and limitations</a> · <a href="data/settlement_locations.json" download>All72 development results</a> · <a href="data/settlement_locations_plan.json" download>Predeclared protocol</a> · <a href="https://doi.org/10.1016/j.jas.2012.12.025">Settlement-hierarchy literature</a></p></div></section><!--settlement-locations-end-->'''
    html=page.read_text();pattern=r'<!--settlement-locations-start-->[\s\S]*?<!--settlement-locations-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<section aria-labelledby="yield-h">'
        if marker not in html:raise ValueError('Missing evidence-page insertion marker')
        html=html.replace(marker,section+'\n'+marker,1)
    html=html.replace('EARTH EVIDENCE · 5 NOVEMBER 2026','EARTH EVIDENCE · RESEARCH UPDATED 10 NOVEMBER 2026')
    page.write_text(html)
    register=ROOT/'calibration/earth_components_20261105/dataset_usage.json'
    exposure=json.loads(register.read_text());exposure['date']='2026-11-10'
    entry=dict(id='settlement_locations_20261110',status='exposed_development_only',
        evidence='reports/SETTLEMENT_LOCATIONS_20261110.md',
        note='HanAD2 county seats and RomanAD150 urban sites reused for 12 fixed-count location variants/72 evaluations. Newly reconstructed slope/HAND inputs, paired controls. No prospective qualification or production adoption; Sui/Tang/Domesday remain spent.')
    exposure['datasets']=[e for e in exposure['datasets'] if e['id']!=entry['id']]+[entry]
    write(register,exposure);shutil.copyfile(register,data/'dataset_usage.json')
    print('Published settlement-development evidence; main settlements/control unchanged.')


if __name__=='__main__':main()

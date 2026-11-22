"""Refresh the current Earth overview while retaining labelled historical studies."""
import hashlib
import json
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from check_v22_release_inputs import verify_correction
    physics = ROOT/'calibration/local_accuracy_20261023/r51_params.json'
    cal = ROOT/'calibration/earth_correction_r51_20261122'
    adopted = json.loads((ROOT/'calibration/local_accuracy_20261023/r51_adoption.json').read_text())
    assert adopted['adopted']=='r51' and all(adopted['scores'][k]['passes'] for k in ['dev4','fine','sealed_r'])
    assert hashlib.sha256(physics.read_bytes()).hexdigest()==adopted['params_sha256']
    correction = {name:json.loads((cal/name/'protocol.json').read_text())['meta'] for name in ['temperature','rain_pattern']}
    hashes = {name:verify_correction(cal/name, physics) for name in correction}
    source = ROOT/'output/tropical_check_20261122/refit_T3/j37_monsoon_descent_0.03419'; regions = {}; paths = []
    for part in ['candidate_dev31','candidate_retired_a','candidate_retired_b','candidate_retired_c','candidate_tropical_t']:
        path = source/part/'summary.json'; paths.append(path); summary=json.loads(path.read_text())
        assert summary['complete']
        for name, row in summary['regions'].items():
            assert name not in regions and row['status']=='passed' and row['numerics']['all_checks_passed']
            regions[name]=row
    assert len(regions)==55
    raw55 = dict(regions=55,monthly_temperature_mae_C=sum(r['temperature']['monthly_mae_C'] for r in regions.values())/55,
        rain_loss=sum(r['rain']['loss'] for r in regions.values())/55)
    cv31 = dict(regions=31,raw_temperature_mae_C=correction['temperature']['raw_monthly_mae_C'],
        corrected_temperature_mae_C=correction['temperature']['held_out_monthly_mae_C'],
        raw_rain_loss=correction['rain_pattern']['raw_loss'],corrected_rain_loss=correction['rain_pattern']['held_out_loss'])
    data=ROOT/'atlases/climate_accuracy/data'; data.mkdir(parents=True,exist_ok=True)
    result=dict(profile='r51',date='2026-11-22',raw_development55=raw55,correction_cluster_cv31=cv31,
        adoption=adopted,recovered_model_sha256=hashes,
        source_files_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*paths,physics,ROOT/'output/earth_correction_r51_20261122/training_receipt.json']},
        interpretation='r51 adoption evidence (policy_v4 against r50, sealed set r) plus corrections retrained for r51 with the unchanged recipe. 55 raw regions and 31 correction regions are different pools; never subtract their errors as a paired improvement.')
    (data/'current_earth_r51.json').write_text(json.dumps(result,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.3),layout='constrained');fig.patch.set_facecolor('#f1f3ef')
    previous=ROOT/'calibration/earth_correction_r50_20261121'
    for ax,name,raw_key,cv_key,metric in [(axes[0],'temperature','raw_monthly_mae_C','held_out_monthly_mae_C','Monthly temperature MAE · °C'),(axes[1],'rain_pattern','raw_loss','held_out_loss','Rain loss · lower is better')]:
        old=json.loads((previous/name/'protocol.json').read_text())['meta'];new=correction[name];x=np.arange(2)
        ax.bar(x-.17,[old[raw_key],new[raw_key]],.34,label='Raw physics',color='#ad7c54')
        ax.bar(x+.17,[old[cv_key],new[cv_key]],.34,label='Cluster CV correction',color='#367a71')
        ax.set(xticks=x,xticklabels=['r50','r51'],ylabel=metric)
        for i,v in enumerate([old[cv_key],new[cv_key]]): ax.text(i+.17,v,f'{v:.4f}',ha='center',va='bottom',fontsize=9)
        ax.set_ylim(0,max(old[raw_key],new[raw_key])*1.18);ax.grid(axis='y',alpha=.15);ax.legend(fontsize=8)
    fig.suptitle('Earth correction models retrained for r51 · the same 31-region study',fontsize=13)
    fig.supxlabel('Fixed recipe; leave whole clusters out; weights selected within that CV.\nDevelopment data, not a blind test. Corrected changes include refitting the correction.',fontsize=9)
    fig.savefig(data/'r51_corrections.png',dpi=145);plt.close(fig)
    section=f'''<!--current-earth-overview-start--><h2>Current adopted raw Earth physics: r51</h2>
<p>On the 55-region development pool (the 49 earlier regions plus six tropical regions), monthly temperature MAE is <strong>{raw55['monthly_temperature_mae_C']:.4f} °C</strong> and rain loss <strong>{raw55['rain_loss']:.5f}</strong>. At adoption, combined error was {100*(1-adopted['scores']['dev4']['S55']['S']):.2f}% below r50 over the 55 regions ({100*(1-adopted['scores']['dev4']['S49']['S']):.2f}% over the earlier 49, {100*(1-adopted['scores']['dev4']['S_t']['S']):.1f}% over the six tropical regions); the paired 28 km check passed (S {adopted['scores']['fine']['S28']['S']:.4f}), and then-unseen set r passed with combined error {100*(1-adopted['scores']['sealed_r']['S']['S']):.2f}% below r50. Set r is now spent. r51 stops treating air over the wet Amazon and Congo forests as desert air (convection there was switched off), and caps how hard convection can rain over land, so coasts such as Maranhão no longer rain out the moisture before it reaches the interior. These are regional checks, not a global accuracy percentage.</p>
<p>The temperature and rainfall corrections were retrained for r51 with the unchanged recipe: <strong>{cv31['corrected_temperature_mae_C']:.4f} °C</strong> and rain loss <strong>{cv31['corrected_rain_loss']:.5f}</strong> on the 31-region study with whole clusters held out (raw {cv31['raw_temperature_mae_C']:.4f} °C / {cv31['raw_rain_loss']:.5f}). The 55-region and 31-region errors are not a paired comparison.</p>
<figure><img src="data/r51_corrections.png" alt="Raw and cluster-cross-validated errors for r50 and r51 on the same 31 development regions"><figcaption>Corrections for r50 and r51 on the same development pool, whole clusters held out.</figcaption></figure>
<p>Known open problems: tropical land still runs 1–2 °C too warm, and the North American monsoon peak remains too weak.</p>
<p><a href="data/current_earth_r51.json" download>Current measurements and provenance</a> · <a href="../../reports/CLIMATE_R51_20261122.md">r51 adoption report</a></p>
<h2>Historical r39 benchmark · 27 October 2026</h2><p class="note">The cards and audit immediately below retain their original r39 measurements and sample definitions. They are not current r51 city accuracy.</p><!--current-earth-overview-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';html=page.read_text()
    if '<!--current-earth-overview-start-->' not in html: raise ValueError('Missing current/historical overview boundary')
    html=re.sub(r'<!--current-earth-overview-start-->.*?<!--current-earth-overview-end-->',lambda m:section,html,count=1,flags=re.S)
    html=re.sub(r'Updated \d+ \w+ \d{4} · current results and historical benchmarks','Updated 22 November 2026 · current results and historical benchmarks',html,count=1)
    page.write_text(html)
    print('Published current r51 overview; historical experiments retained with their original labels')


if __name__=='__main__':main()

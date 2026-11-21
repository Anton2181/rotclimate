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
    physics = ROOT/'calibration/local_accuracy_20261023/r50_params.json'
    cal = ROOT/'calibration/earth_correction_r50_20261121'
    adopted = json.loads((ROOT/'calibration/local_accuracy_20261023/r50_adoption.json').read_text())
    assert adopted['adopted']=='r50' and all(adopted['scores'][k]['passes'] for k in ['dev','fine','sealed_p'])
    assert hashlib.sha256(physics.read_bytes()).hexdigest()==adopted['params_sha256']
    correction = {name:json.loads((cal/name/'protocol.json').read_text())['meta'] for name in ['temperature','rain_pattern']}
    hashes = {name:verify_correction(cal/name, physics) for name in correction}
    source = ROOT/'output/monsoon_convection_20261121/validate94'; regions = {}; paths = []
    for part in ['candidate_dev31','candidate_retired_a','candidate_retired_b','candidate_retired_c']:
        path = source/part/'summary.json'; paths.append(path); summary=json.loads(path.read_text())
        assert summary['complete']
        for name, row in summary['regions'].items():
            assert name not in regions and row['status']=='passed' and row['numerics']['all_checks_passed']
            regions[name]=row
    assert len(regions)==49
    raw49 = dict(regions=49,monthly_temperature_mae_C=sum(r['temperature']['monthly_mae_C'] for r in regions.values())/49,
        rain_loss=sum(r['rain']['loss'] for r in regions.values())/49)
    cv31 = dict(regions=31,raw_temperature_mae_C=correction['temperature']['raw_monthly_mae_C'],
        corrected_temperature_mae_C=correction['temperature']['held_out_monthly_mae_C'],
        raw_rain_loss=correction['rain_pattern']['raw_loss'],corrected_rain_loss=correction['rain_pattern']['held_out_loss'])
    data=ROOT/'atlases/climate_accuracy/data'; data.mkdir(parents=True,exist_ok=True)
    result=dict(profile='r50',date='2026-11-21',raw_development49=raw49,correction_cluster_cv31=cv31,
        adoption=adopted,recovered_model_sha256=hashes,
        source_files_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*paths,physics,ROOT/'output/earth_correction_r50_20261121/training_receipt.json']},
        interpretation='r50 adoption evidence (policy_v3 against r49, sealed set p) plus corrections retrained for r50 with the unchanged recipe. 49 raw regions and 31 correction regions are different pools; never subtract their errors as a paired improvement.')
    (data/'current_earth_r50.json').write_text(json.dumps(result,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.3),layout='constrained');fig.patch.set_facecolor('#f1f3ef')
    previous=ROOT/'calibration/earth_correction_r49_20261121'
    for ax,name,raw_key,cv_key,metric in [(axes[0],'temperature','raw_monthly_mae_C','held_out_monthly_mae_C','Monthly temperature MAE · °C'),(axes[1],'rain_pattern','raw_loss','held_out_loss','Rain loss · lower is better')]:
        old=json.loads((previous/name/'protocol.json').read_text())['meta'];new=correction[name];x=np.arange(2)
        ax.bar(x-.17,[old[raw_key],new[raw_key]],.34,label='Raw physics',color='#ad7c54')
        ax.bar(x+.17,[old[cv_key],new[cv_key]],.34,label='Cluster CV correction',color='#367a71')
        ax.set(xticks=x,xticklabels=['r49','r50'],ylabel=metric)
        for i,v in enumerate([old[cv_key],new[cv_key]]): ax.text(i+.17,v,f'{v:.4f}',ha='center',va='bottom',fontsize=9)
        ax.set_ylim(0,max(old[raw_key],new[raw_key])*1.18);ax.grid(axis='y',alpha=.15);ax.legend(fontsize=8)
    fig.suptitle('Earth correction models retrained for r50 · the same 31-region study',fontsize=13)
    fig.supxlabel('Fixed recipe; leave whole clusters out; weights selected within that CV.\nDevelopment data, not a blind test. Corrected changes include refitting the correction.',fontsize=9)
    fig.savefig(data/'r50_corrections.png',dpi=145);plt.close(fig)
    section=f'''<!--current-earth-overview-start--><h2>Current adopted raw Earth physics: r50</h2>
<p>On the 49-region development pool, monthly temperature MAE is <strong>{raw49['monthly_temperature_mae_C']:.4f} °C</strong> and rain loss <strong>{raw49['rain_loss']:.5f}</strong>. At adoption, combined error was {100*(1-adopted['scores']['dev']['S49']['S']):.2f}% below r49; the paired 28 km check passed (S {adopted['scores']['fine']['S28']['S']:.4f}), and then-unseen set p passed with combined error {100*(1-adopted['scores']['sealed_p']['S']['S']):.2f}% below r49. Set p is now spent. r47–r49 added a rain belt anchored to large plateaus, suppressed convection ahead of the monsoon onset and a 1,750 m plateau height; r50 lets hot land start convecting at lower humidity inside the rain belt, and holds that back where monsoon air descends (the Arabian and Saharan margins). These are regional checks, not a global accuracy percentage.</p>
<p>The temperature and rainfall corrections were retrained for r50 with the unchanged recipe: <strong>{cv31['corrected_temperature_mae_C']:.4f} °C</strong> and rain loss <strong>{cv31['corrected_rain_loss']:.5f}</strong> on the 31-region study with whole clusters held out (raw {cv31['raw_temperature_mae_C']:.4f} °C / {cv31['raw_rain_loss']:.5f}). The 49-region and 31-region errors are not a paired comparison.</p>
<figure><img src="data/r50_corrections.png" alt="Raw and cluster-cross-validated errors for r49 and r50 on the same 31 development regions"><figcaption>Corrections for r49 and r50 on the same development pool, whole clusters held out.</figcaption></figure>
<p>Known open problem: the North American monsoon peak remains too weak (the summer trades over Mexico are not represented); the Sahel and Bengal summer rains improved in the r50 screens.</p>
<p><a href="data/current_earth_r50.json" download>Current measurements and provenance</a> · <a href="../../reports/CLIMATE_R50_20261121.md">r50 adoption report</a></p>
<h2>Historical r39 benchmark · 27 October 2026</h2><p class="note">The cards and audit immediately below retain their original r39 measurements and sample definitions. They are not current r50 city accuracy.</p><!--current-earth-overview-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';html=page.read_text()
    if '<!--current-earth-overview-start-->' not in html: raise ValueError('Missing current/historical overview boundary')
    html=re.sub(r'<!--current-earth-overview-start-->.*?<!--current-earth-overview-end-->',lambda m:section,html,count=1,flags=re.S)
    html=re.sub(r'Updated \d+ \w+ \d{4} · current results and historical benchmarks','Updated 21 November 2026 · current results and historical benchmarks',html,count=1)
    page.write_text(html)
    print('Published current r50 overview; historical experiments retained with their original labels')


if __name__=='__main__':main()

"""Expose a fixed-state transport diagnosis without presenting it as a forecast."""
from pathlib import Path
import json
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from organize_climate_accuracy import organize


def main():
    folder=ROOT/'output/face_convergence_20261103';review=json.loads((folder/'receipt.json').read_text())
    if review['climate_integrations']!=0 or review['adoption'] or review['observations_opened']:
        raise ValueError('Wrong diagnostic scope')
    if file_hash(ROOT/'scripts/diagnose_face_convergence.py')!=review['observer_sha256']:
        raise ValueError('Observer changed since the analysis')
    destination=ROOT/'atlases/climate_accuracy/data'
    for name,key in [('fixed_state_supply.png','image_sha256'),('fixed_state_supply.npz','arrays_sha256')]:
        if file_hash(folder/name)!=review[key]:raise ValueError('Changed diagnostic artifact')
        shutil.copyfile(folder/name,destination/('face_convergence_'+name))
    write_json(destination/'face_convergence.json',review)
    total=review['statistics']['advection_change']['mean_absolute_mm_year']
    remainder=review['statistics']['stencil_remainder']['mean_absolute_mm_year']
    screen_path=ROOT/'output/fitted_flux_20261103/result.json'
    coupled='The separately declared fitted-flux climate screen is not yet complete.'
    if screen_path.exists():
        screen=json.loads(screen_path.read_text())
        if screen['adoption'] or screen['sealed_run']:raise ValueError('Unexpected screen scope')
        write_json(destination/'fitted_flux_screen.json',dict(result=screen,result_sha256=file_hash(screen_path)))
        if screen['outcome']=='screen_complete' and all(r['status']=='complete' for r in screen['profiles'].values()):
            up=screen['profiles']['upwind_flux']['score'];fit=screen['profiles']['fitted_flux']['score'];paired=screen['fitted_vs_upwind']
            coupled=(f'<strong>The separate coupled screen is complete and does not improve climate.</strong> '
                f'On eight reused regions, conservative upwind flux has combined error {up["S"]:.4f} times production, '
                f'and fitted flux {fit["S"]:.4f}. Fitting the faces worsens rain loss by {100*paired["P"]:.2f}% '
                f'versus upwind flux. The analytic numerical checks still pass; they do not establish climate accuracy. '
                '<a href="data/fitted_flux_screen.json" download>Complete coupled-screen scores and scope</a>. '
                'No reserved region was used and neither operator is adopted.')
        else:
            coupled='The separate coupled screen stopped or has failed profiles; no incomplete profile receives a climate gain claim. <a href="data/fitted_flux_screen.json" download>Retained outcomes</a>.'
    section=f'''<!--face-convergence-start--><section aria-labelledby="face-convergence-h">
<h2 id="face-convergence-h">A structural transport problem: the assumed column circulation</h2>
<p>Holding the verified raw r43 world water and winds fixed, replacing point advection with conservative face advection changes the local supply by an annual mean absolute <strong>{total:,.0f} mm of water equivalent</strong>. The difference is almost entirely the compression term −W div(u); the different discrete stencils leave a mean absolute remainder of <strong>{remainder:.1f} mm/year</strong>. These are signed supply terms, not extra rainfall or new integrations.</p>
<figure><a href="data/face_convergence_fixed_state_supply.png"><img src="data/face_convergence_fixed_state_supply.png" width="1890" height="1080" loading="lazy" alt="Raw rainfall and fixed-state advection-supply differences, decomposed into compression and a small stencil remainder"></a><figcaption>The two large supply panels share a symmetric logarithmic scale. The remainder uses a separate ±250 mm/year linear scale. All maps hold the existing climate state fixed; brown is removal and green is supply.</figcaption></figure>
<p>The surface wind is not automatically a stationary whole-column mass circulation. Converging dry air needs compensating upper outflow, vertical exchange or storage. Conserving vapor while keeping that circulation unchanged can therefore produce very large local changes. The earlier mass-balanced counterflow test reduced the wet bias but still had combined error 1.456 times its r42 control: recognizing the constraint is not a completed fix.</p>
<p>This comparison isolates advection only. A full model switch also removes the existing smoothed, warm-only convergence-import closure and changes evaporation, humidity, rain and feedbacks. This world diagnostic does not identify an Earth accuracy gain or predict the full switched climate. No new observations, parameter search, simulation, model adoption or atlas change is involved.</p>
<p>The fitted face scheme is a separate numerical experiment with fixed physical diffusivity and analytic conservation checks. These fixed-state results give stronger reason to improve circulation and vertical water exchange. {coupled}</p>
<p><a href="data/face_convergence.json" download>Exact source identity, scope and unclipped supply statistics</a> · <a href="data/face_convergence_fixed_state_supply.npz">Raw map arrays</a> · <a href="../../reports/FACE_CONVERGENCE_20261103.md">Interpretation and limits</a> · <a href="../../reports/FITTED_FLUX_20261103.md">Fitted numerical operator</a></p>
</section><!--face-convergence-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html'
    text=re.sub(r'<!--face-convergence-start-->[\s\S]*?<!--face-convergence-end-->','',page.read_text())
    text=text.replace('</main>',section+'\n</main>');text,studies=organize(text)
    if organize(text)[0]!=text:raise ValueError('Navigation is not idempotent')
    page.write_text(text);write_json(folder/'publication.json',dict(status='passed',newest=studies[0],page_sha256=file_hash(page)))
    print('Published fixed-state circulation diagnosis, no integration or adoption')


if __name__=='__main__':main()

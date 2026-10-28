"""Publish verified process diagnosis, keeping all adopted climates unchanged."""
from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from analyze_transport_diagnosis import verify_and_summarize
from local_benchmark_protocol import file_hash,write_json
from PIL import Image


def publish(out):
    evidence,result,_=verify_and_summarize(out)
    old=json.loads((out/'diagnosis.json').read_text())
    receipt=json.loads((out/'scientific_verification.json').read_text())
    if evidence!=receipt or any(old.get(key)!=value for key,value in result.items()):
        raise ValueError('Need matching independently recomputed transport diagnosis')
    if file_hash(ROOT/'scripts/analyze_transport_diagnosis.py')!=old['analyzer_sha256']:
        raise ValueError('Changed diagnostic analysis source')
    expected={'transport_water_budgets.png','transport_matched_winds.png','transport_pressure_levels.png','transport_seasonal_maps.png'}
    if set(old['images_sha256'])!=expected:raise ValueError('Changed complete diagnostic figure set')
    data=ROOT/'atlases/climate_accuracy/data';figures=[]
    alts={'transport_water_budgets.png':'Six unchanged climate rainfall curves and signed lower and upper layer water balances',
        'transport_matched_winds.png':'Pressure-matched925–300hPa moisture winds on eleven India land cells, one Mexico land cell and three PNW ocean cells',
        'transport_pressure_levels.png':'Separate925hPa and700hPa east and north winds showing vertical circulation errors',
        'transport_seasonal_maps.png':'Observed and simulated seasonal rain and signed storm redistribution maps for India, Mexico and PNW'}
    for name in ('transport_water_budgets.png','transport_pressure_levels.png','transport_matched_winds.png','transport_seasonal_maps.png'):
        source=out/name
        if file_hash(source)!=old['images_sha256'][name]:raise ValueError('Changed diagnostic figure: '+name)
        shutil.copyfile(source,data/name)
        with Image.open(source) as pic:w,h=pic.size
        figures.append(f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="{alts[name]}"></a></figure>')
    protocol=json.loads((out/'protocol.json').read_text())
    metadata=dict(old,plan=protocol['plan'],recovery=protocol['recovery'],
        scientific_verification_sha256=file_hash(out/'scientific_verification.json'),publisher_sha256=file_hash(Path(__file__)))
    write_json(data/'transport_diagnosis.json',metadata)
    rows=[]
    for region,profiles in old['regions'].items():
        season={'north_india':'JJA','mexico':'SON','pacific_nw':'DJF'}[region]
        for name,row in profiles.items():
            budget=row['full_land']['seasons'][season]
            rows.append(f'<tr><td>{region.replace("_"," ")}</td><td>{"Legacy" if name=="global04" else "Hydrostatic half"}</td><td>{season}</td><td>{-sum(budget["rain"]):.0f} / {budget["observed_rain"]:.0f}</td><td>{sum(budget["storm"]):+.0f}</td><td>{sum(budget["rain_convective"]):.1f}</td><td>{sum(budget["rain_overflow"]):.0f}</td></tr>')
    section='''<!--transport-diagnosis-start--><section aria-labelledby="transport-diagnosis-h"><h2 id="transport-diagnosis-h">Why rainfall is stuck: actual layer transport</h2>
<p><strong>Six saved climates reproduced exactly.</strong> Two fixed ocean settings × three contrasting regions now export their actual branch winds, layer water, upwind vapor faces, vertical donor exchange and separate rainfall components. All original climate arrays remain bit-for-bit identical; this is a process diagnosis, not an improvement in rainfall or a new calibration.</p>
<p>India remains dry in summer; Mexico has excessive autumn rain; PNW has excessive winter rain. India receives positive summer advective supply, while storms and drying remove water. Its explicit empirical convection contributes only about6.5mm of216mm summer rain in the hydrostatic-half case. In Mexico, upper-layer supersaturation overflow supplies about129mm of323mm autumn rain. These signed balances are not independent causal shares, and internal vertical transfer cancels in the full column.</p>
<div class="table"><table><caption>Same full scoring land masks, true area and Gregorian months; diagnostic means differ from the unchanged historical score</caption><thead><tr><th>Region</th><th>Ocean setting</th><th>Season</th><th>Rain model / observed mm</th><th>Storm supply mm</th><th>Empirical convection mm</th><th>Overflow rain mm</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p>The pressure comparison is now like-for-like: modeled925–300hPa water and simultaneous q×wind are integrated before averaging. Matched925hPa and700hPa vectors additionally separate circulation error from humidity weighting. India lacks low-level summer eastward flow; PNW's modeled eastward wind weakens with height while the reference strengthens. The two ocean settings barely change those velocities. The next hypothesis is a thermally consistent separation of lower and upper winds, preserving dry-mass continuity, before further broad coefficient fitting.</p>
'''+''.join(figures)+'''
<p class="note">Coverage is limited:11 matched India land cells,1 Mexico land cell, no PNW land cells,1 Mexico ocean cell and3 PNW ocean cells. Below-ground925hPa comparisons are excluded without fallback. P/PW/winds use identical land pixels and calendar; full land budgets are separate from native metrics. NCEP/NCAR1981–2010 is model-assisted reanalysis; its monthly q×wind lacks submonthly covariance, and WorldClim rainfall has a different reference period. These development regions are not new independent validation. The two-box model does not resolve vertical momentum or energy, and inherited observed cloud/remote-monsoon backgrounds remain fixed.</p>
<p>An isolated thermal-shear operator is now implemented and passes9 manufactured tests: analytic signs, dry continuity, shear preservation, uniform-q transport and the minimum-correction property. The combined focused suite passes52 tests. It is not connected to the coupled climate yet; constructing a common-pressure temperature gradient without terrain artifacts is the next prerequisite. <a href="../../reports/THERMAL_LAYER_PROTOTYPE_20261028.md">Operator prototype and current limits</a>.</p>
<p>All592 frozen inputs/sources,198 solved seasonal steps, exact climate archives, donor exchanges and rain equations were checked. Seven attempts produced six completed strict cases and one controller interruption: a tuple/list bookkeeping comparison was fixed without changing physics, parameters or original evidence. Cumulative counter:1886 attempts,1881 strict passes,4 earlier failures and1 interruption. Adopted Earth r39 and all world, biome and population maps remain unchanged.</p>
<p><a href="data/transport_diagnosis.json" download>Download complete monthly, seasonal, native, pressure-level and verification data</a> · <a href="../../reports/TRANSPORT_DIAGNOSIS_20261028.md">Design, recovery and interpretation</a> · <a href="../../reports/RAINFALL_RECOVERY_PLAN_20261028.md">Rainfall recovery strategy</a></p></section><!--transport-diagnosis-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text()
    if '<!--transport-diagnosis-start-->' in text:
        before,tail=text.split('<!--transport-diagnosis-start-->',1);_,after=tail.split('<!--transport-diagnosis-end-->',1);text=before+section+after
    else:
        anchor='<!--research-list-start-->'
        if text.count(anchor)!=1:raise ValueError('Need one research companion navigation')
        text=text.replace(anchor,section+'\n'+anchor)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_diagnostic_only',metadata_sha256=file_hash(data/'transport_diagnosis.json'),
        images_sha256=old['images_sha256'],publisher_sha256=file_hash(Path(__file__)),physics_or_atlas_adoption=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    publish(ap.parse_args().out.resolve())

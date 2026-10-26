"""Publish a verified manufactured operator example without adopting climate."""
from pathlib import Path
import json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json


def main():
    out=ROOT/'output/two_reservoir_20261026';record=out/'diagnostic.json'
    report=json.loads(record.read_text())
    for name,sha in report['sources_sha256'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Changed prototype source: '+name)
    original=out/'vertical_transport.png'
    if file_hash(original)!=report['image_sha256']:raise ValueError('Changed prototype image')
    data=ROOT/'atlases/climate_accuracy/data';picture=data/'two_reservoir_transport.png'
    shutil.copyfile(original,picture);write_json(data/'two_reservoir_transport.json',report)
    section='''<!--two-reservoir-start--><section aria-labelledby="two-reservoir-h"><h2 id="two-reservoir-h">Two-reservoir transport prototype</h2>
<p><strong>Manufactured operator example, not a climate calibration or observed accuracy gain.</strong> Lower and upper water amounts are independent unknowns. Diagnosed vertical air exchange carries the donor layer's humidity and closes each layer's dry-air continuity. A rising moist flow can moisten the upper return rather than keeping its humidity artificially fixed.</p>
<figure><a href="data/two_reservoir_transport.png"><img src="data/two_reservoir_transport.png" width="1740" height="1160" loading="lazy" alt="Synthetic balanced opposing winds: solved upper humidity reduces a convergence peak compared with an imposed ratio, with zero and five-day mixing separately controlled"></a><figcaption>Same synthetic winds, surface supply, linear removal coefficients and both layer boundary values. Zero vertical mixing is shown separately. Illustrative linear sinks are not cloud physics; no observed climate is scored.</figcaption></figure>
<p>Nine independent equilibrium, matrix/face, analytic convergence and conservation checks pass. The water ledger closes to about3e-14mm/day in this example. The prototype is not coupled to the seasonal climate, and supplies no independent temperatures, saturation, cloud microphysics, storms or momentum. Published Earth/world climate and population maps remain unchanged.</p>
<p><a href="data/two_reservoir_transport.json" download>Download manufactured reservoir diagnostics</a> · <a href="../../reports/TWO_RESERVOIR_20261026.md">Equations, verification and coupling requirements</a></p></section><!--two-reservoir-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text();start='<!--two-reservoir-start-->';end='<!--two-reservoir-end-->'
    if start in content:
        before,rest=content.split(start,1);_,after=rest.split(end,1);content=before+section+after
    else:content=content.replace('</main>',section+'\n</main>')
    page.write_text(content)
    write_json(out/'publication.json',dict(scope='Research operator only; no climate adoption',
        diagnostic_sha256=file_hash(record),page_sha256=file_hash(page),publisher_sha256=file_hash(Path(__file__)),image_sha256=file_hash(picture)))


if __name__=='__main__':main()

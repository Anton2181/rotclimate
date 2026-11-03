"""Publish verified complete transport profiles and explicitly unscored ones."""
from pathlib import Path
import html
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, write_json
from organize_climate_accuracy import organize


def main():
    folder = ROOT / 'output/r42_transport_review_20261102'
    review = json.loads((folder / 'review.json').read_text())
    if review['adoption'] or file_hash(folder / 'monthly_transport_rain.png') != review['figure_sha256']:
        raise ValueError('Unexpected review or changed figure')
    destination = ROOT / 'atlases/climate_accuracy/data'
    packets = {}
    for name, digest in review['packets_sha256'].items():
        source = ROOT / name
        if file_hash(source) != digest:
            raise ValueError('Raw packet changed: ' + name)
        profile = source.parent.parent.name
        filename = 'r42_transport_' + profile + '_' + source.name
        shutil.copyfile(source, destination / filename); packets[filename] = digest
    shutil.copyfile(folder / 'monthly_transport_rain.png', destination / 'r42_transport_monthly.png')
    write_json(destination / 'r42_transport.json', dict(review=review, downloads_sha256=packets,
        publisher_sha256=file_hash(Path(__file__))))
    rows = []
    for name, row in review['profiles'].items():
        label = html.escape(name.replace('_', ' '))
        values = (f'{row["temperature_ratio"]:.4f}', f'{row["rain_ratio"]:.4f}', f'{row["aggregate"]:.4f}') if row['status'] == 'complete' else ('unscored',) * 3
        rows.append(f'<tr><td>{label}</td><td>{row["status"]}</td>' + ''.join(f'<td>{x}</td>' for x in values) + '</tr>')
    links = ''.join(f'<li><a href="data/{name}">{html.escape(name.removeprefix("r42_transport_").removesuffix(".npz").replace("_", " "))}</a></li>' for name in packets)
    section = f'''<!--r42-transport-start--><section aria-labelledby="r42-transport-h">
<h2 id="r42-transport-h">Conservative transport on r42: complete matched profiles</h2>
<p><strong>{review['completed_profiles']} of {review['declared_profiles']} declared profiles complete at this snapshot.</strong> Pending or failed profiles receive no aggregate score. These physical changes are not adopted; current calibration and atlas releases are identified separately. All eight regions reuse development data, with matched forcing/observations and unchanged strict numerical criteria.</p>
<div class="table"><table><caption>Equal-region error ratios to the verified damped r42 control; lower is better</caption><thead><tr><th>Profile</th><th>Status</th><th>Temperature</th><th>Rain loss</th><th>Combined</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<figure><a href="data/r42_transport_monthly.png"><img src="data/r42_transport_monthly.png" width="2160" height="1012" loading="lazy" alt="Monthly observed and simulated rainfall across all eight matched development regions"></a><figcaption>The combined flux/storm change increases India's monsoon but strongly over-rains the dry coast and desert. Counterflow reduces the excess while losing some monsoon gain. Independent-reservoir outcomes are included only once complete.</figcaption></figure>
<p>These results test inherited strengths under changed transport, not a tuned conservative model. Conservation certificates do not establish realistic circulation or global climate accuracy. The follow-up comparison separates vapor flux from storm exchange, then adds explicitly accounted condensation at crest saturation. R42 has that crest-condensation parameter disabled; the new profiles declare the change rather than treating it as part of the baseline.</p>
<p><a href="data/r42_transport.json" download>All profile statuses, source/packet hashes and ratios</a> · <a href="../../reports/TRANSPORT_FACTORS_20261102.md">Interpretation and prospective follow-up</a></p>
<details><summary>Verified raw monthly cell packets for every completed profile</summary><ul>{links}</ul></details>
</section><!--r42-transport-end-->'''
    page = ROOT / 'atlases/climate_accuracy/index.html'
    text = re.sub(r'<!--r42-transport-start-->[\s\S]*?<!--r42-transport-end-->', '', page.read_text())
    text = text.replace('</main>', section + '\n</main>')
    text, studies = organize(text)
    if organize(text)[0] != text:
        raise ValueError('Research navigation must remain idempotent')
    page.write_text(text)
    write_json(folder / 'publication.json', dict(status='passed', newest=studies[0],
        completed_profiles=review['completed_profiles'], raw_packets=len(packets), page_sha256=file_hash(page)))
    print('Published', studies[0], 'with', len(packets), 'verified packets')


if __name__ == '__main__': main()

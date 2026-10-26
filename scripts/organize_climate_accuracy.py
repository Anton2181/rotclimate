"""Keep the portable research companion readable as completed experiments accrue.

Reorders existing published sections only; no climate statistics or data assets
are recalculated. Newest experiment opens, older experiments remain accessible.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]
STUDIES=[
    ('humidity-gate','Rain activation and moisture delivery'),
    ('mass-tracer','Air-mass-aware water transport'),
    ('two-layer','Moist inflow and upper return'),
    ('column-mass','Column mass, wind and rainfall'),
    ('thermal-wind','Thermal wind, rainfall and circulation'),
    ('circulation','Circulation against reanalysis'),
    ('earth-calendar','Observation-calendar alignment'),
    ('flux-column-wind','Conservative flux and column wind'),
    ('vapor-flux','Conservative vapor transport'),
    ('momentum-balance','Land, ocean and pressure balance'),
    ('surface-momentum','Surface momentum'),
    ('column-shear','Pressure-driven column shear'),
]


def organize(page):
    start,end='<!--research-list-start-->','<!--research-list-end-->'
    sections={}
    for key,label in STUDIES:
        pattern=f'<!--{key}-start-->[\\s\\S]*?<!--{key}-end-->'
        found=re.findall(pattern,page)
        if len(found)>1:
            raise ValueError('Duplicate published experiment section: '+key)
        if found:
            sections[key]=found[0].replace('Latest experiment: turning the moisture-column wind',
                                          'Turning the moisture-column wind')
    if not sections:
        raise ValueError('No completed experiment sections found')
    if start in page:
        before,rest=page.split(start,1)
        _,after=rest.split(end,1)
        page=before+after
    for key in sections:
        page=re.sub(f'<!--{key}-start-->[\\s\\S]*?<!--{key}-end-->','',page)
    page=re.sub(r'<script data-research-navigation>[\s\S]*?</script>\s*','',page)
    links=[];details=[]
    for key,label in STUDIES:
        if key not in sections:continue
        links.append(f'<a href="#study-{key}">{label}</a>')
        opened=' open' if not details else ''
        details.append(f'<details id="study-{key}" class="experiment"{opened}><summary>{label}</summary>{sections[key]}</details>')
    content=(start+'<section id="experiments" aria-labelledby="experiments-h"><h2 id="experiments-h">Completed experiments</h2>'
             '<p class="note">Newest result opens first. Expand an earlier experiment for its chart, measurements and limitations.</p>'
             '<nav class="research-index" aria-label="Completed experiment index">'+' · '.join(links)+'</nav>'
             +''.join(details)+'</section>'+end)
    page=page.replace('</main>',content+'\n</main>')
    if '/*research-layout*/' not in page:
        style='''/*research-layout*/
.research-index{display:flex;flex-wrap:wrap;gap:6px 12px;margin:12px 0 20px;font-size:.9rem}
.experiment{border:1px solid var(--rule);border-radius:6px;background:var(--plate);margin:12px 0;padding:12px 16px;scroll-margin-top:16px}
.experiment>summary{cursor:pointer;font-weight:600}.experiment>summary:focus-visible{outline:2px solid var(--link);outline-offset:4px}
.experiment h2{font-size:1.45rem}.experiment figure{padding:8px}.experiment[open]>summary{margin-bottom:16px}
@media(max-width:620px){.experiment{padding:10px}.research-index{display:block}.research-index a{display:inline-block;margin:4px 0}}
'''
        page=page.replace('</style>',style+'</style>')
    if '<a href="#experiments">Experiments</a>' not in page:
        page=page.replace('<a href="../earth_fit/">Earth atlas</a>',
                          '<a href="../earth_fit/">Earth atlas</a> · <a href="#experiments">Experiments</a>')
    if 'data-research-navigation' not in page:
        script='''<script data-research-navigation>
function openResearchHash(){let id;try{id=decodeURIComponent(location.hash.slice(1));}catch{return;}
const target=document.getElementById(id);if(!target)return;const detail=target.closest('details');
if(detail){detail.open=true;requestAnimationFrame(()=>target.scrollIntoView({block:'start'}));}}
addEventListener('hashchange',openResearchHash);openResearchHash();
</script>'''
        page=page.replace('</main>',script+'\n</main>')
    # Removal of an older container can leave blank lines; canonicalize only
    # the whitespace before the new container to make the formatter idempotent.
    page=re.sub(r'\s*<!--research-list-start-->','\n<!--research-list-start-->',page)
    return page,list(sections)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--page',type=Path,default=ROOT/'atlases/climate_accuracy/index.html')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    page,sections=organize(args.page.read_text())
    again,_=organize(page)
    if again!=page:raise ValueError('Research layout transformation is not idempotent')
    args.page.write_text(page)
    result=dict(status='passed',sections=sections,newest_open=sections[0],
                page_sha256=hashlib.sha256(page.encode()).hexdigest(),statistics_recalculated=False)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

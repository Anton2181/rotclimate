"""Re-enable the release-3/4 views on the Earth-fit page after scripts/refresh_atlas_pages.py (which rebuilds index.html from the
template and drops the attributes the individual release-3 publishers added). An attribute is added only when its manifest exists;
the superseded experiments (release 2, feedback, dispatch, network visits, year-complete, food-checked) are not re-enabled.

    enable_release3_page.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; PAGE = ROOT / 'atlases/earth_fit/index.html'; DATA = ROOT / 'atlases/earth_fit/data'
WANT = {'administration.js': [('data-administration-release3', 'release3/admin/administrative_access.json')],
        'administrative-hierarchy.js': [('data-hierarchy-release3', 'release3/hierarchy/administrative_hierarchy.json')],
        'settled-reach.js': [('data-settlement-release3-enabled', 'settlement_release3.json'),
                             ('data-settlement-provisional-enabled', 'settlement_provisional.json'),
                             ('data-release3-layers-enabled', 'release3_layers.json'),
                             ('data-release3-reach-enabled', 'release3_reach.json'),
                             ('data-release3-supply-enabled', 'release3_supply.json')]}

if __name__ == '__main__':
    import re
    html = PAGE.read_text(); added = []
    for script, attrs in WANT.items():
        tag = re.search(r'<script src="' + re.escape(script) + r'"[^>]*></script>', html).group(0); new = tag
        for attr, manifest in attrs:
            if (DATA / manifest).exists() and attr not in new:
                new = new.replace('></script>', f' {attr}></script>'); added.append(attr)
        html = html.replace(tag, new)
    PAGE.write_text(html); print('enabled', added)

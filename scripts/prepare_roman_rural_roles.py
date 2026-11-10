"""Compile aggregate, unscored role evidence; raw observations stay in cache."""
import collections
import concurrent.futures
import html
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from audit_roman_rural_preparation import table, identifier, sha, write
from polity.role_evidence import association_blocks, compile_role_evidence

CONFIG = ROOT / 'calibration/roman_rural_roles_20261110'
CACHE = ROOT / 'data/cache/roman_rural_britain_2018'
OUT = ROOT / 'output/roman_rural_roles_20261110'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source_snapshot = ROOT / 'output/roman_rural_preparation_20261110/source_snapshot.json'
    snapshot = json.loads(source_snapshot.read_text())
    for source in snapshot['files']:
        if sha(CACHE / source['name']) != source['sha256']:
            raise ValueError('Changed observation source: ' + source['name'])
    semantics = json.loads((CONFIG / 'semantic_sources.json').read_text())
    web = ROOT / 'data/cache/roman_rural_britain_metadata/web'
    def metadata(source):
        path = web / source['cache_name']
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            request = urllib.request.Request(source['url'], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
            path.write_bytes(body)
        if sha(path) != source['sha256']:
            raise ValueError('Changed mapping/search metadata: ' + source['url'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(metadata, semantics['pages']))
    search_text = html.unescape(re.sub('<[^>]+>', ' ', (web/'query_structured.html').read_text()))
    search_text = ' '.join(search_text.split())
    for finding in semantics['findings']:
        if 'quote' in finding and ' '.join(finding['quote'].split()) not in search_text:
            raise ValueError('Documented chronology help is absent from pinned source')
    for label in ['jetty', 'roadside settlement']:
        if f'<option value="{label}">' not in (web/'query_structured.html').read_text():
            raise ValueError('Supplemental classification is absent from source search')
    crosswalk = json.loads((CONFIG / 'crosswalk.json').read_text())
    sites, _ = table((CACHE / 'rrs_site_data.csv').read_bytes(), ['ID'])
    ids = {identifier(row['id']) for row in sites}
    labels = {}
    for level in ['major', 'minor']:
        rows, _ = table((CACHE / f'rrs_site_t_{level}.csv').read_bytes(), ['ID'], 'STMID')
        grouped = collections.defaultdict(list)
        for row in rows:
            key = identifier(row['id'])
            if key not in ids:
                raise ValueError('Role refers to missing site record')
            grouped[key].append(row[f'sitetype{level}'])
        labels[level] = grouped
    assoc, _ = table((CACHE / 'rrs_associd.csv').read_bytes(), ['ID'], 'PRN')
    associations = [(identifier(r['id']), r['type'], r['hername'], r['descr']) for r in assoc]
    blocks = association_blocks(ids, associations)
    records = [compile_role_evidence(identifier(row['id']), labels['major'][identifier(row['id'])],
        labels['minor'][identifier(row['id'])], row['datestart'], row['dateend'], crosswalk,
        domestic=row['domesticoccupation']) for row in sites]
    channels = collections.Counter()
    compatible = collections.Counter()
    flags = collections.Counter()
    dates = collections.Counter()
    unknown = collections.Counter()
    multi_channel = 0
    for record in records:
        channels.update(record.channels)
        dates[record.site_time] += 1
        flags.update(record.date_flags)
        unknown.update(record.unknown_labels)
        multi_channel += len(record.channels) > 1
        if record.site_time == 'span_compatible':
            compatible.update(record.channels)
    sizes = collections.Counter(collections.Counter(blocks.values()).values())
    # Verify every exact association key is contained in one blocking component.
    key_blocks = collections.defaultdict(set)
    for record, kind, namespace, description in associations:
        if kind.strip() and description.strip():
            key_blocks[(kind.strip(), namespace.strip(), description.strip())].add(blocks[record])
    if any(len(v) != 1 for v in key_blocks.values()):
        raise RuntimeError('Related observations cross a blocking component')
    result = dict(status='role_evidence_prepared_no_model_evaluation', adopt=False,
        source_snapshot_sha256=sha(source_snapshot), crosswalk_sha256=sha(CONFIG/'crosswalk.json'),
        semantic_sources_sha256=sha(CONFIG/'semantic_sources.json'), producer_sha256=sha(Path(__file__)),
        role_module_sha256=sha(ROOT/'polity/role_evidence.py'),
        parser_sha256=sha(ROOT/'scripts/audit_vidarbha_preparation.py'),
        table_reader_sha256=sha(ROOT/'scripts/audit_roman_rural_preparation.py'),
        records=len(records), records_with_multiple_channels=multi_channel,
        records_per_channel=dict(sorted(channels.items())),
        span_compatible_records_per_channel=dict(sorted(compatible.items())),
        site_time_states=dict(sorted(dates.items())), date_flags=dict(sorted(flags.items())),
        unknown_source_labels=dict(sorted(unknown.items())),
        source_PHASE_DATE1_nonempty=sum(bool(r['phasedate1']) for r in sites),
        source_PHASE_DATE2_nonempty=sum(bool(r['phasedate2']) for r in sites),
        phase_fields_interpreted=False, role_specific_dates_known=0,
        association_blocking=dict(components=sum(sizes.values()),
            component_size_histogram={str(k): v for k, v in sorted(sizes.items())},
            records_in_nontrivial_components=sum(k*v for k,v in sizes.items() if k>1),
            largest_component=max(sizes, default=0), all_keys_contained=True,
            components_are_not_physical_places=True, folds_assigned=False,
            spatial_independence_established=False),
        coordinates=dict(client_map_crs='EPSG:3857', CSV_MAP_crs_assigned=False,
            CSV_MAP_precision_assigned=False, transformed=False),
        physical_places_resolved=False, population_allocated=False,
        institution_staff_or_actor_assigned=False, model_scores_computed=False,
        target_maps_generated=False,
        limits='Context channels may coexist; their sum is not a settlement/population total. Date spans are not role dates. Association blocks prevent exact-key leakage, not all place/spatial leakage. Source-selected British records overlap Roman development; no independent/sealed status.')
    write(OUT/'audit.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

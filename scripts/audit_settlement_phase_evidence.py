"""Audit change dates and related-observation blocks; no dated-role imputation."""
import collections
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import table,identifier,sha,write
from polity.role_evidence import association_blocks
from polity.settlement_phase_evidence import change_evidence,review_blocks

CONFIG=ROOT/'calibration/settlement_phase_evidence_20261111'
CACHE=ROOT/'data/cache/roman_rural_britain_2018'
OUT=ROOT/'output/settlement_phase_evidence_20261111'


def component_summary(blocks):
    sizes=collections.Counter(collections.Counter(blocks.values()).values())
    return dict(components=sum(sizes.values()),nontrivial_components=sum(v for k,v in sizes.items() if k>1),
        records_in_nontrivial_components=sum(k*v for k,v in sizes.items() if k>1),
        largest_component=max(sizes,default=0))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    snapshot=ROOT/'output/roman_rural_preparation_20261110/source_snapshot.json'
    for source in json.loads(snapshot.read_text())['files']:
        if sha(CACHE/source['name'])!=source['sha256']:raise ValueError('Changed cached observation table')
    semantics=json.loads((CONFIG/'semantic_sources.json').read_text())
    if sha(ROOT/'data/cache/roman_rural_britain_metadata/web/overview.cfm')!=semantics['web_scope']['sha256']:
        raise ValueError('Changed source coverage description')
    for source in semantics['book_sources']:
        path=ROOT/'data/cache/roman_rural_britain_metadata/book'/source['cache_text']
        if sha(path)!=source['text_sha256']:raise ValueError('Changed cached methodology text')
    for finding in semantics['findings']:
        text=' '.join((ROOT/'data/cache/roman_rural_britain_metadata/book'/finding['source']).read_text().split())
        for anchor in finding.get('anchors',[]):
            if anchor not in text:raise ValueError('Source-methodology anchor absent: '+anchor)
    core,_=table((CACHE/'rrs_core_data.csv').read_bytes(),['ID'])
    sites,_=table((CACHE/'rrs_site_data.csv').read_bytes(),['ID'])
    assoc,_=table((CACHE/'rrs_associd.csv').read_bytes(),['ID'],'PRN')
    ids={identifier(r['id']) for r in core}
    if ids!={identifier(r['id']) for r in sites}:raise ValueError('Unmatched source records')
    states=collections.Counter();flags=collections.Counter();change_flags=collections.Counter();unknown_roles=0
    for row in sites:
        evidence=change_evidence(row['datestart'],row['dateend'],row['phasedate1'],row['phasedate2'])
        states[evidence.status]+=1;flags.update(evidence.flags)
        if evidence.recorded_changes:change_flags.update(evidence.flags)
        unknown_roles+=not evidence.role_intervals_assigned
    associations=[(identifier(r['id']),r['type'],r['hername'],r['descr']) for r in assoc]
    base=association_blocks(ids,associations)
    reviewed=review_blocks([(identifier(r['id']),r['county'],r['sitename'],r['xrefmap'],r['yrefmap']) for r in core],associations)
    # Every old component is contained in one new block; no observation disappears.
    old_to_new=collections.defaultdict(set)
    for key,value in base.items():old_to_new[value].add(reviewed[key])
    assert set(reviewed)==ids and all(len(v)==1 for v in old_to_new.values())
    collisions={}
    for label,key in [('exact_numeric_XY',lambda r:(float(r['xrefmap']),float(r['yrefmap']))),
                       ('county_name',lambda r:(' '.join(r['county'].casefold().split()),' '.join(r['sitename'].casefold().split())))]:
        counts=collections.Counter(key(r) for r in core)
        collisions[label]=dict(shared_keys=sum(v>1 for v in counts.values()),
            records_at_shared_keys=sum(v for v in counts.values() if v>1))
    roles,_=table((CACHE/'rrs_site_t_minor.csv').read_bytes(),['ID'],'STMID')
    byid=collections.defaultdict(set)
    for row in roles:byid[identifier(row['id'])].add(row['sitetypeminor'].casefold().strip())
    farm_villa={key for key,labels in byid.items() if {'farm','villa'}<=labels}
    result=dict(status='exposed_chronology_identity_audit_no_model_evaluation',adopt=False,
        plan_sha256=sha(CONFIG/'plan.json'),semantic_sources_sha256=sha(CONFIG/'semantic_sources.json'),
        original_source_snapshot_sha256=sha(snapshot),producer_sha256=sha(Path(__file__)),
        phase_module_sha256=sha(ROOT/'polity/settlement_phase_evidence.py'),
        frozen_role_module_sha256=sha(ROOT/'polity/role_evidence.py'),
        parser_sha256=sha(ROOT/'scripts/audit_vidarbha_preparation.py'),
        table_reader_sha256=sha(ROOT/'scripts/audit_roman_rural_preparation.py'),records=len(sites),
        phase_status=dict(sorted(states.items())),all_record_flags=dict(sorted(flags.items())),
        change_record_flags=dict(sorted(change_flags.items())),
        purpose_of_general_change_fields_documented=True,direct_export_column_dictionary_available=False,
        records_with_farm_and_villa_labels=len(farm_villa),records_without_dated_role_intervals=unknown_roles,
        labels_can_describe_successive_roles=True,
        identity=dict(collision_keys=collisions,original_association_blocks=component_summary(base),
            extended_review_blocks=component_summary(reviewed),all_observations_retained=True,
            all_original_components_contained=True,physical_place_merges_performed=False,
            target_place_count_imposed=False,spatial_independence_established=False),
        model_scores_computed=False,population_staff_actor_assigned=False,production_maps_changed=False,
        limits='Major change dates do not identify which role changed, continuous occupation or AD200 institutions. Exact names/points support validation blocking, not automatic physical-place merging. No independent/global qualification or role frequency census.')
    write(OUT/'audit.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()

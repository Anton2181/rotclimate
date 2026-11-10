"""Frozen S2 preparation: records, roles, dates and coverage; no model evaluation.

Raw CSVs stay in the local cache. Public outputs contain aggregate diagnostics
and source identities only, not site rows or coordinates.
"""
import collections
import concurrent.futures
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_vidarbha_preparation import read_table,normalized,number

PLAN=ROOT/'calibration/roman_rural_preparation_20261110/plan.json'
META=ROOT/'calibration/roman_rural_preparation_20261110/metadata_sources.json'
CACHE=ROOT/'data/cache/roman_rural_britain_2018'
OUT=ROOT/'output/roman_rural_preparation_20261110'
BASE='https://archaeologydataservice.ac.uk/catalogue/adsdata/arch-1352-1/dissemination/csv/'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def identifier(value):
    text='' if value is None else str(value).strip()
    # Source schema declares integral numeric keys. Keep non-integral/unexpected
    # tokens visible rather than inventing a numeric/fuzzy match.
    if re.fullmatch(r'[+-]?\d+(?:\.0+)?',text):return str(int(text.split('.')[0]))
    return text


def table(data,required,primary_key='ID'):
    headers,rows,format_=read_table(data)
    mapping={normalized(h):h for h in headers}
    missing=[h for h in required if normalized(h) not in mapping]
    if missing:raise ValueError('Missing documented fields: '+','.join(missing))
    result=[{normalized(h):str(r.get(h,'') or '').strip() for h in headers} for r in rows]
    text=data.decode(format_['encoding'])
    raw=csv.reader(io.StringIO(text,newline=''),dialect='excel');raw_headers=next(raw)
    bad=[any(v.strip() for v in row[len(raw_headers):]) or any(v.strip() for v,h in zip(row,raw_headers) if not h.strip())
         for row in raw if any(v.strip() for v in row)]
    if len(bad)!=len(result):raise ValueError('Row audit disagrees with parsed rows')
    for r,malformed in zip(result,bad):r['__malformed']=malformed
    ids=[identifier(r.get('id')) for r in result]
    primary=[identifier(r.get(normalized(primary_key))) for r in result]
    stats=dict(rows=len(result),nonempty_ids=sum(bool(i) for i in ids),unique_ids=len(set(ids)-{''}),
        repeated_reference_id_rows=sum(bool(i) for i in ids)-len(set(ids)-{''}),
        primary_key=primary_key,nonempty_primary_keys=sum(bool(v) for v in primary),
        unique_primary_keys=len(set(primary)-{''}),duplicate_primary_key_rows=sum(bool(v) for v in primary)-len(set(primary)-{''}),
        malformed_rows=sum(bad),headers=headers,format=format_)
    return result,stats


def date_summary(rows):
    counts=collections.Counter()
    for row in rows:
        a,b=number(row.get('datestart')),number(row.get('dateend'))
        if a is None or b is None:counts['missing_or_nonnumeric_endpoint']+=1;continue
        counts['both_numeric']+=1
        if a==0 or b==0:counts['zero_valued_endpoint']+=1
        if a>b:counts['inverted_interval']+=1;continue
        counts['ordered_interval']+=1
        if a<=200<=b:
            counts['apparent_AD200_compatible']+=1
            if a==0 or b==0:counts['compatible_with_zero_endpoint']+=1
        if a<0 or b<0:counts['BC_endpoint']+=1
    return dict(counts)


def role_summary(rows,known_ids,labels,column):
    field=normalized(column);by_id=collections.defaultdict(set);counts=collections.Counter()
    valid_labels={s.casefold().strip() for s in labels}
    orphan=unknown=blank=duplicate=0
    for r in rows:
        key=identifier(r.get('id'));role=r.get(field,'').strip();canonical=role.casefold()
        if key not in known_ids:orphan+=1
        if not role:blank+=1;continue
        if canonical not in valid_labels:unknown+=1
        if canonical in by_id[key]:duplicate+=1
        by_id[key].add(canonical)
    for roles in by_id.values():counts.update(roles)
    return dict(rows=len(rows),records_with_roles=len(by_id),multi_role_records=sum(len(v)>1 for v in by_id.values()),
        orphan_rows=orphan,unknown_label_rows=unknown,blank_label_rows=blank,duplicate_role_rows=duplicate,
        records_per_role=dict(sorted(counts.items())),roles_are_not_independent_populations=True)


def main():
    plan=json.loads(PLAN.read_text());metadata=json.loads(META.read_text())
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    previous=json.loads((OUT/'source_snapshot.json').read_text()) if (OUT/'source_snapshot.json').exists() else None
    expected={r['name']:r['sha256'] for r in previous['files']} if previous else {}
    def acquire(name):
        path=CACHE/name;url=BASE+name+'%26hs%3Dtrue'
        if not path.exists():
            request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0',
                'Referer':'https://archaeologydataservice.ac.uk/archives/view/romangl/downloads.cfm'})
            with urllib.request.urlopen(request,timeout=30) as response:data=response.read()
            if b'<html' in data[:1000].lower():raise ValueError('HTML rather than source CSV')
            path.write_bytes(data)
        digest=sha(path)
        if name in expected and digest!=expected[name]:raise ValueError('Source snapshot changed: '+name)
        return dict(name=name,url=url,sha256=digest,bytes=path.stat().st_size,published_source_checksum=None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        sources=list(executor.map(acquire,plan['requested_tables']))
    if not previous:
        write(OUT/'source_snapshot.json',dict(source_doi=plan['source_doi'],plan_sha256=sha(PLAN),files=sources,
            raw_source_tables_redistributed=False,checksum_scope='Locally recorded content hashes, not independent archive checksums.'))
    elif previous['plan_sha256']!=sha(PLAN):raise ValueError('Changed preparation protocol')
    data={};stats={}
    required={'rrs_core_data.csv':['ID','AREA'],
        'rrs_site_data.csv':['ID','DATE_START','DATE_END','SETTLEMENT_SIZE'],
        'rrs_site_t_major.csv':['ID','SITE_TYPE_MAJOR'],
        'rrs_site_t_minor.csv':['ID','SITE_TYPE_MINOR'],
        'rrs_associd.csv':['ID','TYPE','DESCR','HER_NAME']}
    for name in plan['requested_tables']:
        pk='STMID' if name in ['rrs_site_t_major.csv','rrs_site_t_minor.csv'] else 'PRN' if name=='rrs_associd.csv' else 'ID'
        data[name],stats[name]=table((CACHE/name).read_bytes(),required[name]+[pk],primary_key=pk)
    core,sites=data['rrs_core_data.csv'],data['rrs_site_data.csv']
    core_ids={identifier(r.get('id')) for r in core}-{''};site_ids={identifier(r.get('id')) for r in sites}-{''}
    coord=collections.Counter();area=collections.Counter()
    documented_columns={'xref','yref'}.issubset(core[0])
    map_columns={'xrefmap','yrefmap'}.issubset(core[0])
    for row in core:
        if documented_columns:
            ex,ny=row['xref'],row['yref'];a,b=number(ex),number(ny)
            if a is None or b is None:coord['missing_or_nonnumeric']+=1
            else:
                coord['numeric_pairs']+=1
                if 0<=a<=700000 and 0<=b<=1300000:coord['broad_OSGB_bounds']+=1
                if a==0 and b==0:coord['zero_pair']+=1
            if len(ex)==6 and len(ny)==6:coord['six_character_pairs']+=1
            if ex.startswith('0') or ny.startswith('0'):coord['leading_zero_present']+=1
        if map_columns:
            coord['exported_MAP_numeric_pairs']+=number(row['xrefmap']) is not None and number(row['yrefmap']) is not None
        value=number(row['area'])
        area['missing_or_nonnumeric' if value is None else 'positive_investigated_area' if value>0 else 'nonpositive']+=1
    lookup={}
    for name in ['_lkup_site_type_mjor.csv','_lkup_site_type_minor.csv']:
        source=next(r for r in metadata['successful_files'] if r['name']==name)
        path=ROOT/'data/cache/roman_rural_britain_metadata'/name
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True)
            request=urllib.request.Request(source['url'],headers={'User-Agent':'Mozilla/5.0',
                'Referer':'https://archaeologydataservice.ac.uk/archives/view/romangl/downloads.cfm'})
            with urllib.request.urlopen(request,timeout=30) as response:body=response.read()
            if hashlib.sha256(body).hexdigest()!=source['sha256']:raise ValueError('Source metadata changed')
            path.write_bytes(body)
        if sha(path)!=source['sha256']:raise ValueError('Changed metadata lookup')
        h,rows,_=read_table(path.read_bytes());lookup[name]=[str(r[h[0]]).strip() for r in rows]
    major=role_summary(data['rrs_site_t_major.csv'],site_ids,lookup['_lkup_site_type_mjor.csv'],'SITE_TYPE_MAJOR')
    minor=role_summary(data['rrs_site_t_minor.csv'],site_ids,lookup['_lkup_site_type_minor.csv'],'SITE_TYPE_MINOR')
    sizes=collections.Counter(r['settlementsize'] for r in sites if r['settlementsize'])
    associations=collections.defaultdict(set);association_orphans=0
    for row in data['rrs_associd.csv']:
        key=identifier(row.get('id'))
        if key not in core_ids:association_orphans+=1
        if row['descr']:associations[(row['type'],row['hername'],row['descr'])].add(key)
    shared=collections.Counter(k[0] for k,ids in associations.items() if len(ids)>1)
    result=dict(status='preparation_only_no_model_evaluation',adopt=False,plan_sha256=sha(PLAN),
        source_snapshot_sha256=sha(OUT/'source_snapshot.json'),producer_sha256=sha(Path(__file__)),
        parser_source_sha256=sha(ROOT/'scripts/audit_vidarbha_preparation.py'),tables=stats,
        record_joins=dict(core_unique_ids=len(core_ids),site_unique_ids=len(site_ids),common_ids=len(core_ids&site_ids),
            site_ids_without_core=len(site_ids-core_ids),core_ids_without_site=len(core_ids-site_ids),association_orphan_rows=association_orphans),
        coordinates=dict(coord,documented_X_REF_Y_REF_present=documented_columns,exported_MAP_fields_present=map_columns,
                         MAP_units_assigned=False),coordinate_transform_performed=False,
        clean_joined_record_ids=len({identifier(r.get('id')) for r in core if not r['__malformed']}&
                                   {identifier(r.get('id')) for r in sites if not r['__malformed']}),
        occupation_intervals=date_summary(sites),
        major_roles=major,minor_roles=minor,size_fields=dict(investigated_AREA=dict(area),
            settlement_size_nonempty=sum(sizes.values()),settlement_size_distinct=len(sizes),
            short_size_wordlist_counts={s:n for s,n in sorted(sizes.items()) if len(s)<=80},
            long_size_label_records=sum(n for s,n in sizes.items() if len(s)>80),population_estimated=False),
        shared_association_identifiers=dict(shared),physical_settlement_groups_inferred=False,
        model_predictions_loaded=False,model_scores_computed=False,target_maps_generated=False,
        limits='Record IDs are not proven unique settlements; size/roles/date intervals do not establish population, phase-specific functions or political authority. British source overlaps Roman development; no independent/sealed status.')
    write(OUT/'audit.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()

"""Preparation-only source audit; no prediction lookup, fitting, target maps or scores."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from settlement_locations_earth import sha,write

PLAN=ROOT/'calibration/vidarbha_preparation_20261110/plan.json'
CACHE=ROOT/'data/cache/vidarbha_2020'
OUT=ROOT/'output/vidarbha_preparation_20261110'


def normalized(name):return re.sub('[^a-z0-9]','',str(name).lower())


def read_table(data):
    for encoding in ('utf-8-sig','cp1252','mac_roman'):
        try:text=data.decode(encoding);break
        except UnicodeDecodeError:continue
    else:raise ValueError('Unsupported text encoding')
    dialect=csv.Sniffer().sniff(text[:8000],delimiters=',;\t')
    reader=csv.reader(io.StringIO(text,newline=''),dialect=dialect)
    raw=next(reader);named=[(i,h.strip()) for i,h in enumerate(raw) if h.strip()]
    headers=[h for _,h in named]
    if len(set(headers))!=len(headers):raise ValueError('Duplicate named CSV headers')
    unnamed=[i for i,h in enumerate(raw) if not h.strip()]
    rows=[];unnamed_cells=extra_cells=0
    for values in reader:
        if not any(v.strip() for v in values):continue
        unnamed_cells+=sum(bool(values[i].strip()) for i in unnamed if i<len(values))
        extra_cells+=sum(bool(v.strip()) for v in values[len(raw):])
        rows.append({h:values[i] if i<len(values) else '' for i,h in named})
    return headers,rows,dict(encoding=encoding,delimiter=dialect.delimiter,total_columns=len(raw),
        blank_header_columns=len(unnamed),nonempty_unnamed_cells=unnamed_cells,nonempty_extra_cells=extra_cells)


def number(value):
    try:
        result=float(str(value).strip())
        return result if math.isfinite(result) else None
    except (ValueError,TypeError):return None


def inspect_table(data):
    headers,rows,format_=read_table(data)
    columns={normalized(h):h for h in headers}
    def values(key):return [r.get(columns.get(key,''),'') for r in rows]
    ids=[str(v or '').strip() for v in values('sitecode')]
    nonempty=[v for v in ids if v]
    x,y=values('xcoord'),values('ycoord')
    valid=plausible=swapped=0
    for xv,yv in zip(x,y):
        lat,lon=number(xv),number(yv)
        if lat is None or lon is None:continue
        valid+=1
        plausible+=16<=lat<=25 and 72<=lon<=85
        swapped+=16<=lon<=25 and 72<=lat<=85
    fields={}
    for name in headers:
        key=normalized(name)
        if any(token in key for token in ('date','period','accuracy','discov','survey','aim','siteinterp')):
            vals=[str(r.get(name,'') or '').strip() for r in rows]
            fields[name]=dict(nonempty=sum(bool(v) for v in vals),distinct_nonempty=len({v for v in vals if v}))
    date_headers=[h for h in headers if 'date' in normalized(h) or 'period' in normalized(h)]
    broad={}
    for term,pattern in [('early_historic',r'early[ -]?historic'),('megalithic',r'megalith'),('medieval',r'medieval'),('explicit_era_text',r'\b(?:BCE?|AD|CE)\b')]:
        broad[term]=sum(bool(re.search(pattern,' '.join(str(r.get(h,'') or '') for h in date_headers),re.I)) for r in rows)
    return dict(headers=headers,rows=len(rows),format=format_,site_id_nonempty=len(nonempty),
        unique_site_ids=len(set(nonempty)),duplicate_site_id_rows=len(nonempty)-len(set(nonempty)),
        site_id_styles=dict(digits_only=sum(v.isdigit() for v in nonempty),prefixed=sum(bool(re.match(r'^[A-Za-z]',v)) for v in nonempty)),
        documented_coordinate_columns_present='xcoord' in columns and 'ycoord' in columns,
        numeric_coordinate_pairs=valid,plausible_documented_axis_pairs=int(plausible),plausible_swapped_axis_pairs=int(swapped),
        metadata_field_completeness=fields,date_text_flags=broad),set(nonempty)


def main():
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    url='https://zenodo.org/api/records/3667657'
    with urllib.request.urlopen(url,timeout=30) as response:metadata=json.load(response)
    manifests=[];tables={};ids={}
    names=['Vidarbha_SiteMasterList.csv','Vidarbha_SettlementSites.csv']
    for name in names:
        source=next(f for f in metadata['files'] if f['key']==name)
        path=CACHE/name
        if not path.exists():
            with urllib.request.urlopen(source['links']['self'],timeout=45) as response:data=response.read()
            kind,digest=source['checksum'].split(':')
            if hashlib.new(kind,data).hexdigest()!=digest:raise ValueError('Source checksum mismatch')
            path.write_bytes(data)
        data=path.read_bytes();kind,digest=source['checksum'].split(':')
        if hashlib.new(kind,data).hexdigest()!=digest:raise ValueError('Cached source differs from frozen record')
        tables[name],ids[name]=inspect_table(data)
        manifests.append(dict(name=name,bytes=len(data),source=source,sha256=hashlib.sha256(data).hexdigest()))
    master,settlement=names
    common=len(ids[master]&ids[settlement])
    reasons=[]
    if not common:reasons.append('No settlement IDs join the supplied coordinate master list')
    if tables[master]['plausible_documented_axis_pairs']==0:
        reasons.append('No coordinate row passes the documented-axis regional envelope; swapped-axis plausibility is diagnostic only')
    if tables[settlement]['duplicate_site_id_rows']:
        reasons.append('Duplicate settlement IDs need source-level resolution')
    result=dict(status='preparation_only_no_model_scores',adopt=False,plan_sha256=sha(PLAN),
        source=dict(doi=metadata['doi'],license=metadata['metadata'].get('license'),api=url,files=manifests),
        tables=tables,joins=dict(master_unique_ids=len(ids[master]),settlement_unique_ids=len(ids[settlement]),
            common_ids=common,casefold_common_ids=len({v.casefold() for v in ids[master]}&{v.casefold() for v in ids[settlement]}),
            settlement_ids_missing_from_master=len(ids[settlement]-ids[master])),
        decision=dict(ready_for_located_transfer=False if reasons else True,reasons=reasons,
            no_automatic_axis_swap=True,no_fuzzy_id_join=True),
        targets_prepared=True,model_predictions_loaded=False,model_scores_computed=False,
        source_sha256=sha(Path(__file__)),
        interpretation='Archaeological literature records, not a complete settlement/population census. No automatic independent or sealed status. No AD200 date invented from broad eras.')
    write(OUT/'audit.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()

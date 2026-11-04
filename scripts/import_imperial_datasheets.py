"""Extract allowlisted geographic evidence; never execute workbook content.

Raw workbooks can contain unrelated game/player material and are not published.
Run with the two local XLSX paths; the committed JSON is sufficient downstream.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def extract(reference, master, authority):
    import openpyxl
    from polity.administration import commandery_key, name_key
    sources={}
    for label,path in [('commanderies',reference),('map',master)]:
        path=Path(path)
        sources[label]=dict(filename=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
    # Cached values only: no formula evaluation, external-link resolution or
    # interpretation of notes/instructions embedded in the spreadsheets.
    ref=openpyxl.load_workbook(reference,read_only=True,data_only=True,keep_links=False)
    book=openpyxl.load_workbook(master,read_only=True,data_only=True,keep_links=False)
    canonical={name_key(c['name']):c for c in authority['commanderies']}
    commanderies=[]
    for rownum,row in enumerate(ref.active.values,1):
        if rownum==1 or len(row)<2 or not row[1]:continue
        name=str(row[1]).strip()
        if name_key(name) not in canonical:raise ValueError('Unknown reference commandery: '+name)
        commanderies.append(dict(id=commandery_key(row[0]),name=canonical[name_key(name)]['name'],
            listed_name=name,region=row[2] if len(row)>2 else None,source_sheet=ref.active.title,source_row=rownum))
    ids={c['id'] for c in commanderies}
    if len(ids)!=len(commanderies) or {c['name'] for c in commanderies}!={c['name'] for c in authority['commanderies']}:
        raise ValueError('Reference IDs must uniquely cover the owner list')
    towns=[]
    def at(row,i):return row[i] if len(row)>i else None
    def text(value):return str(value).strip() if value is not None else None
    for rownum,row in enumerate(book['TownsCities'].values,1):
        if rownum==1 or not row or not isinstance(row[0],(int,float)):continue
        cid=commandery_key(at(row,8))
        towns.append(dict(hex=int(row[0]),name=text(at(row,1)),listed_type=text(at(row,2)),
            province=text(at(row,6)),commandery_name=text(at(row,7)),commandery_id=cid if cid in ids else None,
            commandery_seat=text(at(row,10))=='X',provincial_seat=text(at(row,11))=='X',
            source_sheet='TownsCities',source_row=rownum))
    hexes=[]
    for rownum,row in enumerate(book['Hex'].values,1):
        if rownum<=2 or not row or not isinstance(row[0],(int,float)):continue
        cid=commandery_key(at(row,1))
        if cid not in ids:continue
        hexes.append(dict(hex=int(row[0]),commandery_id=cid,commandery_name=text(at(row,2)),
            province=text(at(row,3)),region=text(at(row,4)),source_sheet='Hex',source_row=rownum))
    ref.close();book.close()
    return dict(version=1,status='game-era geographic evidence, not calibrated parameters',sources=sources,
        importer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),commanderies=commanderies,towns=towns,hexes=hexes,
        scope='Only commandery identity, geographic membership, settlement type and seat flags extracted. '
        'Game supply, population/settlement maxima, wealth, loyalty, faction affiliation, fortification levels, notes and player information excluded. '
        'IDs link records; contradictory names and seat flags remain evidence, not automatic model truth.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('commanderies',type=Path);parser.add_argument('map',type=Path)
    parser.add_argument('--out',type=Path,default=ROOT/'data/imperial_datasheet_evidence.json')
    args=parser.parse_args()
    evidence=extract(args.commanderies,args.map,json.loads((ROOT/'data/imperial_administration.json').read_text()))
    args.out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:len(evidence[k]) for k in ['commanderies','towns','hexes']}))


if __name__=='__main__':main()

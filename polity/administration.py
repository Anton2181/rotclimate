"""Owner-supplied administrative roles, separately from political reach.

Named anchors and local icon evidence preserve touching settlement markers.
Founding numbers do not imply strength. Missing centres stay unlocated.
"""
import unicodedata
import difflib
import re
from collections import defaultdict
import numpy as np
from scipy import ndimage as ndi


def name_key(name):
    text=unicodedata.normalize('NFKD',name).casefold()
    return ''.join(c for c in text if c.isalnum() and not unicodedata.combining(c))


def commandery_key(value):
    """Normalize documented ID formats, without fuzzy geographic inference."""
    value=re.sub(r'[^A-Z0-9]','',str(value or '').upper()).replace('COMMANDERY','C').replace('COM','C')
    if value=='CAPITALC1':return 'CC1'
    if value.startswith('CAPITALC'):return 'CC'+value[len('CAPITALC'):]
    return value


def _colour_components(rgba,colour):
    mask=np.all(rgba[...,:3]==colour,axis=2)&(rgba[...,3]>0)
    labels,_=ndi.label(mask,structure=np.ones((3,3)))
    result=[]
    for i,box in enumerate(ndi.find_objects(labels),1):
        y,x=ndi.center_of_mass(labels[box]==i)
        result.append(dict(x=box[1].start+x,y=box[0].start+y,box=box))
    return result


def _white_run(white,x,y,axis):
    h,w=white.shape;x=int(np.clip(np.floor(x),0,w-1));y=int(np.clip(np.floor(y),0,h-1))
    if not white[y,x]:return 0
    total=1
    for direction in [-1,1]:
        for distance in range(1,24):
            yy=y+(distance*direction if axis==0 else 0);xx=x+(distance*direction if axis==1 else 0)
            if not 0<=yy<h or not 0<=xx<w or not white[yy,xx]:break
            total+=1
    return total


def named_markers(rgba,places,width,height):
    """Identify each named anchor's icon without merging neighbours."""
    rgba=np.asarray(rgba);h,w=rgba.shape[:2]
    purple=_colour_components(rgba,(178,0,255));green=_colour_components(rgba,(0,168,107))
    white=np.all(rgba[...,:3]==255,axis=2)&(rgba[...,3]>0)
    records=[]
    for i,p in enumerate(places,1):
        x=p['x']/width*w;y=p['y']/height*h;kind=None;evidence={}
        for colour,components in [('purple',purple),('green',green)]:
            if not components:continue
            c=min(components,key=lambda c:(c['x']-x)**2+(c['y']-y)**2)
            distance=float(np.hypot(c['x']-x,c['y']-y))
            if distance>2.5:continue
            box=c['box'];patch=rgba[box]
            gold=bool(np.any(np.all(patch[...,:3]==(255,216,0),axis=2)&(patch[...,3]>0)))
            size=max(box[0].stop-box[0].start,box[1].stop-box[1].start)
            kind='imperial monastery' if colour=='green' else 'imperial capital' if gold and size>14 else 'major imperial city' if gold else 'imperial fort'
            evidence=dict(colour=colour,primary_size_px=[box[1].stop-box[1].start,box[0].stop-box[0].start],gold=gold,anchor_distance_source_px=distance)
            break
        if kind is None:
            runs=[_white_run(white,x,y,axis) for axis in [0,1]]
            if min(runs)>=12:kind='fortified city'
            elif min(runs)>=7:kind='fortified town'
            else:kind='unclassified'
            evidence=dict(white_axis_runs_px=runs)
        records.append(dict(id=f'S{i:03d}',name=p['name'],x=float(p['x']),y=float(p['y']),kind=kind,
            symbol_verified=kind!='unclassified',coordinate_basis='existing named map coordinate',symbol_evidence=evidence))
    return records


def match_commanderies(commanderies,markers,sheet,evidence=None):
    by_name=defaultdict(list)
    for m in markers:by_name[name_key(m['name'])].append(m)
    # A unique sheet hex with a matching map anchor documents a spelling
    # alias, e.g. Maēγa and the OCR caption Maēya.
    rows_by_hex=defaultdict(list)
    for row in sheet['towns']:rows_by_hex[int(row[0])].append(row)
    for hid,rows in rows_by_hex.items():
        anchor=sheet['anchors'].get(str(hid))
        if len(rows)!=1 or anchor is None or by_name.get(name_key(rows[0][1])):continue
        matches=[m for m in markers if np.hypot(m['x']-anchor[0],m['y']-anchor[1])<.4]
        if len(matches)==1 and difflib.SequenceMatcher(None,name_key(matches[0]['name']),name_key(rows[0][1])).ratio()>=.75:
            by_name[name_key(rows[0][1])].append(matches[0])
    result=[]
    references={name_key(c['name']):c for c in evidence['commanderies']} if evidence else {}
    for commandery in commanderies:
        matches=by_name[name_key(commandery['centre_name'])];record=dict(commandery)
        reference=references.get(name_key(commandery['name']))
        if reference:
            cid=reference['id']
            seats=[t for t in evidence['towns'] if t['commandery_id']==cid and t['commandery_seat']]
            record.update(source_id=cid,region=reference['region'],datasheet_reference=reference,
                seat_evidence=seats,discrepancies=[])
            for seat in seats:
                if name_key(seat['commandery_name'] or '')!=name_key(commandery['name']):
                    record['discrepancies'].append('Town-sheet commandery name differs; stable ID used for linkage.')
            located=[m for t in seats for m in by_name[name_key(t['name'])]]
            # An explicit flag is useful for differently named administrative
            # seats, but cannot silently supersede a conflicting named centre.
            if len(seats)==1 and len(located)==1:
                seat=seats[0];record.update(seat_name=seat['name'],source_hex=seat['hex'],province=seat['province'],provincial_seat=seat['provincial_seat'])
                if matches and matches[0]['id']!=located[0]['id']:
                    record.update(status='ambiguous',marker_id=None,x=None,y=None,
                        candidate_markers=[dict(m) for m in matches+located])
                    record['discrepancies'].append('Owner named-centre convention and workbook seat flag identify different places; neither chosen as an authority source.')
                    result.append(record);continue
                matches=located
            elif len(seats)>1:
                record.update(status='ambiguous',marker_id=None,x=None,y=None,candidate_markers=[dict(m) for m in located])
                record['discrepancies'].append('Multiple seat flags for this ID; no seat chosen.')
                result.append(record);continue
        if len(matches)==1:
            m=matches[0]
            record.update(status='matched' if m.get('symbol_verified',m['kind']!='unclassified') else 'name_matched_position_unverified',
                marker_id=m['id'],map_name=m['name'],x=m['x'],y=m['y'],kind=m['kind'])
        else:record.update(status='ambiguous' if matches else 'unlocated',marker_id=None,x=None,y=None)
        result.append(record)
    return result


def legion_markers(rgba,width,height):
    """Locations only; never infer manpower or allegiance from founding digits."""
    rgba=np.asarray(rgba);h,w=rgba.shape[:2];labels,_=ndi.label(rgba[...,3]>0)
    result=[]
    for i,box in enumerate(ndi.find_objects(labels),1):
        y,x=ndi.center_of_mass(labels[box]==i)
        result.append(dict(id=f'L{i:02d}',kind='imperial legion',x=(box[1].start+x+.5)*width/w,
            y=(box[0].start+y+.5)*height/h,founding_number=None,number_status='not_transcribed',
            coordinate_basis='separate Imperial Legions source layer',strength=None,
            strength_status='not supplied; founding number is not manpower'))
    return result

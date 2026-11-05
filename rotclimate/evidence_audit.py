"""Trace configured numeric values to evidence without inventing calibration.

This inventory covers selected JSON configuration trees and literal top-level
Python constants, not every numeric expression embedded in model functions.
Unreviewed is an audit gap, not proof a parameter was never studied.
"""
import ast
import fnmatch
import hashlib
import json
from pathlib import Path

STATUSES={'measured_input','definition','published_relationship','earth_fit','historical_fit','scenario','unreviewed'}


def numeric_leaves(value,path=''):
    if isinstance(value,bool):return
    if isinstance(value,(int,float)):
        yield path or '/',value
    elif isinstance(value,dict):
        for k,v in value.items():yield from numeric_leaves(v,path+'/'+str(k).replace('~','~0').replace('/','~1'))
    elif isinstance(value,(list,tuple)):
        for i,v in enumerate(value):yield from numeric_leaves(v,path+'/'+str(i))


def constants(path):
    values={};unresolved=[]
    for node in ast.parse(Path(path).read_text()).body:
        if not isinstance(node,(ast.Assign,ast.AnnAssign)):continue
        targets=node.targets if isinstance(node,ast.Assign) else [node.target]
        for target in targets:
            if not isinstance(target,ast.Name) or not target.id.isupper():continue
            try:values[target.id]=ast.literal_eval(node.value)
            except (ValueError,TypeError):unresolved.append(dict(name=target.id,line=node.lineno,expression=ast.unparse(node.value)))
    return values,unresolved


def classify(path,rules):
    matched=[r for r in rules if fnmatch.fnmatchcase(path,r['pattern'])]
    if not matched:return dict(status='unreviewed',evidence=[],note='Not assigned to a reviewed evidence entry in this inventory.')
    specificity=lambda r:len(r['pattern'].replace('*','').replace('?',''))
    top=max(map(specificity,matched));best=[r for r in matched if specificity(r)==top]
    if len(best)!=1:raise ValueError('Ambiguous evidence rules for '+path)
    r=best[0]
    if r['status'] not in STATUSES:raise ValueError('Unknown evidence status')
    if r['status'] not in {'scenario','unreviewed','definition'} and not r.get('evidence'):raise ValueError('Evidence required for '+r['status'])
    return {k:v for k,v in r.items() if k!='pattern'}


def audit(root,spec):
    root=Path(root);rows=[];sources={};modules=[];evidence_hashes={}
    for m in spec['components']:
        counts={};unresolved=[];start=len(rows)
        for src in m['sources']:
            path=root/src['file'];sources[src['file']]=hashlib.sha256(path.read_bytes()).hexdigest()
            if src.get('kind')=='python_constants':value,missing=constants(path);unresolved.extend(dict(file=src['file'],**v) for v in missing)
            else:value=json.loads(path.read_text())
            allowed=src.get('roots')
            for pointer,number in numeric_leaves(value):
                if allowed and not any(pointer==p or pointer.startswith(p+'/') for p in allowed):continue
                entry=classify(pointer,src.get('rules',[]));counts[entry['status']]=counts.get(entry['status'],0)+1
                for ref in entry.get('evidence',[]):
                    if not ref.startswith(('http://','https://')):
                        if not (root/ref).exists():raise ValueError('Missing evidence reference: '+ref)
                        evidence_hashes[ref]=hashlib.sha256((root/ref).read_bytes()).hexdigest()
                rows.append(dict(component=m['id'],source=src['file'],pointer=pointer,value=number,**entry))
        modules.append(dict(id=m['id'],label=m['label'],validation=m['validation'],observables=m['observables'],next_test=m['next_test'],parameters_reviewed=len(rows)-start,counts=counts,unresolved_expressions=unresolved))
    keys=[(r['component'],r['source'],r['pointer']) for r in rows]
    if len(keys)!=len(set(keys)):raise ValueError('Duplicate configured parameter inventory')
    return dict(version=1,scope=spec['scope'],components=modules,parameters=rows,sources_sha256=sources,evidence_sha256=evidence_hashes)

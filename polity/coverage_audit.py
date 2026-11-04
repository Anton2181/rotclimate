"""Provisional affiliation evidence and coherent seasonal travel coverage.

Coverage does not assign sovereignty. A return must reach the SAME site that
supplies the outward trip; independently nearest outbound/inbound sites do
not prove a reversible journey. Travel thresholds are supplied scenarios.
"""
from collections import defaultdict
import numpy as np
from scipy.sparse.csgraph import dijkstra
from .administration import name_key

SCENARIOS=('evidence','claim_sites','generated')
BUDGETS=(1.,2.,4.)


def source_inventory(inventory,aliases,actors):
    actors=set(actors);owner_map={name_key(k):v for k,v in aliases['owner_aliases'].items()}
    if any(a not in actors for a in owner_map.values()):raise ValueError('Alias points to an unknown actor')
    commandery_markers={c['marker_id'] for c in inventory['commanderies'] if c['status']=='matched'}
    commandery_ids={c['source_id'] for c in inventory['commanderies']}
    result=[]
    for m in inventory['markers']:
        signals=[];unmapped=[]
        for row in m.get('datasheet_records',[]):
            if row.get('commandery_id') in commandery_ids:
                signals.append(dict(actor='Xšāça',basis='workbook commandery ID',row=row.get('source_row')))
            elif row.get('province'):
                actor=owner_map.get(name_key(row['province']))
                if actor:signals.append(dict(actor=actor,basis='explicit workbook owner alias',source_name=row['province'],row=row.get('source_row')))
                else:unmapped.append(row['province'])
        if m['id'] in commandery_markers:signals.append(dict(actor='Xšāça',basis='verified commandery-marker linkage'))
        if m['kind'].startswith('imperial') or m['kind']=='major imperial city':
            signals.append(dict(actor='Xšāça',basis='owner-supplied imperial icon key'))
        choices={s['actor'] for s in signals}
        if not m['symbol_verified']:status='position_unverified';actor=None
        elif len(choices)>1:status='affiliation_conflict';actor=None
        elif len(choices)==1 and not unmapped:status='evidence_linked';actor=next(iter(choices))
        else:status='affiliation_unresolved';actor=None
        result.append(dict(id=m['id'],name=m['name'],x=m['x'],y=m['y'],kind=m['kind'],symbol_verified=m['symbol_verified'],
            actor=actor,status=status,signals=signals,unmapped_owner_names=unmapped))
    return result


def node_memberships(records,generated,claim_actor,snap,actors):
    """Nested source hypotheses. Claim fill supplies ONLY uncertain additions."""
    actor_index={a:i for i,a in enumerate(actors)};nodes=defaultdict(lambda:dict(memberships=set(),unknown=False,record_ids=[]))
    counts=np.zeros((3,len(actors)),int)
    records=[dict(r) for r in records]
    for r in records:
        if not r['symbol_verified']:continue
        n=snap(r['x'],r['y']);r['node']=n
        if r['actor'] is not None:actor=r['actor'];stages=(0,1,2);basis='evidence'
        else:
            nodes[n]['unknown']=True;actor=claim_actor(n);stages=(1,2) if actor else ();basis='painted claim only' if actor else 'unresolved'
        r.update(scenario_actor=actor,scenario_basis=basis)
        nodes[n]['record_ids'].append(r['id'])
        for s in stages:nodes[n]['memberships'].add((s,actor_index[actor]))
    for n in generated:
        actor=claim_actor(n)
        if actor:nodes[int(n)]['memberships'].add((2,actor_index[actor]))
    for v in nodes.values():
        for s,a in v['memberships']:counts[s,a]+=1
    return dict(nodes),counts,records


def site_codes(graph,reverse,source,land_nodes,budgets=BUDGETS):
    """Sparse threshold classes: 3≤1day, 2≤2days, 1≤4days, 0 outside.

    Output rows retain their land-index identity; codes are computed from one
    source before merging, which prevents cross-site return substitution.
    """
    budgets=np.asarray(budgets,float)
    if budgets.shape!=(3,) or not np.isfinite(budgets).all() or np.any(budgets<=0) or np.any(np.diff(budgets)<=0):raise ValueError('Three increasing positive budgets required')
    out=dijkstra(graph,directed=True,indices=int(source),limit=float(budgets[-1]))[land_nodes]
    back=dijkstra(reverse,directed=True,indices=int(source),limit=float(budgets[-1]))[land_nodes]
    keep=np.flatnonzero(out<=budgets[-1])
    one=(3-np.searchsorted(budgets,out[keep],side='left')).astype('u1')
    both=(3-np.searchsorted(budgets,np.maximum(out[keep],back[keep]),side='left')).astype('u1')
    return keep,one,both


def merge_site(month,unknown,node,result):
    idx,one,both=result
    for s,a in node['memberships']:
        month[s,a,0,idx]=np.maximum(month[s,a,0,idx],one)
        month[s,a,1,idx]=np.maximum(month[s,a,1,idx],both)
    if node['unknown']:
        unknown[0,idx]=np.maximum(unknown[0,idx],one)
        unknown[1,idx]=np.maximum(unknown[1,idx],both)


def seasonal_mask(words,budget_index):
    if budget_index not in (0,1,2):raise ValueError('Budget index required')
    words=np.asarray(words,np.uint32);result=np.zeros(words.shape,np.uint16)
    for m in range(12):result|=((((words>>(2*m))&3)>=(3-budget_index)).astype(np.uint16)<<m)
    return result


def aggregate_words(words):
    """Max classes per month, never bitwise-OR independent two-bit codes."""
    words=np.asarray(words,np.uint32);out=np.zeros(words.shape[1:],np.uint32)
    for m in range(12):out|=np.max((words>>(2*m))&3,axis=0)<<(2*m)
    return out

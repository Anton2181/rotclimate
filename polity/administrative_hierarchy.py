"""Recorded administrative links and directed, additive person-travel times.

This is an isolated hierarchy scenario, not a control or courier-speed model.
Parallel transport edges are alternatives; legacy atlas graphs are unchanged.
"""
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from . import control as C, seasons as S, transport as X

LEGS=('capital_to_province','province_to_seat','seat_to_province','province_to_capital')


def hierarchy(inventory):
    rows=inventory['commanderies']
    marker_ids=[m['id'] for m in inventory['markers'] if m['kind']=='imperial capital']
    capitals=[c for c in rows if c.get('marker_id') in marker_ids and c['status']=='matched']
    if len(capitals)!=1:raise ValueError('One verified imperial capital required')
    capital=capitals[0];provinces={}
    for c in rows:
        if c.get('provincial_seat'):
            name=c.get('province')
            if not name or name in provinces:raise ValueError('Unique provincial seat required: '+str(name))
            provinces[name]=c
    if len({c['source_id'] for c in rows})!=len(rows):raise ValueError('Unique commandery IDs required')
    links=[]
    for c in rows:
        parent=provinces.get(c.get('province'))
        status='located' if c['status']=='matched' and parent and parent['status']=='matched' else 'unresolved_seat' if c['status']!='matched' else 'unresolved_province'
        links.append(dict(commandery_id=c['source_id'],name=c['name'],seat_name=c.get('map_name') or c.get('seat_name'),
            province=c.get('province'),province_id=parent['source_id'] if parent else None,
            province_seat=parent.get('map_name') if parent else None,capital_id=capital['source_id'],
            x=c.get('x'),y=c.get('y'),status=status,inventory_status=c['status'],
            local_self_link=bool(parent and parent['source_id']==c['source_id']),
            imperial_self_link=bool(parent and parent['source_id']==capital['source_id'])))
    return dict(capital_id=capital['source_id'],provinces={n:c['source_id'] for n,c in provinces.items()},links=links)


def minimum_graph(n,edges):
    """CSR that selects the least duration for each directed parallel pair."""
    r,c,d=[np.concatenate([np.asarray(e[i]) for e in edges]) for i in range(3)]
    if any(a.ndim!=1 or len(a)!=len(r) for a in [r,c,d]):raise ValueError('Aligned edge arrays required')
    if r.dtype.kind not in 'iu' or c.dtype.kind not in 'iu' or np.any((r<0)|(r>=n)|(c<0)|(c>=n)):
        raise ValueError('Valid integer edge nodes required')
    if not np.isfinite(d).all() or np.any(d<=0):raise ValueError('Finite positive travel durations required')
    order=np.lexsort((d,c,r));r,c,d=r[order],c[order],d[order]
    first=np.r_[True,(r[1:]!=r[:-1])|(c[1:]!=c[:-1])] if len(r) else np.zeros(0,bool)
    return csr_matrix((d[first],(r[first],c[first])),shape=(n,n)),int(len(r)-np.sum(first))


def month_graph(world,st,cl,m,ports,river_places):
    """Fastest additive travel under fixed monthly conditions.

    Sailing uses the existing beat-or-wait edge costs, with no whole-voyage
    fair-weather-spell blending. No relay couriers, handling time or capacity.
    """
    land=st['land'];cell_km=world['cell_km'];mud=cl['mud'][m]
    flood=S.flood_index(cl['flow'][m][st['basin']])
    cross=np.where(st['basin']>0,S.CROSS_DAYS*(1+S.FLOOD_GAIN*flood),0.)
    edges=[C.foot_edges(world['elev'],land,world['road'],S.month_terrain(st['eta'],cl,m),cell_km,
        st['paths'],world.get('ferry'),world.get('tracks'),road_factor=1+(S.MUD_ROAD-1)*mud,
        track_factor=1+(S.MUD_COEFFICIENT-1)*mud,cross=cross)]
    sea_args=(st['water'],world['u'][m],world['v'][m],world['wind'][m],cl['steadiness'][m],cl['sea'][m],cell_km,st['coast_km'])
    edges.append(X.sea_edges_rule(*sea_args,mode='beat') if X.SAILING_RULE=='wait' else X.sea_edges(*sea_args))
    if len(ports):edges.append(X.harbour_edges(land,st['water'],list(ports),cell_km))
    cells=np.zeros(0,np.int64)
    if len(st['river_cells']):
        rr,rc,rd,cells=X.river_edges(st['basin'],st['steps'],cl['flow'][m],cell_km,land.size)
        edges.extend([(rr,rc,rd),X.river_harbour_edges(cells,land.size,list(river_places),land.shape)])
    return minimum_graph(land.size+len(cells),edges)


def parent_times(graph,parent,capital,children,reverse=None):
    """All four directed legs from two searches per provincial parent."""
    out=dijkstra(graph,directed=True,indices=int(parent))
    incoming=dijkstra(graph.T.tocsr() if reverse is None else reverse,directed=True,indices=int(parent))
    children=np.asarray(children,np.int64)
    return np.column_stack([np.full(len(children),incoming[capital]),out[children],incoming[children],np.full(len(children),out[capital])])


def reply_times(days):
    days=np.asarray(days,float)
    if days.shape[-1]!=4 or np.any(days<0):raise ValueError('Four nonnegative directed legs required')
    return days[...,1]+days[...,2],np.sum(days,axis=-1)

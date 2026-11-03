"""Keep cost, duration and mode on the SAME directed transport leg/path.

Existing atlas travel/friction and historical freight coefficients are reused.
Parallel legs are alternatives, not additive costs. This isolated connector
does not alter the legacy travel/trade graphs or infer cargo capacities.
"""
from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from . import control as C,seasons as S,transport as X,trade as T

MODES=('land','sea','sea transfer','river','river transfer')


@dataclass
class FreightPath:
    nodes: np.ndarray
    leg_indices: np.ndarray
    cost_road_km: float
    travel_days: float
    mode_days: dict


class FreightNetwork:
    def __init__(self,n_nodes,legs,*,n_cells=None,river_cells=()):
        """Leg tuple: (origin,destination,road-km cost,travel days,mode index)."""
        self.n_nodes=int(n_nodes);self.n_cells=self.n_nodes if n_cells is None else int(n_cells)
        self.river_cells=np.asarray(river_cells,np.int64)
        if self.n_nodes<1 or not 0<self.n_cells<=self.n_nodes:
            raise ValueError('Positive physical/auxiliary node counts required')
        if self.n_nodes-self.n_cells!=len(self.river_cells) or np.any((self.river_cells<0)|(self.river_cells>=self.n_cells)):
            raise ValueError('Every auxiliary node needs its physical river-cell identity')
        arrays=[np.concatenate([np.asarray(x[i]) for x in legs]) for i in range(5)]
        r,c,cost,days,mode=arrays
        if not all(a.ndim==1 and len(a)==len(r) for a in arrays):raise ValueError('Aligned one-dimensional legs required')
        if r.dtype.kind not in 'iu' or c.dtype.kind not in 'iu' or mode.dtype.kind not in 'iu':
            raise ValueError('Integer node and mode indices required')
        if np.any((r<0)|(r>=self.n_nodes)|(c<0)|(c>=self.n_nodes)|(mode<0)|(mode>=len(MODES))):
            raise ValueError('Invalid leg indices')
        if not np.isfinite(cost).all() or not np.isfinite(days).all() or np.any(cost<=0) or np.any(days<=0):
            raise ValueError('Positive finite cost and duration required')
        # Parallel alternatives: least cost, then shortest duration, then mode.
        # Sorting before CSR construction prevents its duplicate-entry sum.
        order=np.lexsort((mode,days,cost,c,r))
        r,c,cost,days,mode=[a[order] for a in arrays]
        first=np.r_[True,(r[1:]!=r[:-1])|(c[1:]!=c[:-1])] if len(r) else np.zeros(0,bool)
        starts=np.flatnonzero(first)
        counts=np.diff(np.r_[starts,len(r)])
        sums=np.add.reduceat(cost,starts) if len(starts) else np.zeros(0)
        self.parallel_pair_count=int(np.sum(counts>1));self.discarded_parallel_legs=int(len(r)-len(starts))
        self.maximum_sum_to_selected_cost_ratio=1. if not len(starts) else float(np.max(sums/cost[starts]))
        self.origins=r[first].astype(np.int64);self.destinations=c[first].astype(np.int64)
        self.costs=cost[first].astype(float);self.days=days[first].astype(float);self.modes=mode[first].astype(np.uint8)
        self.keys=self.origins*self.n_nodes+self.destinations
        self.base=csr_matrix((self.costs,(self.origins,self.destinations)),shape=(self.n_nodes,self.n_nodes))
        if not np.array_equal(self.base.data,self.costs):raise ValueError('CSR leg identity changed')

    def paths(self,source,destinations):
        if not 0<=source<self.n_cells:raise ValueError('Physical source required')
        distance,parent=dijkstra(self.base,directed=True,indices=int(source),return_predecessors=True)
        out={}
        for destination in destinations:
            destination=int(destination)
            if not 0<=destination<self.n_cells:raise ValueError('Physical destination required')
            if not np.isfinite(distance[destination]):out[destination]=None;continue
            backward=[destination]
            while backward[-1]!=source:
                node=int(parent[backward[-1]])
                if node<0 or len(backward)>self.n_nodes:raise RuntimeError('Invalid path predecessor chain')
                backward.append(node)
            nodes=np.array(backward[::-1],np.int64)
            keys=nodes[:-1]*self.n_nodes+nodes[1:];indices=np.searchsorted(self.keys,keys)
            if not np.array_equal(self.keys[indices],keys):raise RuntimeError('Missing path-leg metadata')
            cost=float(self.costs[indices].sum());duration=float(self.days[indices].sum())
            if not np.isclose(cost,distance[destination],rtol=1e-10,atol=1e-8):raise RuntimeError('Path cost identity failed')
            bymode={name:float(self.days[indices][self.modes[indices]==i].sum()) for i,name in enumerate(MODES)}
            out[destination]=FreightPath(nodes,indices,cost,duration,bymode)
        return out

    def physical_cells(self,nodes):
        nodes=np.asarray(nodes,np.int64);cells=nodes.copy();aux=nodes>=self.n_cells
        cells[aux]=self.river_cells[nodes[aux]-self.n_cells]
        return cells


def month_freight_network(world,st,cl,month,ports=(),river_places=()):
    """Freight-cost and physical-day versions of the inherited same legs.

    Sailing uses the trade graph's edgewise seasonal expectation, not the
    separate whole-voyage fair-weather-spell approximation. Weather is held
    at the selected model month; no forecast across a long voyage is inferred.
    """
    land=st['land'];cell_km=world['cell_km'];legs=[]
    def add(edges,cost,mode):
        r,c,days=edges;legs.append((r,c,np.broadcast_to(cost,np.shape(days)),days,np.full(len(r),mode,np.uint8)))
    eta=S.month_terrain(st['eta'],cl,month);mud=cl['mud'][month]
    flood=S.flood_index(cl['flow'][month][st['basin']])
    cross=np.where(st['basin']>0,S.CROSS_DAYS*(1+S.FLOOD_GAIN*flood),0.)
    foot=C.foot_edges(world['elev'],land,world['road'],eta,cell_km,st['paths'],world.get('ferry'),world.get('tracks'),
        road_factor=1+(S.MUD_ROAD-1)*mud,track_factor=1+(S.MUD_COEFFICIENT-1)*mud,cross=cross)
    add(foot,foot[2]*C.ROAD_KM_DAY,0)
    sea_day=T.SEA_KM_DAY*T.SEA_PER_KM/T.ROAD_PER_KM
    sea=X.sea_edges(st['water'],world['u'][month],world['v'][month],world['wind'][month],
                    cl['steadiness'][month],cl['sea'][month],cell_km,st['coast_km'])
    add(sea,sea[2]*sea_day,1)
    if len(ports):
        harbour=X.harbour_edges(land,st['water'],list(ports),cell_km)
        add(harbour,harbour[2]*sea_day,2)
    cells=np.zeros(0,np.int64)
    if len(st['river_cells']):
        real=X.river_edges(st['basin'],st['steps'],cl['flow'][month],cell_km,land.size)
        priced=X.river_edges(st['basin'],st['steps'],cl['flow'][month],cell_km,land.size,
            down_km_day=T.ROAD_PER_KM/T.RIVER_DOWN_PER_KM,up_km_day=T.ROAD_PER_KM/T.RIVER_UP_PER_KM)
        if any(not np.array_equal(real[i],priced[i]) for i in [0,1,3]):
            raise ValueError('Cost/time river topology or auxiliary identities differ')
        cells=real[3];add(real[:3],priced[2],3)
        transfer=X.river_harbour_edges(cells,land.size,list(river_places),land.shape)
        add(transfer,transfer[2]*X.RIVER_DOWN_KM_DAY*T.RIVER_DOWN_PER_KM/T.ROAD_PER_KM,4)
    return FreightNetwork(land.size+len(cells),legs,n_cells=land.size,river_cells=cells)

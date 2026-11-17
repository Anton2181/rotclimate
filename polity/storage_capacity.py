"""Explicit physical-store geometry, independent of food stocks and atlas defaults.

Arithmetic consistency never qualifies archaeological evidence. Quantities keep
units and provenance;missing values remain missing. Outputs are geometric
net-edible equivalents,not operational/historical capacity or annual production.
"""
from dataclasses import dataclass
import math


KINDS={'observation','author_estimate','analogy','scenario','unknown'}


@dataclass(frozen=True)
class Quantity:
    value: float | None
    unit: str
    kind: str
    source: str
    locator: str

    def __post_init__(self):
        if self.kind not in KINDS or not all(isinstance(v,str) and v.strip() for v in (self.unit,self.source,self.locator)):
            raise ValueError('Explicit unit,evidence kind,source and locator required')
        if self.value is None:
            if self.kind!='unknown':raise ValueError('Missing quantity must be labelled unknown')
        elif self.kind=='unknown' or isinstance(self.value,bool) or not isinstance(self.value,(int,float)) or not math.isfinite(self.value) or self.value<0:
            raise ValueError('Known quantities must be finite,nonnegative and retain their evidence kind')


@dataclass(frozen=True)
class PhysicalStore:
    store_id: str
    role: str | None
    location: str | None
    phase: str | None
    owner_access: str | None
    commodity: str | None
    stored_state: str | None
    energy_pool: str | None
    material_basis: str
    area_basis: str
    usable_area: Quantity
    effective_depth: Quantity
    bulk_density: Quantity
    density_commodity: str | None
    density_stored_state: str | None
    net_edible_yield: Quantity
    edible_energy_density: Quantity
    structural_mass_limit: Quantity
    preservation_condition: str | None
    duration_condition: str | None


@dataclass(frozen=True)
class FlowReference:
    annual_energy: Quantity
    commodity: str | None
    location: str | None
    phase: str | None
    energy_pool: str | None


def convert(store: PhysicalStore, flow: FlowReference | None=None):
    if not isinstance(store.store_id,str) or not store.store_id.strip():raise ValueError('Physical store identity required')
    if store.area_basis!='single_commodity_allocated_usable':
        raise ValueError('Gross footprint/unallocated mixed space cannot fund a cereal conversion')
    if store.material_basis not in {'stored_material','already_net_edible'}:raise ValueError('Explicit material accounting basis required')
    inputs={'usable_area':(store.usable_area,'m2'),'effective_depth':(store.effective_depth,'m'),
        'bulk_density':(store.bulk_density,'kg_stored/m3'),'net_edible_yield':(store.net_edible_yield,'kg_edible/kg_stored'),
        'edible_energy_density':(store.edible_energy_density,'kcal/kg_edible'),
        'structural_mass_limit':(store.structural_mass_limit,'kg_stored/m2')}
    for field,(q,unit) in inputs.items():
        if q.unit!=unit:raise ValueError(f'{field} requires {unit}')
    if store.net_edible_yield.value is not None and store.net_edible_yield.value>1:raise ValueError('Net-edible yield cannot exceed one')
    for q in [store.bulk_density,store.edible_energy_density]:
        if q.value is not None and q.value==0:raise ValueError('Known density and edible energy density must be positive')
    if store.material_basis=='already_net_edible' and store.net_edible_yield.value not in (None,1):
        raise ValueError('Already-net edible material cannot receive another deduction')
    if store.material_basis=='already_net_edible' and store.stored_state not in (None,'net_edible'):
        raise ValueError('Already-net material requires an explicit net_edible stored state')
    gaps=[field for field,(q,_) in inputs.items() if q.value is None and field!='structural_mass_limit']
    for field in ['commodity','stored_state','energy_pool']:
        if not getattr(store,field):gaps.append(field)
    for field,actual,expected in [('density_commodity',store.density_commodity,store.commodity),
                                  ('density_stored_state',store.density_stored_state,store.stored_state)]:
        if not actual:gaps.append(field)
        elif expected and actual!=expected:raise ValueError(f'{field} mismatches stored material')
    volume=mass=energy=None;structural_ok=None
    if not gaps:
        volume=store.usable_area.value*store.effective_depth.value
        mass=volume*store.bulk_density.value
        energy=mass*store.net_edible_yield.value*store.edible_energy_density.value
        if not all(math.isfinite(v) for v in [volume,mass,energy]):raise ValueError('Converted quantities must remain finite')
        if store.structural_mass_limit.value is not None:
            limit=store.usable_area.value*store.structural_mass_limit.value
            if mass>limit:raise ValueError('Proposed fill exceeds the explicit structural mass limit')
            structural_ok=True
    operational_gaps=[field for field in ['role','location','phase','owner_access','preservation_condition','duration_condition'] if not getattr(store,field)]
    if store.structural_mass_limit.value is None:operational_gaps.append('structural_mass_limit')
    days=None;flow_status='not_supplied'
    if flow is not None:
        if flow.annual_energy.unit!='kcal/year_365':raise ValueError('Flow requires kcal/year_365')
        match=all(getattr(store,key) and getattr(flow,key)==getattr(store,key) for key in ['commodity','location','phase','energy_pool'])
        if not match:flow_status='incompatible_or_unknown_context'
        elif flow.annual_energy.value is None or flow.annual_energy.value<=0:flow_status='nonpositive_or_unknown_flow'
        elif energy is None:flow_status='unknown_geometric_energy'
        else:
            days=energy/flow.annual_energy.value*365
            if not math.isfinite(days):raise ValueError('Day equivalent must remain finite')
            flow_status='conditional_geometric_equivalent'
    return dict(store_id=store.store_id,geometric_volume_m3=volume,stored_mass_kg=mass,geometric_net_energy_kcal=energy,
        geometric_flow_days=days,flow_status=flow_status,arithmetic_gaps=gaps,operational_gaps=operational_gaps,
        structural_fill_supported=structural_ok,operational_capacity_kcal=None,empirically_qualified=False,
        input_evidence_kinds={field:q.kind for field,(q,unit) in inputs.items()},
        flow_evidence_kind=None if flow is None else flow.annual_energy.kind)

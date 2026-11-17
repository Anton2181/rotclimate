from dataclasses import replace
from decimal import Decimal

import pytest

from polity.storage_capacity import PhysicalStore,FlowReference,Quantity,convert


def q(value,unit):return Quantity(value,unit,'unknown' if value is None else 'scenario','manufactured test','explicit fixture')


def store():
    return PhysicalStore('synthetic-a','commercial','made-up place','made-up phase','scenario access','barley','husked',
        'net edible cereal','stored_material','single_commodity_allocated_usable',q(100.,'m2'),q(.5,'m'),
        q(700.,'kg_stored/m3'),'barley','husked',q(.8,'kg_edible/kg_stored'),q(3500.,'kcal/kg_edible'),
        q(500.,'kg_stored/m2'),'scenario ventilation','scenario duration')


def flow(value=365000.):return FlowReference(q(value,'kcal/year_365'),'barley','made-up place','made-up phase','net edible cereal')


def test_manufactured_units_match_independent_decimal_arithmetic():
    result=convert(store(),flow())
    volume=Decimal('100')*Decimal('.5');mass=volume*Decimal('700');energy=mass*Decimal('.8')*Decimal('3500')
    assert result['geometric_volume_m3']==float(volume)==50
    assert result['stored_mass_kg']==float(mass)==35000
    assert result['geometric_net_energy_kcal']==float(energy)==98000000
    assert result['geometric_flow_days']==pytest.approx(float(energy/Decimal('365000')*365))
    assert result['operational_capacity_kcal'] is None and not result['empirically_qualified']


@pytest.mark.parametrize('field,unit',[('effective_depth','m'),('bulk_density','kg_stored/m3')])
def test_missing_geometry_or_density_remains_unknown(field,unit):
    result=convert(replace(store(),**{field:q(None,unit)}),flow())
    assert result['geometric_net_energy_kcal'] is None and field in result['arithmetic_gaps']
    assert result['geometric_flow_days'] is None


@pytest.mark.parametrize('basis',['gross_footprint','unallocated_mixed'])
def test_unallocated_space_cannot_be_converted_as_cereal(basis):
    with pytest.raises(ValueError):convert(replace(store(),area_basis=basis))


@pytest.mark.parametrize('values',[dict(density_commodity='wheat'),dict(density_stored_state='clean')])
def test_material_and_state_must_match_density(values):
    with pytest.raises(ValueError):convert(replace(store(),**values))


def test_explicit_structural_limit_rejects_overfilled_geometry():
    with pytest.raises(ValueError,match='structural'):convert(replace(store(),structural_mass_limit=q(300.,'kg_stored/m2')))


def test_unknown_support_and_access_do_not_become_operational_capacity():
    result=convert(replace(store(),structural_mass_limit=q(None,'kg_stored/m2'),owner_access=None,preservation_condition=None))
    assert result['geometric_net_energy_kcal']==98000000
    assert result['structural_fill_supported'] is None
    assert set(result['operational_gaps'])=={'structural_mass_limit','owner_access','preservation_condition'}
    assert result['operational_capacity_kcal'] is None


def test_already_net_material_rejects_repeated_deduction():
    with pytest.raises(ValueError,match='another deduction'):convert(replace(store(),material_basis='already_net_edible'))
    result=convert(replace(store(),material_basis='already_net_edible',stored_state='net_edible',density_stored_state='net_edible',net_edible_yield=q(1.,'kg_edible/kg_stored')))
    assert result['geometric_net_energy_kcal']==122500000


def test_husked_mass_cannot_be_relabelled_as_already_net_edible():
    with pytest.raises(ValueError,match='stored state'):
        convert(replace(store(),material_basis='already_net_edible',net_edible_yield=q(1.,'kg_edible/kg_stored')))


@pytest.mark.parametrize('value',[0.,None])
def test_zero_or_unknown_flow_has_undefined_days(value):
    result=convert(store(),flow(value));assert result['geometric_flow_days'] is None
    assert result['flow_status']=='nonpositive_or_unknown_flow'


@pytest.mark.parametrize('values',[dict(location='other'),dict(phase='other'),dict(commodity='wheat'),dict(energy_pool='raw calories')])
def test_incompatible_flow_does_not_generate_days(values):
    result=convert(store(),replace(flow(),**values));assert result['geometric_flow_days'] is None
    assert result['flow_status']=='incompatible_or_unknown_context'


@pytest.mark.parametrize('value',[-1.,float('inf'),float('nan'),True])
def test_invalid_quantity_rejected(value):
    with pytest.raises(ValueError):q(value,'m2')


def test_unit_mismatch_and_missing_provenance_rejected():
    with pytest.raises(ValueError):convert(replace(store(),effective_depth=q(50.,'cm')))
    with pytest.raises(ValueError):Quantity(1.,'m','scenario','','')


def test_observation_labels_do_not_automatically_establish_qualification():
    s=store()
    # This is an invented label to check behavior,not a source observation.
    s=replace(s,usable_area=replace(s.usable_area,kind='observation'))
    assert not convert(s)['empirically_qualified']

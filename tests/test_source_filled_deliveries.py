import numpy as np
import pytest
from polity.source_filled_deliveries import source_filled_deliveries


def run(**changes):
    args=dict(job_ids=np.array([7,2]),job_raw_cargo=[100.,40.],source_ids=np.array([2,7]),source_requested=[40.,100.],source_withdrawn=[0.,60.],source_unfilled=[40.,40.]);args.update(changes);return source_filled_deliveries(**args)


def test_exact_identity_join_and_partial_zero_cargo_retention_once():
    y=run();np.testing.assert_array_equal(y.raw_withdrawn,[60.,0.]);np.testing.assert_array_equal(y.retained_source_filled,[57.,0.]);np.testing.assert_array_equal(y.retained_unfilled_potential,[38.,38.]);np.testing.assert_array_equal(y.retained_source_filled+y.retained_unfilled_potential,y.retained_packed_potential)


def test_raw_source_requests_cannot_be_replaced_with_retained_food():
    with pytest.raises(ValueError):run(source_requested=[38.,95.],source_withdrawn=[0.,57.],source_unfilled=[38.,38.])


def test_empty_jobs_and_no_input_mutation_or_output_alias():
    source=np.array([0.,60.]);before=source.copy();y=run(source_withdrawn=source);y.raw_withdrawn[0]=0.;np.testing.assert_array_equal(source,before)
    z=source_filled_deliveries(np.array([],dtype='i8'),[],np.array([],dtype='i8'),[],[],[]);assert z.raw_withdrawn.size==0


@pytest.mark.parametrize('changes',[
    dict(source_ids=np.array([2,8])),dict(source_ids=np.array([2,2])),dict(job_ids=np.array([7.,2.])),
    dict(source_withdrawn=[0.,101.]),dict(source_unfilled=[40.,39.]),dict(source_withdrawn=[0.,float('nan')]),
    dict(job_raw_cargo=[99.,40.]),dict(retention=1.1),dict(source_requested=[40.]),
])
def test_missing_duplicate_changed_or_nonphysical_source_records_rejected(changes):
    with pytest.raises(ValueError):run(**changes)

import numpy as np
import pytest
from experiments.reservoir_block_solver import solve_block
from test_vertical_transport import setup_case


@pytest.mark.parametrize('seed',[31,32,33])
def test_block_solve_matches_independent_sparse_solution_and_actual_face_ledger(seed):
    op=setup_case(seed);rng=np.random.default_rng(seed)
    source=rng.uniform(1e-6,3e-5,(2,)+op.shape);reaction=rng.uniform(1e-6,2e-5,source.shape)
    boundary=8*op.layer_mass
    reference,_=op.solve(source,reaction,boundary,diffusion=60000.)
    actual,c=solve_block(op,source,reaction,boundary,diffusion=60000.,rtol=1e-11,max_iter=2000)
    assert c['method']=='block_gauss_seidel'
    np.testing.assert_allclose(actual,reference,atol=1e-9,rtol=1e-10)
    terms,_=op.terms(actual,diffusion=60000.)
    assert np.max(np.abs(source[:,1:-1,1:-1]+terms-(reaction*actual)[:,1:-1,1:-1]))<1e-13
    np.testing.assert_array_equal(actual[:,op.border],boundary[:,op.border])


def test_uniform_specific_humidity_equilibrium_survives_block_solver_over_terrain():
    op=setup_case();known=12*op.layer_mass
    water,c=solve_block(op,known*1e-5,1e-5,known,diffusion=60000.,guess=.5*known,rtol=1e-11,max_iter=2000)
    np.testing.assert_allclose(water,known,atol=1e-9)
    assert c['diagonal_scaled_residual_mm']<=c['tolerance_mm']


def test_insufficient_block_work_cannot_pass_on_small_updates_and_recovers_same_matrix():
    op=setup_case();source=np.full((2,)+op.shape,1e-5);boundary=8*op.layer_mass
    with pytest.raises(RuntimeError,match='actual equation'):
        solve_block(op,source,1e-6,boundary,diffusion=60000.,rtol=1e-13,max_iter=1,recover=False)
    water,c=solve_block(op,source,1e-6,boundary,diffusion=60000.,rtol=1e-13,max_iter=1)
    reference,_=op.solve(source,1e-6,boundary,diffusion=60000.)
    np.testing.assert_array_equal(water,reference)
    assert c['method']=='sparse_recovery'


@pytest.mark.parametrize('changes',[dict(rtol=0),dict(max_iter=0),dict(diffusion=-1)])
def test_invalid_block_solver_settings_rejected(changes):
    op=setup_case();source=np.ones((2,)+op.shape)*1e-5
    with pytest.raises(ValueError):solve_block(op,source,1e-5,source*86400.,**changes)

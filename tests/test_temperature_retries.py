import numpy as np

from rotclimate.temperature import iterate_temperature,TemperatureConvergenceError


def test_no_retry_reproduces_the_original_temperature_loop():
    initial=np.array([0.,2.])
    state=initial
    for i in range(25):
        solved=3-2*state
        update=np.abs(solved-state)
        done=i>0 and update.max()<.05
        state=solved if done else state+.25*(solved-state)
        if done:
            break
    result=iterate_temperature(lambda state,first:3-2*state,initial,25,.25)
    np.testing.assert_array_equal(result.temperature,solved)
    np.testing.assert_array_equal(result.update,update)
    assert result.iterations==i+1 and len(result.stages)==1


def test_bounded_retry_stabilises_stiff_temperature_wind_feedback():
    first_flags=[]
    retries=[]
    def solve(state,first):
        first_flags.append(first)
        return 11-10*state
    result=iterate_temperature(solve,np.array([0.]),8,.25,retries=2,on_retry=retries.append)
    assert result.converged and len(result.stages)==2
    assert result.stages[0]['relaxation']==.25 and result.stages[1]['relaxation']==.125
    assert result.update.max()<.05
    np.testing.assert_allclose(result.temperature,1.,atol=.05)
    assert first_flags.count(True)==1  # retries continue, never restore the stale warm start
    assert len(retries)==1 and retries[0]['relaxation']==.125


def test_no_fixed_point_stops_at_the_exact_budget_without_faking_convergence():
    result=iterate_temperature(lambda state,first:state+1,np.array([0.]),4,.25,retries=2)
    assert not result.converged
    assert result.iterations==4+8+16
    assert result.update.max()==1.
    error=TemperatureConvergenceError(19,153.3,result,1.)
    assert error.details['iterations']==28
    assert len(error.details['stages'])==3
    assert 'seasonal step 19' in str(error)


def test_accelerated_retry_recovers_a_noncontractive_linear_fixed_point():
    # Damping cannot make a positive derivative above one contractive.
    # Anderson can solve the equilibrium without changing its equation.
    result=iterate_temperature(lambda x,first:1.1*x+1,np.array([0.]),8,.25,retries=1,acceleration=True)
    assert result.converged and result.update.max()<.05
    np.testing.assert_allclose(result.temperature,-10,atol=.05)
    assert result.stages[-1]['method']=='anderson'


def test_acceleration_cannot_claim_a_fixed_point_for_a_constant_nonzero_residual():
    result=iterate_temperature(lambda x,first:x+1,np.array([0.]),4,.25,retries=2,acceleration=True)
    assert not result.converged and result.iterations==28 and result.update.max()==1

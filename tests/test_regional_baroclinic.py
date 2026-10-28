"""Independent box eigenmodes, weighted flux budgets and passive edge checks."""
import numpy as np
import pytest

from rotclimate.regional_baroclinic import embed_two_layers, mass_divergence, solve_regional_mode

SCALES = dict(wave_speed_ms=50., momentum_drag_s=1/(5*86400.), thermal_drag_s=1/(20*86400.))


@pytest.mark.parametrize("axis", [0, 1])
def test_closed_box_eigenmode(axis):
    ny, nx = 13, 17
    dx = 80000.
    c, r, rt = SCALES.values()
    j, i = np.mgrid[:ny, :nx]
    length = (ny, nx)[axis]
    phase = np.pi * ((j, i)[axis] + .5) / length
    phi = 120 * np.cos(phase)
    kd = 2 * np.sin(np.pi/(2*length)) / dx
    q = (rt + c*c*kd*kd/r) * phi
    out = solve_regional_mode(q, dx, 0., **SCALES)
    expected_u = np.zeros((ny, nx+1))
    expected_v = np.zeros((ny+1, nx))
    if axis == 1:
        expected_u[:, 1:-1] = 120*kd/r * np.sin(np.pi*np.arange(1,nx)/nx)
    else:
        expected_v[1:-1] = 120*kd/r * np.sin(np.pi*np.arange(1,ny)/ny)[:, None]
    np.testing.assert_allclose(out.geopotential, phi, atol=1e-8, rtol=1e-10)
    np.testing.assert_allclose(out.u_east, expected_u, atol=1e-9, rtol=1e-10)
    np.testing.assert_allclose(out.v_south, expected_v, atol=1e-9, rtol=1e-10)


def test_variable_mass_manufactured_solution_uses_weighted_flux_not_velocity_divergence():
    ny, nx = 11, 16
    dx = 70000.
    c, r, rt = SCALES.values()
    j, i = np.mgrid[:ny, :nx]
    mass = 1 - .6*np.exp(-((i-7)**2+(j-4)**2)/10)
    phi = 70*np.cos(np.pi*(i+.5)/nx)*np.cos(2*np.pi*(j+.5)/ny)
    u, v = np.zeros((ny,nx+1)), np.zeros((ny+1,nx))
    u[:,1:-1] = -np.diff(phi, axis=1)/(r*dx)
    v[1:-1] = -np.diff(phi, axis=0)/(r*dx)
    # Independent finite-volume expression; no production divergence helper.
    fx = u[:,1:-1] * .5*(mass[:,:-1]+mass[:,1:])
    fy = v[1:-1] * .5*(mass[:-1]+mass[1:])
    div = (np.diff(np.pad(fx,((0,0),(1,1))),axis=1)
           + np.diff(np.pad(fy,((1,1),(0,0))),axis=0))/(mass*dx)
    q = c*c*div + rt*phi
    out = solve_regional_mode(q,dx,0.,column_mass=mass,**SCALES)
    np.testing.assert_allclose(out.geopotential,phi,atol=1e-8,rtol=1e-10)
    np.testing.assert_allclose(out.u_east,u,atol=1e-9,rtol=1e-10)
    np.testing.assert_allclose(out.v_south,v,atol=1e-9,rtol=1e-10)
    assert np.abs((np.diff(u,axis=1)+np.diff(v,axis=0))/dx-div).max()>1e-6


def test_no_spurious_motion_at_rest_over_mass_gradient():
    j,i = np.mgrid[:9,:13]
    mass = .3 + .7*i/12
    q = np.full(mass.shape,.0003)
    out = solve_regional_mode(q,100000.,7e-5+1e-6*j,column_mass=mass,**SCALES)
    np.testing.assert_allclose(out.geopotential,q/SCALES['thermal_drag_s'],rtol=1e-10,atol=1e-8)
    assert max(np.abs(out.u_east).max(),np.abs(out.v_south).max())<1e-10


@pytest.mark.parametrize('edges', [{},dict(west='impedance',east='impedance'),
                                 dict(north='impedance',south='impedance',east='impedance',west='impedance')])
def test_independent_mass_energy_and_boundary_budgets(edges):
    j,i=np.mgrid[:12,:16]
    mass=.4+.5*np.exp(-((i-7)**2+(j-5)**2)/25)
    q=.0007*np.cos(np.pi*(i+.5)/16)*np.cos(np.pi*(j+.5)/12)+.0001
    f=7e-5+1e-5*(j-6)/6
    dx=100000.
    c,r,rt=SCALES.values()
    out=solve_regional_mode(q,dx,f,column_mass=mass,boundaries=edges,**SCALES)
    u,v,phi=out.u_east,out.v_south,out.geopotential
    supply=np.sum(mass*phi*q/c**2)
    momentum=r*(np.sum(.5*(mass[:,:-1]+mass[:,1:])*u[:,1:-1]**2)
                +np.sum(.5*(mass[:-1]+mass[1:])*v[1:-1]**2))
    thermal=np.sum(mass*rt*(phi/c)**2)
    # Independent face pressure work and divergence theorem, including corners.
    boundary_work=(np.sum(mass[:,-1]*phi[:,-1]*u[:,-1])-np.sum(mass[:,0]*phi[:,0]*u[:,0])
                   +np.sum(mass[-1]*phi[-1]*v[-1])-np.sum(mass[0]*phi[0]*v[0]))/dx
    net_flux=(np.sum(mass[:,-1]*u[:,-1])-np.sum(mass[:,0]*u[:,0])
              +np.sum(mass[-1]*v[-1])-np.sum(mass[0]*v[0]))/dx
    assert boundary_work>=0
    assert supply==pytest.approx(momentum+thermal+boundary_work,rel=1e-11)
    assert c*c*net_flux+np.sum(mass*(rt*phi-q))==pytest.approx(0.,abs=1e-13)
    assert np.sum(mass*out.divergence_per_s)==pytest.approx(net_flux,abs=1e-19)
    assert out.certificate['relative_modal_energy_error']<1e-11
    if edges:
        assert boundary_work>0
    else:
        assert boundary_work==0
        assert np.count_nonzero(u[:,[0,-1]])==0
        assert np.count_nonzero(v[[0,-1]])==0


def test_changing_column_mass_units_leaves_physical_solution_unchanged():
    j,i=np.mgrid[:8,:12]
    mass=.4+.6*i/11
    q=.001*np.cos(i)*np.cos(j)
    args=dict(boundaries=dict(east='impedance'),**SCALES)
    a=solve_regional_mode(q,90000.,7e-5,column_mass=mass,**args)
    b=solve_regional_mode(q,90000.,7e-5,column_mass=mass*10332,**args)
    for field in ('u_east','v_south','geopotential','divergence_per_s'):
        np.testing.assert_allclose(getattr(a,field),getattr(b,field),rtol=1e-10,atol=1e-10)
    assert a.certificate['modal_energy_input_m2_s3']==pytest.approx(b.certificate['modal_energy_input_m2_s3'],rel=1e-11)


def test_two_layer_embedding_retains_local_and_boundary_dry_mass_with_donor_exchange():
    j,i=np.mgrid[:13,:17]
    mass=1-.5*np.exp(-((i-9)**2+(j-4)**2)/8)
    q=.001*np.exp(-((i-8)**2+(j-6)**2)/6)
    edges=dict(east='impedance',west='impedance',north='impedance',south='impedance')
    out=solve_regional_mode(q,100000.,7e-5,column_mass=mass,boundaries=edges,**SCALES)
    layers=embed_two_layers(out)
    for axis in ('u_east','v_south'):
        np.testing.assert_array_equal(.25*layers['lower_'+axis]+.75*layers['upper_'+axis],0.)
    lower_div=mass_divergence(layers['lower_u_east'],layers['lower_v_south'],mass,100000.)
    upper_div=mass_divergence(layers['upper_u_east'],layers['upper_v_south'],mass,100000.)
    up=layers['upward_exchange_per_total_column_s']
    np.testing.assert_allclose(.25*lower_div+up,0.,atol=1e-20)
    np.testing.assert_allclose(.75*upper_div-up,0.,atol=1e-20)
    assert up[6,8]>0


def test_passive_edges_approach_continuous_one_dimensional_helmholtz_solution():
    # f=0, uniform Q: -c²/r phi'' + rt phi = Q;
    # outward velocity=phi/c. Analytic Robin box, first-order edge placement.
    c,r,rt=SCALES.values()
    length=1600000.
    k=np.sqrt(r*rt)/c
    q0=.0005
    errors=[]
    for nx in (12,24,48):
        dx=length/nx
        x=(np.arange(nx)+.5)*dx-length/2
        coeff=-(r/c)*(q0/rt)/(k*np.sinh(k*length/2)+(r/c)*np.cosh(k*length/2))
        expected=q0/rt+coeff*np.cosh(k*x)
        out=solve_regional_mode(np.full((3,nx),q0),dx,0.,boundaries=dict(east='impedance',west='impedance'),**SCALES)
        errors.append(np.max(np.abs(out.geopotential-expected)))
    # First order is deliberate: phi at exterior face uses adjacent cell value.
    assert errors[1]<.57*errors[0]
    assert errors[2]<.57*errors[1]


@pytest.mark.parametrize('overrides', [dict(column_mass=0),dict(column_mass=np.nan),
    dict(boundaries={'outer':'wall'}),dict(boundaries={'west':'periodic'}),dict(wave_speed_ms=0),
    dict(thermal_drag_s=0),dict(coriolis=np.inf)])
def test_invalid_configuration_rejected(overrides):
    args=dict(coriolis=7e-5,**SCALES)
    args.update(overrides)
    with pytest.raises(ValueError):
        solve_regional_mode(np.zeros((5,7)),100000.,**args)

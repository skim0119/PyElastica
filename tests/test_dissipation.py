__doc__ = """ Test Dissipation module for in Elastica implementation"""

# System imports
import numpy as np
from test_rod.test_rods import MockTestRod
from elastica.dissipation import DamperBase, ExponentialDamper
from numpy.testing import assert_allclose
from elastica.utils import Tolerance


def test_damper_base():
    test_rod = MockTestRod()
    test_rod.velocity_collection = np.ones(3) * 5.0
    test_rod.omega_collection = np.ones(3) * 11.0

    class TestDamper(DamperBase):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def dampen_rates(self, rod, time):
            rod.velocity_collection *= time
            rod.omega_collection *= time

    test_damper = TestDamper(_system=test_rod)
    test_damper.dampen_rates(test_rod, 2)
    assert_allclose(test_rod.velocity_collection, 10.0, atol=Tolerance.atol())
    assert_allclose(test_rod.omega_collection, 22.0, atol=Tolerance.atol())


def test_damper_base_properties_access():
    test_rod = MockTestRod()

    class TestDamper(DamperBase):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # Able to access properties in constraint class
            assert self._system == test_rod

        def dampen_rates(self, rod, time):
            assert self._system == test_rod

    test_damper = TestDamper(_system=test_rod)
    test_damper.dampen_rates(test_rod, 2)


def test_exponential_damper():

    test_rod = MockTestRod()
    test_rod.mass[:] = 1.0
    test_dilatation = 2.0 * np.ones((3, test_rod.n_elem))
    test_inv_mass_second_moment_of_inertia = 3.0 * np.ones((3, 3, test_rod.n_elem))
    test_rod.dilatation = test_dilatation.copy()
    test_rod.inv_mass_second_moment_of_inertia = (
        test_inv_mass_second_moment_of_inertia.copy()
    )
    damping_constant = 0.25
    dt = 0.5
    exponential_damper = ExponentialDamper(
        _system=test_rod, damping_constant=damping_constant, time_step=dt
    )
    # check common prefactors
    # e ^ (-damp_coeff * dt)
    ref_translational_exponential_damping_coefficient = np.exp(-0.25 * 0.5)
    # e ^ (-damp_coeff * dt * elemental_mass * inv_mass_second_moment_of_inertia)
    ref_rotational_exponential_damping_coefficient = np.exp(
        -0.25 * 0.5 * 1.0 * 3.0
    ) * np.ones(
        (
            3,
            test_rod.n_elem,
        )
    )
    # end corrections
    ref_rotational_exponential_damping_coefficient[:, 0] = np.exp(
        -0.25 * 0.5 * 1.5 * 3.0
    )
    ref_rotational_exponential_damping_coefficient[:, -1] = np.exp(
        -0.25 * 0.5 * 1.5 * 3.0
    )
    assert_allclose(
        exponential_damper.translational_exponential_damping_coefficient,
        ref_translational_exponential_damping_coefficient,
        atol=Tolerance.atol(),
    )
    assert_allclose(
        exponential_damper.rotational_exponential_damping_coefficient,
        ref_rotational_exponential_damping_coefficient,
        atol=Tolerance.atol(),
    )

    pre_damping_velocity_collection = np.random.rand(3, test_rod.n_elem + 1)
    test_rod.velocity_collection = (
        pre_damping_velocity_collection.copy()
    )  # We need copy of the list not a reference to this array
    pre_damping_omega_collection = np.random.rand(3, test_rod.n_elem)
    test_rod.omega_collection = (
        pre_damping_omega_collection.copy()
    )  # We need copy of the list not a reference to this array
    exponential_damper.dampen_rates(test_rod, time=0)
    post_damping_velocity_collection = (
        pre_damping_velocity_collection
        * ref_translational_exponential_damping_coefficient
    )
    # multiplying_factor = ref_rot_coeff ^ dilation
    post_damping_omega_collection = (
        pre_damping_omega_collection
        * ref_rotational_exponential_damping_coefficient ** 2.0
    )
    assert_allclose(
        post_damping_velocity_collection,
        test_rod.velocity_collection,
        atol=Tolerance.atol(),
    )
    assert_allclose(
        post_damping_omega_collection, test_rod.omega_collection, atol=Tolerance.atol()
    )
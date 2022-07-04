__doc__ = """ Test Dissipation module for in Elastica implementation"""

# System imports
from elastica.dissipation import DamperBase, ExponentialDamper, FilterDamper
from elastica.utils import Tolerance

import numpy as np
from numpy.testing import assert_allclose

import pytest

from test_rod.test_rods import MockTestRod


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


@pytest.mark.parametrize("filter_order", [-1, 0, 3.2])
def test_filter_damper_init_invalid_filter_order(filter_order):
    test_rod = MockTestRod()
    with pytest.raises(ValueError) as exc_info:
        _ = FilterDamper(
            _system=test_rod,
            filter_order=filter_order,
        )
    assert (
        exc_info.value.args[0]
        == "Invalid filter order! Filter order must be a positive integer."
    )


@pytest.mark.parametrize("filter_order", [2, 3, 4])
def test_filter_damper_init(filter_order):

    test_rod = MockTestRod()
    filter_damper = FilterDamper(
        _system=test_rod,
        filter_order=filter_order,
    )
    assert filter_damper.filter_order == filter_order
    assert_allclose(
        filter_damper.velocity_filter_term, np.zeros((3, test_rod.n_elem + 1))
    )
    assert_allclose(filter_damper.omega_filter_term, np.zeros((3, test_rod.n_elem)))


@pytest.mark.parametrize("filter_order", [2, 3, 4])
def test_filter_damper_dampen_rates(filter_order):
    test_rod = MockTestRod()
    filter_damper = FilterDamper(
        _system=test_rod,
        filter_order=filter_order,
    )
    test_rod.velocity_collection[...] = 2.0
    test_rod.omega_collection[...] = 3.0
    filter_damper.dampen_rates(rod=test_rod, time=0)
    # filter should keep a spatially invariant field unaffected
    post_damping_velocity_collection = 2.0 * np.ones_like(test_rod.velocity_collection)
    post_damping_omega_collection = 3.0 * np.ones_like(test_rod.omega_collection)
    assert_allclose(
        post_damping_velocity_collection,
        test_rod.velocity_collection,
        atol=Tolerance.atol(),
    )
    assert_allclose(
        post_damping_omega_collection, test_rod.omega_collection, atol=Tolerance.atol()
    )

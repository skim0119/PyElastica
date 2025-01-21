__doc__ = """Symplectic time steppers and concepts for integrating the kinematic and dynamic equations of rod-like objects.  """

from typing import Any

from itertools import zip_longest

from elastica.typing import (
    SystemCollectionType,
    StepType,
    SteppersOperatorsType,
)

import numpy as np

from elastica.rod.data_structures import (
    overload_operator_kinematic_numba,
    overload_operator_dynamic_numba,
)
from elastica.systems.protocol import SymplecticSystemProtocol
from .protocol import SymplecticStepperProtocol

"""
Developer Note
--------------

For the reasons why we define Mixin classes here, the developer
is referred to the same section on `explicit_steppers.py`.
"""


class SymplecticStepperMixin:
    def __init__(self: SymplecticStepperProtocol):
        self.steps_and_prefactors: Final[SteppersOperatorsType] = (
            self.build_step_methods()
        )

    def build_step_methods(self: SymplecticStepperProtocol) -> SteppersOperatorsType:
        # Let the total number of steps for the Symplectic method
        # be (2*n + 1) (for time-symmetry).
        _steps: list[StepType] = self.get_steps()
        # Prefac here is necessary because the linear-exponential integrator
        # needs only the prefactor and not the dt.
        _prefactors: list[StepType] = self.get_prefactors()
        assert int(np.ceil(len(_steps) / 2)) == len(
            _prefactors
        ), f"{len(_steps)=}, {len(_prefactors)=}"

        # Separate the kinematic and dynamic steps
        _kinematic_steps: list[StepType] = _steps[::2]
        _dynamic_steps: list[StepType] = _steps[1::2]

        def no_operation(*args: Any) -> None:
            pass

        return tuple(
            zip_longest(
                _prefactors,
                _kinematic_steps,
                _dynamic_steps,
                fillvalue=no_operation,
            )
        )

    def step(
        self: SymplecticStepperProtocol,
        SystemCollection: SystemCollectionType,
        time: np.float64,
        dt: np.float64,
    ) -> np.float64:
        return SymplecticStepperMixin.do_step(
            self, self.steps_and_prefactors, SystemCollection, time, dt
        )

    # TODO: Merge with .step method in the future.
    # DEPRECATED: Use .step instead.
    @staticmethod
    def do_step(
        TimeStepper: SymplecticStepperProtocol,
        steps_and_prefactors: SteppersOperatorsType,
        SystemCollection: SystemCollectionType,
        time: np.float64,
        dt: np.float64,
    ) -> np.float64:
        """
        Function for doing symplectic stepper over the user defined rods (system).

        Returns
        -------
        time: float
            The time after the integration step.

        """
        for kin_prefactor, kin_step, dyn_step in steps_and_prefactors[:-1]:

            for system in SystemCollection.block_systems():
                kin_step(system, time, dt)

            time += kin_prefactor(dt)

            # Constrain only values
            SystemCollection.constrain_values(time)

            # We need internal forces and torques because they are used by interaction module.
            for system in SystemCollection.block_systems():
                system.compute_internal_forces_and_torques(time)
                # system.update_internal_forces_and_torques()

            # Add external forces, controls etc.
            SystemCollection.synchronize(time)

            for system in SystemCollection.block_systems():
                dyn_step(system, time, dt)

            # Constrain only rates
            SystemCollection.constrain_rates(time)

        # Peel the last kinematic step and prefactor alone
        last_kin_prefactor = steps_and_prefactors[-1][0]
        last_kin_step = steps_and_prefactors[-1][1]

        for system in SystemCollection.block_systems():
            last_kin_step(system, time, dt)
        time += last_kin_prefactor(dt)
        SystemCollection.constrain_values(time)

        # Call back function, will call the user defined call back functions and store data
        SystemCollection.apply_callbacks(time, round(time / dt))

        # Zero out the external forces and torques
        for system in SystemCollection.block_systems():
            system.zeroed_out_external_forces_and_torques(time)

        return time

    def step_single_instance(
        self: SymplecticStepperProtocol,
        System: SymplecticSystemProtocol,
        time: np.float64,
        dt: np.float64,
    ) -> np.float64:

        for kin_prefactor, kin_step, dyn_step in self.steps_and_prefactors[:-1]:
            kin_step(System, time, dt)
            time += kin_prefactor(dt)
            System.compute_internal_forces_and_torques(time)
            dyn_step(System, time, dt)

        # Peel the last kinematic step and prefactor alone
        last_kin_prefactor = self.steps_and_prefactors[-1][0]
        last_kin_step = self.steps_and_prefactors[-1][1]

        last_kin_step(System, time, dt)
        return time + last_kin_prefactor(dt)


class PositionVerlet(SymplecticStepperMixin):
    """
    Position Verlet symplectic time stepper class, which
    includes methods for second-order position Verlet.
    """

    def get_steps(self) -> list[StepType]:
        return [
            self._first_kinematic_step,
            self._first_dynamic_step,
            self._first_kinematic_step,
        ]

    def get_prefactors(self) -> list[StepType]:
        return [
            self._first_prefactor,
            self._first_prefactor,
        ]

    def _first_prefactor(self, dt: np.float64) -> np.float64:
        return 0.5 * dt

    def _first_kinematic_step(
        self, System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
    ) -> None:
        prefac = self._first_prefactor(dt)
        overload_operator_kinematic_numba(
            System.n_nodes,
            prefac,
            System.kinematic_states.position_collection,
            System.kinematic_states.director_collection,
            System.velocity_collection,
            System.omega_collection,
        )

    def _first_dynamic_step(
        self, System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
    ) -> None:
        overload_operator_dynamic_numba(
            System.dynamic_states.rate_collection,
            System.dynamic_rates(time, dt),
        )


class VelocityVerlet(SymplecticStepperMixin):
    """
    Velocity Verlet symplectic time stepper class.
    """

    def get_steps(self) -> list[StepType]:
        return [
            self._no_operation,
            self._first_dynamic_step,
            self._first_kinematic_step,
            self._second_dynamic_step,
            self._no_operation,
        ]

    def get_prefactors(self) -> list[StepType]:
        return [
            self._first_prefactor,
            self._second_prefactor,
            self._third_prefactor,
        ]

    def _no_operation(*args: Any) -> None:
        pass

    def _first_prefactor(self, dt: np.float64) -> np.float64:
        return 0.0

    def _second_prefactor(self, dt: np.float64) -> np.float64:
        return 0.0

    def _third_prefactor(self, dt: np.float64) -> np.float64:
        return 1.0 * dt

    def _first_kinematic_step(
        self, System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
    ) -> None:
        overload_operator_kinematic_numba(
            System.n_nodes,
            dt,
            System.kinematic_states.position_collection,
            System.kinematic_states.director_collection,
            System.velocity_collection,
            System.omega_collection,
        )

    def _first_dynamic_step(
        self, System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
    ) -> None:
        overload_operator_dynamic_numba(
            System.dynamic_states.rate_collection,
            System.dynamic_rates(time, dt / 2.0),
        )

    def _second_dynamic_step(
        self, System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
    ) -> None:
        overload_operator_dynamic_numba(
            System.dynamic_states.rate_collection,
            System.dynamic_rates(time, dt / 2.0),
        )


class SemiImplicitEuler(SymplecticStepperMixin):
    """
    Semi-Implicit (Explicit) symplectic time stepper class.
    Slightly (30%) faster than the Position Verlet with reduced
    convergence.
    First order symplectic euler method.
    """

    def get_steps(self) -> list[StepType]:
        return [
            self._no_operation,
            self._dynamic_step,
            self._kinematic_step,
        ]

    def get_prefactors(self) -> list[StepType]:
        return [
            self._first_prefactor,
            self._second_prefactor,
        ]

    def _no_operation(*args: Any) -> None:
        pass

    def _first_prefactor(self, dt: np.float64) -> np.float64:
        return 0.0

    def _second_prefactor(self, dt: np.float64) -> np.float64:
        return 1.0 * dt

    def _kinematic_step(
        self, System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
    ) -> None:
        overload_operator_kinematic_numba(
            System.n_nodes,
            dt,
            System.kinematic_states.position_collection,
            System.kinematic_states.director_collection,
            System.velocity_collection,
            System.omega_collection,
        )

    def _dynamic_step(
        self, System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
    ) -> None:
        overload_operator_dynamic_numba(
            System.dynamic_states.rate_collection,
            System.dynamic_rates(time, dt),
        )


class ThirdOrderSymplectic(SymplecticStepperMixin):
    """
    Third order symplectic time stepper class based on Ruth 1983.
    """

    def get_steps(self) -> list[StepType]:
        return [
            self._kinematic_step_with_prefactor(2.0 / 3.0),
            self._dynamic_step_with_prefactor(7.0 / 24.0),
            self._kinematic_step_with_prefactor(-2.0 / 3.0),
            self._dynamic_step_with_prefactor(3.0 / 4.0),
            self._kinematic_step_with_prefactor(1.0),
            self._dynamic_step_with_prefactor(-1.0 / 24.0),
            self._no_operation,
        ]

    def get_prefactors(self) -> list[StepType]:
        return [
            self._prefactor(0.0),
            self._prefactor(0.0),
            self._prefactor(0.0),
            self._prefactor(1.0),
        ]

    def _no_operation(*args: Any) -> None:
        pass

    def _prefactor(self, factor: np.float64) -> np.float64:
        def func(dt: np.float64) -> np.float64:
            return dt * factor

        return func

    def _kinematic_step_with_prefactor(self, factor: np.float64) -> StepType:
        def func(
            System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
        ) -> None:
            overload_operator_kinematic_numba(
                System.n_nodes,
                factor * dt,
                System.kinematic_states.position_collection,
                System.kinematic_states.director_collection,
                System.velocity_collection,
                System.omega_collection,
            )

        return func

    def _dynamic_step_with_prefactor(self, factor: np.float64) -> StepType:
        def func(
            System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
        ) -> None:
            overload_operator_dynamic_numba(
                System.dynamic_states.rate_collection,
                System.dynamic_rates(time, factor * dt),
            )

        return func


class FourthOrderSymplectic(SymplecticStepperMixin):
    """
    Fourth order symplectic time stepper class based on Ruth 1983.
    """

    def get_steps(self) -> list[StepType]:
        c1 = c4 = 1.0 / (2.0 * (2.0 - 2.0 ** (1.0 / 3.0)))
        c2 = c3 = (1.0 - 2.0 ** (1.0 / 3.0)) / (2.0 * (2.0 - 2.0 ** (1.0 / 3.0)))
        d1 = d3 = 1.0 / (2.0 - 2.0 ** (1.0 / 3.0))
        d2 = -(2.0 ** (1.0 / 3.0)) / (2.0 - 2.0 ** (1.0 / 3.0))
        d4 = 0.0
        return [
            self._kinematic_step_with_prefactor(c4),
            self._dynamic_step_with_prefactor(d4),
            self._kinematic_step_with_prefactor(c3),
            self._dynamic_step_with_prefactor(d3),
            self._kinematic_step_with_prefactor(c2),
            self._dynamic_step_with_prefactor(d2),
            self._kinematic_step_with_prefactor(c1),
            self._dynamic_step_with_prefactor(d1),
            self._no_operation,
        ]

    def get_prefactors(self) -> list[StepType]:
        return [
            self._prefactor(0.0),
            self._prefactor(0.0),
            self._prefactor(0.0),
            self._prefactor(0.0),
            self._prefactor(1.0),
        ]

    def _no_operation(*args: Any) -> None:
        pass

    def _prefactor(self, factor: np.float64) -> np.float64:
        def func(dt: np.float64) -> np.float64:
            return dt * factor

        return func

    def _kinematic_step_with_prefactor(self, factor: np.float64) -> StepType:
        def func(
            System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
        ) -> None:
            overload_operator_kinematic_numba(
                System.n_nodes,
                factor * dt,
                System.kinematic_states.position_collection,
                System.kinematic_states.director_collection,
                System.velocity_collection,
                System.omega_collection,
            )

        return func

    def _dynamic_step_with_prefactor(self, factor: np.float64) -> StepType:
        def func(
            System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
        ) -> None:
            overload_operator_dynamic_numba(
                System.dynamic_states.rate_collection,
                System.dynamic_rates(time, factor * dt),
            )

        return func


class PEFRL(SymplecticStepperMixin):
    """
    Position Extended Forest-Ruth Like Algorithm of
    I.M. Omelyan, I.M. Mryglod and R. Folk, Computer Physics Communications 146, 188 (2002),
    http://arxiv.org/abs/cond-mat/0110585
    """

    # xi and chi are confusing, but be careful!
    ξ: np.float64 = np.float64(0.1786178958448091e0)  # ξ
    λ: np.float64 = -np.float64(0.2123418310626054e0)  # λ
    χ: np.float64 = -np.float64(0.6626458266981849e-1)  # χ

    # Pre-calculate other coefficients
    lambda_dash_coeff: np.float64 = 0.5 * (1.0 - 2.0 * λ)
    xi_chi_dash_coeff: np.float64 = 1.0 - 2.0 * (ξ + χ)

    def get_steps(self) -> list[StepType]:
        operators = [
            self._first_kinematic_step,
            self._first_dynamic_step,
            self._second_kinematic_step,
            self._second_dynamic_step,
            self._third_kinematic_step,
        ]
        return operators + operators[-2::-1]

    def get_prefactors(self) -> list[StepType]:
        return [
            self._first_kinematic_prefactor,
            self._second_kinematic_prefactor,
            self._third_kinematic_prefactor,
            self._second_kinematic_prefactor,
            self._first_kinematic_prefactor,
        ]

    def _first_kinematic_prefactor(self, dt: np.float64) -> np.float64:
        return self.ξ * dt

    def _first_kinematic_step(
        self, System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
    ) -> None:
        prefac = self._first_kinematic_prefactor(dt)
        overload_operator_kinematic_numba(
            System.n_nodes,
            prefac,
            System.kinematic_states.position_collection,
            System.kinematic_states.director_collection,
            System.velocity_collection,
            System.omega_collection,
        )
        # System.kinematic_states += prefac * System.kinematic_rates(time, prefac)

    def _first_dynamic_step(
        self, System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
    ) -> None:
        prefac = self.lambda_dash_coeff * dt
        overload_operator_dynamic_numba(
            System.dynamic_states.rate_collection,
            System.dynamic_rates(time, prefac),
        )
        # System.dynamic_states += prefac * System.dynamic_rates(time, prefac)

    def _second_kinematic_prefactor(self, dt: np.float64) -> np.float64:
        return self.χ * dt

    def _second_kinematic_step(
        self, System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
    ) -> None:
        prefac = self._second_kinematic_prefactor(dt)
        overload_operator_kinematic_numba(
            System.n_nodes,
            prefac,
            System.kinematic_states.position_collection,
            System.kinematic_states.director_collection,
            System.velocity_collection,
            System.omega_collection,
        )
        # System.kinematic_states += prefac * System.kinematic_rates(time, prefac)

    def _second_dynamic_step(
        self, System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
    ) -> None:
        prefac = self.λ * dt
        overload_operator_dynamic_numba(
            System.dynamic_states.rate_collection,
            System.dynamic_rates(time, prefac),
        )
        # System.dynamic_states += prefac * System.dynamic_rates(time, prefac)

    def _third_kinematic_prefactor(self, dt: np.float64) -> np.float64:
        return self.xi_chi_dash_coeff * dt

    def _third_kinematic_step(
        self, System: SymplecticSystemProtocol, time: np.float64, dt: np.float64
    ) -> None:
        prefac = self._third_kinematic_prefactor(dt)
        # Need to fill in
        overload_operator_kinematic_numba(
            System.n_nodes,
            prefac,
            System.kinematic_states.position_collection,
            System.kinematic_states.director_collection,
            System.velocity_collection,
            System.omega_collection,
        )
        # System.kinematic_states += prefac * System.kinematic_rates(time, prefac)

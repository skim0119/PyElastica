__doc__ = """ Rod base classes and implementation details that need to be hidden from the user"""
import numpy as np
import functools

from ._linalg import _batch_matmul, _batch_matvec, _batch_cross
from ._calculus import quadrature_kernel, difference_kernel
from ._rotations import _inv_rotate

# TODO Add documentation for all functions


@functools.lru_cache(maxsize=1)
def _get_z_vector():
    return np.array([0.0, 0.0, 1.0]).reshape(3, -1)


# First the constitutive laws, only simple linear for now
class _LinearConstitutiveModel:

    # Needs
    # kappa, kappa0, strain (sigma), sigma0, B, S in specified formats
    # maybe use __init__ to initialize if not found?
    def __init__(self, rest_sigma, rest_kappa, shear_matrix, bend_matrix):
        self.rest_sigma = rest_sigma
        self.shear_matrix = shear_matrix
        self.bend_matrix = bend_matrix

    def _compute_internal_shear_stretch_stresses_from_model(self):
        """
        Linear force functional
        Operates on
        S : (3,3,n) tensor and sigma (3,n)

        Returns
        -------

        """
        self._compute_shear_stetch_strains()  # concept : needs to compute sigma
        # TODO : the _batch_matvec kernel needs to depend on the representation of Shearmatrix
        self.internal_stress = _batch_matvec(
            self.shear_matrix, self.sigma - self.rest_sigma
        )

    def _compute_internal_bending_twist_stresses_from_model(self):
        """
        Linear force functional
        Operates on
        B : (3,3,n) tensor and curvature kappa (3,n)

        Returns
        -------

        """
        self._compute_bending_twist_strains()  # concept : needs to compute kappa
        # TODO : the _batch_matvec kernel needs to depend on the representation of Bendmatrix
        self.internal_couple = _batch_matvec(
            self.bend_matrix, self.kappa - self.rest_kappa
        )


class _LinearConstitutiveModelWithStrainRate(_LinearConstitutiveModel):
    def __init__(self):
        super(_LinearConstitutiveModelWithStrainRate, self).__init__()

    def _compute_internal_shear_stretch_stresses_from_model(self):
        """
        Linear force functional
        Operates on
        S : (3,3,n) tensor and sigma (3,n)

        Returns
        -------

        """
        # Calculates stress based purely on strain component
        super(_LinearConstitutiveModelWithStrainRate, self)._compute_internal_shear_stretch_stresses_from_model()
        self._compute_shear_stetch_strain_rates()  # concept : needs to compute sigma_dot
        # TODO : the _batch_matvec kernel needs to depend on the representation of ShearStrainmatrix
        self.internal_stress += _batch_matvec(
            self.shear_strain_matrix, self.sigma_dot
        )

    def _compute_internal_bending_twist_stresses_from_model(self):
        """
        Linear force functional
        Operates on
        B : (3,3,n) tensor and curvature kappa (3,n)

        Returns
        -------

        """
        # Calculates stress based purely on strain component
        super(_LinearConstitutiveModelWithStrainRate, self)._compute_internal_bending_twist_stresses_from_model()
        self._compute_bending_twist_strain_rates()  # concept : needs to compute kappa rate
        # TODO : the _batch_matvec kernel needs to depend on the representation of Bendmatrix
        self.internal_couple += _batch_matvec(
            self.bend_matrix, self.kappa_dot
        )


# The interface class, as seen from global scope
# Can be made common to all entities in the code
class RodBase:
    """
    Base class for all rods
    # TODO : What needs to be ported here?
    """

    def __init__(self):
        pass

    def get_velocity(self):
        return self.velocity

    def get_angular_velocity(self):
        return self.omega

    def get_acceleration(self):
        return (self._compute_internal_forces() + self.external_forces) / self.mass

    def get_angular_acceleration(self):
        return self._compute_internal_torques() + self.external_torques


class _CosseratRodBase(RodBase):
    # I'm assuming number of elements can be deduced from the size of the inputs
    def __init__(self, position, velocity, omega, directors, rest_lengths, mass, density,
                 mass_second_moment_of_inertia):
        self.position = position
        self.velocity = velocity
        self.omega = omega
        self.directors = directors
        self.rest_lengths = rest_lengths
        self.mass = mass
        self.density = density
        self.volume = self.mass / self.density
        self.mass_second_moment_of_inertia = mass_second_moment_of_inertia

    def _compute_geometry_from_state(self):
        """
        Returns
        -------

        """
        # Compute eq (3.3) from 2018 RSOS paper

        # Note : we can use the two-point difference kernel, but it needs unnecessary padding
        # and hence will always be slower
        position_diff = self.position[..., 1:] - self.position[..., :-1]
        self.lengths = np.sqrt(np.einsum("ij,ij->j", position_diff, position_diff))
        self.tangents = position_diff / self.lengths
        # resize based on volume conservation
        self.radius = np.sqrt(self.volume / self.lengths / np.pi)

    def _compute_all_dilatations(self):
        """
        Compute element and Voronoi region dilatations
        Returns
        -------

        """
        # Caveat : Needs already set rest_lengths and rest voronoi domain lengths
        # Put in initialization

        self.dilatation = self.lengths / self.rest_lengths

        # Cmopute eq (3.4) from 2018 RSOS paper

        # Note : we can use trapezoidal kernel, but it has padding and will be slower
        voronoi_lengths = 0.5 * (self.lengths[1:] + self.lengths[:-1])

        # Cmopute eq (3.45 from 2018 RSOS paper
        self.voronoi_dilatation = voronoi_lengths / self.rest_voronoi_lengths

    def _compute_dilatation_rate(self):
        """

        Returns
        -------

        """
        # self.lengths = l_i = |r^{i+1} - r^{i}|
        r_dot_v = np.einsum("ij,ij->j", self.position, self.velocity)
        r_plus_one_dot_v = np.einsum(
            "ij, ij->j", self.position[..., 1:], self.velocity[..., :-1]
        )
        r_dot_v_plus_one = np.einsum(
            "ij, ij->j", self.position[..., :-1], self.velocity[..., 1:]
        )
        self.dilatation_rate = (
            (r_dot_v[..., :-1] + r_dot_v[..., 1:] - r_dot_v_plus_one - r_plus_one_dot_v)
            / self.lengths
            / self.rest_lengths
        )

    def _compute_shear_stetch_strains(self):
        # Quick trick : Instead of evaliation Q(et-d^3), use property that Q*d3 = (0,0,1), a constant
        self._compute_all_dilatations()
        self.sigma = (
            self.dilatation * _batch_matvec(self.directors, self.tangents)
            - _get_z_vector()
        )

    def _compute_bending_twist_strains(self):
        self.kappa = _inv_rotate(self.directors) / self.rest_voronoi_lengths

    def _compute_internal_forces(self):
        # Compute n_l and cache it using internal_stress
        # Be careful about usage though
        self._compute_internal_shear_stretch_stresses_from_model()
        # Signifies Q^T n_L / e
        # Not using batch matvec as I don't want to take directors.T here
        cosserat_internal_stress = (
            np.einsum("jik, jk->ik", self.directors, self.internal_stress)
            / self.dilatation  # computed in comp_dilatation <- compute_strain <- compute_stress
        )
        return difference_kernel(cosserat_internal_stress)

    def _compute_internal_torques(self):
        # Compute \tau_l and cache it using internal_couple
        # Be careful about usage though
        self._compute_internal_bending_twist_stresses_from_model()
        # Compute dilatation rate when needed, dilatation itself is done before
        # in internal_stresses
        self._compute_dilatation_rate()

        voronoi_dilatation_cube_cached = 1.0 / self.voronoi_dilatation ** 3
        # Delta(\tau_L / \Epsilon^3)
        bend_twist_couple_2D = difference_kernel(
            self.internal_couple * voronoi_dilatation_cube_cached
        )
        # \mathcal{A}[ (\kappa x \tau_L ) * \hat{D} / \Epislon^3 ]
        bend_twist_couple_3D = quadrature_kernel(
            _batch_cross(self.kappa, self.internal_couple)
            * self.rest_voronoi_lengths
            * voronoi_dilatation_cube_cached
        )
        # (Qt x n_L) * \hat{l}
        shear_stretch_couple = (
            _batch_cross(
                _batch_matvec(self.directors, self.tangents), self.internal_stress
            )
            * self.rest_lengths
        )

        # I apply common sub expression elimination here, as J w / e is used in both the lagrangian and dilatation
        # terms
        # TODO : the _batch_matvec kernel needs to depend on the representation of J, and should be coded as such
        J_omega_upon_e = (
            _batch_matvec(self.mass_second_moment_of_inertia, self.omega)
            / self.dilatation
        )

        # (J \omega_L / e) x \omega_L
        # Warning : Do not do micro-optimization here : you can ignore dividing by dilatation as we later multiply by it
        # but this causes confusion and violates SRP
        lagrangian_transport = _batch_cross(J_omega_upon_e, self.omega)

        # Note : in the computation of dilatation_rate, there is an optimization opportunity as dilatation rate has
        # a dilatation-like term in the numerator, which we cancel here
        # (J \omega_L / e^2) . (de/dt)
        unsteady_dilatation = J_omega_upon_e * self.dilatation_rate / self.dilatation

        return (
            bend_twist_couple_2D
            + bend_twist_couple_3D
            + shear_stretch_couple
            + lagrangian_transport
            + unsteady_dilatation
        )


class CosseratRod(_LinearConstitutiveModel, _CosseratRodBase):
    def __init__(self, position, velocity, omega, directors, rest_lengths, mass, density,
                 mass_second_moment_of_inertia, rest_sigma, rest_kappa, shear_matrix,
                 bend_matrix):
        _LinearConstitutiveModel.__init__(rest_sigma, rest_kappa, shear_matrix,
                                          bend_matrix)
        _CosseratRodBase.__init__(position, velocity, omega, directors, rest_lengths,
                                  mass, density, mass_second_moment_of_inertia)
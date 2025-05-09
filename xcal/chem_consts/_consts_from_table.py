import numpy as np
import os
import h5py
import chemparse
from ._periodictabledata import atom_weights

def calculate_molecular_mass(formula):
    """
    interpret the formula as either a dictionary
    or a chemical formula
    """
    formula_dict = interpret_formula(formula)
    M = 0.
    for k,v in formula_dict.items():
        M += v * atom_weights[k]

    return M

def interpret_formula(formula):
    """
    Determine whether the formula is a dictionary or a string,
    interpret string to a dictionary,
    and then calculate the number of distinct elements present in the formula.

    @author Wenrui Li, Purdue University
    @date   04/12/2022
    """
    if isinstance(formula, dict):
        return formula

    elif isinstance(formula, str):
        # interpret string to a dictionary
        return chemparse.parse_formula(formula)

def get_mass_absp_c_vs_E(formula, energy_vector):
    """
    Calculate the mass absorption coefficient (mu) as a function of energy,
    using mass absorption coefficients from the NIST website:
    https://physics.nist.gov/PhysRefData/XrayMassCoef/tab3.html.

    Author: Wenrui Li, Purdue University
    Date: 12/14/2023

    Parameters
    ----------
    formula : str/dict
        Chemical formula of the compound, either as a string or a dict.
        For example, "H2O" and {"H": 2, "O": 1} are both acceptable.
    energy_vector : list/numpy.ndarray
        Energy (units: keV) list or 1D array for which beta values are calculated.

    Returns
    -------
    numpy.ndarray
        Linear attenuation coefficient values in mm^-1, with the same size as energy_vector.

    """
    # Path to the mass attenuation coefficient data file
    cc_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "chem_consts", "mu_en.h5")

    # Interpret the input formula
    formula_dict = interpret_formula(formula)

    # Initialize the total mass attenuation coefficient array
    mu_rhotot = np.zeros_like(energy_vector)

    molecular_mass = calculate_molecular_mass(formula)

    # Read the mass attenuation coefficient data file
    # Calculate the linear attenuation coefficient for the given formula
    with h5py.File(cc_path, 'r') as fid:
        for elem, nelem in formula_dict.items():
            wi = nelem * atom_weights[elem] / molecular_mass

            d = np.array(fid[f"/{elem}/data"])

            E = d[:, 0]
            mu_rho = d[:, 2]

            # Interpolate in log-log space using the prescribed method
            logmu_rho = np.interp(np.log(energy_vector), np.log(E), np.log(mu_rho), left=0.0, right=0.0)
            mu_rho_loginterp = np.exp(logmu_rho)

            # Accumulate the total mass energy-absorption coefficient
            mu_rhotot += wi * mu_rho_loginterp

        # Calculate the linear attenuation coefficient (g/cm^2))
        mu = mu_rhotot

    return mu

def get_lin_att_c_vs_E(density, formula, energy_vector):
    """
    Calculate the linear attenuation coefficient (mu) as a function of energy,
    using mass attenuation coefficients from the NIST website:
    https://physics.nist.gov/PhysRefData/XrayMassCoef/tab3.html.

    Author: Wenrui Li, Purdue University
    Date: 04/12/2022

    Parameters
    ----------
    density : float
        Density of the material in g/cm^3.
    formula : str/dict
        Chemical formula of the compound, either as a string or a dict.
        For example, "H2O" and {"H": 2, "O": 1} are both acceptable.
    energy_vector : list/numpy.ndarray
        Energy (units: keV) list or 1D array for which beta values are calculated.

    Returns
    -------
    numpy.ndarray
        Linear attenuation coefficient values in mm^-1, with the same size as energy_vector.

    """
    # Path to the mass attenuation coefficient data file
    cc_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "chem_consts", "mu_en.h5")

    # Interpret the input formula
    formula_dict = interpret_formula(formula)

    # Initialize the total mass attenuation coefficient array
    mu_rhotot = np.zeros_like(energy_vector)

    molecular_mass = calculate_molecular_mass(formula)

    # Read the mass attenuation coefficient data file
    # Calculate the linear attenuation coefficient for the given formula
    with h5py.File(cc_path, 'r') as fid:
        for elem, nelem in formula_dict.items():
            wi = nelem * atom_weights[elem] / molecular_mass

            d = np.array(fid[f"/{elem}/data"])

            E = d[:, 0]
            mu_rho = d[:, 1]

            # Interpolate in log-log space using the prescribed method
            logmu_rho = np.interp(np.log(energy_vector), np.log(E), np.log(mu_rho), left=0.0, right=0.0)
            mu_rho_loginterp = np.exp(logmu_rho)

            # Accumulate the total mass attenuation coefficient
            mu_rhotot += wi * mu_rho_loginterp

        # Calculate the linear attenuation coefficient (convert from cm^-1 to mm^-1)
        mu = density * mu_rhotot / 10

    return mu


def get_lin_absp_c_vs_E(density, formula, energy_vector):
    """
    Calculate the linear energy-absorption coefficient (mu) as a function of energy,
    using mass energy-absorption coefficients from the NIST website:
    https://physics.nist.gov/PhysRefData/XrayMassCoef/tab3.html.

    Author: Wenrui Li, Purdue University
    Date: 04/12/2022

    Parameters
    ----------
    density : float
        Density of the material in g/cm^3.
    formula : str/dict
        Chemical formula of the compound, either as a string or a dict.
        For example, "H2O" and {"H": 2, "O": 1} are both acceptable.
    energy_vector : list/numpy.ndarray
        Energy (units: keV) list or 1D array for which beta values are calculated.

    Returns
    -------
    numpy.ndarray
        Linear energy-absorption coefficient values in mm^-1, with the same size as energy_vector.

    """
    # Path to the mass energy-absorption coefficient data file
    cc_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "chem_consts", "mu_en.h5")

    # Interpret the input formula
    formula_dict = interpret_formula(formula)

    # Initialize the total mass energy-absorption coefficient array
    mu_rhotot = np.zeros_like(energy_vector)

    molecular_mass = calculate_molecular_mass(formula)

    # Read the mass energy-absorption coefficient data file
    with h5py.File(cc_path, 'r') as fid:
        for elem, nelem in formula_dict.items():
            wi = nelem * atom_weights[elem] / molecular_mass

            d = np.array(fid[f"/{elem}/data"])

            E = d[:, 0]
            mu_rho = d[:, 2]

            # Interpolate in log-log space using the prescribed method
            logmu_rho = np.interp(np.log(energy_vector), np.log(E), np.log(mu_rho), left=0.0, right=0.0)
            mu_rho_loginterp = np.exp(logmu_rho)

            # Accumulate the total mass energy-absorption coefficient
            mu_rhotot += wi * mu_rho_loginterp

        # Calculate the linear energy-absorption coefficient (convert from cm^-1 to mm^-1)
        mu = density * mu_rhotot / 10

    return mu


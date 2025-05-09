# Basic Packages
import os
import numpy as np
import matplotlib.pyplot as plt
import warnings
import mbirjax
import h5py

from xcal.chem_consts import get_lin_att_c_vs_E
from xcal import calc_forward_matrix
from xcal._utils import Gen_Circle
import spekpy as sp  # Import SpekPy
from xcal.defs import Material
from xcal.chem_consts._periodictabledata import density
from xcal.models import *

import torch

def read_mv_hdf5(file_name):
    data = []
    with h5py.File(file_name, 'r') as f:
        for key in f.keys():
            grp_i = f[key]
            dict_i = {}
            for sub_key in grp_i.keys():
                if isinstance(grp_i[sub_key], h5py.Group):
                    dict_i[sub_key] = {k: v for k, v in grp_i[sub_key].attrs.items()}
                else:
                    dict_i[sub_key] = np.array(grp_i[sub_key])
            data.append(dict_i)
    return data

# Customerize forward projector with a forward function that do forwald projection of a given mask.
class fw_projector:
    def __init__(self, angles, num_channels, delta_pixel=1):
        """

        Parameters
        ----------
        energies
        N_views
        psize
        xcenter
        arange
        """
        self.angles = angles
        self.num_channels = num_channels
        self.delta_pixel = delta_pixel
        self.sinogram_shape = (len(angles), 1, self.num_channels)

    def forward(self, mask):
        """

        Parameters
        ----------
        mask : numpy.ndarray
            3D mask for pure solid object.

        Returns
        -------
        lai : numpy.ndarray
            Linear attenuation integral, of size M measurement * N energy bins.

        """

        ct_model_for_generation = mbirjax.ParallelBeamModel(self.sinogram_shape, self.angles)
        # Print out model parameters
        ct_model_for_generation.print_params()
        projections = ct_model_for_generation.forward_project(mask) * self.delta_pixel

        return projections

def gen_datasets_3_voltages():
    os.makedirs('./output/', exist_ok=True)
    # Pixel size in mm units.
    rsize = 0.01  # mm

    # Number of channels in detector
    nchanl = 1024

    # Scanned cylinders
    materials = ['V', 'Al', 'Ti', 'Mg']
    mat_density = [density['%s' % formula] for formula in materials]  # g/cm³

    # 5 cylinders are evenly distributed on a circle
    Radius = [1 for _ in range(len(materials))]
    arrange_with_radius = 3
    centers = [[np.sin(rad_angle) * arrange_with_radius, np.cos(rad_angle) * arrange_with_radius]
               for rad_angle in np.linspace(-np.pi / 2, -np.pi / 2 + np.pi * 2, len(materials), endpoint=False)]

    # Simulated sinogram parameters
    num_views = 40
    tilt_angle = np.pi / 2  # Tilt range of +-90deg
    # Generate the array of view angles
    angles = np.linspace(-tilt_angle, tilt_angle, num_views, endpoint=False)

    # Each mask represents a homogenous cylinder.
    mask_list = []
    for mat_id, mat in enumerate(materials):
        circle = Gen_Circle((nchanl, nchanl), (rsize, rsize))
        mask_list.append(circle.generate_mask(Radius[mat_id], centers[mat_id])[np.newaxis])

    plt.figure(1)
    plt.imshow(np.sum(
        np.array([ml * get_lin_att_c_vs_E(mat_density[i], materials[i], 60.0) for i, ml in enumerate(mask_list)]),
        axis=(0, 1)), vmin=0, vmax=0.5)

    # Adding a colorbar
    cbar = plt.colorbar()
    cbar.set_label('$mm^{-1}$')  # Label for the colorbar

    # Optional: Add title and axis labels
    plt.title('Linear Attenuation Coefficients at 60 kV')
    plt.savefig('./output/d1_lac.png')
    voltage_list = [80, 130, 180]  # kV

    max_simkV = max(voltage_list)
    takeoff_angle = 20
    ref_takeoff_angle = 11
    # Energy bins.
    energies = np.linspace(1.5, max_simkV - 0.5, max_simkV-1)

    # Use Spekpy to generate a source spectra dictionary.
    src_spec_list = []
    # fig, axs = plt.subplots(1, 1, figsize=(12, 9), dpi=80)
    # plt.figure(2)
    print('\nRunning demo script (10 mAs, 100 cm)\n')
    for simkV in voltage_list:
        s = sp.Spek(kvp=simkV, th=ref_takeoff_angle, dk=1, mas=1, char=True)  # Create the spectrum model
        k, phi_k = s.get_spectrum(edges=False)  # Get arrays of energy & fluence spectrum
        # Adjust the fluence for the detector pixel area.
        phi_k = phi_k * ((rsize / 10) ** 2)  # Convert pixel size from mm² to cm²
        ## Plot the x-ray spectrum

        # Initialize a zero-filled spectrum array with length max_simkV.
        src_spec = np.zeros(max_simkV - 1)
        src_spec[:simkV - 1] = phi_k  # Assign spectrum values starting from 1.5 keV
        src_spec_list.append(src_spec)
        # axs.plot(energies, src_spec_list[-1],
        #          label='Char: kvp:%d Anode angle:%d' % (simkV, ref_takeoff_angle))
    src_spec_list = np.array(src_spec_list)
    src_spec_list = src_spec_list.reshape((len(voltage_list), 1, -1))

    print('\nFinished!\n')
    # axs.set_xlabel('Energy  [keV]', fontsize=8)
    # axs.set_ylim((0, 1E2))
    # axs.set_ylabel('Differential fluence  [mm$^{-2}$ mAs$^{-1}$ keV$^{-1}$]', fontsize=8)
    # axs.set_title('X-ray Source spectrum generated by spekpy')
    # axs.legend(fontsize=8)

    # A dictionary of source spectra with source voltage from 30 kV to 200 kV
    src_spec_list = np.array(src_spec_list)
    # plt.savefig('./output/d1_source_spec.png')

    plt.figure(3)

    sources = [Reflection_Source(voltage=(voltage, None, None), takeoff_angle=(ref_takeoff_angle, None, None), single_takeoff_angle=True) for
        voltage in voltage_list]
    for src_i, source in enumerate(sources):
        source.set_src_spec_list(energies, src_spec_list, voltage_list, [ref_takeoff_angle])
        plt.plot(energies, source(energies), label='%d kV'%voltage_list[src_i])
    plt.title('Spectrally distributed photon flux')
    plt.xlabel('Energy  [keV]')
    plt.legend()
    plt.savefig('./output/d1_source_spec.png')

    plt.figure(4)
    psb_fltr_mat = [Material(formula='Al', density=2.702), Material(formula='Cu', density=8.92)]
    filter_1 = Filter(psb_fltr_mat[0:1], thickness=(3, None, None))
    plt.plot(energies, filter_1(energies), label='3mm Al')
    plt.title('Filter Responses')
    plt.legend()
    plt.xlabel('Energy  [keV]')
    plt.savefig('./output/d1_fliter.png')

    plt.figure(5)
    scint_params_list = [
        {'formula': 'CsI', 'density': 4.51},
        {'formula': 'Gd3Al2Ga3O12', 'density': 6.63},
        {'formula': 'Lu3Al5O12', 'density': 6.73},
        {'formula': 'CdWO4', 'density': 7.9},
        {'formula': 'Y3Al5O12', 'density': 4.56},
        {'formula': 'Bi4Ge3O12', 'density': 7.13},
        {'formula': 'Gd2O2S', 'density': 7.32}
    ]
    psb_scint_mat = [Material(formula=scint_p['formula'], density=scint_p['density']) for scint_p in scint_params_list]
    scintillator_1 = Scintillator(materials=psb_scint_mat[0:1], thickness=(0.33, None, None))
    plt.plot(energies, scintillator_1(energies), label='0.33 mm CsI')
    plt.title('Scintillator Response.')
    plt.legend()
    plt.xlabel('Energy  [keV]')
    plt.savefig('./output/d1_scintillator.png')

    plt.figure(6)
    gt_spec_list = [(source(energies) * filter_1(energies)  * scintillator_1(energies)).numpy() for source in sources]
    for spec_i, gt_spec in enumerate(gt_spec_list):
        plt.plot(energies, gt_spec / np.trapezoid(gt_spec, energies), label='%d kV'%voltage_list[spec_i])
    plt.legend()
    plt.title('X-ray spectral effective spectrum')
    plt.xlabel('Energy  [keV]')
    plt.savefig('./output/d1_effective spectrum.png')

    plt.figure(7)
    datasets = []
    label_list = ['80 kV', '130 kV', '180 kV']
    for case_i, gt_spec in zip(np.arange(len(gt_spec_list)), gt_spec_list):

        spec_F_train_list = []
        trans_list = []

        lac_vs_E_list = []
        # Each mask represents a homogenous cylinder.
        # Each lac_vs_E represents the homogenous material's linear attenuation coefficient.
        for i in range(len(mask_list)):
            formula = materials[i]
            den = mat_density[i]
            lac_vs_E_list.append(get_lin_att_c_vs_E(den, formula, energies))

        # SVMBIR Forward Projector, you can use your customerize forward projector.
        projector = fw_projector(angles, num_channels=nchanl, delta_pixel=rsize)
        # Forward Matrix F. calc_forward_matrix.rst uses given forward projector, LAC value,
        # and masks of homogenous objects to calculate a forward matrix.
        spec_F = calc_forward_matrix(mask_list, lac_vs_E_list, projector)

        # Add poisson noise before reaching detector/scintillator.
        trans = np.trapezoid(spec_F * gt_spec, energies, axis=-1)
        trans_0 = np.trapezoid(gt_spec, energies, axis=-1)
        trans_noise = np.random.poisson(trans).astype(np.float64)
        trans_noise /= trans_0

        # Store noiseless transmission data and forward matrix.
        trans_list.append(trans_noise)
        spec_F_train = spec_F.reshape((-1, spec_F.shape[-1]))
        spec_F_train_list.append(spec_F_train)
        spec_F_train_list = np.array(spec_F_train_list)
        trans_list = np.array(trans_list)

        plt.plot(trans_list[0][16, 0], label=label_list[case_i])

        d = {
            'measurement': trans_list,
            'forward_mat': spec_F_train_list,
            'source': sources[case_i],
            'filter': filter_1,
            'scintillator': scintillator_1,
        }
        datasets.append(d)
    plt.savefig('./output/d1_sim_trans.png')
    plt.close('all')
    return datasets


from xcal.defs import Material
from xcal.models import Base_Spec_Model, prepare_for_interpolation
from xcal.models import Filter, Scintillator
import torch
class Synchrotron_Source(Base_Spec_Model):
    def __init__(self, voltage):
        """
        A template source model designed specifically for reflection sources, including all necessary methods.

        Args:
            voltage (tuple): (initial value, lower bound, upper bound) for the source voltage.
                These three values cannot be all None. It will not be optimized when lower == upper.
        """
        params_list = [{'voltage': voltage}]
        super().__init__(params_list)


    def set_src_spec_list(self, src_spec_list, src_voltage_list):
        """Set source spectra for interpolation, which will be used only by forward function.

        Args:
            src_spec_list (numpy.ndarray): This array contains the reference X-ray source spectra. Each spectrum in this array corresponds to a specific combination of the ref_takeoff_angle and one of the source voltages from src_voltage_list.
            src_voltage_list (numpy.ndarray): This is a sorted array containing the source voltages, each corresponding to a specific reference X-ray source spectrum.
        """
        self.src_spec_list = np.array(src_spec_list)
        self.src_voltage_list = np.array(src_voltage_list)
        modified_src_spec_list = prepare_for_interpolation(self.src_spec_list, self.src_voltage_list)
        self.src_spec = torch.tensor(modified_src_spec_list[0], dtype=torch.float32)


    def forward(self, energies):
        """
        Takes X-ray energies and returns the source spectrum.

        Args:
            energies (torch.Tensor): A tensor containing the X-ray energies of a poly-energetic source in units of keV.

        Returns:
            torch.Tensor: The source response.
        """

        return self.src_spec
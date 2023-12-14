# Basic Packages
import os
import numpy as np
import matplotlib.pyplot as plt
import warnings
import svmbir
import h5py

from xspec.chem_consts import get_lin_att_c_vs_E
from xspec.dictSE import cal_fw_mat
from xspec._utils import Gen_Circle
import spekpy as sp  # Import SpekPy
from xspec.defs import *
from xspec import paramSE
from xspec.chem_consts._periodictabledata import density

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
    def __init__(self, angles, num_channels, delta_pixel=1, geometry='parallel'):
        """

        Parameters
        ----------
        energies
        N_views
        psize
        xcenter
        geometry
        arange
        """
        self.angles = angles
        self.num_channels = num_channels
        self.delta_pixel = delta_pixel
        self.geometry = geometry

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

        projections = svmbir.project(mask, self.angles, self.num_channels) * self.delta_pixel

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
    plt.imshow(np.sum(np.array([ml*get_lin_att_c_vs_E(mat_density[i], materials[i], 60.0) for i, ml in enumerate(mask_list)]), axis=(0,1)), vmin=0, vmax=0.5)

    # Adding a colorbar
    cbar = plt.colorbar()
    cbar.set_label('$mm^{-1}$')  # Label for the colorbar

    # Optional: Add title and axis labels
    plt.title('Linear Attenuation Coefficients at 60 kV')
    plt.savefig('./output/1.png')

    simkV_list = np.linspace(30, 200, 18, endpoint=True).astype('int')
    max_simkV = max(simkV_list)
    anode_angle = 11

    # Energy bins.
    energies = np.linspace(1, max_simkV, max_simkV)

    # Use Spekpy to generate a source spectra dictionary.
    src_spec_list = []
    plt.figure(2)
    fig, axs = plt.subplots(1, 1, figsize=(12, 9), dpi=80)
    print('\nRunning demo script (10 mAs, 100 cm)\n')
    for simkV in simkV_list:
        s = sp.Spek(kvp=simkV + 1, th=anode_angle, dk=1, mas=10, char=True)  # Create the spectrum model
        k, phi_k = s.get_spectrum(edges=True)  # Get arrays of energy & fluence spectrum
        phi_k = phi_k * ((rsize / 10) ** 2)
        ## Plot the x-ray spectrum
        axs.plot(k[::2], phi_k[::2],
                 label='Char: kvp:%d Anode angle:%d' % (simkV, anode_angle))
        src_spec = np.zeros((max_simkV))
        src_spec[:simkV] = phi_k[::2]
        src_spec_list.append(src_spec)

    print('\nFinished!\n')
    axs.set_xlabel('Energy  [keV]', fontsize=8)
    axs.set_ylim((0, 0.2E4))
    axs.set_ylabel('Differential fluence  [mm$^{-2}$ mAs$^{-1}$ keV$^{-1}$]', fontsize=8)
    axs.set_title('X-ray Source spectrum generated by spekpy')
    axs.legend(fontsize=8)

    # A dictionary of source spectra with source voltage from 30 kV to 200 kV
    src_spec_list = np.array(src_spec_list)
    plt.savefig('./output/2.png')

    plt.figure(3)
    num_src_v = 3
    voltage_list = [80.0, 130.0, 180.0] # kV
    # Bound is a python structure to store the possible range for a continuous variable.
    src_vol_bound = Bound(lower=30.0, upper=200.0)
    takeoff_angle_bound = Bound(lower=5.0, upper=45.0)
    # Source is a python structure to store a source's parameters, including
    # energy bins, kV list and corresponding source spectral dictionary, bound of source voltage, and source voltage.
    Src_config = [Source(energies, simkV_list, 11, src_spec_list,
                         src_vol_bound, takeoff_angle_bound, voltage=vv, takeoff_angle=14,
                         optimize_voltage=False, optimize_takeoff_angle=False) for vv in
                  voltage_list]
    ref_src_spec_list = []
    for sc in Src_config:
        # Pass a source's parameters to Source_Model.
        src_model = paramSE.Source_Model(sc)
        with (torch.no_grad()):
            # Forward function of the Source_Model is the source spectrum/spectrally distributed photon flux.
            ref_src_spec_list.append(src_model(energies).data.numpy())
            plt.plot(energies, src_model(energies).data, label = '%d kV'%sc.voltage)
    plt.title('Spectrally distributed photon flux')
    plt.xlabel('Energy  [keV]')
    plt.legend()
    plt.savefig('./output/3.png')

    plt.figure(4)
    fltr_th_bound = Bound(lower=0.0, upper=10.0)  # 0.0 ~ 10.0 mm

    fltr_th = 3.0  # mm

    # Filter is a python structure to store a filter's parameters.
    Fltr_config = [Filter([], fltr_th_bound, fltr_mat=Material(formula='Al', density=2.702), fltr_th=fltr_th),
                   ]

    ref_fltr_resp_list = []
    for fci, fr in enumerate(Fltr_config):
        # Forward function of the Filter_Model is the filter response.
        fltr_model = paramSE.Filter_Model(fr)
        with (torch.no_grad()):
            ref_fltr_resp_list.append(fltr_model(energies).data.numpy())
            plt.plot(energies, fltr_model(energies).data, label='%d mm %s' % (fr.fltr_th, fr.fltr_mat.formula))
    plt.title('Filter Responses')
    plt.legend()
    plt.xlabel('Energy  [keV]')
    plt.savefig('./output/4.png')

    plt.figure(5)
    scint_th_bound = Bound(lower=0.01, upper=0.5)
    # Use Lu3Al5O12, the third scintillator, as ground truth scintillator.
    # Scintillator is a python structure to store a scintillator's parameters.
    Scint_config = [Scintillator([], scint_th_bound, scint_mat=Material(formula='CsI', density=4.51), scint_th = 0.33)]
    ref_scint_cvt_list = []
    for st in Scint_config:
        # Forward function of the Scintillator_Model is the scintillator response.
        scint_model = paramSE.Scintillator_Model(st)
        with (torch.no_grad()):
            ref_scint_cvt_list.append(scint_model(energies).data.numpy())
            plt.plot(energies, scint_model(energies).data, label='%.2f mm %s'%(st.scint_th, st.scint_mat.formula))
    plt.title('Scintillator Response.')
    plt.legend()
    plt.xlabel('Energy  [keV]')
    plt.savefig('./output/5.png')

    plt.figure(6)
    model_combination = [Model_combination(src_ind=0, fltr_ind_list=[0], scint_ind=0),
                         Model_combination(src_ind=1, fltr_ind_list=[0], scint_ind=0),
                         Model_combination(src_ind=2, fltr_ind_list=[0], scint_ind=0),
                        ]

    gt_spec_list= []
    ll = [ '80 kV', '130 kV', '180 kV']
    i = 0
    for mc in model_combination:
        src_s = ref_src_spec_list[mc.src_ind]
        fltr_s = ref_fltr_resp_list[mc.fltr_ind_list[0]]
        for fii in mc.fltr_ind_list[1:]:
            fltr_s=fltr_s*ref_fltr_resp_list[fii]
        scint_s  = ref_scint_cvt_list[mc.scint_ind]
        gt_spec = src_s*fltr_s*scint_s
        gt_spec /= np.trapz(gt_spec, energies, axis=-1)
        gt_spec_list.append(gt_spec)
        plt.plot(energies, gt_spec, label=ll[i])
        i+=1
    plt.legend()
    plt.title('X-ray spectral energy response')
    plt.xlabel('Energy  [keV]')
    plt.savefig('./output/6.png')

    datasets=[]
    plt.figure(7)
    for case_i, gt_spec, mc in zip(np.arange(len(gt_spec_list)), gt_spec_list, model_combination):

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
        pfp = fw_projector(angles, num_channels=nchanl, delta_pixel=rsize)
        # Forward Matrix F. cal_fw_mat uses given forward projector, LAC value,
        # and masks of homogenous objects to calculate a forward matrix.
        spec_F = cal_fw_mat(mask_list, lac_vs_E_list, energies, pfp)

        # Decomposed Source-Filter-Scintillator Model
        src_s = ref_src_spec_list[mc.src_ind]
        fltr_s = ref_fltr_resp_list[mc.fltr_ind_list[0]]
        for fii in mc.fltr_ind_list[1:]:
            fltr_s = fltr_s * ref_fltr_resp_list[fii]
        scint_s = ref_scint_cvt_list[mc.scint_ind]

        # Add poisson noise before reaching detector/scintillator.
        lambda_1 = spec_F * src_s * fltr_s
        lambda_0 = src_s * fltr_s
        lambda_noise = np.random.poisson(lambda_1)
        trans_noise = np.trapz(lambda_noise * scint_s, energies, axis=-1)
        trans_noise /= np.trapz(lambda_0 * scint_s, energies, axis=-1)

        # Store noiseless transmission data and forward matrix.
        trans_list.append(trans_noise)
        spec_F_train = spec_F.reshape((-1, spec_F.shape[-1]))
        spec_F_train_list.append(spec_F_train)
        spec_F_train_list = np.array(spec_F_train_list)
        trans_list = np.array(trans_list)

        plt.plot(trans_list[0][16, 0], label=ll[case_i])

        # Save simulated dataset to h5py file.
        src_dict_h5 = {
            'energies': energies,
            'src_spec': ref_src_spec_list[mc.src_ind],
            'voltage': float(Src_config[mc.src_ind].voltage)
        }

        fltr_dict_h5 = {}

        for i in mc.fltr_ind_list:
            fltr_dict_h5['fltr_mat_0_formula'] = Fltr_config[i].fltr_mat.formula
            fltr_dict_h5['fltr_mat_0_density'] = Fltr_config[i].fltr_mat.density
            fltr_dict_h5['fltr_mat_0_th'] = Fltr_config[i].fltr_th

        scint_dict_h5 = {
            'scint_th': Scint_config[mc.scint_ind].scint_th,
            'scint_mat_formula': Scint_config[mc.scint_ind].scint_mat.formula,
            'scint_mat_density': Scint_config[mc.scint_ind].scint_mat.density
        }

        d = {
            'measurement': trans_list,
            'forward_mat': spec_F_train_list,
            'src_config': src_dict_h5,
            'fltr_config': fltr_dict_h5,
            'scint_config': scint_dict_h5,
        }
        datasets.append(d)
    return datasets
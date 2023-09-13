import numpy as np
from numpy.core.numeric import asanyarray
import torch
from scipy.signal import butter,filtfilt,find_peaks
import matplotlib.pyplot as plt


light_speed = 299792458.0 # Speed of light
Planck_constant = 6.62607015E-34 # Planck's constant
Joule_per_eV = 1.602176565E-19 # Joules per electron-volts


def to_tensor(data):
    if isinstance(data, torch.Tensor):
        return data
    return torch.tensor(data)


def min_max_normalize_scalar(value, data_min, data_max):
    value = to_tensor(value)
    data_min = to_tensor(data_min)
    data_max = to_tensor(data_max)

    normalized_value = (value - data_min) / (data_max - data_min)

    # If the original input was a standard Python scalar, return a scalar
    if isinstance(value, (float, int)):
        return normalized_value.item()
    return normalized_value


def min_max_denormalize_scalar(normalized_value, data_min, data_max):
    normalized_value = to_tensor(normalized_value)
    data_min = to_tensor(data_min)
    data_max = to_tensor(data_max)

    value = normalized_value * (data_max - data_min) + data_min

    # If the original input was a standard Python scalar, return a scalar
    if isinstance(normalized_value, (float, int)):
        return value.item()
    return value

def is_sorted(lst):
    return all(lst[i] <= lst[i+1] for i in range(len(lst)-1))

def get_wavelength(energy):
    # How is energy related to the wavelength of radiation?
    # https://www.e-education.psu.edu/meteo300/node/682
    return (Planck_constant*light_speed/(energy*Joule_per_eV)) #in mm


def trapz_weight(x, axis=-1):
    """Modified from numpy.trapz. 
       Return weights for y to integrate along the given axis using the composite trapezoidal rule.
    """
    x = asanyarray(x)
    if x.ndim == 1:
        d = np.diff(x)
        # reshape to correct shape
        shape = [1]
        shape[axis] = d.shape[0]
        d = d.reshape(shape)
    else:
        d = np.diff(x, axis=axis)
    nd = 1
    slice1 = [slice(None)]*nd
    slice2 = [slice(None)]*nd
    slice1[axis] = slice(1, None)
    slice2[axis] = slice(None, -1)

    d = np.insert(d,0,0)
    d = np.insert(d,len(d),0)
    d = (d[tuple(slice1)] + d[tuple(slice2)]) / 2.0
    return d

def plot_est_spec(energies, weights_list, coef_, method, src_fltr_info_dict, scint_info_dict, S, mutiply_coef=True,save_path=None):
    plt.figure(figsize=(16,12))
    sd_info=[sfid+sid for sfid in src_fltr_info_dict for sid in scint_info_dict]
    est_sp = weights_list@ coef_
    est_legend = ['%s estimated spectrum'%method]
    plt.plot(energies,est_sp)
    plt.title('%s Estimated Spectrum.\n $|\omega|_1=%.3f$'%(method, np.sum( coef_)))

    for i in S:
        if mutiply_coef:
            plt.plot(energies,weights_list.T[i]* coef_[i])
            eneg_ind = np.argmax(weights_list.T[i])
            plt.text(energies[eneg_ind], weights_list.T[i,eneg_ind]* coef_[i]*1.05, r'%.3f'% coef_[i],\
            horizontalalignment='center', verticalalignment='center')
        else:
            plt.plot(energies,weights_list.T[i], alpha=0.2)
            eneg_ind = np.argmax(weights_list.T[i])
            plt.text(energies[eneg_ind], weights_list.T[i,eneg_ind]*1.05, r'%.3f'% coef_[i],\
            horizontalalignment='center', verticalalignment='center')
        est_legend.append('%.2f mm %s, %.2f mm %s'%(sd_info[i][1],sd_info[i][0],sd_info[i][3],sd_info[i][2]))
    plt.legend(est_legend,fontsize=10)
    if save_path is not None:
        plt.savefig(save_path)





def plot_est_spec_versa(energies, weights_list, coef_, method, spec_info_dict, S, mutiply_coef=True,save_path=None):
    plt.figure(figsize=(16,12))
    est_sp = weights_list@ coef_
    est_legend = ['%s estimated spectrum'%method]
    plt.plot(energies,est_sp)
    plt.title('%s Estimated Spectrum.\n $|\omega|_1=%.3f$'%(method, np.sum( coef_)))

    for i in S:
        if mutiply_coef:
            plt.plot(energies,weights_list.T[i]* coef_[i],label=spec_info_dict[i])
            eneg_ind = np.argmax(weights_list.T[i])
            plt.text(energies[eneg_ind], weights_list.T[i,eneg_ind]* coef_[i]*1.05, r'%.3f'% coef_[i],\
            horizontalalignment='center', verticalalignment='center')
        else:
            plt.plot(energies,weights_list.T[i], alpha=0.2,label=spec_info_dict[i])
            eneg_ind = np.argmax(weights_list.T[i])
            plt.text(energies[eneg_ind], weights_list.T[i,eneg_ind]*1.05, r'%.3f'% coef_[i],\
            horizontalalignment='center', verticalalignment='center')
    plt.legend(fontsize=10)
    if save_path is not None:
        plt.savefig(save_path)



def sep_lh_freq(spectrum, order=2, cutoff=0.2, height=1e-3):
    """

    Parameters
    ----------
    spectrum: numpy.ndarray
        X-Ray spectrum to be seperate into smooth part and peaks.
    order: int
        The order of the filter. An input to scipy.signal.butter.
    cutoff: float
        Desired cutoff frequency of the filter. (0,1)
    height: float
        Required height of peaks.

    Returns
    -------
    smooth: 1D numpy.ndarray
        Smooth part of an 1D sequence.
    high_freq: 1D numpy.ndarray
        High frequency part of an 1D sequence.
    peaks: list
        1D sequence represents the indexes of peaks.

    """

    b, a = butter(order, cutoff, btype='low', analog=False)
    smooth = filtfilt(b, a, spectrum)
    high_freq = spectrum - smooth

    x1, _ = find_peaks(high_freq, height)
    x2, _ = find_peaks(spectrum, height)
    x = set(x1) & set(x2)
    peaks = np.array(list(x))

    return smooth, high_freq, peaks

def gen_high_con_mat(peaks, energies, width=2, mat_type='Equilateral Triangle'):
    """Generate high contrast matrix containing normalized triangles functions as columns,

    Parameters
    ----------
    peaks: list
        1D sequence represents the indexes of peaks.
    energies: numpy.ndarray
        List of X-ray energies of a poly-energetic source in units of keV.
    width: traingle

    Returns
    -------
    B: 2D numpy.ndarray
        The high contrast matrix, which is a highly sparse non-negative matrix.

    """
    xv, yv = np.meshgrid(energies[peaks], energies)
    if mat_type == 'Equilateral Triangle':
        B = np.clip(1-np.abs(1/width * (yv-xv)),0,1)
    elif mat_type == 'Right Triangle':
        mask = (yv-xv)>=0
        B = np.clip(1-(1/width * (yv-xv)),0,1)*mask
    elif mat_type == 'Left Triangle':
        mask = (yv-xv)<=0
        B = np.clip(1+(1/width * (yv-xv)),0,1)*mask
    return B

def normalize_sp(spectrum, energies, high_freq, peaks,energies_w=None, order=2, cutoff=0.2, height=1e-3):
    if energies_w is None:
        energies_w = np.ones(np.shape(spectrum))
    smooth, high_freq, peaks=sep_lh_freq(spectrum.flatten(), order=order, cutoff=cutoff, height=height)
    smooth = np.clip(smooth,0,np.inf)
    B=gen_high_con_mat(peaks, energies, width=5,mat_type='Right Triangle')
    W = np.diag(energies_w)
    B /= np.sum(W@B)
    sm_pks = np.sum(W@(smooth+B@high_freq[peaks]))
    smooth/= sm_pks
    high_freq/= sm_pks 
    return smooth, high_freq, peaks

def huber_func(omega, c):
    if np.abs(omega)<c:
        return omega**2/2
    else:
        return c*np.abs(omega)-c**2/2
        
def binwised_spec_cali_cost(y,x,h,F,W,B,beta,c,energies):
    m,n = np.shape(F)
    e=(y - F @W@ (x + B @ h))
    cost = e.T@e/m
    rho_cost = 0
    for i in range(len(x)-1):
        rho_cost+=beta*(energies[i+1]-energies[i])*huber_func((x[i+1]-x[i])/(energies[i+1]-energies[i]),c)
        
    return cost,rho_cost
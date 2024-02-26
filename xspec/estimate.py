import sys
import atexit
import warnings
import numpy as np
import copy
import pprint

import torch
import torch.optim as optim
from torch.nn.parameter import Parameter
from torch.multiprocessing import Pool
import torch.multiprocessing as mp

mp.set_sharing_strategy('file_system')

import logging
from xspec.opt._pytorch_lbfgs.functions.LBFGS import FullBatchLBFGS as NNAT_LBFGS
from xspec._utils import *
from xspec.models import get_merged_params_list, get_concatenated_params_list, denormalize_parameter_as_tuple
def weighted_mse_loss(input, target, weight):
    return 0.5 * torch.mean(weight * (input - target) ** 2)



def fit_cell(energies,
             nrads,
             forward_matrices,
             spec_models,
             params,
             weights=None,
             learning_rate=0.02,
             max_iterations=5000,
             stop_threshold=1e-3,
             optimizer_type='NNAT_LBFGS',
             loss_type='transmission'):
    """Other arguments are same as param_based_spec_estimate.

    Parameters
    ----------
    filters : list of Filter
        Each Filter.fltr_mat should be specified to a Material instead of None.
    scintillators
        Each Scintillator.scint_mat should be specified to a Material instead of None.

    Returns
    -------
    stop_iter : int
        Stop iteration.
    final_cost_value : float
        Final cost value
    final_model : spec_distrb_energy_resp
        An instance of spec_distrb_energy_resp after optimization, containing
    """

    logger = logging.getLogger(str(mp.current_process().pid))

    def print(*args, **kwargs):
        message = ' '.join(map(str, args))
        logger.info(message)

    def print_params(params):
        for key, value in sorted(params.items()):
            if isinstance(value, tuple):
                print(f"{key}: {denormalize_parameter_as_tuple(value)[0].numpy()}")
            else:
                print(f"{key}: {value}")
        print()


    spec_models = [[copy.deepcopy(cm) for cm in component_models] for component_models in spec_models]
    params = copy.deepcopy(params)
    parameters = []
    for component_models in spec_models:
        for cm in component_models:
            cm.set_estimates(params)
            parameters += list(cm.parameters())
    parameters = list(set(parameters))
    loss = torch.nn.MSELoss()

    if optimizer_type == 'Adam':
        ot = 'Adam'
        iter_prt = 50
        optimizer = optim.Adam(parameters, lr=learning_rate)
    elif optimizer_type == 'NNAT_LBFGS':
        ot = 'NNAT_LBFGS'
        iter_prt = 5
        optimizer = NNAT_LBFGS(parameters, lr=learning_rate)
    else:
        warnings.warn(f"The optimizer type {optimizer_type} is not supported.")
        sys.exit("Exiting the script due to unsupported optimizer type.")

    cost = np.inf
    print('Start Estimation.')
    for iter in range(1, max_iterations + 1):
        if iter % iter_prt == 0:
            print('Iteration:', iter)

        def closure():
            if torch.is_grad_enabled():
                optimizer.zero_grad()
            cost = 0
            for yy, FF, ww, component_models in zip(nrads, forward_matrices, weights, spec_models):
                spec = component_models[0](energies)
                for cm in component_models[1:]:
                    spec = spec*cm(energies)
                spec /= torch.trapz(spec, energies)
                trans_value = torch.trapz(FF * spec, energies, axis=-1).reshape((-1, 1))

                if loss_type == 'transmission':
                    sub_cost = weighted_mse_loss(trans_value, yy, ww)
                elif loss_type == 'attmse':
                    sub_cost = 0.5 * loss(-torch.log(trans_value), -torch.log(yy))
                else:
                    raise ValueError('loss_type should be \'mse\' or \'wmse\' or \'attmse\'. ', 'Given', loss_type)
                cost += sub_cost
            if cost.requires_grad and ot != 'NNAT_LBFGS':
                cost.backward()
            return cost

        cost = closure()

        if torch.isnan(cost):
            for component_models in spec_models:
                for cm in component_models:
                    print(cm.get_estimates())
            return iter, closure().item(), params

        if ot == 'NNAT_LBFGS':
            cost.backward()

        for component_models in spec_models:
            for cm in component_models:
                has_nan = check_gradients_for_nan(cm)
                if has_nan:
                    return iter, closure().item(), params

        with (torch.no_grad()):
            if iter == 1:
                print('Initial cost: %e' % (closure().item()))

        # Before the update, clone the current parameters
        old_params = [parameter.data.clone() for parameter in parameters]

        if ot == 'Adam':
            optimizer.step()
        elif ot == 'NNAT_LBFGS':
            options = {'closure': closure, 'current_loss': cost,
                       'max_ls': 100, 'damping': False}
            cost, grad_new, _, _, closures_new, grads_new, desc_dir, fail = optimizer.step(options=options)

        with (torch.no_grad()):
            if iter % iter_prt == 0:
                print('Cost:', cost.item())
                print_params(params)
            # After the update, check if the update is too small
            small_update = True
            for parameter,old_param in zip(parameters,old_params):
                if torch.norm(parameter.data.clamp(0, 1) - old_param.clamp(0, 1)) > stop_threshold:
                    small_update = False
                    break

            if small_update:
                print(f"Stopping at epoch {iter} because updates are too small.")
                print('Cost:', cost.item())
                print_params(params)
                break
    return iter, cost.item(), params


def init_logging(filename, num_processes):
    worker_id = mp.current_process().pid
    logger = logging.getLogger(str(worker_id))
    logger.setLevel(logging.INFO)

    if filename is None:
        handler = logging.StreamHandler()
    else:
        handler = logging.FileHandler(f"{filename}_{worker_id % num_processes}.log")

    formatter = logging.Formatter('%(asctime)s  - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Register a cleanup function to close the logger when the process exits
    atexit.register(close_logging, logger)


def close_logging(logger):
    handlers = logger.handlers[:]
    for handler in handlers:
        handler.close()
        logger.removeHandler(handler)


class Estimate():
    def __init__(self, energies):
        """

        Args:
            energies (numpy.ndarray): Array of interested X-ray photon energies in keV with size N_energies_bins.
        """
        self.energies = torch.tensor(energies, dtype=torch.float32)
        self.nrads = []
        self.forward_matrices = []
        self.spec_models = []
        self.weights = []



    def add_data(self, nrad, forward_matrix, component_models, weight=None):
        """

        Args:

            nrad (numpy.ndarray): Normalized radiograph with dimensions [N_views, N_rows, N_cols].
            forward_matrix (numpy.ndarray): Forward matricx corresponds to nrad with dimensions [N_views, N_rows, N_cols, N_energiy_bins]. We provide ``xspec.calc_forward_matrix`` to calculate a forward matrix from a 3D mask for a homogenous object.
            component_models (object): An instance of Base_Spec_Model.
            weight (numpy.ndarray): weight crresponds to nrad.

        Returns:

        """
        self.nrads.append(torch.tensor(nrad.reshape((-1, 1)), dtype=torch.float32))
        self.num_sp_datasets = len(self.nrads)
        self.forward_matrices.append(torch.tensor(forward_matrix, dtype=torch.float32))
        self.spec_models.append(component_models)

        if weight is None:
            weight = 1.0 / self.nrads[-1]
        else:
            weight = torch.tensor(weight.reshape((-1, 1)), dtype=torch.float32)
        self.weights.append(weight)

    def fit(self, learning_rate=0.001, max_iterations=5000, stop_threshold=1e-4,
            optimizer_type='Adam', loss_type='transmission', logpath=None,
             num_processes=1):
        """

        Args:
            learning_rate (float, optional): [Default=0.001] Learning rate for the optimization process.
            max_iterations (int, optional): [Default=5000] Maximum number of iterations for the optimization.
            stop_threshold (float, optional): [Default=1e-4] Scalar valued stopping threshold in percent.
                If stop_threshold=0.0, then run max iterations.
            optimizer_type (str, optional): [Default='Adam'] Type of optimizer to use. If we do not have
                accurate initial guess use 'Adam', otherwise, 'NNAT_LBFGS' can provide a faster convergence.
            loss_type (str, optional): [Default='transmission'] Calculate loss function in 'transmission' or 'attenuation' space.

        Returns:

        """
        # Calculate params_list
        concatenate_params_list = [get_concatenated_params_list([cm._params_list for cm in concatenate_models]) for
                                   concatenate_models in self.spec_models]
        merged_params_list = get_merged_params_list(concatenate_params_list)

        # Use multiprocessing pool to parallelize the optimization process
        with Pool(processes=num_processes, initializer=init_logging, initargs=(logpath, num_processes)) as pool:
            # Apply optimization function to each combination of model parameters
            result_objects = [
                pool.apply_async(
                    fit_cell,
                    args=(self.energies, self.nrads, self.forward_matrices, self.spec_models, params,
                    self.weights, learning_rate,
                    max_iterations, stop_threshold,
                    optimizer_type, loss_type)
                )
                for params in merged_params_list
            ]

            # Gather results from all parallel optimizations
            print('Number of cases for different discrete parameters:', len(result_objects))
            results = [r.get() for r in result_objects]  # Retrieve results from async calls
        cost_list = [res[1] for res in results]
        optimal_cost_ind = np.argmin(cost_list)
        best_params = results[optimal_cost_ind][2]
        self.params = best_params
        for component_models in self.spec_models:
            for cm in component_models:
                cm.set_estimates(best_params)
    def get_spec_models(self):
        """ Obtain optimized spectral models.

        Returns:
            list: A list of compenent lists. Each compenent list contains all used components to scan the corresponding radiograph.
        """
        return self.spec_models
    def get_params(self):
        """ Obtain optimized parameters.

        Returns:
            dict: A dictionary contains all parameters.
        """
        return self.params

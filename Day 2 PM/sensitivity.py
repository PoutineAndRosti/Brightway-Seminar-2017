from bw2calc import ParameterVectorLCA, ParallelMonteCarlo
from scipy.stats import ks_2samp
from stats_arrays import uncertainty_choices
import multiprocessing
import numpy as np


def pawn_worker(args):
    fu, method, index, unconditional_cdf, n_c, n = args
    lca = ParameterVectorLCA(fu, method)
    lca.load_data()
    next(lca)
    array = lca.params[index:index + 1]
    lhc = (np.random.random(size=n) + np.arange(n)) / n
    n_samples = uncertainty_choices[int(array['uncertainty_type'][0])].ppf(
        array, lhc.reshape((1, -1))).ravel()
    results = []

    for fixed in n_samples:

        scores = []

        for _ in range(n_c):
            sample = lca.rng.next()
            sample[index] = fixed

            lca.rebuild_all(sample)
            lca.lci_calculation()
            lca.lcia_calculation()
            scores.append(lca.score)

        results.append(ks_2samp(unconditional_cdf, np.array(scores))[0])

    return (index, np.median(results))


def pawn_sensitivity(fu, method, indices, cpus=None, n_u=1000, n_c=50, n=20):
    unconditional_cdf = ParallelMonteCarlo(fu, method, n_u, cpus=cpus).calculate()

    with multiprocessing.Pool(processes=cpus) as pool:
        results = pool.map(
            pawn_worker,
            [(fu, method, index, unconditional_cdf.copy(), n_c, n)
             for index in indices]
        )
    return results

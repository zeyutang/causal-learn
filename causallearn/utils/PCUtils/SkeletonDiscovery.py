from itertools import permutations, combinations

import numpy as np

from causallearn.graph.GraphClass import CausalGraph
from causallearn.utils.PCUtils.Helper import append_value
from causallearn.utils.cit import chisq, gsq


def skeleton_discovery(data, alpha, indep_test, stable=True, background_knowledge=None, verbose=False):
    '''
    Perform skeleton discovery

    Parameters
    ----------
    data : data set (numpy ndarray)
    alpha: desired significance level in (0, 1) (float)
    indep_test : name of the independence test being used
           - "Fisher_Z": Fisher's Z conditional independence test
           - "Chi_sq": Chi-squared conditional independence test
           - "G_sq": G-squared conditional independence test
    stable : run stabilized skeleton discovery if True (default = True)

    Returns
    -------
    cg : a CausalGraph object

    '''

    assert type(data) == np.ndarray
    assert 0 < alpha < 1

    no_of_var = data.shape[1]
    cg = CausalGraph(no_of_var)
    cg.set_ind_test(indep_test)
    if indep_test == chisq or indep_test == gsq:
        # if dealing with discrete data, data is numpy.ndarray with n rows m columns,
        # for each column, translate the discrete values to int indexs starting from 0,
        #   e.g. [45, 45, 6, 7, 6, 7] -> [2, 2, 0, 1, 0, 1]
        #        ['apple', 'apple', 'pear', 'peach', 'pear'] -> [0, 0, 2, 1, 2]
        # in old code, its presumed that discrete `data` is already indexed,
        # but here we make sure it's in indexed form, so allow more user input e.g. 'apple' ..
        def _unique(column):
            return np.unique(column, return_inverse=True)[1]
        cg.is_discrete = True
        cg.data = np.apply_along_axis(_unique, 0, data).astype(np.int64)
        cg.cardinalities = np.max(cg.data, axis=0) + 1
    else:
        cg.data = data

    depth = -1
    while cg.max_degree() - 1 > depth:
        depth += 1
        edge_removal = []
        for x in range(no_of_var):
            Neigh_x = cg.neighbors(x)
            if len(Neigh_x) < depth - 1:
                continue
            for y in Neigh_x:
                Neigh_x_noy = np.delete(Neigh_x, np.where(Neigh_x == y))
                for S in combinations(Neigh_x_noy, depth):
                    if background_knowledge is not None and (
                            background_knowledge.is_forbidden(cg.G.nodes[x], cg.G.nodes[y])
                            and background_knowledge.is_forbidden(cg.G.nodes[y], cg.G.nodes[x])):
                        if verbose: print('%d ind %d | %s with background background_knowledge\n' % (x, y, S))
                        if not stable:
                            edge1 = cg.G.get_edge(cg.G.nodes[x], cg.G.nodes[y])
                            if edge1 is not None:
                                cg.G.remove_edge(edge1)
                            edge2 = cg.G.get_edge(cg.G.nodes[y], cg.G.nodes[x])
                            if edge2 is not None:
                                cg.G.remove_edge(edge2)
                        else:
                            edge_removal.append((x, y))  # after all conditioning sets at
                            edge_removal.append((y, x))  # depth l have been considered
                            append_value(cg.sepset, x, y, S)
                            append_value(cg.sepset, y, x, S)
                        break
                    else:
                        p = cg.ci_test(x, y, S)
                        if p > alpha:
                            if verbose: print('%d ind %d | %s with p-value %f\n' % (x, y, S, p))
                            if not stable:
                                edge1 = cg.G.get_edge(cg.G.nodes[x], cg.G.nodes[y])
                                if edge1 is not None:
                                    cg.G.remove_edge(edge1)
                                edge2 = cg.G.get_edge(cg.G.nodes[y], cg.G.nodes[x])
                                if edge2 is not None:
                                    cg.G.remove_edge(edge2)
                            else:
                                edge_removal.append((x, y))  # after all conditioning sets at
                                edge_removal.append((y, x))  # depth l have been considered
                                append_value(cg.sepset, x, y, S)
                                append_value(cg.sepset, y, x, S)
                            break
                        else:
                            if verbose: print('%d dep %d | %s with p-value %f\n' % (x, y, S, p))

        for (x, y) in list(set(edge_removal)):
            edge1 = cg.G.get_edge(cg.G.nodes[x], cg.G.nodes[y])
            if edge1 is not None:
                cg.G.remove_edge(edge1)

    return cg

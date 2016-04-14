###############################################################################
#                                                                             #
#    This library is free software; you can redistribute it and/or            #
#    modify it under the terms of the GNU Lesser General Public               #
#    License as published by the Free Software Foundation; either             #
#    version 3.0 of the License, or (at your option) any later version.       #
#                                                                             #
#    This library is distributed in the hope that it will be useful,          #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of           #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU        #
#    Lesser General Public License for more details.                          #
#                                                                             #
#    You should have received a copy of the GNU Lesser General Public         #
#    License along with this library.                                         #
#                                                                             #
###############################################################################

__author__ = "Tim Lamberton"
__copyright__ = "Copyright 2015"
__credits__ = ["Tim Lamberton"]
__license__ = "GPL3"
__maintainer__ = "Tim Lamberton"
__email__ = "tim.lamberton@gmail.com"

###############################################################################

# system imports
from nose.tools import assert_true
from tools import assert_equal_arrays, assert_almost_equal_arrays
import numpy as np
import scipy.spatial.distance as sp_distance
import random
from groopm.distance import (mediod,
                             density_distance,
                             reachability_order,
                             argrank,
                             pcoords,
                             ccoords)

###############################################################################
###############################################################################
###############################################################################
###############################################################################

def test_mediod():
    points = np.array([[0, 0, 1], 
                       [1, 1, 1], # mediod?
                       [1, 1, 2],
                       [1, 2, 1]])
    distances = sp_distance.pdist(points, metric="cityblock")
    assert_true(mediod(distances) == 1,
                "`mediod` returns index of mediod")

                
def test_argrank():
    assert_equal_arrays(argrank([5, 3, 4, 8]),
                        [2, 0, 1, 3],
                        "`argrank` returns integer rank of values in one-dimensional array")

    assert_equal_arrays(argrank([5, 3, 8, 8]),
                        [1, 0, 2.5, 2.5],
                        "`argrank` returns mean of tied ranks")

    arr2d = np.array([[1, 10, 5, 2], [1, 4, 6, 2], [5, 5, 3, 10]])
    ranks2d = np.array([[0, 3, 2, 1], [0, 2, 3, 1], [1.5, 1.5, 0, 3]])
    assert_equal_arrays(argrank(arr2d, axis=1),
                        ranks2d,
                        "`argrank(..,axis=1)` returns ranks along rows of 2D array")
    assert_equal_arrays(argrank(arr2d.T, axis=0),
                        ranks2d.T,
                        "`argrank(..,axis=0)` returns ranks along columns of 2D array")
                        
    assert_equal_arrays(argrank([5, 3, 4, 8], weights=[2, 2, 1, 3]),
                        argrank([5, 3, 4, 8, 5, 3, 8, 8])[:4],
                        "`argrank` returns weighted ranks when weights parameter is passed")
    
    assert_equal_arrays(argrank([[1, 10, 5, 2],
                                 [1,  4, 6, 2]
                                ], weights=[5, 1, 1, 6], axis=1),
                        argrank([[1, 10, 5, 2, 1, 1, 1, 1, 2, 2, 2, 2, 2],
                                 [1,  4, 6, 2, 1, 1, 1, 1, 2, 2, 2, 2, 2]
                                ], axis=1)[:, :4],
                        "`argrank` broadcasts weights vector along rows of 2D array")
                        
    assert_equal_arrays(argrank([[1, 10, 5, 2],
                                 [1,  4, 6, 2]
                                ], weights=[2, 5], axis=0),
                        argrank([[1, 10, 5, 2],
                                 [1,  4, 6, 2],
                                 [1, 10, 5, 2],
                                 [1,  4, 6, 2],
                                 [1,  4, 6, 2],
                                 [1,  4, 6, 2],
                                 [1,  4, 6, 2]
                                ], axis=0)[:2],
                        "`argrank` broadcasts weights vector along columns of 2D array")
                        
                        
def test_density_distance():
    """
    Y encodes distances for pairs:
    (0, 1) =  2.2
    (0, 2) =  7.2
    (0, 3) = 10.4
    (0, 4) =  6.7
    (1, 2) = 12.8
    (1, 3) =  8.6
    (1, 4) =  8.9
    (2, 3) = 12.7
    (2, 4) =  8.6
    (3, 4) =  2.2
    
    closest to furtherest distances
    0 = 2.2, 6.7,  7.2, 10.4
    1 = 2.2, 8.6,  8.9, 12.8
    2 = 7.2, 8.6, 12.7, 12.8
    3 = 2.2, 8.6, 10.4, 12.7
    4 = 2.2, 6.7,  8.6,  8.9
    """
    Y = np.array([2.2, 7.2, 10.4, 6.7, 12.8, 8.6, 8.9, 12.7, 8.6, 2.2])
    w = np.ones(len(Y), dtype=np.intp)
    
    # core_distances: [2.2, 2.2, 7.2, 2.2, 2.2]
    assert_equal_arrays(density_distance(Y, w, 1),
                        [2.2, 7.2, 10.4, 6.7, 12.8, 8.6, 8.9, 12.7, 8.6, 2.2],
                        "`density_distance` for nearest neighbour returns distances unchanged")
                        
    # core_distances: [6.7, 8.6, 8.6, 8.6, 6.7]
    assert_equal_arrays(density_distance(Y, w, 2),
                        [6.7, 7.2, 10.4, 6.7, 12.8, 8.6, 8.9, 12.7, 8.6, 6.7],
                        "computes `density_distance` for 2-nearest neighbour")
         
    # core_distances: [10.4, 12.8, 12.8, 12.7, 8.9]               
    assert_equal_arrays(density_distance(Y, w, 4),
                        [10.4, 10.4, 10.4, 8.9, 12.8, 12.7, 8.9, 12.7, 8.9, 8.9],
                        "computes `density_distance` for 4-nearest neighbour")
                        
    
    """
    Y encodes weighted distances for pairs:
    (0, 1) =  17.7
    (0, 2) =  70.0
    (0, 3) =  97.1
    (0, 4) =  50.8
    (1, 2) = 121.6
    (1, 3) =  79.4
    (1, 4) =  82.1
    (2, 3) = 120.9
    (2, 4) =  77.3
    (3, 4) =  14.4
    
    w encodes pairwise weights:
    (0, 1) =  4
    (0, 2) =  8
    (0, 3) =  6
    (0, 4) = 10
    (1, 2) =  6
    (1, 3) =  6
    (1, 4) = 10
    (2, 3) = 12
    (2, 4) = 20
    (3, 4) = 15
    
    cumulative weights
    0 =  4, 14, 22, 28
    1 =  4, 10, 20, 26
    2 =  8, 28, 36, 42
    3 = 15, 21, 27, 39
    4 = 15, 25, 45, 55
    
    closest to furtherest distances
    0 = 17.7, 50.8,  70.0,  97.1
    1 = 17.7, 79.4,  82.1, 121.6
    2 = 70.0, 77.3, 120.9, 121.6
    3 = 14.4, 79.4,  97.1, 120.9
    4 = 14.4, 50.8,  77.3,  82.1  
    """ 
    Y = np.array([17.7, 70., 97.1, 50.8, 121.6, 79.4, 82.1, 120.9, 77.3, 14.4])
    w = np.array([   4,   8,    6,   10,     6,    6,   10,    12,   20,   15])
    
    # core_distances: [50.8, 82.1, 70.0, 14.4, 14.4] 
    assert_equal_arrays(density_distance(Y, w, 20),
                        [50.8, 70., 97.1, 50.8, 121.6, 79.4, 82.1, 120.9, 77.3, 14.4],
                        "computes weighted `density_distance` at various limits")
                        
    # core_distances: [97.1, 121.6, 77.3, 97.1, 50.8] 
    assert_equal_arrays(density_distance(Y, w, 30),
                        [97.1, 77.3, 97.1, 50.8, 121.6, 97.1, 82.1, 120.9, 77.3, 50.8],
                        "computes weighted `density_distance` at various limits")
                        
                        
def test_reachability_order():
    """
    Y encodes weighted distances for pairs:
    (0, 1) =  17.7
    (0, 2) =  70.0
    (0, 3) =  97.1
    (0, 4) =  50.8
    (1, 2) = 121.6
    (1, 3) =  79.4
    (1, 4) =  82.1
    (2, 3) = 120.9
    (2, 4) =  77.3
    (3, 4) =  14.4
    """
    Y = np.array([17.7, 70., 97.1, 50.8, 121.6, 79.4, 82.1, 120.9, 77.3, 14.4])
    print reachability_order(Y)
    assert_equal_arrays(reachability_order(Y),
                        [0, 1, 4, 3, 2],
                        "`reachability_order` returns reachability traversal order")
                        
    

def test_condensed_index():
    n = random.randint(3, 10)
    indices = np.arange(n * (n - 1) // 2)
    
    assert_equal_arrays(pcoords(np.arange(n), n),
                        indices,
                        "`pcoords` computes linear index of condensed distance matrix")
                        
    yi = ccoords(np.arange(n), np.arange(n), n)
    assert_equal_arrays(yi[np.triu_indices(n, k=1)],
                        indices,
                        "`ccoords` computes linear index correctly when row < col")
    assert_equal_arrays(yi.T[np.triu_indices(n, k=1)],
                        indices,
                        "`ccoords` computes linear index correctly when row > col")
                        


###############################################################################
###############################################################################
###############################################################################
###############################################################################

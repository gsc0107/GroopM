#!/usr/bin/env python
###############################################################################
#                                                                             #
#    cluster.py                                                               #
#                                                                             #
#    A collection of classes / methods used when clustering contigs           #
#                                                                             #
#    Copyright (C) Michael Imelfort, Tim Lamberton                            #
#                                                                             #
###############################################################################
#                                                                             #
#          .d8888b.                                    888b     d888          #
#         d88P  Y88b                                   8888b   d8888          #
#         888    888                                   88888b.d88888          #
#         888        888d888 .d88b.   .d88b.  88888b.  888Y88888P888          #
#         888  88888 888P"  d88""88b d88""88b 888 "88b 888 Y888P 888          #
#         888    888 888    888  888 888  888 888  888 888  Y8P  888          #
#         Y88b  d88P 888    Y88..88P Y88..88P 888 d88P 888   "   888          #
#          "Y8888P88 888     "Y88P"   "Y88P"  88888P"  888       888          #
#                                             888                             #
#                                             888                             #
#                                             888                             #
#                                                                             #
###############################################################################
#                                                                             #
#    This program is free software: you can redistribute it and/or modify     #
#    it under the terms of the GNU General Public License as published by     #
#    the Free Software Foundation, either version 3 of the License, or        #
#    (at your option) any later version.                                      #
#                                                                             #
#    This program is distributed in the hope that it will be useful,          #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of           #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #
#    GNU General Public License for more details.                             #
#                                                                             #
#    You should have received a copy of the GNU General Public License        #
#    along with this program. If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################

__author__ = "Michael Imelfort, Tim Lamberton"
__copyright__ = "Copyright 2012/2013"
__credits__ = ["Tim Lamberton", "Michael Imelfort"]
__license__ = "GPL3"
__maintainer__ = "Tim Lamberton"
__email__ = "t.lamberton@uq.edu.au"

###############################################################################

import numpy as np
import numpy.linalg as np_linalg
import scipy.cluster.hierarchy as sp_hierarchy
import operator

# local imports
import distance
import corre
from bin import BinManager
from partition import MarkerPartitionTool

###############################################################################
###############################################################################
###############################################################################
###############################################################################

def run_cluster_engine(timer,
                       dbFileName,
                       markerFileName,
                       minSize,
                       minBP,
                       minLength,
                       force=False):
    pm = ProfileManager(dbFileName, markerFileName)
    # check that the user is OK with nuking stuff...
    if not force and not pm.promptOnOverwrite():
        return
        
    profile = pm.loadData(timer, minLength=minLength)
    ce = FeatureGlobalRankAndClassificationClusterEngine(profile)
    
    # cluster and bin!
    print "Create cores"
    ce.makeBins(out_bins=profile.binIds)
    print "    %s" % timer.getTimeStamp()
    
    bt = BinQualityTool(profile, minSize=minSize, minBP=minBP)
    bt.unbinLowQualityAssignments(out_bins=profile.binIds)

    # Now save all the stuff to disk!
    print "Saving bins"
    pm.setBinAssignments(profile, nuke=True)
    print "    %s" % timer.getTimeStamp()
        
        
## Algorithms
class HybridHierachicalClusterEngine:
    """Hybrid hierarchical clustering algorthm"""
    def makeBins(self, out_bins):
        """Run binning algorithm"""
        
        self.setup()

        dists = self.distances()
        Z = sp_hierarchy.average(dists)
        out_bins[...] = self.fcluster(Z)
            
    def setup(self):
        pass
            
    def distances(self):
        # computes pairwise distances of observations
        pass
        
    def fcluster(self, Z):
        # finds flat clusters from linkage matrix
        pass
        
        
class FeatureGlobalRankAndClassificationClusterEngine(HybridHierarchicalClusterEngine):
    """Cluster using hierarchical clusturing with feature distance ranks and marker taxonomy"""
    def __init__(self, profile, threshold=1):
        self._profile = profile
        self._ct = ClassificationCoherenceClusterTool(profile.markers)
        self._features = (profile.covProfile, profile.kmerSigs)
        self._hybrid_ranks = None
        self._threshold = threshold
        
    def setup(self):
        feature_distances = tuple(sp_distance.pdist(f, metric="euclidean") for f in self._features)
        weights = sp_distance.pdist(self._profile.contigLengths, operator.mul)
        feature_ranks = distance.argrank_weighted(feature_distances, weights=weights, axis=1)
        self._hybrid_ranks = np_linalg.norm(feature_ranks, axis=0)
        
    def distances(self):
        return self._hybrid_ranks
        
    def fcluster(self, Z):
        return self._ct.cluster_classification(Z, self._threshold)
        
    
            
# Mediod clustering
class MediodsClusterEngine:
    """Iterative mediod clustering algorithm"""
    
    def makeBins(self, init, out_bins):
        """Run binning algorithm
        
        Parameters
        ----------
        init : ndarray
            Array of indices used to determine starting points for new
            clusters.
        out_bins: ndarray
            1-D array of initial bin ids. An id of 0 is considered unbinned. 
            The bin id for the `i`th original observation will be stored in
            `out_bins[i]`.
        """
        self.setup()
        
        bin_counter = np.max(out_bins)
        mediod = None
        queue = init

        while(True):
            if mediod is None:
                if len(queue) == 0:
                    break
                mediod = queue.pop()
                if out_bins[mediod] != 0:
                    mediod = None
                    continue
                round_counter = 0
                bin_counter += 1
                out_binds[mediod] = bin_counter

            round_counter += 1
            print "Recruiting bin %d, round %d." % (bin_counter, round_counter)
            
            is_unbinned = out_bins == 0
            print "Found %d unbinned." % np.count_nonzero(is_unbinned)

            is_old_members = out_bins == bin_counter
            putative_members = np.flatnonzero(np.logical_and(is_unbinned, is_old_members))
            recruited = self.recruit(mediod, putative_members=putative_members)
            
            out_bins[recruited] = bin_counter
            members = np.flatnonzero(out_bins == bin_counter)
            
            print "Recruited %d members." % (members.size - old_members.size)
            
            if len(members)==1:
                new_mediod = members
            else:
                index = self.mediod(members)
                new_mediod = members[index]


            if new_mediod == mediod:
                print "Mediod is stable after %d rounds." % round_counter
                mediod = None
            else:
                mediod = new_mediod

        print " %d bins made." % bin_counter
        
    def setup():
        pass
        
    def recruit(self, mediod, putative_members):
        # recruit contigs close to a mediod contig
        pass
        
    def mediod(self, indices):
        # computes pairwise distances of observations
        pass
        
        
class FeatureRankCorrelationClusterEngine(MediodsClusteringEngine):
    """Cluster using mediod feature distance rank correlation"""
    def __init__(self, profile, threshold=0.5):
        self._profile = profile
        self._features = (profile.covProfiles, profile.kmerSigs)
        self._threshold = threshold
        
    def mediod(self, indices):
        feature_ranks = tuple(distance.argrank(sp_distance.cdist(f[indices], f, metric="euclidean"), axis=1)[:, indices] for f in self._features)
        return np_linalg.norm(feature_dists, axis=0).sum(axis=1).argmin()
        
    def recruit(self, origin, putative_members):
        (covRanks, kmerRanks) = tuple(distance.argrank(sp_distance.cdist(f[[origin]], f, metric="euclidean")[0]) for f in self._features)
        return corre.getMergers((covRanks, kmerRanks), threshold=self._threshold, unmerged=putative_members)
        

###############################################################################
###############################################################################
###############################################################################
###############################################################################

#!/usr/bin/env python
from __future__ import division
###############################################################################
#                                                                             #
#    som.py                                                                   #
#                                                                             #
#    GroopM self organising map engine                                        #
#                                                                             #
#    Copyright (C) Michael Imelfort                                           #
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
# This script uses / is inspired by chunks of code and ideas originally
# developed by Kyle Dickerson and others
# Here: http://www.singingtree.com/~kyle/blog/archives/00000251.htm
# and Here: http://paraschopra.com/sourcecode/SOM/index.php
###############################################################################
## Kyle Dickerson
## kyle.dickerson@gmail.com
## Jan 15, 2008
##
## Self-organizing map using scipy
## This code is licensed and released under the GNU GPL
##
## This code uses a square grid rather than hexagonal grid, as scipy allows for
## fast square grid computation. I designed sompy for speed, so attempting to
## read the code may not be very intuitive. If you're trying to learn how SOMs
## work, I would suggest starting with Paras Chopras SOMPython code:
##  http://www.paraschopra.com/sourcecode/SOM/index.php
## It has a more intuitive structure for those unfamiliar with scipy,
## however it is much slower. If you do use this code for something,
## please let me know, I'd like to know if has been useful to anyone.
###############################################################################

__author__ = "Michael Imelfort"
__copyright__ = "Copyright 2012"
__credits__ = ["Michael Imelfort"]
__license__ = "GPL3"
__version__ = "0.0.1"
__maintainer__ = "Michael Imelfort"
__email__ = "mike@mikeimelfort.com"
__status__ = "Development"

###############################################################################

import sys
from random import *
from math import *
import sys
import numpy as np
import os
from PIL import Image, ImageDraw
import string

# GroopM imports
from torusMesh import TorusMesh as tm
import rainbow

###############################################################################
###############################################################################
###############################################################################
###############################################################################

class SOMManager:
    """Manage multiple SOMs"""
    def __init__(self):
        pass

class SOM:
    """A single instance of a self organising map"""
    def __init__(self, side, dimension, learning_rate=0.15):
        self.side = side                            # side length of the grid
        self.dimension = dimension                  # size of our grid vectors
        self.bestMatchCoords = []                   # x/y coords of classified vectors

        self.radius = float(side)/2.0               # the radius of neighbour nodes which will be influenced by each new training vector
        self.learning_rate = learning_rate          # the amount of influence
        
        # initialise the nodes to random values between 0 -> 1
        print "    Making data structure"
        self.TM = tm(self.side, dimension=self.dimension, randomize=True)
        
    def getNodes(self):
        """Get the weighting nodes"""
        return self.TM.nodes
    
#------------------------------------------------------------------------------
# CLASSIFICATION 

    # Classify!
    # run this after training to get an X/Y for each vector 
    # you'd like to classify
    def classify(self, names_vector=[], data_vector=[[]]):
        print "Start classification..."
        index_array = np.arange(len(data_vector))
        for j in index_array:
            # find the best match between then data vector and the
            # current grid
            best = self.TM.bestMatch(data_vector[j])
            self.bestMatchCoords.append(best)
        print "Done"

#------------------------------------------------------------------------------
# TRAINING 
        
    def train(self, train_vector, iterations=1000, vectorSubSet = 400, weightImgFileName=""):
        """Train the SOM
        
        Train vector is a list of numpy arrays
        """
        
        print "    Start training -->", iterations, "iterations"
        
        # over time we'll shrink the radius of nodes which
        # are influenced by the current training node
        time_constant = iterations/log(self.radius)
        
        # make a set of "delta nodes"
        # these contain the changes to the set of grid nodes
        # and we will add their values to the grid nodes
        # once we have input all the training nodes
        delta_nodes = np.zeros_like(self.TM.nodes)
        
        for i in range(1, iterations+1):
            # reset the deltas
            delta_nodes.fill(0.0)

            # gaussian decay on radius and amount of influence
            radius_decaying=self.radius*exp(-1.0*i/time_constant)
            learning_rate_decaying=self.learning_rate*exp(-1.0*i/time_constant)
            radius_ratio = radius_decaying / float(self.side)
            
            # calculate once!
            rad_div_val = 2 * radius_decaying * i

            # we would ideally like to select guys from the training set at random
            
            index_array = np.arange(len(train_vector))
            np.random.shuffle(index_array)
            cut_off = int(len(index_array)/vectorSubSet)
            if(len(train_vector) < vectorSubSet):
                cut_off = len(train_vector) # if less than 1000 training vectors, set this to suit 
            elif(cut_off < vectorSubSet): # else, try to make sure there are at least 1000
                cut_off = vectorSubSet
            counter = 0

            for j in index_array:

                counter += 1
                sys.stdout.write("\r    Iteration: %i of %i, Comparison: %i of %i, Radius: %04f " % (i, iterations, counter, cut_off, radius_ratio))
                sys.stdout.flush()
                if(counter > cut_off):
                    break 
                # find the best match between then training vector and the
                # current grid
                best = self.TM.bestMatch(train_vector[j])
                
                # apply the learning to the neighbors on the grid
                for row in range(int(best[0] - radius_decaying), int(best[0] + radius_decaying + 1)):
                    for col in range(int(best[1] - radius_decaying), int(best[1] + radius_decaying + 1)):
                        # now we check to see that the euclidean distance is less than
                        # the specified distance.
                        true_dist = np.sqrt( (best[0] - row)**2 + (best[1] - col)**2 )
                        check_dist = np.round(true_dist+0.00001)
                        if(check_dist <= radius_decaying):
                            rrow = np.mod(row,self.TM.rows) 
                            rcol = np.mod(col,self.TM.columns)
                            # influence is propotional to distance
                            influence = exp( (-1.0 * (true_dist**2)) / rad_div_val)
                            
                            # however, the learning rate also counts
                            #inv_influence = 1 - influence
                            #self.TM.nodes[rrow,rcol] =  inv_influence*self.TM.nodes[rrow,rcol]+influence*train_vector[j]
                            inf_lrd = influence*learning_rate_decaying
                            inv_inf_lrd = 1-inf_lrd
                            delta_nodes[rrow,rcol] += inf_lrd*(train_vector[j]-self.TM.nodes[rrow,rcol])

            print "- (done)"
            # add the deltas to the grid nodes
            self.TM.nodes += delta_nodes
            
            # renormalise the vector
            if(False):
                for r in range(self.rows):
                    for c in range(self.columns):
                        for v in range(self.dimension):
                            if(self.nodes[r,c,v] < 0):
                                self.nodes[r,c,v] = 0
                            elif(self.nodes[r,c,v] > 1):
                                self.nodes[r,c,v] = 1

            self.TM.reNorm()
            
            # make a tmp image, perhaps
            if(weightImgFileName != ""):
                filename = weightImgFileName+"_%04d" % i+".png"
                print "   writing:",filename
                self.TM.renderSurface(filename)

#------------------------------------------------------------------------------
# IO and IMAGE RENDERING 

    def transColour(self, val):
        """Transform color value"""
        return 10 * log(val)

    def renderBestMatches(self, fileName, weighted=False):
        """make an image of where best matches lie
        
        set weighted to use a heatmap view of where they map        
        """
        img_points = np.zeros((self.TM.rows,self.TM.columns))
        try:
            img = Image.new("RGB", (self.TM.columns, self.TM.rows))
            if(weighted):   # color points by bestmatch density 
                max = 0
                for point in self.bestMatchCoords:
                    img_points[point[0],point[1]] += 1
                    if(max < img_points[point[0],point[1]]):
                        max  = img_points[point[0],point[1]]
                max += 1
                resolution = 200
                if(max < resolution):
                    resolution = max - 1
                max  = self.transColour(max)
                rainbow = Rainbow.rainbow(0, max, resolution, "gbr")
                for point in self.bestMatchCoords:
                    img.putpixel((point[1],point[0]), rainbow.getColour(self.transColour(img_points[point[0],point[1]])))
            else:       # make all best match points white
                for point in self.bestMatchCoords:
                    img.putpixel((point[1],point[0]), (255,255,255))
            img = img.resize((self.TM.columns*10, self.TM.rows*10),Image.NEAREST)
            img.save(fileName)
        except:
            print sys.exc_info()[0]
            raise

###############################################################################
###############################################################################
###############################################################################
###############################################################################

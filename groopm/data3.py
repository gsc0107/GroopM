#!/usr/bin/env python
###############################################################################
#                                                                             #
#    data3.py                                                                 #
#                                                                             #
#    GroopM - Low level data management and file parsing                      #
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
__copyright__ = "Copyright 2012-2016"
__credits__ = ["Michael Imelfort", "Tim Lamberton"]
__license__ = "GPL3"
__maintainer__ = "Tim Lamberton"
__email__ = "t.lamberton@uq.edu.au"

__current_GMDB_version__ = 6

###############################################################################

import sys
from os.path import splitext as op_splitext, basename as op_basename
from string import maketrans as s_maketrans

import tables
import numpy as np
import scipy.spatial.distance as sp_distance
from scipy.spatial.distance import cdist, squareform

# GroopM imports
from utils import CSVReader

# BamM imports
try:
    from bamm.bamParser import BamParser as BMBP
    from bamm.cWrapper import *
    from bamm.bamFile import BM_coverageType as BMCT
except ImportError:
    print """ERROR: There was an error importing BamM. This probably means that
BamM is not installed properly or not in your PYTHONPATH. Installation
instructions for BamM are located at:

    http://ecogenomics.github.io/BamM

If you're sure that BamM is installed (properly) then check your PYTHONPATH. If
you still encounter this error. Please lodge a bug report at:

    http://github.com/ecogenomics/BamM/issues

Exiting...
--------------------------------------------------------------------------------
"""
    sys.exit(-1)

np.seterr(all='raise')

# shut up pytables!
import warnings
warnings.filterwarnings('ignore', category=tables.NaturalNameWarning)

###############################################################################
###############################################################################
###############################################################################
###############################################################################
class DataManager:
    """Top level class for manipulating GroopM data

    Use this class for parsing in raw data into a hdf DB and
    for reading from and updating same DB

    NOTE: All tables are kept in the same order indexed by the contig ID
    Tables managed by this class are listed below

    ------------------------
     PROFILES
    group = '/profile'
    ------------------------
    **Kmer Signature**
    table = 'kms'
    'mer1' : tables.FloatCol(pos=0)
    'mer2' : tables.FloatCol(pos=1)
    'mer3' : tables.FloatCol(pos=2)
    ...

    [DEL] **Kmer Vals**
    table = 'kpca'
    'pc1' : tables.FloatCol(pos=0)
    'pc2' : tables.FloatCol(pos=1)
    'pc3' : tables.FloatCol(pos=2)
    ...

    **Coverage profile**
    table = 'coverage'
    'stoit1' : tables.FloatCol(pos=0)
    'stoit2' : tables.FloatCol(pos=1)
    'stoit3' : tables.FloatCol(pos=2)
    ...

    [DEL] **Transformed coverage profile**
    table = 'transCoverage'
    'x' : tables.FloatCol(pos=0)
    'y' : tables.FloatCol(pos=1)
    'z' : tables.FloatCol(pos=2)

    **Coverage profile norms**
    table = 'normCoverage'
    'normCov' : tables.FloatCol(pos=0)
    
    [NEW]
    ------------------------
     PROFILE DISTANCES
    group = '/profile_distances'
    ------------------------
    **Kmer condensed distances***
    table = 'kmy'
    'Y' : tables.FloatCol(pos=0)
    
    **Coverage condensed distances**
    table = 'coveragey'
    'Y' : tables.FloatCol(pos=0)
    
    **Combined condensed density distances**
    table = 'comby'
    'Y': tables.FloatCol(pos=0)

    ------------------------
     LINKS
    group = '/links'
    ------------------------
    ** Links **
    table = 'links'
    'contig1'    : tables.Int32Col(pos=0)            # reference to index in meta/contigs
    'contig2'    : tables.Int32Col(pos=1)            # reference to index in meta/contigs
    'numReads'   : tables.Int32Col(pos=2)            # number of reads supporting this link
    'linkType'   : tables.Int32Col(pos=3)            # the type of the link (SS, SE, ES, EE)
    'gap'        : tables.Int32Col(pos=4)            # the estimated gap between the contigs
    
    [NEW]
    ------------------------
     MAPPINGS
    group = '/mappings'
    ------------------------
    **Mappings***
    table = 'mappings'
    'marker'    : tables.StringCol(512, pos=1)      # marker id
    'contig'    : tables.Int32Col(pos=0)            # reference to index in meta/contigs
    
    **Mapping classifications***
    table = 'classification'
    'domain'    : tables.Int32Col(pos=0)            # taxon id
    'phylum'    : tables.Int32Col(pos=1)
    'class'     : tables.Int32Col(pos=2)
    'order'     : tables.Int32Col(pos=3)
    'family'    : tables.Int32Col(pos=4)
    'genus'     : tables.Int32Col(pos=5)
    'species'   : tables.Int32Col(pos=6)
        
    [NEW]
    ------------------------
     MAPPING DISTANCES
    group = '/mapping_distances'
    ------------------------
    **Classification condensed distances***
    table = 'taxoy'
    'Y' : tables.FloatCol(pos=0)

    ------------------------
     METADATA
    group = '/meta'
    ------------------------
    ** Metadata **
    table = 'meta'
    'stoitColNames' : tables.StringCol(512, pos=0)
    'numStoits'     : tables.Int32Col(pos=1)
    'merColNames'   : tables.StringCol(4096,pos=2)
    'merSize'       : tables.Int32Col(pos=3)
    'numMers'       : tables.Int32Col(pos=4)
    'numCons'       : tables.Int32Col(pos=5)
    'numBins'       : tables.Int32Col(pos=6)
    'clustered'     : tables.BoolCol(pos=7)           # set to true after clustering is complete
    'complete'      : tables.BoolCol(pos=8)           # set to true after clustering finishing is complete
    'formatVersion' : tables.Int32Col(pos=9)          # groopm file version
    [NEW] 'numMarkers'  : tables.Int32Col(pos=10)
    [NEW] 'taxonNames'  : tables.StringCol(4096, pos=11)
    [NEW] 'markerNames' : tables.StringCol(512, pos=1)

    [DEL] **PC variance**
    table = 'kpca_variance'
    'pc1_var' : tables.FloatCol(pos=0)
    'pc2_var' : tables.FloatCol(pos=1)
    'pc3_var' : tables.FloatCol(pos=2)
    ...

    ** Contigs **
    table = 'contigs'
    'cid'    : tables.StringCol(512, pos=0)
    'bid'    : tables.Int32Col(pos=1)
    'length' : tables.Int32Col(pos=2)
    'gc'     : tables.FloatCol(pos=3)

    ** Bins **
    table = 'bins'
    'bid'        : tables.Int32Col(pos=0)
    'numMembers' : tables.Int32Col(pos=1)
    'isLikelyChimeric' : tables.BoolCol(pos=2)

    [DEL] **Transformed coverage corners**
    table = 'transCoverageCorners'
    'x' : tables.FloatCol(pos=0)
    'y' : tables.FloatCol(pos=1)
    'z' : tables.FloatCol(pos=2)

    """
    kms_dtype = lambda mers: [(mer, float) for mer in mers]
    coverage_dtype = lambda cols: [(col, float) for col in cols]
    normCoverage_dtype = [('normCov', float)]
    links_dtype = [('contig1', int),
                   ('contig2', int),
                   ('numReads', int),
                   ('linkType', int),
                   ('gap', int)]
    meta_dtype = [('stoitColNames', '|S512'),
                  ('numStoits', int),
                  ('merColNames', '|S4096'),
                  ('merSize', int),
                  ('numMers', int),
                  ('numCons', int),
                  ('numBins', int),
                  ('clustered', bool),     # set to true after clustering is complete
                  ('complete', bool),      # set to true after clustering finishing is complete
                  ('formatVersion', int)]
    contigs_dtype=[('cid', '|S512'),
                   ('bid', int),
                   ('length', int),
                   ('gc', float)]
    bins_dtype=[('bid', int),
                ('numMembers', int),
                ('isLikelyChimeric', bool)]

#------------------------------------------------------------------------------
# DB CREATION / INITIALISATION  - PROFILES

    def createDB(self, timer, bamFiles, contigsFile, markerFile, dbFileName, cutoff, kmerSize=4, force=False, threads=1):
        """Main wrapper for parsing all input files"""
        # load all the passed vars
        stoitColNames = []

        kse = KmerSigEngine(kmerSize)
        conParser = ContigParser()
        bamParser = BamParser()
        mapper = MappingParser()

        cid_2_indices = {}

        # make sure we're only overwriting existing DBs with the users consent
        try:
            with open(dbFileName) as f:
                if(not force):
                    user_option = self.promptOnOverwrite(dbFileName)
                    if(user_option != "Y"):
                        print "Operation cancelled"
                        return False
                    else:
                        print "Overwriting database",dbFileName
        except IOError as e:
            print "Creating new database", dbFileName

        # create the db
        try:
            with tables.open_file(dbFileName, mode = "w", title = "GroopM") as h5file:
                # Create groups under "/" (root) for storing profile information and metadata
                profile_group = h5file.create_group("/", "profile", "Assembly profiles")
                meta_group = h5file.create_group("/", "meta", "Associated metadata")
                links_group = h5file.create_group("/", "links", "Paired read link information")
                profile_distances_group = h5file.create_group("/", "profile_distances", "Pairwise profile distances")
                mapping_group = h5file.create_group("/", "mappings", "Assembly mappings")
                mapping_distances_group = h5file.create_group("/", "mapping_distances", "Pairwise mapping distances")
                
                #------------------------
                # parse contigs
                #
                # Contig IDs are key. Any keys existing in other files but not in this file will be
                # ignored. Any missing keys in other files will be given the default profile value
                # (typically 0). Ironically, we don't store the CIDs here, these are saved one time
                # only in the bin table
                #
                # Before writing to the database we need to make sure that none of them have
                # 0 coverage @ all stoits.
                #------------------------
                import mimetypes
                GM_open = open
                try:
                    # handle gzipped files
                    mime = mimetypes.guess_type(contigsFile)
                    if mime[1] == 'gzip':
                        import gzip
                        GM_open = gzip.open
                except:
                    print "Error when guessing contig file mimetype"
                    raise
                try:
                    with GM_open(contigsFile, "r") as f:
                        try:
                            (con_names, con_gcs, con_lengths, con_ksigs) = conParser.parse(f, cutoff, kse)
                            num_cons = len(con_names)
                            cid_2_indices = dict(zip(con_names, range(num_cons)))
                        except:
                            print "Error parsing contigs"
                            raise
                except:
                    print "Could not parse contig file:",contigsFile,sys.exc_info()[0]
                    raise

                #------------------------
                # parse bam files
                #------------------------
                (ordered_bamFiles, _rowwise_links, cov_profiles) = bamParser.parse(bamFiles,
                                                                                  con_names,
                                                                                  cid_2_indices,
                                                                                  threads)
                tot_cov = [sum(profile) for profile in cov_profiles]
                good_indices = np.flatnonzero(tot_cov)
                bad_indices = [i for i in range(num_cons) if i not in good_indices]

                if len(bad_indices) > 0:
                    # report the bad contigs to the user
                    # and strip them before writing to the DB
                    print "****************************************************************"
                    print " IMPORTANT! - there are %d contigs with 0 coverage" % len(bad_indices)
                    print " across all stoits. They will be ignored:"
                    print "****************************************************************"
                    for i in xrange(0, min(5, len(bad_indices))):
                        print con_names[bad_indices[i]]
                    if len(bad_indices) > 5:
                      print '(+ %d additional contigs)' % (len(bad_indices)-5)
                    print "****************************************************************"

                    con_names = con_names[good_indices]
                    con_lengths = con_lengths[good_indices]
                    con_gcs = con_gcs[good_indices]
                    cov_profiles = cov_profiles[good_indices]
                    con_ksigs = con_ksigs[good_indices]

                num_cons = len(good_indices)
                
                #------------------------
                # parse mapping files
                #------------------------
                try:
                    with open(markerFile, "r") as f:
                        try:
                            (map_con_names, map_markers, map_taxstrings) = mapper.parse(f, True)
                        except:
                            print "Error parsing mapping data"
                            raise
                except:
                    print "Error opening marker file:", markerFile, sys.exc_info()[0]
                    raise
                
                #------------------------
                # write kmer sigs
                #------------------------
                # store the raw calculated kmer sigs in one table
                kms_desc = np.array([tuple(i) for i in con_ksigs], dtype=self.kms_dtype(kse.kmerCols))
                try:
                    h5file.create_table(profile_group,
                                       'kms',
                                       kms_desc,
                                       title='Kmer signatures',
                                       expectedrows=num_cons
                                       )
                except:
                    print "Error creating kmer sig table:", sys.exc_info()[0]
                    raise

                #------------------------
                # write cov profiles
                #------------------------
                # build a table template based on the number of bamfiles we have
                for i, bf in enumerate(ordered_bamFiles):
                    # assume the file is called something like "fred.bam"
                    # we want to rip off the ".bam" part
                    bam_desc = _get_bam_descriptor(bf, i + 1)
                    stoitColNames.append(bam_desc)
                stoitColNames = np.array(stoitColNames)

                # raw coverages
                coverage_desc = np.array([tuple(i) for i in cov_profiles], dtype=self.coverage_dtype(stoitColNames))
                try:
                    h5file.create_table(profile_group,
                                       'coverage',
                                       coverage_desc,
                                       title="Bam based coverage",
                                       expectedrows=num_cons)
                except:
                    print "Error creating coverage table:", sys.exc_info()[0]
                    raise

                # normalised coverages
                norm_coverages = np.linalg.norm(cov_profiles, axis=1)
                normCoverages_desc = np.array(norm_coverages, dtype=self.normCoverage_dtype)
                try:
                    h5file.create_table(profile_group,
                                       'normCoverage',
                                       normCoverages_desc,
                                       title="Normalised coverage",
                                       expectedrows=num_cons)
                except:
                    print "Error creating norm coverage table:", sys.exc_info()[0]
                    raise

                #------------------------
                # Add a table for the contigs
                #------------------------
                contigs_desc = np.array(zip(con_names, [0]*num_cons, con_lengths, con_gcs),
                                        dtype=self.contigs_dtype)
                try:
                    h5file.create_table(meta_group,
                                        'contigs',
                                         contigs_desc,
                                         title="Contig information",
                                         expectedrows=num_cons
                                        )
                except:
                    print "Error creating contig table:", sys.exc_info()[0]
                    raise

                #------------------------
                # Add a table for the bins
                #------------------------
                bins_desc = np.array([], dtype=self.bins_dtype)
                try: 
                    h5file.create_table(meta_group,
                                       'bins',
                                       bins_desc,
                                       title="Bin information",
                                       expectedrows=1)
                except:
                    print "Error creating bin metadata table:", sys.exc_info()[0]
                    raise

                #------------------------
                # contig links
                #------------------------
                # set table size according to the number of links returned from
                # the previous call
                links_desc = np.array(rowwise_links, dtype=self.links_dtype)
                try:
                    h5file.create_table(links_group,
                                       'links',
                                       links_desc,
                                       title="Contig Links",
                                       expectedrows=len(rowwise_links))
                except:
                    print "Error creating links table:", sys.exc_info()[0]
                    raise

                #------------------------
                # Add metadata
                #------------------------
                meta_desc = np.array([(str.join(',',stoitColNames),
                                       len(stoitColNames),
                                       str.join(',',kse.kmerCols),
                                       kmerSize,
                                       len(kse.kmerCols),
                                       num_cons,
                                       0,
                                       False,
                                       False,
                                       __current_GMDB_version__)],
                                     dtype=self.meta_dtype)
                try:
                    h5file.create_table(meta_group,
                                        'meta',
                                        meta_desc,
                                        "Descriptive data",
                                        expectedrows=1)
                except:
                    print "Error creating metadata table:", sys.exc_info()[0]
                    raise


        except:
            print "Error creating database:", dbFileName, sys.exc_info()[0]
            raise

        print "****************************************************************"
        print "Data loaded successfully!"
        print " ->",num_cons,"contigs"
        print " ->",len(stoitColNames),"BAM files"
        print "Written to: '"+dbFileName+"'"
        print "****************************************************************"
        print "    %s" % timer.getTimeStamp()

        # all good!
        return True

    def promptOnOverwrite(self, dbFileName, minimal=False):
        """Check that the user is ok with overwriting the db"""
        input_not_ok = True
        valid_responses = ['Y','N']
        vrs = ",".join([str.lower(str(x)) for x in valid_responses])
        while(input_not_ok):
            if(minimal):
                option = raw_input(" Overwrite? ("+vrs+") : ")
            else:

                option = raw_input(" ****WARNING**** Database: '"+dbFileName+"' exists.\n" \
                                   " If you continue you *WILL* delete any previous analyses!\n" \
                                   " Overwrite? ("+vrs+") : ")
            if(option.upper() in valid_responses):
                print "****************************************************************"
                return option.upper()
            else:
                print "Error, unrecognised choice '"+option.upper()+"'"
                minimal = True

#------------------------------------------------------------------------------
# GET TABLES - GENERIC
            
    def iterwhere(self, h5file, path, table, condition):
        """return the indices into the db which meet the condition"""
        return h5file.get_node(path, table).where(condition)
            
    def iterrows(self, h5file, path, table, rows):
        """return the indices into the db which meet the condition"""
        # check the DB out and see if we need to change anything about it
        table = h5file.get_node(path, table)
        if(len(rows) != 0):
            return (table[x] for x in rows)
        else:
            return (x for x in table.iterrows())
            
#------------------------------------------------------------------------------
# GET TABLES - PROFILES

    def getKmerSigs(self, dbFileName, indices=[]):
        """Load columns from kmer sig profile"""
        with tables.open_file(dbFileName, 'r') as h5file:
            return np.array([list(x) for x in self.iterrows(h5file, "/profile", "kms", indices)])
        
    def getCoverages(self, dbFileName, indices=[]):
        """Load columns from coverage profile"""
        with tables.open_file(dbFileName, 'r') as h5file:
            return np.array([list(x) for x in self.iterrows(h5file, "/profile", "coverage", indices)])
        
    def getNormCoverages(self, dbFileName, indices=[]):
        """Load columns for coverage norms"""
        with tables.open_file(dbFileName, 'r') as h5file:
            return np.array([list(x) for x in self.iterrows(h5file, "/profile", "normCoverage", indices)])

#------------------------------------------------------------------------------
# GET LINKS

    def restoreLinks(self, dbFileName, indices=[]):
        """Restore the links hash for a given set of indices"""
        with tables.open_file(dbFileName, 'r') as h5file:
            full_record = [list(x) for x in self.iterwhere(h5file, "/links", "links", "contig1 >= 0")]
        if indices == []:
            # get all!
            indices = self.getConditionalIndices(dbFileName)

        links_hash = {}
        if full_record != []:
            for record in full_record:
                # make sure we have storage
                if record[0] in indices and record[1] in indices:
                    try:
                        links_hash[record[0]].append(record[1:])
                    except KeyError:
                        links_hash[record[0]] = [record[1:]]
        return links_hash
            
#------------------------------------------------------------------------------
# GET TABLES - CONTIGS

    def getConditionalIndices(self, dbFileName, condition):
        """return the indices into the db which meet the condition"""
        if('' == condition):
            condition = "cid != ''" # no condition breaks everything!
        with tables.open_file(dbFileName, 'r') as h5file:
            return np.array([x.nrow for x in self.iterwhere(h5file, "/meta", "contigs", condition)])
        
    def byContigRows(self, h5file, indices=[]):
        """Load tuple of contig table rows"""
        return self.iterrows(h5file, "/meta", "contigs", indices)

    def getContigNames(self, dbFileName, indices=[]):
        """Load contig names"""
        with tables.open_file(dbFileName, 'r') as h5file:
            return [x["cid"] for x in self.byContigRows(h5file,  indices)]
        
    def getBins(self, dbFileName, indices=[]):
        """Load bin assignments"""
        with tables.open_file(dbFileName, 'r') as h5file:
            return [x["bid"] for x in self.byContigRows(h5file,  indices)]

    def getContigLengths(self, dbFileName, indices=[]):
        """Load contig lengths"""
        with tables.open_file(dbFileName, 'r') as h5file:
            return [x["length"] for x in self.byContigRows(h5file,  indices)]

    def getContigGCs(self, dbFileName, indices=[]):
        """Load contig gcs"""
        with tables.open_file(dbFileName, 'r') as h5file:
            return [x["gc"] for x in self.byContigRows(h5file,  indices)]
                            
#------------------------------------------------------------------------------
# GET TABLES - BINS
       
    def getBinStats(self, dbFileName):
        """Load data from bins table

        Returns a dict of type:
        { bid : numMembers }
        """
        ret_dict = {}
        with tables.open_file(dbFileName, 'r') as h5file:
            for x in self.iterrows(h5file, "/meta", "bins", []):
                ret_dict[x[0]] = x[1]
        return ret_dict
        
#------------------------------------------------------------------------------
# GET METADATA

    def _getMeta(self, dbFileName):
        """return the metadata table as a structured array"""
        with tables.open_file(dbFileName, 'r') as h5file:
            return h5file.root.meta.meta[0]

    def getGMDBFormat(self, dbFileName):
        """return the format version of this GM file"""
        # this guy needs to be a bit different to the other meta methods
        # becuase earlier versions of GM didn't include a format parameter
        try:
            this_DB_version = self._getMeta(dbFileName)['formatVersion']
        except ValueError:
            # this happens when an oldskool formatless DB is loaded
            this_DB_version = 0
        return this_DB_version

    def getNumStoits(self, dbFileName):
        """return the value of numStoits in the metadata tables"""
        return self._getMeta(dbFileName)['numStoits']

    def getMerColNames(self, dbFileName):
        """return the value of merColNames in the metadata tables"""
        return self._getMeta(dbFileName)['merColNames']

    def getMerSize(self, dbFileName):
        """return the value of merSize in the metadata tables"""
        return self._getMeta(dbFileName)['merSize']

    def getNumMers(self, dbFileName):
        """return the value of numMers in the metadata tables"""
        return self._getMeta(dbFileName)['numMers']

    def getNumCons(self, dbFileName):
        """return the value of numCons in the metadata tables"""
        return self._getMeta(dbFileName)['numCons']

    def getNumBins(self, dbFileName):
        """return the value of numBins in the metadata tables"""
        return self._getMeta(dbFileName)['numBins']

    def getStoitColNames(self, dbFileName):
        """return the value of stoitColNames in the metadata tables"""
        return self._getMeta(dbFileName)['stoitColNames']

    def isClustered(self, dbFileName):
        """Has this data set been clustered?"""
        return self._getMeta(dbFileName)['clustered']

    def isComplete(self, dbFileName):
        """Has this data set been *completely* clustered?"""
        return self._getMeta(dbFileName)['complete']
            
#------------------------------------------------------------------------------
#  SET OPERATIONS - UPDATE BINS  
        
    def setBinAssignments(self, dbFileName, updates={}, nuke=False):
        """Set per-contig bins

        updates is a dictionary which looks like:
        { tableRow : bid }
        """
        
        # get the contigs table image
        with tables.open_file(dbFileName, mode='r') as h5file:
            if nuke:
                (con_names, con_lens, con_gcs) = zip(*[(x[0], x[2], x[3]) for x in self.byContigRows(h5file, indices)])
                num_cons = len(con_lens)
                # clear all bin assignments
                bins = [0]*num_cons
            else:
                (con_names, bins, con_lens, con_gcs) = zip(*[tuple(x) for x in self.byContigRows(h5file, indices)])
        
        # now apply the updates
        for tr in updates.keys():
            bins[tr] = updates[tr]

        # build the new contigs table image
        contigs_desc = np.array(zip(con_names, bins, con_lens, con_gcs),
                                dtype=self.meta_dtype)
        
        # build the new bins table image
        (bid, num_members) = np.unique(bids, return_counts=True)
        updates = [(bid, num_members, False) for (bid, num_members) in zip(bid, num_members)] #isLikelyChimeric is always false
        bins_desc = np.array(updates, dtype=self.bins_dtype)
        
        # update num bins metadata
        num_bins = len(bid) - int(0 in bid)
        meta = self._getMeta(dbFileName)
        meta['numBins'] = num_bins      
        meta_desc = np.array([meta], dtype=self.bins_dtype)
                                
          
        # Let's do the update atomically... 
        with tables.open_file(dbFileName, mode='a', root_uep='/') as h5file:
            meta_group = h5file.get_node('/', name='meta')
            
            try:
                # get rid of any failed attempts
                h5file.remove_node(meta_group, 'tmp_contigs')
            except:
                pass
            try:
                h5file.create_table(meta_group,
                                    'tmp_contigs',
                                    image,
                                    title="Contig information",
                                    expectedrows=num_cons)
            except:
                print "Error creating contig table:", sys.exc_info()[0]
                raise
                
            # update bin table
            try:
                h5file.remove_node(meta_group, 'tmp_bins')
            except:
                pass

            try:
                h5file.create_table(meta_group,
                                    'tmp_bins',
                                    bins_desc,
                                    title="Bin information",
                                    expectedrows=len(bid))
            except:
                print "Error creating bins table:", sys.exc_info()[0]
                raise
                
            # update meta table
            try:
                h5file.remove_node(meta_group, 'tmp_meta')
            except:
                pass
                
            try:
                h5file.create_table(meta_group,
                                    'tmp_meta',
                                    meta_desc,
                                    title="Descriptive data",
                                    expectedrows=1)
            except:
                print "Error creating meta table:", sys.exc_info()[0]
                raise

            # rename the tmp tables to overwrite
            h5file.rename_node(meta_group, 'contigs', 'tmp_contigs', overwrite=True)
            h5file.rename_node(meta_group, 'bins', 'tmp_bins', overwrite=True)
            h5file.rename_node(meta_group, 'meta', 'tmp_meta', overwrite=True)
            
    def nukeBins(self, dbFileName):
        """Reset all bin information, completely"""
        print "    Clearing all old bin information from",dbFileName
        self.setBinAssignments(dbFileName, updates={}, nuke=True)

#------------------------------------------------------------------------------
#  SET OPERATIONS - METADATA      
        
    def _setMeta(self, dbFileName, meta):
        meta_desc = np.array([meta], dtype=self.meta_dtype)
        with tables.open_file(dbFileName, mode='a', root_uep='/') as h5file:
            # get hold of the group
            meta_group = h5file.get_node('/', name='meta')
            # nuke any previous failed attempts
            try:
                h5file.remove_node(meta_group, 'tmp_meta')
            except:
                pass
            try:
                h5file.create_table(meta_group,
                                    'tmp_meta',
                                    meta_desc,
                                    "Descriptive data",
                                    expectedrows=1)
            except:
                print "Error creating metadata table:", sys.exc_info()[0]
                raise
            # rename the tmp table to overwrite
            h5file.rename_node(meta_group, 'meta', 'tmp_meta', overwrite=True)

    def setGMDBFormat(self, dbFileName, version):
        """Update the GMDB format version"""
        meta = self._getMeta(dbFileName)
        meta['formatVersion'] = version
        self._setMeta(dbFileName, meta)

    def setClustered(self, dbFileName):
        """Set the state of clustering"""
        meta = self._getMeta(dbFileName)
        meta['clustered'] = True
        self._setMeta(dbFileName, meta)

    def setComplete(self, dbFileName):
        """Set the state of completion"""
        meta = self._getMeta(dbFileName)
        meta['complete'] = True
        self._setMeta(dbFileName, meta)

#------------------------------------------------------------------------------
# FILE / IO

    def dumpData(self, dbFileName, fields, outFile, separator, useHeaders):
        """Dump data to file"""
        header_strings = []
        data_arrays = []

        if fields == ['all']:
            fields = ['contig', 'size', 'gc', 'bin', 'coverage', 'ncoverage', 'mers']

        num_fields = len(fields)
        data_converters = []

        try:
            for field in fields:
                if field == 'contig':
                    header_strings.append('cid')
                    data_arrays.append(self.getContigNames(dbFileName))
                    data_converters.append(lambda x : x)

                elif field == 'size':
                    header_strings.append('size')
                    data_arrays.append(self.getContigLengths(dbFileName))
                    data_converters.append(lambda x : str(x))

                elif field == 'gc':
                    header_strings.append('GC%')
                    data_arrays.append(self.getContigGCs(dbFileName))
                    data_converters.append(lambda x : str(x))

                elif field == 'bin':
                    header_strings.append('bid')
                    data_arrays.append(self.getBins(dbFileName))
                    data_converters.append(lambda x : str(x))

                elif field == 'coverage':
                    stoits = self.getStoitColNames(dbFileName).split(',')
                    for stoit in stoits:
                        header_strings.append(stoit)
                    data_arrays.append(self.getCoverageProfiles(dbFileName))
                    data_converters.append(lambda x : separator.join(["%0.4f" % i for i in x]))
                    
                elif field == 'ncoverage':
                    header_strings.append('normCoverage')
                    data_arrays.append(self.getNormCoverages(dbFileName))
                    data_converters.append(lambda x : separator.join(["%0.4f" % i for i in x]))

                elif field == 'mers':
                    mers = self.getMerColNames(dbFileName).split(',')
                    for mer in mers:
                        header_strings.append(mer)
                    data_arrays.append(self.getKmerSigs(dbFileName))
                    data_converters.append(lambda x : separator.join(["%0.4f" % i for i in x]))
        except:
            print "Error opening DB:", dbFileName, sys.exc_info()[0]
            raise

        try:
            with open(outFile, 'w') as fh:
                if useHeaders:
                    header = separator.join(header_strings) + "\n"
                    fh.write(header)

                num_rows = len(data_arrays[0])
                for i in range(num_rows):
                    fh.write(data_converters[0](data_arrays[0][i]))
                    for j in range(1, num_fields):
                        fh.write(separator+data_converters[j](data_arrays[j][i]))
                    fh.write('\n')
        except:
            print "Error opening output file %s for writing" % outFile
            raise

      
#------------------------------------------------------------------------------
# Helpers          
def _get_bam_descriptor(fullPath, index_num):
    """AUX: Reduce a full path to just the file name minus extension"""
    return str(index_num) + '_' + op_splitext(op_basename(fullPath))[0]
    
    
class _with_db:
    """Wrap database file in a `with` compatible object"""
    def __init__(self, dbFileName, silent=False, checkUpgrade=True):
        self._dbFileName = dbFileName
        if checkUpgrade:
            self.checkAndUpgradeDB(self._dbFileName, silent=silent)
        
    def __enter__(self): 
        """generate a database iterator"""
        # check the DB out and see if we need to change anything about it
        self._h5file = tables.open_file(self._dbFileName, mode='r')
        return self._h5file.__enter__()
            
    def __exit__(self, type, value, traceback):
        self._h5file.__exit__(type, value, traceback)
        if value is not None:
            print "Error opening DB:",dbFileName, sys.exc_info()[0]
        else:
            return True
            
###############################################################################
###############################################################################
###############################################################################
###############################################################################
class ContigParser:
    """Main class for reading in and parsing contigs"""
    def __init__(self): pass

    def readFasta(self, fp): # this is a generator function
        header = None
        seq = None
        while True:
            for l in fp:
                if l[0] == '>': # fasta header line
                    if header is not None:
                        # we have reached a new sequence
                        yield header, "".join(seq)
                    header = l.rstrip()[1:].partition(" ")[0] # save the header we just saw
                    seq = []
                else:
                    seq.append(l.rstrip())
            # anything left in the barrel?
            if header is not None:
                yield header, "".join(seq)
            break

    def parse(self, contigFile, cutoff, kse):
        """Do the heavy lifting of parsing"""
        print "Parsing contigs"
        contigInfo = {} # save everything here first so we can sort accordingly
        for cid,seq in self.readFasta(contigFile):
            if len(seq) >= cutoff:
                contigInfo[cid] = (kse.getKSig(seq.upper()), len(seq), self.calculateGC(seq))

        # sort the contig names here once!
        con_names = np.array(sorted(contigInfo.keys()))

        # keep everything in order...
        con_gcs = np.array([contigInfo[cid][2] for cid in con_names])
        con_lengths = np.array([contigInfo[cid][1] for cid in con_names])
        con_ksigs = np.array([contigInfo[cid][0] for cid in con_names])

        return (con_names, con_gcs, con_lengths, con_ksigs)

    def calculateGC(self, seq):
      """Calculate fraction of nucleotides that are G or C."""
      testSeq = seq.upper()
      gc = testSeq.count('G') + testSeq.count('C')
      at = testSeq.count('A') + testSeq.count('T')

      return float(gc) / (gc + at)

    def getWantedSeqs(self, contigFile, wanted, storage={}):
        """Do the heavy lifting of parsing"""
        print "Parsing contigs"
        for cid,seq in self.readFasta(contigFile):
            if(cid in wanted):
                storage[cid] = seq
        return storage

###############################################################################
###############################################################################
###############################################################################
###############################################################################
class KmerSigEngine:
    """Simple class for determining kmer signatures"""
    
    compl = s_maketrans('ACGT', 'TGCA')
    
    def __init__(self, kLen=4):
        self.kLen = kLen
        (self.kmerCols, self.llDict) = self.makeKmerColNames(makeLL=True)
        self.numMers = len(self.kmerCols)

    def makeKmerColNames(self, makeLL=False):
        """Work out the range of kmers required based on kmer length

        returns a list of sorted kmers and optionally a llo dict
        """
        # build up the big list
        base_words = ("A","C","G","T")
        out_list = ["A","C","G","T"]
        for i in range(1,self.kLen):
            working_list = []
            for mer in out_list:
                for char in base_words:
                    working_list.append(mer+char)
            out_list = working_list

        # pare it down based on lexicographical ordering
        ret_list = []
        ll_dict = {}
        for mer in out_list:
            lmer = self.shiftLowLexi(mer)
            ll_dict[mer] = lmer
            if lmer not in ret_list:
                ret_list.append(lmer)
        if makeLL:
            return (sorted(ret_list), ll_dict)
        else:
            return sorted(ret_list)

    def getGC(self, seq):
        """Get the GC of a sequence"""
        Ns = seq.count('N') + seq.count('n')
        compl = s_maketrans('ACGTacgtnN', '0110011000')
        return sum([float(x) for x in list(seq.translate(compl))])/float(len(seq) - Ns)

    def shiftLowLexi(self, seq):
        """Return the lexicographically lowest form of this sequence"""
        # build a dictionary to know what letter to switch to
        rseq = seq.translate(self.compl)[::-1]
        if(seq < rseq):
            return seq
        return rseq

    def getKSig(self, seq):
        """Work out kmer signature for a nucleotide sequence

        returns a tuple of floats which is the kmer sig
        """
        # tmp storage
        sig = dict(zip(self.kmerCols, [0.0] * self.numMers))
        # the number fo kmers in this sequence
        num_mers = len(seq)-self.kLen+1
        for i in range(0,num_mers):
            try:
                sig[self.llDict[seq[i:i+self.kLen]]] += 1.0
            except KeyError:
                # typically due to an N in the sequence. Reduce the number of mers we've seen
                num_mers -= 1

        # normalise by length and return
        try:
            return tuple([sig[x] / num_mers for x in self.kmerCols])
        except ZeroDivisionError:
            print "***WARNING*** Sequence '%s' is not playing well with the kmer signature engine " % seq
            return tuple([0.0] * self.numMers)

###############################################################################
###############################################################################
###############################################################################
###############################################################################
class BamParser:
    """Parse multiple bam files and write the output to hdf5 """
    def parse(self, bamFiles, contigNames, cid2Indices, threads):
        """Parse multiple bam files and store the results in the main DB"""
        print "Parsing BAM files using %d threads" % threads

        BP = BMBP(BMCT(CT.P_MEAN_TRIMMED, 5, 5))
        BP.parseBams(bamFiles,
                     doLinks=False,
                     doCovs=True,
                     threads=threads,
                     verbose=True)

        # we need to make sure that the ordering of contig names is consistent
        # first we get a dict that connects a contig name to the index in
        # the coverages array
        con_name_lookup = dict(zip(BP.BFI.contigNames,
                                   range(len(BP.BFI.contigNames))))

        # Next we build the cov_sigs array by appending the coverage
        # profiles in the same order. We need to handle the case where
        # there is no applicable contig in the BamM-derived coverages
        cov_sigs = []
        for cid in contigNames:
            try:
                cov_sigs.append(tuple(BP.BFI.coverages[con_name_lookup[cid]]))
            except KeyError:
                # when a contig is missing from the BAM we just give it 0
                # coverage. It will be removed later with a warning then
                cov_sigs.append(tuple([0.]*len(bamFiles)))

        #######################################################################
        # LINKS ARE DISABLED UNTIL STOREM COMES ONLINE
        #######################################################################
        # transform the links into something a little easier to parse later
        rowwise_links = []
        if False:
            for cid in links:
                for link in links[cid]:
                    try:
                        rowwise_links.append((cid2Indices[cid],     # contig 1
                                              cid2Indices[link[0]], # contig 2
                                              int(link[1]),         # numReads
                                              int(link[2]),         # linkType
                                              int(link[3])          # gap
                                              ))
                    except KeyError:
                        pass

        return ([BP.BFI.bamFiles[i].fileName for i in range(len(bamFiles))],
                rowwise_links,
                np.array(cov_sigs))

    
###############################################################################
###############################################################################
###############################################################################
###############################################################################
class MappingParser:
    """Read a file of tab delimited contig names, marker names and optionally classifications."""
    def parse(self, fp, doclassifications=False):
        con_names = []
        con_markers = []
        if doclassifications:
            con_taxstrings = []
           
        reader = CSVReader()
        for l in reader.readCSV(fp, "\t"):

            con_names.append(l[0])
            con_markers.append(l[1])
            if doclassifications:
                if len(l) > 2:
                    con_taxstrings.append(l[2])
                else:
                    con_taxstrings.append("")
        
        if doclassifications:
            return (con_names, con_markers, con_taxstrings)
        else:
            return (con_names, con_markers)

###############################################################################
###############################################################################
###############################################################################
###############################################################################
# DB UPGRADE
def DB1_PCAKsigs(ksigs):
    # stub pca calculation
    return (zip(ksigs[:, 0], ksigs[:, 1]), np.zeros(len(ksigs)))
    
    
class DB4_CoverageTransformer:
    # stup coverage transformation
    def __init__(self,
                 numContigs,
                 numStoits,
                 normCoverages,
                 kmerNormPC1,
                 coverageProfiles,
                 stoitColNames,
                 scaleFactor=1000):
        self.numContigs = numContigs
        self.numStoits = numStoits
        self.normCoverages = normCoverages
        self.kmerNormPC1 = kmerNormPC1
        self.covProfiles = coverageProfiles
        self.stoitColNames = stoitColNames
        self.indices = range(self.numContigs)
        self.scaleFactor = scaleFactor
        
        self.TCentre = None
        self.transformedCP = np.zeros((numContigs, 3))
        self.corners = np.zeros((numStoits, 3))

        
class DataManagerUpgrader:
    def __init__(self):
        self._dm = DataManager
        
    def checkAndUpgradeDB(self, dbFileName, silent=False):
        """Check the DB and upgrade if necessary"""
        # get the DB format version
        this_DB_version = self._dm.getGMDBFormat(dbFileName)
        if __current_GMDB_version__ == this_DB_version:
            if not silent:
                print "    GroopM DB version (%s) up to date" % this_DB_version
            return

        # now, if we get here then we need to do some work
        upgrade_tasks = {}
        upgrade_tasks[(0,1)] = self.upgradeDB_0_to_1
        upgrade_tasks[(1,2)] = self.upgradeDB_1_to_2
        upgrade_tasks[(2,3)] = self.upgradeDB_2_to_3
        upgrade_tasks[(3,4)] = self.upgradeDB_3_to_4
        upgrade_tasks[(4,5)] = self.upgradeDB_4_to_5
        upgrade_tasks[(5,6)] = self.upgradeDB_5_to_6

        # we need to apply upgrades in order!
        # keep applying the upgrades as long as we need to
        while this_DB_version < __current_GMDB_version__:
            task = (this_DB_version, this_DB_version+1)
            upgrade_tasks[task](dbFileName)
            this_DB_version += 1

    def upgradeDB_0_to_1(self, dbFileName):
        """Upgrade a GM db from version 0 to version 1"""
        print "*******************************************************************************\n"
        print "              *** Upgrading GM DB from version 0 to version 1 ***"
        print ""
        print "                            please be patient..."
        print ""
        # the change in this version is that we'll be saving the first
        # two kmerSig PCA's in a separate table
        print "    Calculating and storing the kmerSig PCAs"

        # don't compute the PCA of the ksigs just store dummy data
        ksigs = self.getKmerSigs(dbFileName)
        pc_ksigs, sumvariance = DB1_PCAKsigs(ksigs)
        num_cons = len(pc_ksigs)

        db_desc = [('pc1', float),
                   ('pc2', float)]
        try:
            with tables.open_file(dbFileName, mode='a', root_uep="/profile") as profile_group:
                try:
                    profile_group.create_table('/',
                                              'kpca',
                                              np.array(pc_ksigs, dtype=db_desc),
                                              title='Kmer signature PCAs',
                                              expectedrows=num_cons
                                              )
                except:
                    print "Error creating KMERVALS table:", sys.exc_info()[0]
                    raise
        except:
            print "Error opening DB:",dbFileName, sys.exc_info()[0]
            raise

        # update the formatVersion field and we're done
        self.setGMDBFormat(dbFileName, 1)
        print "*******************************************************************************"

    def upgradeDB_1_to_2(self, dbFileName):
        """Upgrade a GM db from version 1 to version 2"""
        print "*******************************************************************************\n"
        print "              *** Upgrading GM DB from version 1 to version 2 ***"
        print ""
        print "                            please be patient..."
        print ""
        # the change in this version is that we'll be saving a variable number of kmerSig PCA's
        # and GC information for each contig
        print "    Calculating and storing the kmer signature PCAs"

        # grab any data needed from database before opening if for modification
        bin_ids = self.getBins(dbFileName)
        orig_con_names = self.getContigNames(dbFileName)

        # compute the PCA of the ksigs
        conParser = ContigParser()
        ksigs = self.getKmerSigs(dbFileName)
        pc_ksigs, sumvariance = DB1_PCAKSigs(ksigs)
        num_cons = len(pc_ksigs)

        db_desc = []
        for i in xrange(0, len(pc_ksigs[0])):
          db_desc.append(('pc' + str(i+1), float))

        try:
            with tables.open_file(dbFileName, mode='a', root_uep="/") as h5file:
                pg = h5file.get_node('/', name='profile')
                try:
                    try:
                        h5file.remove_node(pg, 'tmp_kpca')
                    except:
                        pass

                    h5file.create_table(pg,
                                       'tmp_kpca',
                                       np.array(pc_ksigs, dtype=db_desc),
                                       title='Kmer signature PCAs',
                                       expectedrows=num_cons
                                      )

                    h5file.rename_node(pg, 'kpca', 'tmp_kpca', overwrite=True)

                except:
                    print "Error creating kpca table:", sys.exc_info()[0]
                    raise

                # Add GC
                contigFile = raw_input('\nPlease specify fasta file containing the bam reference sequences: ')
                with open(contigFile, "r") as f:
                    try:
                        contigInfo = {}
                        for cid,seq in conParser.readFasta(f):
                            contigInfo[cid] = (len(seq), conParser.calculateGC(seq))

                        # sort the contig names here once!
                        con_names = np.array(sorted(contigInfo.keys()))

                        # keep everything in order...
                        con_gcs = np.array([contigInfo[cid][1] for cid in con_names])
                        con_lengths = np.array([contigInfo[cid][0] for cid in con_names])
                    except:
                        print "Error parsing contigs"
                        raise

                # remove any contigs not in the current DB (these were removed due to having zero coverage)
                good_indices = [i for i in range(len(orig_con_names)) if orig_con_names[i] in con_names]

                con_names = con_names[good_indices]
                con_lengths = con_lengths[good_indices]
                con_gcs = con_gcs[good_indices]
                bin_ids = bin_ids[good_indices]

                meta_group = h5file.get_node('/', name='meta')
                self.setBinAssignments((h5file, meta_group),
                               image=zip(con_names,
                                         bin_ids,
                                         con_lengths,
                                         con_gcs)
                               )
        except:
            print "Error opening DB:",dbFileName, sys.exc_info()[0]
            raise

        # update the formatVersion field and we're done
        self._dm.setGMDBFormat(dbFileName, 2)
        print "*******************************************************************************"

    def upgradeDB_2_to_3(self, dbFileName):
        """Upgrade a GM db from version 2 to version 3"""
        print "*******************************************************************************\n"
        print "              *** Upgrading GM DB from version 2 to version 3 ***"
        print ""
        print "                            please be patient..."
        print ""
        # the change in this version is that we'll be saving the variance for each kmerSig PCA
        print "    Calculating and storing variance of kmer signature PCAs"

        # compute the PCA of the ksigs
        conParser = ContigParser()
        ksigs = self.getKmerSigs(dbFileName)
        pc_ksigs, sumvariance = DB1_PCAKSigs(ksigs)

        # calcualte variance of each PC
        pc_var = [sumvariance[0]]
        for i in xrange(1, len(sumvariance)):
          pc_var.append(sumvariance[i]-sumvariance[i-1])
        pc_var = tuple(pc_var)

        db_desc = []
        for i in xrange(0, len(pc_var)):
          db_desc.append(('pc' + str(i+1) + '_var', float))

        try:
            with tables.open_file(dbFileName, mode='a', root_uep="/") as h5file:
                meta = h5file.get_node('/', name='meta')
                try:
                    try:
                        h5file.remove_node(meta, 'tmp_kpca_variance')
                    except:
                        pass

                    h5file.create_table(meta,
                                              'tmp_kpca_variance',
                                              np.array([pc_var], dtype=db_desc),
                                              title='Variance of kmer signature PCAs',
                                              expectedrows=1
                                              )

                    h5file.rename_node(meta, 'kpca_variance', 'tmp_kpca_variance', overwrite=True)

                except:
                    print "Error creating kpca_variance table:", sys.exc_info()[0]
                    raise
        except:
            print "Error opening DB:", dbFileName, sys.exc_info()[0]
            raise

        # update the formatVersion field and we're done
        self.setGMDBFormat(dbFileName, 3)
        print "*******************************************************************************"

    def upgradeDB_3_to_4(self, dbFileName):
        """Upgrade a GM db from version 3 to version 4"""
        print "*******************************************************************************\n"
        print "              *** Upgrading GM DB from version 3 to version 4 ***"
        print ""
        print "                            please be patient..."
        print ""
        # the change in this version is that we'll be adding a chimeric flag for each bin
        print "    Adding chimeric flag for each bin."
        print "    !!! Groopm core must be run again for this flag to be properly set. !!!"

        # read existing data in 'bins' table
        try:
            with tables.open_file(dbFileName, mode='r') as h5file:
                ret_dict = {}
                all_rows = h5file.root.meta.bins.read()
                for row in all_rows:
                    ret_dict[row[0]] = row[1]
        except:
            print "Error opening DB:", dbFileName, sys.exc_info()[0]
            raise

        # write new table with chimeric flag set to False by default
        db_desc = [('bid', int),
                   ('numMembers', int),
                   ('isLikelyChimeric', bool)]

        data = []
        for bid in ret_dict:
          data.append((bid, ret_dict[bid], False))

        bd = np.array(data, dtype=db_desc)

        try:
            with tables.open_file(dbFileName, mode='a', root_uep="/") as h5file:
                meta_group = h5file.get_node('/', name='meta')

                try:
                    h5file.remove_node(meta_group, 'tmp_bins')
                except:
                    pass

                try:
                    h5file.create_table(meta_group,
                                       'tmp_bins',
                                       bd,
                                       title="Bin information",
                                       expectedrows=1)
                except:
                    print "Error creating META table:", sys.exc_info()[0]
                    raise

                h5file.rename_node(meta_group, 'bins', 'tmp_bins', overwrite=True)
        except:
            print "Error opening DB:",dbFileName, sys.exc_info()[0]
            raise

        # update the formatVersion field and we're done
        self.setGMDBFormat(dbFileName, 4)
        print "*******************************************************************************"

    def upgradeDB_4_to_5(self, dbFileName):
        """Upgrade a GM db from version 4 to version 5"""
        print "*******************************************************************************\n"
        print "              *** Upgrading GM DB from version 4 to version 5 ***"
        print ""
        print "                            please be patient..."
        print ""
        # the change in this version is that we'll be saving the transformed coverage coords
        print "    Saving transformed coverage profiles"
        print "    You will not need to re-run parse or core due to this change"

        # we need to get the raw coverage profiles and the kmerPCA1 data
        indices = self.getConditionalIndices(dbFileName, silent=False, checkUpgrade=False)
        kPCA_1 = self.getKmerPCAs(dbFileName, indices=indices)[:,0]
        raw_coverages = self.getCoverageProfiles(dbFileName, indices=indices)
        norm_coverages = np.array([np.linalg.norm(raw_coverages[i]) for i in range(len(indices))])

        CT = DB4_CoverageTransformer(len(indices),
                                     self._dm.getNumContigs(dbFileName),
                                     norm_coverages,
                                     kPCA_1,
                                     raw_coverages,
                                     self._dm.getStoitNames(dbFileName))
                 
        # now CT stores the transformed coverages and other important information
        # we will write this to the database
        with tables.open_file(dbFileName, mode='a', root_uep="/") as h5file:
            meta_group = h5file.get_node('/', name='meta')
            profile_group = h5file.get_node('/', name='profile')

            # raw coverages - we may have reordered rows, so we should fix this now!
            try:
                h5file.remove_node(meta_group, 'tmp_coverages')
            except:
                pass

            try:
                h5file.create_table(profile_group,
                                   'tmp_coverages',
                                   np.array(CT.covProfiles,
                                            dtype=[(col_name, float) for col_name in CT.stoitColNames]),
                                   title="Bam based coverage",
                                   expectedrows=CT.numContigs)
            except:
                print "Error creating coverage table:", sys.exc_info()[0]
                raise

            h5file.rename_node(profile_group, 'coverage', 'tmp_coverages', overwrite=True)

            # transformed coverages
            db_desc = [('x', float),
                       ('y', float),
                       ('z', float)]
            try:
                h5file.create_table(profile_group,
                                   'transCoverage',
                                   np.array(CT.transformedCP , dtype=db_desc),
                                   title="Transformed coverage",
                                   expectedrows=CT.numContigs)
            except:
                print "Error creating transformed coverage table:", sys.exc_info()[0]
                raise

            # transformed coverage corners
            try:
                h5file.create_table(meta_group,
                                   'transCoverageCorners',
                                   np.array(CT.corners , 
                                            dtype=[('x', float),
                                                   ('y', float),
                                                   ('z', float)]),
                                   title="Transformed coverage corners",
                                   expectedrows=CT.numStoits)
            except:
                print "Error creating transformed coverage corner table:", sys.exc_info()[0]
                raise


            # normalised coverages
            try:
                h5file.create_table(profile_group,
                                   'normCoverage',
                                   np.array(CT.normCoverages , dtype=[('normCov', float)]),
                                   title="Normalised coverage",
                                   expectedrows=CT.numContigs)
            except:
                print "Error creating normalised coverage table:", sys.exc_info()[0]
                raise

        # stoit col names may have been shuffled
        meta_data = (",".join([str(i) for i in CT.stoitColNames]),
                    CT.numStoits,
                    self.getMerColNames(dbFileName),
                    self.getMerSize(dbFileName),
                    self.getNumMers(dbFileName),
                    self.getNumCons(dbFileName),
                    self.getNumBins(dbFileName),
                    self.isClustered(dbFileName),
                    self.isComplete(dbFileName),
                    self.getGMDBFormat(dbFileName))

        with tables.open_file(dbFileName, mode='a', root_uep="/") as h5file:
            self.setMeta(h5file, meta_data, overwrite=True)

        # update the formatVersion field and we're done
        self.setGMDBFormat(dbFileName, 5)
        print "*******************************************************************************"
        
        
    def upgradeDB_5_to_6(self, dbFileName):
        """Upgrade a GM db from version 5 to version 6"""
        print "*******************************************************************************\n"
        print "              *** Upgrading GM DB from version 5 to version 6 ***"
        print ""
        print "                            please be patient..."
        print ""
        # the changes in this version are as follows:
        #   deleting transformed coverage coords
        print "    Saving transformed coverage profiles"
        print "    You will not need to re-run parse or core due to this change"

        # we need to get the raw coverage profiles and the kmerPCA1 data
        indices = self.getConditionalIndices(dbFileName, silent=False, checkUpgrade=False)
        kPCA_1 = self.getKmerPCAs(dbFileName, indices=indices)[:,0]
        raw_coverages = self.getCoverageProfiles(dbFileName, indices=indices)
        norm_coverages = np.array([np.linalg.norm(raw_coverages[i]) for i in range(len(indices))])

        
        CT = CoverageTransformer()
        CT.stoitColNames = np.array(self.getStoitColNames(dbFileName).split(","))
        CT.normCoverages = norm_coverages
        CT.numContigs = len(indices)
        CT.numStoits = self.getNumStoits(dbFileName)
        CT.transformedCP = [tuple(i) for i in np.zeros((CT.numContigs, 3))]
        CT.covProfiles = [tuple(i) for i in raw_coverages]
        CT.corners = [tuple(i) for i in np.zeros((CT.numStoits, 3))]

        # now CT stores the transformed coverages and other important information
        # we will write this to the database
        with tables.open_file(dbFileName, mode='a', root_uep="/") as h5file:
            meta_group = h5file.get_node('/', name='meta')
            profile_group = h5file.get_node('/', name='profile')

            # raw coverages - we may have reordered rows, so we should fix this now!
            db_desc = []
            for scn in CT.stoitColNames:
                db_desc.append((scn, float))

            try:
                h5file.remove_node(meta_group, 'tmp_coverages')
            except:
                pass

            try:
                h5file.create_table(profile_group,
                                   'tmp_coverages',
                                   np.array(CT.covProfiles, dtype=db_desc),
                                   title="Bam based coverage",
                                   expectedrows=CT.numContigs)
            except:
                print "Error creating coverage table:", sys.exc_info()[0]
                raise

            h5file.rename_node(profile_group, 'coverage', 'tmp_coverages', overwrite=True)

            # transformed coverages
            db_desc = [('x', float),
                       ('y', float),
                       ('z', float)]
            try:
                h5file.create_table(profile_group,
                                   'transCoverage',
                                   np.array(CT.transformedCP , dtype=db_desc),
                                   title="Transformed coverage",
                                   expectedrows=CT.numContigs)
            except:
                print "Error creating transformed coverage table:", sys.exc_info()[0]
                raise

            # transformed coverage corners
            db_desc = [('x', float),
                       ('y', float),
                       ('z', float)]
            try:
                h5file.create_table(meta_group,
                                   'transCoverageCorners',
                                   np.array(CT.corners , dtype=db_desc),
                                   title="Transformed coverage corners",
                                   expectedrows=CT.numStoits)
            except:
                print "Error creating transformed coverage corner table:", sys.exc_info()[0]
                raise


            # normalised coverages
            db_desc = [('normCov', float)]
            try:
                h5file.create_table(profile_group,
                                   'normCoverage',
                                   np.array(CT.normCoverages , dtype=db_desc),
                                   title="Normalised coverage",
                                   expectedrows=CT.numContigs)
            except:
                print "Error creating normalised coverage table:", sys.exc_info()[0]
                raise

        # stoit col names may have been shuffled
        meta_data = (",".join([str(i) for i in CT.stoitColNames]),
                    CT.numStoits,
                    self.getMerColNames(dbFileName),
                    self.getMerSize(dbFileName),
                    self.getNumMers(dbFileName),
                    self.getNumCons(dbFileName),
                    self.getNumBins(dbFileName),
                    self.isClustered(dbFileName),
                    self.isComplete(dbFileName),
                    self.getGMDBFormat(dbFileName))

        with tables.open_file(dbFileName, mode='a', root_uep="/") as h5file:
            self.setMeta(h5file, meta_data, overwrite=True)

        # update the formatVersion field and we're done
        self.setGMDBFormat(dbFileName, 5)
        print "*******************************************************************************"
        
        
        
###############################################################################
###############################################################################
###############################################################################
###############################################################################
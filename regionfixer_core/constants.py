#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#   Region Fixer.
#   Fix your region files with a backup copy of your Minecraft world.
#   Copyright (C) 2020  Alejandro Aguilera (Fenixin)
#   https://github.com/Fenixin/Minecraft-Region-Fixer
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#



################
# Return values
################

RV_OK = 0  # world scanned and no problems found
RV_CRASH = 1  # crash or end unexpectedly
RV_NOTHING_TO_SCAN = 20  # no files/worlds to scan
# RV_WRONG_COMMAND = 2  # the command line used is wrong and region fixer didn't execute. argparse uses this value by default
RV_BAD_WORLD = 3  # scan completed successfully but problems have been found in the scan




# --------------
# Chunk related:
# --------------
# Used to mark the status of chunks:
CHUNK_NOT_CREATED = -1
CHUNK_OK = 0
CHUNK_CORRUPTED = 1
CHUNK_WRONG_LOCATED = 2
CHUNK_TOO_MANY_ENTITIES = 3
CHUNK_SHARED_OFFSET = 4
CHUNK_MISSING_ENTITIES_TAG = 5

# Chunk statuses
CHUNK_STATUSES = [CHUNK_NOT_CREATED,
                  CHUNK_OK,
                  CHUNK_CORRUPTED,
                  CHUNK_WRONG_LOCATED,
                  CHUNK_TOO_MANY_ENTITIES,
                  CHUNK_SHARED_OFFSET,
                  CHUNK_MISSING_ENTITIES_TAG]

# Status that are considered problems
CHUNK_PROBLEMS = [CHUNK_CORRUPTED,
                  CHUNK_WRONG_LOCATED,
                  CHUNK_TOO_MANY_ENTITIES,
                  CHUNK_SHARED_OFFSET,
                  CHUNK_MISSING_ENTITIES_TAG]

# Text describing each chunk status
CHUNK_STATUS_TEXT = {CHUNK_NOT_CREATED: "Not created",
                     CHUNK_OK: "OK",
                     CHUNK_CORRUPTED: "Corrupted",
                     CHUNK_WRONG_LOCATED: "Wrong located",
                     CHUNK_TOO_MANY_ENTITIES: "Too many entities",
                     CHUNK_SHARED_OFFSET: "Sharing offset",
                     CHUNK_MISSING_ENTITIES_TAG: "Missing Entities tag"
                     }

# arguments used in the options
CHUNK_PROBLEMS_ARGS = {CHUNK_CORRUPTED: 'corrupted',
                       CHUNK_WRONG_LOCATED: 'wrong-located',
                       CHUNK_TOO_MANY_ENTITIES: 'entities',
                       CHUNK_SHARED_OFFSET: 'shared-offset',
                       CHUNK_MISSING_ENTITIES_TAG: 'missing_tag'
                       }

# used in some places where there is less space
CHUNK_PROBLEMS_ABBR = {CHUNK_CORRUPTED: 'c',
                       CHUNK_WRONG_LOCATED: 'w',
                       CHUNK_TOO_MANY_ENTITIES: 'tme',
                       CHUNK_SHARED_OFFSET: 'so',
                       CHUNK_MISSING_ENTITIES_TAG: 'mt'
                       }

# Dictionary with possible solutions for the chunks problems,
# used to create options dynamically
# The possible solutions right now are:
CHUNK_SOLUTION_REMOVE = 51
CHUNK_SOLUTION_REPLACE = 52
CHUNK_SOLUTION_REMOVE_ENTITIES = 53
CHUNK_SOLUTION_RELOCATE_USING_DATA = 54

CHUNK_PROBLEMS_SOLUTIONS = {CHUNK_CORRUPTED: [CHUNK_SOLUTION_REMOVE, CHUNK_SOLUTION_REPLACE],
                       CHUNK_WRONG_LOCATED: [CHUNK_SOLUTION_REMOVE, CHUNK_SOLUTION_REPLACE, CHUNK_SOLUTION_RELOCATE_USING_DATA],
                       CHUNK_TOO_MANY_ENTITIES: [CHUNK_SOLUTION_REMOVE_ENTITIES, CHUNK_SOLUTION_REPLACE],
                       CHUNK_SHARED_OFFSET: [CHUNK_SOLUTION_REMOVE, CHUNK_SOLUTION_REPLACE],
                       CHUNK_MISSING_ENTITIES_TAG: [CHUNK_SOLUTION_REMOVE, CHUNK_SOLUTION_REPLACE]}

# chunk problems that can be fixed (so they don't need to be removed or replaced)
FIXABLE_CHUNK_PROBLEMS = [CHUNK_CORRUPTED, CHUNK_MISSING_ENTITIES_TAG, CHUNK_WRONG_LOCATED]

# list with problem, status-text, problem arg tuples
CHUNK_PROBLEMS_ITERATOR = []
for problem in CHUNK_PROBLEMS:
    CHUNK_PROBLEMS_ITERATOR.append((problem,
                                    CHUNK_STATUS_TEXT[problem],
                                    CHUNK_PROBLEMS_ARGS[problem]))

# Used to know where to look in a chunk status tuple
TUPLE_NUM_ENTITIES = 0
TUPLE_STATUS = 1




# ---------------
# Region related:
# ---------------
# Used to mark the status of region files:
REGION_OK = 100
REGION_TOO_SMALL = 101
REGION_UNREADABLE = 102
REGION_UNREADABLE_PERMISSION_ERROR = 103

# Region statuses
REGION_STATUSES = [REGION_OK,
                   REGION_TOO_SMALL,
                   REGION_UNREADABLE,
                   REGION_UNREADABLE_PERMISSION_ERROR]

# Text describing each region status used to list all the problem at the end of the scan
REGION_STATUS_TEXT = {REGION_OK: "OK",
                      REGION_TOO_SMALL: "Too small",
                      REGION_UNREADABLE: "Unreadable IOError",
                      # This status differentiates IOError from a file that you don't have permission to access
                      # TODO: It would be better to open region files only in write mode when needed
                      REGION_UNREADABLE_PERMISSION_ERROR: "Permission error"
                      }

# Status that are considered problems
REGION_PROBLEMS = [REGION_TOO_SMALL,
                   REGION_UNREADABLE,
                   REGION_UNREADABLE_PERMISSION_ERROR]

# arguments used in the options
REGION_PROBLEMS_ARGS = {REGION_TOO_SMALL: 'too_small',
                        REGION_UNREADABLE: 'unreadable',
                        REGION_UNREADABLE_PERMISSION_ERROR: 'permission_error'
                        }

# used in some places where there is less space
REGION_PROBLEMS_ABBR = {REGION_TOO_SMALL: 'ts',
                        REGION_UNREADABLE: 'ur',
                        REGION_UNREADABLE_PERMISSION_ERROR: 'pe'
                        }

# Dictionary with possible solutions for the region problems,
# used to create options dynamically
# The possible solutions right now are:
REGION_SOLUTION_REMOVE = 151
REGION_SOLUTION_REPLACE = 152

REGION_PROBLEMS_SOLUTIONS = {REGION_TOO_SMALL: [REGION_SOLUTION_REMOVE, REGION_SOLUTION_REPLACE]}

# list with problem, status-text, problem arg tuples
REGION_PROBLEMS_ITERATOR = []
for problem in REGION_PROBLEMS:
    try:
        REGION_PROBLEMS_ITERATOR.append((problem,
                                         REGION_STATUS_TEXT[problem],
                                         REGION_PROBLEMS_ARGS[problem]))
    except KeyError:
        pass



# ------------------
# Data file related:
# ------------------
# Used to mark the status of data files:
DATAFILE_OK = 200
DATAFILE_UNREADABLE = 201

# Data files statuses
DATAFILE_STATUSES = [DATAFILE_OK,
                     DATAFILE_UNREADABLE]

# Status that are considered problems
DATAFILE_PROBLEMS = [DATAFILE_UNREADABLE]

# Text describing each chunk status
DATAFILE_STATUS_TEXT = {DATAFILE_OK: "OK",
                        DATAFILE_UNREADABLE: "The data file cannot be read"
                        }

# arguments used in the options
DATAFILE_PROBLEMS_ARGS = {DATAFILE_OK: 'OK',
                          DATAFILE_UNREADABLE: 'unreadable'
                          }

# used in some places where there is less space
DATAFILE_PROBLEM_ABBR = {DATAFILE_OK: 'ok',
                         DATAFILE_UNREADABLE: 'ur'
                         }

# Dictionary with possible solutions for the chunks problems,
# used to create options dynamically
# The possible solutions right now are:
DATAFILE_SOLUTION_REMOVE = 251

DATAFILE_PROBLEMS_SOLUTIONS = {DATAFILE_UNREADABLE: [DATAFILE_SOLUTION_REMOVE]}

# list with problem, status-text, problem arg tuples
DATAFILE_PROBLEMS_ITERATOR = []
for problem in DATAFILE_PROBLEMS:
    DATAFILE_PROBLEMS_ITERATOR.append((problem,
                                       DATAFILE_STATUS_TEXT[problem],
                                       DATAFILE_PROBLEMS_ARGS[problem]))

CHUNK_PROBLEMS_ITERATOR = []
for problem in CHUNK_PROBLEMS:
    CHUNK_PROBLEMS_ITERATOR.append((problem,
                                    CHUNK_STATUS_TEXT[problem],
                                    CHUNK_PROBLEMS_ARGS[problem]))

# Dimension names:
DIMENSION_NAMES = {"": "Overworld",
                   "DIM1": "The End",
                   "DIM-1": "Nether"
                   }

# Region files types
LEVEL_DIR = "region"
POI_DIR = "poi"
ENTITIES_DIR = "entities"
REGION_TYPES_NAMES = {LEVEL_DIR: ("level/region", "Level/Region"),
                      POI_DIR: ("POIs", "POIs"),
                      ENTITIES_DIR: ("entities", "Entities" )
                      }

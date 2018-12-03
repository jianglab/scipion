#!/usr/bin/env python

"""
This script will simply create symbolic links from files in an input
folder. The links will be created in an output folder and every some
time the last link will be 'touched' simulating an image that is being
acquired by the microscope.
"""

import sys, os
import time
from glob import glob

import pyworkflow.utils as pwutils


def usage(error):
    print """
    ERROR: %s
    
    Usage: simulate_acquisition.py INPUT_PATTERN OUTPUT_FOLDER TIME
        INPUT_PATTERN: input pattern matching input files.
        OUTPUT_FOLDER: where to create the output links.
        [GAIN_PATTERN]: gain file will be linked at beginning
        [DELAY, default 30]: delay in seconds between file appearance
    """ % error
    sys.exit(1)    


if not len(sys.argv) in (3,4,5):
    usage("Incorrect number of input parameters")

inputPattern = sys.argv[1]
outputDir = sys.argv[2]
if len(sys.argv) == 4:
    try:
        delay = int(sys.argv[3])
        gain = None
    except Exception:
        gain = sys.argv[3]
        delay = 30
elif len(sys.argv) == 5:
    try:
        delay = int(sys.argv[3])
        gain = sys.argv[4]
    except Exception:
        try:
            gain = sys.argv[3]
            delay = int(sys.argv[4])
        except:
            usage("DELAY must be an integer.")
else:
    delay = 30
    gain = None

inputFiles = glob(pwutils.expandPattern(inputPattern))
inputFiles.sort()
if gain is not None:
    gain = glob(pwutils.expandPattern(gain))
    lenGain = len(gain)
    if lenGain > 1:
        usage("The GAIN_PATTERN must match with only one file (%d find)."
              % lenGain)
    elif lenGain == 0:
        usage("No file found matching the GAIN_PATTERN")
    else:
        gain = gain[0]
        print "Gain path: ", gain
print "Input pattern: ", inputPattern
# print "Input files: ", inputFiles
print "Delay: ", str(delay), " seconds."

print "Cleaning output directory: ", outputDir
pwutils.cleanPath(outputDir)
pwutils.makePath(outputDir)



aTime = int(delay)
n = 5
t = aTime / n
# print "t=%s" % aTime

if gain is not None:
    outputPath = os.path.join(outputDir, os.path.basename(gain))
    print "Linking %s -> %s" % (outputPath, gain)
    pwutils.cleanPath(outputPath)
    pwutils.createAbsLink(gain, outputPath)

for f in inputFiles:
    outputPath = os.path.join(outputDir, os.path.basename(f))
    print "Linking %s -> %s" % (outputPath, f)

    for i in range(n):
        open(outputPath, 'w').close()
        time.sleep(t)
    pwutils.cleanPath(outputPath)
    pwutils.createAbsLink(f, outputPath)

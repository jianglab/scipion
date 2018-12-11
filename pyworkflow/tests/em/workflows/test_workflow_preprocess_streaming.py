# ***************************************************************************
# *
# * Authors:     David Maluenda (dmaluenda@cnb.csic.es) [1]
# *
# * [1] Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# ***************************************************************************/

# System imports
import shutil
import sys
import time
import os
from glob import glob
import threading
import socket

# Scipion imports
import pyworkflow as pw
import pyworkflow.utils as pwutils
from pyworkflow.object import Pointer
from pyworkflow.protocol.constants import LEVEL_ADVANCED
from pyworkflow.tests import BaseTest, setupTestProject, DataSet
from pyworkflow.em import ImageHandler
from pyworkflow.protocol import getProtocolFromDb
from pyworkflow.em.protocol import (ProtImportMovies, ProtMonitorSummary,
                                    ProtImportMicrographs, ProtImportAverages,
                                    ProtSubSet, ProtUnionSet, ProtUserSubSet,
                                    ProtExtractCoords)

# Plugin imports
ProtMotionCorr = pwutils.importFromPlugin('motioncorr.protocols', 'ProtMotionCorr')

ProtCTFFind = pwutils.importFromPlugin('grigoriefflab.protocols', 'ProtCTFFind')

ProtGctf = pwutils.importFromPlugin('gctf.protocols', 'ProtGctf')

DogPickerProtPicking = pwutils.importFromPlugin('appion.protocols', 'DogPickerProtPicking')

SparxGaussianProtPicking = pwutils.importFromPlugin('eman2.protocols', 'SparxGaussianProtPicking')
EmanProtInitModel = pwutils.importFromPlugin('eman2.protocols', 'EmanProtInitModel')

# ProtRelion2Autopick = pwutils.importFromPlugin('relion.protocols', 'ProtRelion2Autopick')
# ProtRelionExtractParticles = pwutils.importFromPlugin('relion.protocols', 'ProtRelionExtractParticles')
ProtRelionClassify2D = pwutils.importFromPlugin('relion.protocols', 'ProtRelionClassify2D')

try:
    from xmipp3.protocols import (XmippProtOFAlignment, XmippProtMovieGain,
                                  XmippProtMovieMaxShift, XmippProtCTFMicrographs,
                                  XmippProtMovieCorr, XmippProtCTFConsensus,
                                  XmippProtPreprocessMicrographs,
                                  XmippProtParticlePicking, XmippParticlePickingAutomatic,
                                  XmippProtConsensusPicking, XmippProtCL2D,
                                  XmippProtExtractParticles, XmippProtTriggerData,
                                  XmippProtEliminateEmptyParticles,
                                  XmippProtScreenParticles,
                                  XmippProtReconstructSignificant, XmippProtRansac,
                                  XmippProtAlignVolume, XmippProtReconstructSwarm,
                                  XmippProtStrGpuCrrSimple, XmippProtCropResizeVolumes,
                                  XmippProtEliminateEmptyClasses)
except Exception as exc:
     pwutils.pluginNotFound('xmipp', errorMsg=exc)




def setExtendedInput(protDotInput, lastProt, extended):
    if isinstance(lastProt, list):
        for idx, prot in enumerate(lastProt):
            inputPointer = Pointer(prot, extended=extended[idx])
            protDotInput.append(inputPointer)
    else:
        protDotInput.set(lastProt)
        protDotInput.setExtended(extended)

confDict = {}

# Form:   --------------------------------------------- #
projName = 'TestPreprocessStreamingWorkflow'  # do NOT change!!
confDict['MOTIONCOR2'] = -1 if ProtMotionCorr is not None else -1
confDict['GCTF'] = -1 if ProtGctf is not None else -1
confDict['CRYOLO'] = 1  # if ProtCryolo is not None else -1
confDict['RELION'] = -1 if ProtRelionClassify2D is not None else -1
confDict['GL2D'] = -1
confDict['FRAMES'] = [1, 0]
confDict['DOSE0'] = 0
confDict['DOSEF'] = 0
confDict['OPTICAL_FLOW'] = False
confDict['PARTSIZE'] = int(80*3.54)  # in A
confDict['MICS2PICK'] = 3
confDict['SYMGROUP'] = 'd2'
# ----------------------------------------------------- #

# Conf.: ---------------------------------------------- #
# path/*.mrc (do NOT use ~ for home) or (datasetName, pattern):
depositionPattern = ('relion13_tutorial', 'betagal/Micrographs/*mrcs')  #  "/path/to/the/deposition/folder/*.mrcs"  #
schedule = True
confDict['PATTERN'] = '*.mrcs'
confDict['AMP_CONTR'] = 0.1
confDict['SPH_AB'] = 2.
confDict['VOL_KV'] = 300
confDict['SAMPLING'] = 3.54
confDict['TIMEOUT'] = 1*60
confDict['blackOnWhite'] = True
confDict['highCPUusage'] = 32
confDict['partsToClass'] = 2000
# ----------------------------------------------------- #


class TestPreprocessStreamingWorkflow(BaseTest):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.isTest = type(depositionPattern) == tuple
        if cls.isTest:
            cls.ds = DataSet(depositionPattern[0], depositionPattern[0], '')
            cls.ds = DataSet.getDataSet(depositionPattern[0])
        cls.importThread = threading.Thread(target=cls._createInputLinks)
        cls.importThread.start()
        # Wait until the first link is created
        time.sleep(5)

    @classmethod
    def _createInputLinks(cls):
        # Create a test folder path
        pattern = cls.ds.getFile(depositionPattern[1]) \
                    if cls.isTest else depositionPattern

        files = glob(pattern)

        # the amount of input data is defined here
        nFiles = len(files)

        assert nFiles > 0, "No files found matching '%s'" % pattern

        for i in range(nFiles):
            # Loop over the number of input movies if we want more for testing
            f = files[i % nFiles]
            _, cls.ext = os.path.splitext(f)
            moviePath = cls.proj.getTmpPath('movie%06d%s' % (i + 1, cls.ext))
            pwutils.createAbsLink(f, moviePath)
            time.sleep(confDict['TIMEOUT'])

    # def _registerProt(self, prot, output=None, monitor=True, wait=True):
    #     if schedule:
    #         self.proj.saveProtocol(prot)
    #     else:
    #         self.proj.launchProtocol(prot, wait=False)
    #         if wait:
    #             self._waitOutput(prot, output)
    #     if monitor and output is not None:
    #         self.summaryList.append(prot)
    #         self.summaryExt.append(output)

    # def _waitOutput(self, prot, outputAttributeName, timeout=10):
    #     """ Wait until the output is being generated by the protocol. """
    #
    #     def _loadProt():
    #         # Load the last version of the protocol from its own database
    #         prot2 = getProtocolFromDb(prot.getProject().path,
    #                                   prot.getDbPath(),
    #                                   prot.getObjId())
    #         # Close DB connections
    #         prot2.getProject().closeMapper()
    #         prot2.closeMappers()
    #         return prot2
    #
    #     t0 = time.time()
    #     prot2 = _loadProt()
    #
    #     while not prot2.hasAttribute(outputAttributeName):
    #
    #         prot2 = _loadProt()
    #         if time.time() - t0 > timeout * 60:
    #             break
    #
    #     # Update the protocol instance to get latest changes
    #     self.proj._updateProtocol(prot)

    def test_pattern(self):

        from scripts.scipionbox_preprocess_workflow import preprocessWorkflow

        preprocessWorkflow(self.proj, os.path.abspath(self.proj.getTmpPath()), confDict)


        os.system('%s python %s %s &' % (pw.getScipionScript(),
                               pw.getScipionPath('scripts/schedule_project.py'),
                               projName))

        os.system('%s project %s &' % (pw.getScipionScript(), projName))



# if __name__ == "__main__":
#

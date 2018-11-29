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


# Form:   --------------------------------------------- #
projName = 'TestPreprocessStreamingWorkflow'  # do NOT change!!
gpuMotion = -1 if ProtMotionCorr is not None else -1
gpuGctf = -1 if ProtGctf is not None else -1
gpuCryolo = 1  # if ProtCryolo is not None else -1
gpuRelion = -1 if ProtRelionClassify2D is not None else -1
gpuGl2d = -1
frame1 = 1
frameN = 0
dose0 = 0
doseF = 0
doOF = False
partSize = int(80*3.54)  # in A
doManualPick = False
nMicsToPick = 1
symmGr = 'd2'
# ----------------------------------------------------- #

# Conf.: ---------------------------------------------- #
# path/*.mrc (do NOT use ~ for home) or (datasetName, pattern):
depositionPattern = ('relion13_tutorial', 'betagal/Micrographs/*mrcs')  #  "/path/to/the/deposition/folder/*.mrcs"  #
schedule = True
ampContr = 0.1
sphAberr = 2.
volKv = 300
sampRate = 3.54
TIMEOUT = 1*60
blackOnWhite = True
highCPUusage = 32
partsToClass = 2000
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
            time.sleep(TIMEOUT)

    def _registerProt(self, prot, output=None, monitor=True, wait=True):
        if schedule:
            self.proj.saveProtocol(prot)
        else:
            self.proj.launchProtocol(prot, wait=False)
            if wait:
                self._waitOutput(prot, output)
        if monitor and output is not None:
            self.summaryList.append(prot)
            self.summaryExt.append(output)

    def _waitOutput(self, prot, outputAttributeName, timeout=10):
        """ Wait until the output is being generated by the protocol. """

        def _loadProt():
            # Load the last version of the protocol from its own database
            prot2 = getProtocolFromDb(prot.getProject().path,
                                      prot.getDbPath(),
                                      prot.getObjId())
            # Close DB connections
            prot2.getProject().closeMapper()
            prot2.closeMappers()
            return prot2

        t0 = time.time()
        prot2 = _loadProt()

        while not prot2.hasAttribute(outputAttributeName):

            prot2 = _loadProt()
            if time.time() - t0 > timeout * 60:
                break

        # Update the protocol instance to get latest changes
        self.proj._updateProtocol(prot)

    def test_pattern(self):
        self.summaryList = []
        self.summaryExt = []


        # ***********   MOVIES   ***********************************************
        doDose = False if doseF == 0 else True
        # ----------- IMPORT MOVIES -------------------
        protImport = self.newProtocol(ProtImportMovies,
                                      objLabel='import movies',
                                      importFrom=ProtImportMovies.IMPORT_FROM_FILES,
                                      filesPath=os.path.abspath(
                                          self.proj.getTmpPath()),
                                      filesPattern="movie*%s" % self.ext,
                                      amplitudeContrast=ampContr,
                                      sphericalAberration=sphAberr,
                                      voltage=volKv,
                                      samplingRate=sampRate,
                                      doseInitial=dose0,
                                      dosePerFrame=doseF,
                                      dataStreaming=True,
                                      timeout=TIMEOUT)
        self._registerProt(protImport, 'outputMovies')

        # ----------- MOVIE GAIN --------------------------
        protMG = self.newProtocol(XmippProtMovieGain,
                                  objLabel='Xmipp - movie gain',
                                  frameStep=20,
                                  movieStep=20,
                                  useExistingGainImage=False)
        setExtendedInput(protMG.inputMovies, protImport, 'outputMovies')
        self._registerProt(protMG, 'outputImages', wait=False)

        # ----------- MOTIONCOR ----------------------------
        if gpuMotion > -1:
            protMC = self.newProtocol(ProtMotionCorr,
                                      objLabel='MotionCor2 - movie align.',
                                      gpuList=str(gpuMotion),
                                      doApplyDoseFilter=doDose,
                                      patchX=9, patchY=9)
            setExtendedInput(protMC.inputMovies, protImport, 'outputMovies')
            self._registerProt(protMC, 'outputMovies')

            # ----------- MAX SHIFT -----------------------------
            protMax1 = self.newProtocol(XmippProtMovieMaxShift,
                                       objLabel='Xmipp - max shift')
            setExtendedInput(protMax1.inputMovies, protMC, 'outputMovies')
            self._registerProt(protMax1, 'outputMicrographs')

            protMax = protMax1

        else:
        # ----------- CORR ALIGN ----------------------------
            protCA = self.newProtocol(XmippProtMovieCorr,
                                      objLabel='Xmipp - corr. align.',
                                      alignFrame0=frame1,
                                      alignFrameN=frameN)
            setExtendedInput(protCA.inputMovies, protImport, 'outputMovies')
            self._registerProt(protCA, 'outputMovies')

        # ----------- MAX SHIFT -----------------------------
            protMax2 = self.newProtocol(XmippProtMovieMaxShift,
                                        objLabel='Xmipp - max shift',
                                        maxFrameShift=10,
                                        maxMovieShift=15)
            setExtendedInput(protMax2.inputMovies, protCA, 'outputMovies')
            self._registerProt(protMax2, 'outputMovies')

            protMax = protMax2

        # ----------- OF ALIGNMENT --------------------------
        if doOF:
            protOF = self.newProtocol(XmippProtOFAlignment,
                                      objLabel='Xmipp - OF align.',
                                      doApplyDoseFilter=doDose,
                                      applyDosePreAlign=False)  # -----------------------------------
            setExtendedInput(protOF.inputMovies, protMax, 'outputMovies')
            self._registerProt(protOF, 'outputMicrographs')

            alignedMicsLastProt = protOF
        else:
            alignedMicsLastProt = protMax


        # *********   CTF ESTIMATION   *****************************************

        # --------- CTF ESTIMATION 1 ---------------------------
        protCTF1 = self.newProtocol(XmippProtCTFMicrographs,
                                    objLabel='Xmipp - ctf estimation')
        setExtendedInput(protCTF1.inputMicrographs,
                         alignedMicsLastProt, 'outputMicrographs')
        self._registerProt(protCTF1, 'outputCTF', wait=False)

        # --------- CTF ESTIMATION 2 ---------------------------
        if gpuGctf>-1:
            protCTF2 = self.newProtocol(ProtGctf,
                                        objLabel='gCTF estimation',
                                        gpuList=str(gpuGctf))
            setExtendedInput(protCTF2.inputMicrographs,
                             alignedMicsLastProt, 'outputMicrographs')
            self._registerProt(protCTF2, 'outputCTF', wait=False, monitor=False)

        else:
            protCTF2 = self.newProtocol(ProtCTFFind,
                                        objLabel='GrigorieffLab - CTFfind')
            setExtendedInput(protCTF2.inputMicrographs,
                             alignedMicsLastProt, 'outputMicrographs')
            self._registerProt(protCTF2, 'outputCTF', wait=False, monitor=False)

        if not schedule:
            self._waitOutput(protCTF1, 'outputCTF')
            self._waitOutput(protCTF2, 'outputCTF')

        # --------- CTF CONSENSUS 1 ---------------------------
        protCTFs = self.newProtocol(XmippProtCTFConsensus,
                                    objLabel='Xmipp - CTF consensus',
                                    useDefocus=True,
                                    useAstigmatism=True,
                                    useResolution=True,
                                    resolution=17.0,
                                    useCritXmipp=True,
                                    calculateConsensus=True,
                                    minConsResol=15.0)
        setExtendedInput(protCTFs.inputCTF, protCTF1, 'outputCTF')
        setExtendedInput(protCTFs.inputCTF2, protCTF2, 'outputCTF')
        self._registerProt(protCTFs, 'outputMicrographs')


        # *************   PICKING   ********************************************
        # Resizing to a sampling rate larger than 3A/px
        downSampPreMics = sampRate / 3 if sampRate < 3 else 1
        # Fixing an even boxsize big enough: int(x/2+1)*2 = ceil(x/2)*2 = even!
        bxSize = int(partSize / sampRate / downSampPreMics / 2 + 1) * 2

        # --------- PREPROCESS MICS ---------------------------
        protPreMics = self.newProtocol(XmippProtPreprocessMicrographs,
                                   objLabel='Xmipp - preprocess Mics',
                                   doRemoveBadPix=True,
                                   doInvert=blackOnWhite,
                                   doDownsample=sampRate<3,
                                   downFactor=downSampPreMics)
        setExtendedInput(protPreMics.inputMicrographs,
                         protCTFs, 'outputMicrographs')
        self._registerProt(protPreMics, 'outputMicrographs', monitor=False)

        # --------- PARTICLE PICKING 1 ---------------------------
        protPP1 = self.newProtocol(SparxGaussianProtPicking,
                                   objLabel='Eman - Sparx auto-picking',
                                   boxSize=bxSize)
        setExtendedInput(protPP1.inputMicrographs, protPreMics, 'outputMicrographs')
        self._registerProt(protPP1, 'outputCoordinates', wait=False, monitor=False)

        # --------- PARTICLE PICKING 2 ---------------------------
        if gpuCryolo>-1:
            protPP2 = self.newProtocol(SparxGaussianProtPicking,  # ------------------- Put CrYolo here!!
                                       objLabel='Sphire - CrYolo auto-picking',
                                       # gpuList=str(gpuCryolo),
                                       boxSize=bxSize)
            setExtendedInput(protPP2.inputMicrographs, protPreMics, 'outputMicrographs')
            self._registerProt(protPP2, 'outputCoordinates', wait=False, monitor=False)

        if doManualPick:
            # -------- TRIGGER MANUAL-PICKER ---------------------------
            protTRIG0 = self.newProtocol(XmippProtTriggerData,
                                         objLabel='Xmipp - trigger some mics',
                                         outputSize=nMicsToPick,
                                         delay=30,
                                         allImages=False)
            setExtendedInput(protTRIG0.inputImages, protPreMics, 'outputMicrographs')
            self._registerProt(protTRIG0, 'outputMicrographs', monitor=False)

            # -------- XMIPP MANUAL-PICKER -------------------------
            protPPman = self.newProtocol(XmippProtParticlePicking,
                                         objLabel='Xmipp - manual picking',
                                         doInteractive=False)
            setExtendedInput(protPPman.inputMicrographs, protTRIG0, 'outputMicrographs')
            self._registerProt(protPPman, 'outputCoordinates', monitor=False)

            # -------- XMIPP AUTO-PICKING ---------------------------
            protPPauto = self.newProtocol(XmippParticlePickingAutomatic,
                                          objLabel='Xmipp - auto picking',
                                          xmippParticlePicking=protPPman,
                                          micsToPick=1  # other
                                          )
            protPPauto.addPrerequisites(protPPman.getObjId())
            setExtendedInput(protPPauto.inputMicrographs, protPreMics, 'outputMicrographs')
            self._registerProt(protPPauto, 'outputCoordinates', monitor=False)

        if not schedule:
            self._waitOutput(protPP1, 'outputCoordinates')
            # self._waitOutput(protPPauto, 'outputCoordinates')
        # --------- CONSENSUS PICKING AND -----------------------
        pickers = [protPP1]
        pickersOuts = ['outputCoordinates']
        if gpuCryolo > -1:
            pickers.append(protPP2)
            pickersOuts.append('outputCoordinates')
        if doManualPick:
            pickers.append(protPPauto)
            pickersOuts.append('outputCoordinates')

        if len(pickers) > 1:
            protCPand = self.newProtocol(XmippProtConsensusPicking,
                                      objLabel='Xmipp - consensus picking (AND)',
                                      consensus=-1,
                                      consensusRadius=0.1*bxSize)
            setExtendedInput(protCPand.inputCoordinates, pickers, pickersOuts)
            self._registerProt(protCPand, 'consensusCoordinates')

            # --------- CONSENSUS PICKING OR -----------------------
            protCPor = self.newProtocol(XmippProtConsensusPicking,
                                      objLabel='Xmipp - consensus picking (OR)',
                                      consensus=1,
                                      consensusRadius=0.1 * bxSize)

            setExtendedInput(protCPor.inputCoordinates, pickers, pickersOuts)
            self._registerProt(protCPor, 'consensusCoordinates')
            finalPicker = protCPor
            outputCoordsStr = 'consensusCoordinates'

            # --------- EXTRACT PARTICLES AND ----------------------
            protExtract = self.newProtocol(XmippProtExtractParticles,
                                           objLabel='Xmipp - extract particles (AND)',
                                           boxSize=bxSize,
                                           downsampleType=0,  # Same as picking
                                           doRemoveDust=True,
                                           doNormalize=True,
                                           doInvert=False,
                                           doFlip=True)
            setExtendedInput(protExtract.inputCoordinates,
                             protCPand, 'consensusCoordinates')
            # setExtendedInput(protExtract.inputMicrographs,
            #                  protPreMics, 'outputMicrographs')
            setExtendedInput(protExtract.ctfRelations, protCTF1, 'outputCTF')
            self._registerProt(protExtract, 'outputParticles')

        else:
            finalPicker = pickers[0]
            outputCoordsStr = pickersOuts[0]


        # ---------------------------------- OR/SINGLE PICKING BRANCH ----------

        # --------- EXTRACT PARTICLES OR ----------------------
        ORstr = ' (OR)' if len(pickers)>1 else ''
        protExtraOR = self.newProtocol(XmippProtExtractParticles,
                                       objLabel='Xmipp - extract particles%s'%ORstr,
                                       boxSize=bxSize,
                                       downsampleType=0,  # Same as picking
                                       doRemoveDust=True,
                                       doNormalize=True,
                                       doInvert=False,
                                       doFlip=True)
        setExtendedInput(protExtraOR.inputCoordinates,
                         finalPicker, outputCoordsStr)
        # setExtendedInput(protExtraOR.inputMicrographs,
        #                  protPreMics, 'outputMicrographs')
        setExtendedInput(protExtraOR.ctfRelations, protCTF1, 'outputCTF')
        self._registerProt(protExtraOR, 'outputParticles')


        # ***********   PROCESS PARTICLES   ************************************

        # --------- ELIM EMPTY PARTS OR ---------------------------
        protEEPor = self.newProtocol(XmippProtEliminateEmptyParticles,
                                     objLabel='Xmipp - Elim. empty part.%s'%ORstr,
                                     inputType=0,
                                     threshold=1.1)
        setExtendedInput(protEEPor.inputParticles, protExtraOR, 'outputParticles')
        self._registerProt(protEEPor, 'outputParticles')

        # --------- TRIGGER PARTS OR ---------------------------
        protTRIGor = self.newProtocol(XmippProtTriggerData,
                                      objLabel='Xmipp - trigger data to stats%s'%ORstr,
                                      outputSize=1000, delay=30,
                                      allImages=True,
                                      splitImages=False)
        setExtendedInput(protTRIGor.inputImages, protEEPor, 'outputParticles')
        self._registerProt(protTRIGor, 'outputParticles', monitor=False)

        # --------- SCREEN PARTS OR ---------------------------
        protSCRor = self.newProtocol(XmippProtScreenParticles,
                                     objLabel='Xmipp - Screen particles%s'%ORstr)
        protSCRor.autoParRejection.set(XmippProtScreenParticles.REJ_MAXZSCORE)
        protSCRor.autoParRejectionSSNR.set(XmippProtScreenParticles.REJ_PERCENTAGE_SSNR)
        protSCRor.autoParRejectionVar.set(XmippProtScreenParticles.REJ_VARIANCE)
        setExtendedInput(protSCRor.inputParticles, protTRIGor, 'outputParticles')
        self._registerProt(protSCRor, 'outputParticles')

        # --------- EXTRACT COORD ----------------------------
        protExtraC = self.newProtocol(ProtExtractCoords,
                                      objLabel='Scipion - extrac coord.')
        setExtendedInput(protExtraC.inputParticles, protSCRor, 'outputParticles')
        setExtendedInput(protExtraC.inputMicrographs, protPreMics, 'outputMicrographs')
        self._registerProt(protExtraC, 'outputCoordinates', monitor=False)

        # --------- EXTRACT FULL SIZE PART ------------------
        protExtraFull = self.newProtocol(XmippProtExtractParticles,
                                        objLabel='Xmipp - extract part. FULL SIZE',
                                        boxSize= int(partSize / sampRate)+1,
                                        downsampleType=1,  # other mics
                                        doRemoveDust=True,
                                        doNormalize=True,
                                        doInvert=blackOnWhite,  # maybe invert here bc the preprocess is skip
                                        doFlip=True)
        setExtendedInput(protExtraFull.inputCoordinates,
                         protExtraC, 'outputCoordinates')
        setExtendedInput(protExtraFull.inputMicrographs,
                         protCTFs, 'outputMicrographs')
        setExtendedInput(protExtraFull.ctfRelations, protCTFs, 'outputCTF')
        self._registerProt(protExtraFull, 'outputParticles')

        # ----------------------------- END OF OR/SINGLE PICKING BRANCH --------

        # ----------------------------- AND PICKING BRANCH ---------------------
        if len(pickers) < 2:  # if so, Elim. Empty and Screen are the same of above
            protSCR = protSCRor
        else:
            # --------- ELIM EMPTY PARTS AND ---------------------------
            protEEP = self.newProtocol(XmippProtEliminateEmptyParticles,
                                       objLabel='Xmipp - Elim. empty part. (AND)',
                                       inputType=0,
                                       threshold=1.1)
            setExtendedInput(protEEP.inputParticles, protExtract, 'outputParticles')
            self._registerProt(protEEP, 'outputParticles')

            # --------- TRIGGER PARTS AND  ---------------------------
            protTRIG = self.newProtocol(XmippProtTriggerData,
                                        objLabel='Xmipp - trigger data to stats (AND)',
                                        outputSize=1000, delay=30,
                                        allImages=True,
                                        splitImages=False)
            setExtendedInput(protTRIG.inputImages, protEEP, 'outputParticles')
            self._registerProt(protTRIG, 'outputParticles', monitor=False)

            # --------- SCREEN PARTS AND  ---------------------------
            protSCR = self.newProtocol(XmippProtScreenParticles,
                                       objLabel='Xmipp - screen particles (AND)')
            protSCR.autoParRejection.set(XmippProtScreenParticles.REJ_MAXZSCORE)
            protSCR.autoParRejectionSSNR.set(XmippProtScreenParticles.REJ_PERCENTAGE_SSNR)
            protSCR.autoParRejectionVar.set(XmippProtScreenParticles.REJ_VARIANCE)
            setExtendedInput(protSCR.inputParticles, protTRIG, 'outputParticles')
            self._registerProt(protSCR, 'outputParticles')


        # ************   CLASSIFY 2D   *****************************************

        # --------- TRIGGER PARTS ---------------------------
        protTRIG2 = self.newProtocol(XmippProtTriggerData,
                                     objLabel='Xmipp - trigger data to classify',
                                     outputSize=partsToClass, delay=30,
                                     allImages=False)
        setExtendedInput(protTRIG2.inputImages, protSCR, 'outputParticles')
        self._registerProt(protTRIG2, 'outputParticles', monitor=False)

        # --------- XMIPP CL2D ---------------------------
        protCL = self.newProtocol(XmippProtCL2D,
                                  objLabel='Xmipp - Cl2d',
                                  doCore=False,
                                  numberOfClasses=16,
                                  numberOfMpi=int(highCPUusage/2))
        setExtendedInput(protCL.inputParticles, protTRIG2, 'outputParticles')
        self._registerProt(protCL, 'outputClasses', wait=False)

        # --------- AUTO CLASS SELECTION I---------------------------
        protCLSEL1 = self.newProtocol(XmippProtEliminateEmptyClasses,
                                     objLabel='Xmipp - Auto class selection I',
                                     threshold=8.0)
        setExtendedInput(protCLSEL1.inputClasses, protCL, 'outputClasses')
        self._registerProt(protCLSEL1, 'outputAverages')

        # --------- Relion 2D classify ---------------------------
        protCL2 = self.newProtocol(ProtRelionClassify2D,
                                   objLabel='Relion - 2D classifying',
                                   useGpu=gpuRelion>-1,
                                   gpuList=str(gpuRelion),
                                   numberOfClasses=16,
                                   numberOfMpi=int(highCPUusage/2))
        setExtendedInput(protCL2.inputParticles, protTRIG2, 'outputParticles')
        self._registerProt(protCL2, 'outputClasses', wait=False)

        # --------- AUTO CLASS SELECTION I---------------------------
        protCLSEL2 = self.newProtocol(XmippProtEliminateEmptyClasses,
                                     objLabel='Xmipp - Auto class selection II',
                                     threshold=8.0)
        setExtendedInput(protCLSEL2.inputClasses, protCL2, 'outputClasses')
        self._registerProt(protCLSEL2, 'outputAverages')

        # if not schedule:
        #     self._waitOutput(protCL, 'outputClasses')
        # # --------- CONVERT TO AVERAGES 1---------------------------
        # protAVER1 = self.newProtocol(ProtUserSubSet,
        #                              objLabel='Classes -> Averages I',
        #                              outputClassName="SetOfAverages",
        #                              sqliteFile=os.path.join(protCL._getPath(),
        #                                                      "classes2D.sqlite,")
        #                              )
        # setExtendedInput(protAVER1.inputObject, protCL, 'outputClasses')
        # self._registerProt(protAVER1, 'outputRepresentatives', monitor=False)
        #
        # if not schedule:
        #     self._waitOutput(protCL2, 'outputClasses')
        # # --------- CONVERT TO AVERAGES 2---------------------------
        # protAVER2 = self.newProtocol(ProtUserSubSet,
        #                              objLabel='Classes -> Averages II',
        #                              outputClassName="SetOfAverages",
        #                              sqliteFile=os.path.join(protCL2._getPath(),
        #                                                      "classes2D.sqlite,")
        #                              )
        # setExtendedInput(protAVER2.inputObject, protCL2, 'outputClasses')
        # self._registerProt(protAVER2, 'outputRepresentatives', monitor=False)

        # --------- JOIN SETS ---------------------------
        protJOIN = self.newProtocol(ProtUnionSet, objLabel='Scipion - Join sets')
        setExtendedInput(protJOIN.inputSets,
                         [protCLSEL1, protCLSEL2],
                         ['outputAverages', 'outputAverages'])
        self._registerProt(protJOIN, 'outputSet', monitor=False)

        # # --------- AUTO CLASS SELECTION ---------------------------
        # protCLSEL = self.newProtocol(XmippProtEliminateEmptyClasses,
        #                              objLabel='Xmipp - Auto class selection',
        #                              inputType=1,
        #                              threshold=8.0)
        # setExtendedInput(protCLSEL.inputClasses, protJOIN, 'outputSet')
        # self._registerProt(protCLSEL, 'outputAverages')


        # ***************   INITIAL VOLUME   ***********************************

        # --------- EMAN INIT VOLUME ---------------------------
        protINITVOL = self.newProtocol(EmanProtInitModel,
                                       objLabel='Eman - Initial vol',
                                       symmetryGroup=symmGr,
                                       numberOfThreads=int(highCPUusage/4))
        setExtendedInput(protINITVOL.inputSet, protJOIN, 'outputSet')
        self._registerProt(protINITVOL)

        # --------- RECONSTRUCT SIGNIFICANT ---------------------------
        protSIG = self.newProtocol(XmippProtReconstructSignificant,
                                   objLabel='Xmipp - Recons. significant',
                                   symmetryGroup=symmGr,
                                   numberOfMpi=int(highCPUusage/2))
        setExtendedInput(protSIG.inputSet, protJOIN, 'outputSet')
        self._registerProt(protSIG)

        # --------- RECONSTRUCT RANSAC ---------------------------
        protRAN = self.newProtocol(XmippProtRansac,
                                   objLabel='Xmipp - Ransac significant',
                                   symmetryGroup=symmGr,
                                   numberOfThreads=int(highCPUusage/4))
        setExtendedInput(protRAN.inputSet, protJOIN, 'outputSet')
        self._registerProt(protRAN)

        #  FIXME: ADD WAIT IF NOT SCHEDULE
        # --------- CREATING AN ALIGNED SET OF VOLUMES -----------
        protAVOL = self.newProtocol(XmippProtAlignVolume,
                                    objLabel='Xmipp - Join/Align volumes',
                                    numberOfThreads=highCPUusage)
        setExtendedInput(protAVOL.inputReference, protSIG, 'outputVolume')
        setExtendedInput(protAVOL.inputVolumes,
                         [protINITVOL, protRAN, protSIG],
                         ['outputVolumes', 'outputVolumes', 'outputVolume'])
        self._registerProt(protAVOL, 'outputVolumes', monitor=False)

        # --------- SWARM CONSENSUS INITIAL VOLUME ---------------
        protSWARM = self.newProtocol(XmippProtReconstructSwarm,
                                     objLabel='Xmipp - Swarm init. vol.',
                                     symmetryGroup=symmGr,
                                     numberOfMpi=highCPUusage)
        setExtendedInput(protSWARM.inputParticles, protTRIG2, 'outputParticles')
        setExtendedInput(protSWARM.inputVolumes, protAVOL, 'outputVolumes')
        self._registerProt(protSWARM, 'outputVolume')

        # --------- RESIZE THE INITIAL VOL TO FULL SIZE ----------
        protVOLfull = self.newProtocol(XmippProtCropResizeVolumes,
                                       objLabel='Resize volume - FULL FIZE',
                                       doResize=True,
                                       resizeOption=0,  # fix samplig rate
                                       resizeSamplingRate=sampRate)
        setExtendedInput(protVOLfull.inputVolumes, protSWARM, 'outputVolume')
        self._registerProt(protVOLfull, 'outputVolumes', monitor=False)


        # ************   FINAL PROTOCOLS   *************************************

        # --------- GL2D in streaming --------------------
        if gpuGl2d>-1:
            protGL2D = self.newProtocol(XmippProtStrGpuCrrSimple,
                                        objLabel='Xmipp - GL2D static',
                                        gpuList=str(gpuGl2d))
            setExtendedInput(protGL2D.inputRefs, protJOIN, 'outputSet')
            setExtendedInput(protGL2D.inputParticles, protSCRor, 'outputParticles')
            self._registerProt(protGL2D, 'outputClasses')

        # --------- SUMMARY MONITOR -----------------------
        protMonitor = self.newProtocol(ProtMonitorSummary,
                                  objLabel='Scipion - Summary Monitor')
        setExtendedInput(protMonitor.inputProtocols,
                         self.summaryList, self.summaryExt)
        self._registerProt(protMonitor, 'output***', wait=False, monitor=False)

        os.system('%s python %s %s &' % (pw.getScipionScript(),
                               pw.getScipionPath('scripts/schedule_project.py'),
                               projName))

        os.system('%s project %s &' % (pw.getScipionScript(), projName))

        import time
        time.sleep(10)


# if __name__ == "__main__":
#

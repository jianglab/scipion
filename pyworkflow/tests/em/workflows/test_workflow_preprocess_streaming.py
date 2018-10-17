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

ProtRelion2Autopick = pwutils.importFromPlugin('relion.protocols', 'ProtRelion2Autopick')
ProtRelionExtractParticles = pwutils.importFromPlugin('relion.protocols', 'ProtRelionExtractParticles')
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
                                  XmippProtStrGpuCrrSimple, XmippProtCropResizeVolumes)
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
hasCUDA = False
frame1 = 1
frameN = 0
doOF = False
partSize = int(80*3.54)  # in A
nMicsToPick = 3
symmGr = 'd2'
# ----------------------------------------------------- #

# Conf.: ---------------------------------------------- #
projName = 'TestPreprocessStreamingWorkflow'
schedule = True
ampContr = 0.1
sphAberr = 2.
volKv = 300
sampRate = 3.54
TIMEOUT = 5*60
blackOnWhite = True
# ----------------------------------------------------- #


class TestPreprocessStreamingWorkflow(BaseTest):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        # if os.path.exists(cls.proj.path):
        #     print("\n >>> WARNING: 'cls.proj.path' already exists,\n"
        #             "     do you want to overwrite it? >>> (YES/no) <<< ")
        #     yesno = raw_input()
        #     if yesno.lower() == 'no':
        #         sys.exit(0)
        #     else:
        #         shutil.rmtree(cls.proj.path)
        cls.ds = DataSet('relion13_tutorial', 'relion13_tutorial', '')
        cls.ds = DataSet.getDataSet('relion13_tutorial')
        cls.importThread = threading.Thread(target=cls._createInputLinks)
        cls.importThread.start()
        # Wait until the first link is created
        time.sleep(5)

    @classmethod
    def _createInputLinks(cls):
        # Create a test folder path
        pattern = cls.ds.getFile('betagal/Micrographs/*mrcs')
        files = glob(pattern)

        # the amount of input data is defined here
        nFiles = len(files)

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
            if wait is not None:
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
        if hasCUDA:
            protMC = self.newProtocol(ProtMotionCorr,
                                      objLabel='MotionCor2 - movie align.')
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
                                      doSaveMovie=False,
                                      alignFrame0=3,            # ------------ ASK to COSS ----------
                                      alignFrameN=10,
                                      useAlignToSum=True,
                                      useAlignment=False,
                                      doApplyDoseFilter=False)  # -----------------------------------
            setExtendedInput(protOF.inputMovies, protMax, 'outputMovies')
            self._registerProt(protOF, 'outputMicrographs')

            alignedMicsLastProt = protOF
        else:
            alignedMicsLastProt = protMax

        # --------- CTF ESTIMATION 1 ---------------------------
        protCTF1 = self.newProtocol(XmippProtCTFMicrographs,
                                    objLabel='Xmipp - ctf estimation')
        setExtendedInput(protCTF1.inputMicrographs,
                         alignedMicsLastProt, 'outputMicrographs')
        self._registerProt(protCTF1, 'outputCTF', wait=False)

        # --------- CTF ESTIMATION 2 ---------------------------
        if not hasCUDA:
            protCTF2 = self.newProtocol(ProtCTFFind,
                                        objLabel='GrigorieffLab - CTFfind')
            setExtendedInput(protCTF2.inputMicrographs,
                             alignedMicsLastProt, 'outputMicrographs')
            self._registerProt(protCTF2, 'outputCTF', wait=False, monitor=False)

        # --------- CTF ESTIMATION 3 ---------------------------
        else:
            protCTF2 = self.newProtocol(ProtGctf,
                                        objLabel='gCTF estimation')
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

        # --------- PREPROCESS MICS ---------------------------
        downSampPreMics = sampRate/3 if sampRate<3 else 1  # desired samp. rate > 3A/px
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
        bxSize = int(partSize/sampRate/downSampPreMics)
        protPP1 = self.newProtocol(SparxGaussianProtPicking,
                                  objLabel='Eman - Sparx auto-picking',
                                  boxSize=bxSize)
        setExtendedInput(protPP1.inputMicrographs, protPreMics, 'outputMicrographs')
        self._registerProt(protPP1, 'outputCoordinates', wait=False, monitor=False)

        # --------- PARTICLE PICKING 2 ---------------------------
        # protPP2 = self.newProtocol(DogPickerProtPicking,  # ------------------- Put here CrYolo!!
        #                           objLabel='Sphire - CrYolo auto-picking',
        #                           diameter=partSize)
        # setExtendedInput(protPP2.inputMicrographs, protPreMics, 'outputMicrographs')
        # self._registerProt(protPP2, 'outputCoordinates', wait=False, monitor=False)

        # --------- TRIGGER MANUAL-PICKER ---------------------------
        protTRIG0 = self.newProtocol(XmippProtTriggerData,
                                     objLabel='Xmipp - trigger some mics',
                                     outputSize=nMicsToPick,
                                     delay=30,
                                     allParticles=False)
        setExtendedInput(protTRIG0.inputImages, protPreMics, 'outputMicrographs')
        self._registerProt(protTRIG0, 'outputMicrographs', monitor=False)

        # --------- XMIPP MANUAL-PICKER -------------------------
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
            # self._waitOutput(protPP2, 'outputCoordinates')
        # --------- CONSENSUS PICKING AND -----------------------
        protCPand = self.newProtocol(XmippProtConsensusPicking,
                                  objLabel='Xmipp - consensus picking AND',
                                  consensus=-1,
                                  consensusRadius=0.1*bxSize)
        setExtendedInput(protCPand.inputCoordinates,
                         [protPP1, protPPauto], #protPP2,
                         ['outputCoordinates', 'outputCoordinates'])#,
                          #'outputCoordinates'])
        self._registerProt(protCPand, 'consensusCoordinates')

        # --------- CONSENSUS PICKING OR -----------------------
        protCPor = self.newProtocol(XmippProtConsensusPicking,
                                  objLabel='Xmipp - consensus picking OR',
                                  consensus=1,
                                  consensusRadius=0.1 * bxSize)
        setExtendedInput(protCPor.inputCoordinates,
                         [protPP1, protPPauto], #protPP2,
                         ['outputCoordinates', 'outputCoordinates'])#,
                          #'outputCoordinates'])
        self._registerProt(protCPor, 'consensusCoordinates')

        # --------- EXTRACT PARTICLES AND ----------------------
        protExtract = self.newProtocol(XmippProtExtractParticles,
                                       objLabel='Xmipp - extract particles AND',
                                       boxSize=bxSize,
                                       downsampleType=0,  # Same as picking
                                       doRemoveDust=True,
                                       doNormalize=True,
                                       doInvert=False,
                                       doFlip=True)
        setExtendedInput(protExtract.inputCoordinates,
                         protCPand, 'consensusCoordinates')
        # setExtendedInput(protExtract.inputMicrographs,
        #                  alignedMicsLastProt, 'outputMicrographs')
        setExtendedInput(protExtract.ctfRelations, protCTFs, 'outputCTF')
        self._registerProt(protExtract, 'outputParticles')

        # --------- EXTRACT PARTICLES OR ----------------------
        protExtraOR = self.newProtocol(XmippProtExtractParticles,
                                       objLabel='Xmipp - extract particles OR',
                                       boxSize=bxSize,
                                       downsampleType=0,  # Same as picking
                                       doRemoveDust=True,
                                       doNormalize=True,
                                       doInvert=False,
                                       doFlip=True)
        setExtendedInput(protExtraOR.inputCoordinates,
                         protCPor, 'consensusCoordinates')
        # setExtendedInput(protExtraOR.inputMicrographs,
        #                  alignedMicsLastProt, 'outputMicrographs')
        setExtendedInput(protExtraOR.ctfRelations, protCTFs, 'outputCTF')
        self._registerProt(protExtraOR, 'outputParticles')

        # --------- ELIM EMPTY PARTS OR ---------------------------
        protEEPor = self.newProtocol(XmippProtEliminateEmptyParticles,
                                     objLabel='Xmipp - Elim. empty part.',
                                     inputType=0,
                                     threshold=1.1)
        setExtendedInput(protEEPor.inputParticles, protExtraOR, 'outputParticles')
        self._registerProt(protEEPor, 'outputParticles')

        # --------- TRIGGER PARTS OR ---------------------------
        protTRIGor = self.newProtocol(XmippProtTriggerData,
                                      objLabel='Xmipp - trigger data to stats',
                                      outputSize=1000, delay=30,
                                      allParticles=True,
                                      splitParticles=False)
        setExtendedInput(protTRIGor.inputImages, protEEPor, 'outputParticles')
        self._registerProt(protTRIGor, 'outputParticles', monitor=False)

        # --------- SCREEN PARTS OR ---------------------------
        protSCRor = self.newProtocol(XmippProtScreenParticles,
                                     objLabel='Xmipp - Screen particles')
        protSCRor.autoParRejection.set(XmippProtScreenParticles.REJ_MAXZSCORE)
        protSCRor.autoParRejectionSSNR.set(XmippProtScreenParticles.REJ_PERCENTAGE_SSNR)
        protSCRor.autoParRejectionVar.set(XmippProtScreenParticles.REJ_VARIANCE)
        setExtendedInput(protSCRor.inputParticles, protTRIGor, 'outputParticles')
        self._registerProt(protSCRor, 'outputParticles')

        # --------- EXTRACT COORD ----------------------------
        protExtraC = self.newProtocol(ProtExtractCoords,
                                      objLabel='Scipion - extrac coord.')
        setExtendedInput(protExtraC.inputParticles, protSCRor, 'outputParticles')
        setExtendedInput(protExtraC.inputMicrographs, protCTFs, 'outputMicrographs')
        self._registerProt(protExtraC, 'outputCoordinates', monitor=False)

        # --------- EXTRACT FULL SIZE PART ------------------
        protExtraFull = self.newProtocol(XmippProtExtractParticles,
                                        objLabel='Xmipp - extract part. FULL SIZE',
                                        boxSize= int(bxSize * downSampPreMics),
                                        downsampleType=1,  # other mics
                                        doRemoveDust=True,
                                        doNormalize=True,
                                        doInvert=blackOnWhite,  # maybe invert here bc the preprocess is skip
                                        doFlip=True)
        setExtendedInput(protExtraFull.inputCoordinates,
                         protExtraC, 'consensusCoordinates')
        setExtendedInput(protExtraFull.inputMicrographs,
                         alignedMicsLastProt, 'outputMicrographs')
        setExtendedInput(protExtraFull.ctfRelations, protCTFs, 'outputCTF')
        self._registerProt(protExtraFull, 'outputParticles')

        # --------- ELIM EMPTY PARTS AND ---------------------------
        protEEP = self.newProtocol(XmippProtEliminateEmptyParticles,
                                   objLabel='Xmipp - Elim. empty part.',
                                   inputType=0,
                                   threshold=1.1)
        setExtendedInput(protEEP.inputParticles, protExtract, 'outputParticles')
        self._registerProt(protEEP, 'outputParticles')

        # --------- TRIGGER PARTS AND  ---------------------------
        protTRIG = self.newProtocol(XmippProtTriggerData,
                                    objLabel='Xmipp - trigger data to stats',
                                    outputSize=1000, delay=30,
                                    allParticles=True,
                                    splitParticles=False)
        setExtendedInput(protTRIG.inputImages, protEEP, 'outputParticles')
        self._registerProt(protTRIG, 'outputParticles', monitor=False)

        # --------- SCREEN PARTS AND  ---------------------------
        protSCR = self.newProtocol(XmippProtScreenParticles,
                                   objLabel='Xmipp - screen particles')
        protSCR.autoParRejection.set(XmippProtScreenParticles.REJ_MAXZSCORE)
        protSCR.autoParRejectionSSNR.set(XmippProtScreenParticles.REJ_PERCENTAGE_SSNR)
        protSCR.autoParRejectionVar.set(XmippProtScreenParticles.REJ_VARIANCE)
        setExtendedInput(protSCR.inputParticles, protTRIG, 'outputParticles')
        self._registerProt(protSCR, 'outputParticles')

        # --------- TRIGGER PARTS ---------------------------
        protTRIG2 = self.newProtocol(XmippProtTriggerData,
                                     objLabel='Xmipp - trigger data to classify',
                                     outputSize=5000, delay=30,
                                     allParticles=False)
        setExtendedInput(protTRIG2.inputImages, protSCR, 'outputParticles')
        self._registerProt(protTRIG2, 'outputParticles', monitor=False)

        # --------- CL2D 1 ---------------------------
        protCL = self.newProtocol(XmippProtCL2D,
                                  objLabel='Xmipp - Cl2d',
                                  doCore=False,
                                  numberOfClasses=16,
                                  numberOfMpi=8)
        setExtendedInput(protCL.inputParticles, protTRIG2, 'outputParticles')
        self._registerProt(protCL, 'outputClasses', wait=False)

        # --------- Relion 2D classify ---------------------------
        protCL2 = self.newProtocol(ProtRelionClassify2D,
                                   objLabel='Relion - 2D classifying',
                                   numberOfClasses=16,
                                   numberOfMpi=8)
        setExtendedInput(protCL2.inputParticles, protTRIG2, 'outputParticles')
        self._registerProt(protCL2, 'outputClasses', wait=False)

        if not schedule:
            self._waitOutput(protCL, 'outputClasses')
        # --------- CONVERT TO AVERAGES 1---------------------------
        protAVER1 = self.newProtocol(ProtUserSubSet,
                                     objLabel='Classes -> Averages I',
                                     outputClassName="SetOfAverages",
                                     sqliteFile=protCL._getPath("classes2D.sqlite,")
                                     )
        setExtendedInput(protAVER1.inputObject, protCL, 'outputClasses')
        self._registerProt(protAVER1, 'outputRepresentatives', monitor=False)

        if not schedule:
            self._waitOutput(protCL2, 'outputClasses')
        # --------- CONVERT TO AVERAGES 2---------------------------
        protAVER2 = self.newProtocol(ProtUserSubSet,
                                     objLabel='Classes -> Averages II',
                                     outputClassName="SetOfAverages",
                                     sqliteFile=protCL2._getPath("classes2D.sqlite,")
                                     )
        setExtendedInput(protAVER2.inputObject, protCL2, 'outputClasses')
        self._registerProt(protAVER2, 'outputRepresentatives', monitor=False)

        # --------- JOIN SETS ---------------------------
        protJOIN = self.newProtocol(ProtUnionSet, objLabel='Scipion - Join sets')
        setExtendedInput(protJOIN.inputSets,
                         [protAVER1, protAVER2],
                         ['outputRepresentatives', 'outputRepresentatives'])
        self._registerProt(protJOIN, 'outputSet', monitor=False)

        # --------- AUTO CLASS SELECTION ---------------------------
        protCLSEL = self.newProtocol(XmippProtEliminateEmptyParticles,
                                     objLabel='Xmipp - Auto class selection',
                                     inputType=1,
                                     threshold=8.0)
        setExtendedInput(protCLSEL.inputAverages, protJOIN, 'outputSet')
        self._registerProt(protCLSEL, 'outputAverages')

        # --------- INITIAL VOLUME ---------------------------
        protINITVOL = self.newProtocol(EmanProtInitModel,
                                       objLabel='Eman - Initial vol',
                                       symmetryGroup=symmGr)
        setExtendedInput(protINITVOL.inputSet, protCLSEL, 'outputAverages')
        self._registerProt(protINITVOL)

        # --------- RECONSTRUCT SIGNIFICANT ---------------------------
        protSIG = self.newProtocol(XmippProtReconstructSignificant,
                                   objLabel='Xmipp - Recons. significant',
                                   symmetryGroup=symmGr)
        setExtendedInput(protSIG.inputSet, protCLSEL, 'outputAverages')
        self._registerProt(protSIG)

        # --------- RECONSTRUCT RANSAC ---------------------------
        protRAN = self.newProtocol(XmippProtRansac,
                                   objLabel='Xmipp - Ransac significant',
                                   symmetryGroup=symmGr)
        setExtendedInput(protRAN.inputSet, protCLSEL, 'outputAverages')
        self._registerProt(protRAN)

        #  FIXME: ADD WAIT IF NOT SCHEDULE
        # --------- CREATING AN ALIGNED SET OF VOLUMES -----------
        protAVOL = self.newProtocol(XmippProtAlignVolume,
                                    objLabel='Xmipp - Join/Align volumes')
        setExtendedInput(protAVOL.inputReference, protSIG, 'outputVolume')
        setExtendedInput(protAVOL.inputVolumes,
                         [protINITVOL, protRAN, protSIG],
                         ['outputVolumes', 'outputVolumes', 'outputVolume'])
        self._registerProt(protAVOL, 'outputVolumes', monitor=False)

        # --------- SWARM CONSENSUS INITIAL VOLUME ---------------
        protSWARM = self.newProtocol(XmippProtReconstructSwarm,
                                     objLabel='Xmipp - Swarm init. vol.',
                                     symmetryGroup=symmGr)
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

        # --------- GL2D in streaming --------------------
        if hasCUDA:
            protGL2D = self.newProtocol(XmippProtStrGpuCrrSimple,
                                        objLabel='Xmipp - GL2D static')
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



# if __name__ == "__main__":
#
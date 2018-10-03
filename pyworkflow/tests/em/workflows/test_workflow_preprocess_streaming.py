# ***************************************************************************
# *
# * Authors:     J.M. de la Rosa Trevin (delarosatrevin@scilifelab.se) [1]
# *
# * [1] Science for Life Laboratory, Stockholm University
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
                                    ProtSubSet, ProtUnionSet, ProtUserSubSet)

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
                                  XmippProtConsensusPicking, XmippProtCL2D,
                                  XmippProtExtractParticles, XmippProtTriggerData,
                                  XmippProtEliminateEmptyParticles,
                                  XmippProtScreenParticles,
                                  XmippProtReconstructSignificant, XmippProtRansac, XmippProtAlignVolume, XmippProtReconstructSwarm)
except Exception as exc:
     pwutils.pluginNotFound('xmipp', errorMsg=exc)


# Load the number of movies for the simulation, by default equal 5, but
# can be modified in the environement
def _getVar(varSuffix, varType, default=None):
    return varType(os.environ.get('SCIPION_TEST_STREAM_%s' % varSuffix, default))

MOVS = _getVar('MOVS', int, 10)
PATTERN = _getVar('PATTERN', str, '')
DELAY = _getVar('DELAY', int, 10) # in seconds
# Change the timeout to stop waiting for new files
TIMEOUT = _getVar('TIMEOUT', int, 60)


def setExtendedInput(protDotInput, lastProt, extended):
    if isinstance(lastProt, list):
        for idx, prot in enumerate(lastProt):
            inputPointer = Pointer(prot, extended=extended[idx])
            protDotInput.append(inputPointer)
    else:
        protDotInput.set(lastProt)
        protDotInput.setExtended(extended)


# Please set if your system is able to run CUDA devices #
hasCUDA = False                                         #
schedule = True                                         #
projName = 'TestPreprocessStreamingWorkflow'
# ----------------------------------------------------- #

class TestPreprocessStreamingWorkflow(BaseTest):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.ds = DataSet('relion21_tutorial', 'relion21_tutorial', '')
        cls.ds = DataSet.getDataSet('relion21_tutorial')
        cls.importThread = threading.Thread(target=cls._createInputLinks)
        cls.importThread.start()
        # Wait until the first link is created
        time.sleep(5)

    @classmethod
    def _createInputLinks(cls):
        # Create a test folder path
        pattern = PATTERN if PATTERN else cls.ds.getFile('betagal/Micrographs/*mrcs')
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

    def _registerProt(self, prot, output=None):
        if schedule:
            self.proj.saveProtocol(prot)
        else:
            self.proj.launchProtocol(prot, wait=False)
            if output is not None:
                self._waitOutput(prot, output)

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

        # ----------- IMPORT MOVIES -------------------
        protImport = self.newProtocol(ProtImportMovies,
                                      objLabel='import movies',
                                      importFrom=ProtImportMovies.IMPORT_FROM_FILES,
                                      filesPath=os.path.abspath(
                                          self.proj.getTmpPath()),
                                      filesPattern="movie*%s" % self.ext,
                                      amplitudConstrast=0.1,
                                      sphericalAberration=2.,
                                      voltage=300,
                                      samplingRate=3.54,
                                      dataStreaming=True,
                                      timeout=TIMEOUT)
        self._registerProt(protImport, 'outputMovies')

        # ----------- MOVIE GAIN --------------------------
        protMG = self.newProtocol(XmippProtMovieGain,
                                  objLabel='movie gain',
                                  frameStep=20,
                                  movieStep=20,
                                  useExistingGainImage=False)
        setExtendedInput(protMG.inputMovies, protImport, 'outputMovies')
        self._registerProt(protMG)

        # ----------- MOTIONCOR ----------------------------
        if hasCUDA:
            protMC = self.newProtocol(ProtMotionCorr,
                                      objLabel='motioncor2')
            setExtendedInput(protCA.inputMovies, protImport, 'outputMovies')
            self._registerProt(protMC, 'outputMovies')

        # ----------- MAX SHIFT -----------------------------
            protMax1 = self.newProtocol(XmippProtMovieMaxShift,
                                       objLabel='max shift')
            setExtendedInput(protMax1.inputMovies, protMC, 'outputMovies')
            self._registerProt(protMax1, 'outputMicrographs')

            alignedMicsLastProt = protMax1

        else:
        # ----------- CORR ALIGN ----------------------------
            protCA = self.newProtocol(XmippProtMovieCorr,
                                      objLabel='corr allignment')
            setExtendedInput(protCA.inputMovies, protImport, 'outputMovies')
            self._registerProt(protCA, 'outputMovies')

        # ----------- MAX SHIFT -----------------------------
            protMax2 = self.newProtocol(XmippProtMovieMaxShift,
                                       objLabel='max shift')
            setExtendedInput(protMax2.inputMovies, protCA, 'outputMovies')
            self._registerProt(protMax2, 'outputMovies')

        # ----------- OF ALIGNMENT --------------------------
            protOF = self.newProtocol(XmippProtOFAlignment,
                                      objLabel='of alignment',
                                      doSaveMovie=False,
                                      alignFrame0=3,
                                      alignFrameN=10,
                                      sumFrame0=3,
                                      sumFrameN=10,
                                      useAlignToSum=False,
                                      useAlignment=False,
                                      doApplyDoseFilter=False)
            setExtendedInput(protOF.inputMovies, protMax2, 'outputMovies')
            self._registerProt(protOF, 'outputMicrographs')

            alignedMicsLastProt = protOF

        # --------- PREPROCESS MICS ---------------------------
        # protInv = self.newProtocol(XmippProtPreprocessMicrographs,
        #                             objLabel='invert contrast',
        #                             # doDownsample=True, downFactor=1.5,
        #                             doInvert=True, doCrop=False, runMode=1)
        # setExtendedInput(protInv.inputMicrographs, alignedMicsLastProt,
        #                  'outputMicrographs')
        # self._registerProt(protInv, 'outputMicrographs')
        # alignedMicsLastProt = protInv

        # --------- CTF ESTIMATION 1 ---------------------------
        protCTF1 = self.newProtocol(XmippProtCTFMicrographs,
                                    objLabel='XMIPP ctf estimation')
        setExtendedInput(protCTF1.inputMicrographs,
                         alignedMicsLastProt, 'outputMicrographs')
        self._registerProt(protCTF1)

        # --------- CTF ESTIMATION 2 ---------------------------
        protCTF2 = self.newProtocol(ProtCTFFind,
                                    objLabel='CTFFIND estimation')
        setExtendedInput(protCTF2.inputMicrographs,
                         alignedMicsLastProt, 'outputMicrographs')
        self._registerProt(protCTF2)

        # --------- CTF ESTIMATION 3 ---------------------------
        if hasCUDA:
            protCTF3 = self.newProtocol(ProtGctf,
                                        objLabel='gCTF estimation')
            setExtendedInput(protCTF3.inputMicrographs,
                             alignedMicsLastProt, 'outputMicrographs')
            self._registerProt(protCTF3)

        if not schedule:
            self._waitOutput(protCTF1, 'outputCTF')
            self._waitOutput(protCTF2, 'outputCTF')
        # --------- CTF CONSENSUS 1 ---------------------------
        protCONS = self.newProtocol(XmippProtCTFConsensus,
                                    objLabel='ctf consensus',
                                    useDefocus=False,
                                    useAstigmatism=False,
                                    resolution=17.0,
                                    calculateConsensus=False,  # This fails! Please, see XmippProtCTFConsensus
                                    minConsResol=15.0,
                                    )
        setExtendedInput(protCONS.inputCTF, protCTF1, 'outputCTF')
        setExtendedInput(protCONS.inputCTF2, protCTF2, 'outputCTF')
        self._registerProt(protCONS, 'outputMicrographs')

        if hasCUDA:
            if not schedule:
                self._waitOutput(protCONS, 'outputCTF')
            # --------- CTF CONSENSUS 2 ---------------------------
            protCONS2 = self.newProtocol(XmippProtCTFConsensus,
                                        objLabel='ctf consensus',
                                        useDefocus=False,
                                        useAstigmatism=False,
                                        resolution=17.0,
                                        minConsResol=15.0
                                        )
            setExtendedInput(protCONS2.inputCTF, protCONS, 'outputCTF')
            setExtendedInput(protCONS2.inputCTF2, protCTF3, 'outputCTF')
            self._registerProt(protCONS2, 'outputMicrographs')

            # # ---------- INTERSECTION CTF CONSENSUS -----------------
            # protGoodCtfs = self.newProtocol(ProtSubSet,
            #                            setOperation=ProtSubSet.SET_INTERSECTION)
            # setExtendedInput(protGoodCtfs.inputFullSet,
            #                  protCONS, 'outputMicrographs')
            # setExtendedInput(protGoodCtfs.inputSubSet,
            #                  protCONS2, 'outputMicrographs')
            # self._registerProt(protGoodCtfs, 'outputMicrographs')

            goodCtfs = protCONS2

        else:
            goodCtfs = protCONS


        # --------- PARTICLE PICKING 1 ---------------------------
        protPP1 = self.newProtocol(SparxGaussianProtPicking,
                                  objLabel='SPARX particle picking',
                                  boxSize=80)
        setExtendedInput(protPP1.inputMicrographs, goodCtfs, 'outputMicrographs')
        self._registerProt(protPP1)

        # --------- PARTICLE PICKING 2 ---------------------------
        protPP2 = self.newProtocol(DogPickerProtPicking,
                                  objLabel='DOGPICKER particle picking',
                                  diameter=3.54*80)
        setExtendedInput(protPP2.inputMicrographs, goodCtfs, 'outputMicrographs')
        self._registerProt(protPP2)

        if not schedule:
            self._waitOutput(protPP1, 'outputCoordinates')
            self._waitOutput(protPP2, 'outputCoordinates')
        # --------- CONSENSUS PICKING ---------------------------
        protCP = self.newProtocol(XmippProtConsensusPicking,
                                  objLabel='consensus picking')
        setExtendedInput(protCP.inputCoordinates,
                         [protPP1, protPP2],
                         ['outputCoordinates', 'outputCoordinates'])
        self._registerProt(protCP, 'consensusCoordinates')

        # --------- EXTRACT PARTICLES ---------------------------
        protExtract = self.newProtocol(ProtRelionExtractParticles,  # Change to Xmipp extract when it works fine
                                       objLabel='extract particles',
                                       boxSize=80,
                                       downsampleType=1,
                                       doRemoveDust=True,
                                       doNormalize=True,
                                       doInvert=True,
                                       doFlip=True)
        setExtendedInput(protExtract.inputCoordinates,
                         protPP1, 'outputCoordinates')  # protCP.consensusCoordinates-----------------------
        setExtendedInput(protExtract.inputMicrographs,
                         alignedMicsLastProt, 'outputMicrographs')
        # setExtendedInput(protExtract.ctfRelations, goodCtfs, 'outputCTF')  # uncomment this when ctfConsensus work fine
        self._registerProt(protExtract, 'outputParticles')

        # --------- ELIM EMPTY PARTS ---------------------------
        protEEP = self.newProtocol(XmippProtEliminateEmptyParticles,
                                   objLabel='elim empty particles',
                                   inputType=0,
                                   threshold=1.1)
        setExtendedInput(protEEP.inputParticles, protExtract, 'outputParticles')
        self._registerProt(protEEP, 'outputParticles')

        # --------- TRIGGER PARTS ---------------------------
        protTRIG = self.newProtocol(XmippProtTriggerData,
                                    objLabel='trigger data',
                                    outputSize=1000, delay=30,
                                    allParticles=True,
                                    splitParticles=False)
        setExtendedInput(protTRIG.inputParticles, protEEP, 'outputParticles')
        self._registerProt(protTRIG, 'outputParticles')
        #
        # --------- SCREEN PARTS ---------------------------
        protSCR = self.newProtocol(XmippProtScreenParticles,
                                   objLabel='screen particles')
        protSCR.autoParRejection.set(XmippProtScreenParticles.REJ_MAXZSCORE)
        protSCR.autoParRejectionSSNR.set(XmippProtScreenParticles.REJ_PERCENTAGE_SSNR)
        protSCR.autoParRejectionVar.set(XmippProtScreenParticles.REJ_NONE)  # Change this to REJ_VARIANCE when Extraction is done by Xmipp!!
        setExtendedInput(protSCR.inputParticles, protTRIG, 'outputParticles')
        self._registerProt(protSCR, 'outputParticles')

        # --------- TRIGGER PARTS ---------------------------
        protTRIG2 = self.newProtocol(XmippProtTriggerData,
                                     objLabel='another trigger data',
                                     outputSize=2000, delay=30,
                                     allParticles=False,
                                     splitParticles=False)
        setExtendedInput(protTRIG2.inputParticles, protSCR, 'outputParticles')
        self._registerProt(protTRIG2, 'outputParticles')


        # --------- CL2D 1 ---------------------------
        protCL = self.newProtocol(XmippProtCL2D, objLabel='cl2d',
                                  numberOfClasses=16, numberOfMpi=8)
        setExtendedInput(protCL.inputParticles, protTRIG2, 'outputParticles')
        self._registerProt(protCL)

        # --------- Relion 2D classify ---------------------------
        protCL2 = self.newProtocol(ProtRelionClassify2D,
                                   objLabel='relion 2D classification',
                                   numberOfClasses=16, numberOfMpi=8)
        setExtendedInput(protCL2.inputParticles, protTRIG2, 'outputParticles')
        self._registerProt(protCL2)

        if not schedule:
            self._waitOutput(protCL, 'outputClasses')
        # --------- CONVERT TO AVERAGES 1---------------------------
        protAVER1 = self.newProtocol(ProtUserSubSet,
                                     objLabel='set of averages 1',
                                     outputClassName="SetOfAverages",
                                     sqliteFile=os.path.join(
                                         protCL._getPath(),
                                         "classes2D_stable_core.sqlite,"))
        setExtendedInput(protAVER1.inputObject, protCL, 'outputClasses')
        self._registerProt(protAVER1, 'outputRepresentatives')

        if not schedule:
            self._waitOutput(protCL2, 'outputClasses')
        # --------- CONVERT TO AVERAGES 2---------------------------
        protAVER2 = self.newProtocol(ProtUserSubSet,
                                     objLabel='set of averages 2',
                                     outputClassName="SetOfAverages",
                                     sqliteFile=os.path.join(
                                         protCL2._getPath(),
                                         "classes2D.sqlite,"))
        setExtendedInput(protAVER2.inputObject, protCL2, 'outputClasses')
        self._registerProt(protAVER2, 'outputRepresentatives')

        # --------- JOIN SETS ---------------------------
        protJOIN = self.newProtocol(ProtUnionSet, objLabel='join sets')
        setExtendedInput(protJOIN.inputSets,
                         [protAVER1, protAVER2], 'outputRepresentatives')
        self._registerProt(protJOIN, 'outputSet')

        # --------- AUTO CLASS SELECTION ---------------------------
        protCLSEL = self.newProtocol(XmippProtEliminateEmptyParticles,
                                     objLabel='auto class selection',
                                     inputType=1,
                                     threshold=8.0)
        setExtendedInput(protCLSEL.inputParticles, protJOIN, 'outputSet')
        setExtendedInput(protCLSEL.inputAverages, protJOIN, 'outputSet')
        self._registerProt(protCLSEL, 'outputParticles')

        # --------- INITIAL VOLUME ---------------------------
        protINITVOL = self.newProtocol(EmanProtInitModel,
                                       objLabel='Eman initial vol',
                                       symmetryGroup='d2')
        setExtendedInput(protINITVOL.inputSet, protCLSEL, 'outputParticles')
        self._registerProt(protINITVOL)

        # --------- RECONSTRUCT SIGNIFICANT ---------------------------
        protSIG = self.newProtocol(XmippProtReconstructSignificant,
                                   objLabel='Reconstruct significant',
                                   symmetryGroup='d2',
                                   iter=30)  # iter=15)
        setExtendedInput(protSIG.inputSet, protCLSEL, 'outputParticles')
        self._registerProt(protSIG)

        # --------- RECONSTRUCT RANSAC ---------------------------
        protRAN = self.newProtocol(XmippProtRansac,
                                   objLabel='Ransac significant',
                                   symmetryGroup='d2',
                                   iter=30)  # iter=15)
        setExtendedInput(protRAN.inputSet, protRAN, 'outputParticles')
        self._registerProt(protCLSEL)

        #  FIX ME: ADD WAIT IF NOT ESCHEDULE
        # --------- CREATING AN ALIGNED SET OF VOLUMES -----------
        protAVOL = self.newProtocol(XmippProtAlignVolume,
                                     objLabel='Join and align volumes',
                                     iter=30)  # iter=15)
        setExtendedInput(protAVOL.inputReference, protSIG, 'outputVolume')
        setExtendedInput(protAVOL.inputVolumes, [protRAN, protINITVOL, protSIG],
                         ['outputVolumes', 'outputVolumes', 'outputVolume'])
        self._registerProt(protAVOL)


        # --------- SWARM CONSENSUS INITIAL VOLUME ---------------
        protSWARM = self.newProtocol(XmippProtReconstructSwarm,
                                     objLabel='Swarm initial volume',
                                     symmetryGroup='d2')
                                     # iter=30)  # iter=15)
        setExtendedInput(protSWARM.inputParticles, protTRIG2, 'outputParticles')
        setExtendedInput(protSWARM.inputVolumes, protAVOL, 'outputVolumes')
        self._registerProt(protSWARM)




        os.system('%s python %s %s &' % (pw.getScipionScript(),
                               pw.getScipionPath('scripts/schedule_project.py'),
                               projName))

        os.system('%s project %s &' % (pw.getScipionScript(), projName))



# if __name__ == "__main__":
#
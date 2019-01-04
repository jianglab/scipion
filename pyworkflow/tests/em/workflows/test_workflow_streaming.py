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

import time
import os
from glob import glob
import threading
import socket

from pyworkflow.protocol import getProtocolFromDb
from pyworkflow.protocol.constants import LEVEL_ADVANCED
import pyworkflow.utils as pwutils
from pyworkflow.utils import importFromPlugin
from pyworkflow.tests import BaseTest, setupTestProject, DataSet
from pyworkflow.em import ImageHandler
from pyworkflow.em.protocol import (ProtImportMovies, ProtMonitorSummary,
                                    ProtImportMicrographs, ProtImportAverages)

XmippProtOFAlignment = importFromPlugin('xmipp3.protocols', 'XmippProtOFAlignment', doRaise=True)
SparxGaussianProtPicking = importFromPlugin('eman2.protocols', 'SparxGaussianProtPicking', doRaise=True)
ProtCTFFind = importFromPlugin('grigoriefflab.protocols', 'ProtCTFFind', doRaise=True)
ProtRelionExtractParticles = importFromPlugin('relion.protocols', 'ProtRelionExtractParticles', doRaise=True)
ProtRelion2Autopick = importFromPlugin('relion.protocols', 'ProtRelion2Autopick')


# Load the number of movies for the simulation, by default equal 5, but
# can be modified in the environement
def _getVar(varSuffix, varType, default=None):
    return varType(os.environ.get('SCIPION_TEST_STREAM_%s' % varSuffix, default))

MOVS = _getVar('MOVS', int, 10)
PATTERN = _getVar('PATTERN', str, '')
DELAY = _getVar('DELAY', int, 10) # in seconds
# Change the timeout to stop waiting for new files
TIMEOUT = _getVar('TIMEOUT', int, 60)


class TestStreamingWorkflow(BaseTest):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.ds = DataSet.getDataSet('movies')
        cls.importThread = threading.Thread(name="createInputLinks",
                                            target=cls._createInputLinks)
        cls.importThread.start()
        # Wait until the first link is created
        time.sleep(5)

    @classmethod
    def _createInputLinks(cls):
        # Create a test folder path
        pattern = PATTERN if PATTERN else cls.ds.getFile('ribo/Falcon*mrcs')
        files = glob(pattern)
        nFiles = len(files)
        nMovies = MOVS

        for i in range(nMovies):
            # Loop over the number of input movies if we want more for testing
            f = files[i % nFiles]
            _, cls.ext = os.path.splitext(f)
            moviePath = cls.proj.getTmpPath('movie%06d%s' % (i+1, cls.ext))
            pwutils.createAbsLink(f, moviePath)
            time.sleep(DELAY)

    def test_pattern(self):

        # ----------- IMPORT MOVIES -------------------
        protImport = self.newProtocol(ProtImportMovies,
                                      objLabel='import movies',
                                      importFrom=ProtImportMovies.IMPORT_FROM_FILES,
                                      filesPath=os.path.abspath(self.proj.getTmpPath()),
                                      filesPattern="movie*%s" % self.ext,
                                      amplitudConstrast=0.1,
                                      sphericalAberration=2.,
                                      voltage=300,
                                      samplingRate=3.54,
                                      dataStreaming=True,
                                      timeout=TIMEOUT)

        self.proj.launchProtocol(protImport, wait=False)
        self._waitOutput(protImport, 'outputMovies')

        # ----------- OF ALIGNMENT --------------------------
        protOF = self.newProtocol(XmippProtOFAlignment,
                                  objLabel='OF alignment',
                                  doSaveMovie=False,
                                  alignFrame0=3,
                                  alignFrameN=10,
                                  sumFrame0=3,
                                  sumFrameN=10,
                                  useAlignToSum=False,
                                  useAlignment=False,
                                  doApplyDoseFilter=False)

        protOF.inputMovies.set(protImport.outputMovies)
        self.proj.launchProtocol(protOF, wait=False)
        self._waitOutput(protOF, 'outputMicrographs')

        # --------- CTF ESTIMATION ---------------------------

        protCTF = self.newProtocol(ProtCTFFind,
                                   objLabel='ctffind4')
        protCTF.inputMicrographs.set(protOF.outputMicrographs)
        self.proj.launchProtocol(protCTF, wait=False)
        self._waitOutput(protCTF, 'outputCTF')

        # --------- SUMMARY MONITOR --------------------------

        protMonitor = self.newProtocol(ProtMonitorSummary,
                                       objLabel='summary')

        protMonitor.inputProtocols.append(protImport)
        protMonitor.inputProtocols.append(protOF)
        protMonitor.inputProtocols.append(protCTF)

        self.proj.launchProtocol(protMonitor, wait=False)

        # Wait until the thread that is creating links finish:
        self.importThread.join()


class TestBaseRelionStreaming(BaseTest):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.ds = DataSet.getDataSet('relion_tutorial')
        cls.importThread = threading.Thread(name="createInputLinksR",
                                            target=cls._createInputLinks)
        cls.importThread.start()
        # Wait until the first link is created
        time.sleep(5)
    
    @classmethod
    def _createInputLinks(cls):
        # Create a test folder path
        pattern = cls.ds.getFile('allMics')
        files = glob(pattern)
        nFiles = len(files)
        
        for i in range(nFiles):
            # Loop over the number of input movies if we want more for testing
            f = files[i % nFiles]
            _, cls.ext = os.path.splitext(f)
            moviePath = cls.proj.getTmpPath('movie%06d%s' % (i + 1, cls.ext))
            pwutils.createAbsLink(f, moviePath)
            time.sleep(10)
    
    def _waitOutput(self, prot, outputAttributeName):
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
        
        counter = 1
        prot2 = _loadProt()
        
        while not prot2.hasAttribute(outputAttributeName):
            time.sleep(5)
            prot2 = _loadProt()
            if counter > 1000:
                break
            counter += 1
        
        # Update the protocol instance to get latest changes
        self.proj._updateProtocol(prot)
    
    def _waitUntilMinSize(self, emSet, size=5):
        counter = 0
        while not emSet.getSize() >= size:
            time.sleep(5)
            emSet.load()
            if counter > 1000:
                break
            counter += 1
    
    
class TestRelionExtractStreaming(TestBaseRelionStreaming):
    def testRisosome(self):
        # First, import a set of micrographs
        print("Importing a set of micrographs...")
        protImport = self.newProtocol(ProtImportMicrographs,
                                      filesPath=os.path.abspath(self.proj.getTmpPath()),
                                      filesPattern="*%s" % self.ext,
                                      samplingRateMode=1,
                                      magnification=79096,
                                      scannedPixelSize=56, voltage=300,
                                      sphericalAberration=2.0,
                                      dataStreaming=True,
                                      fileTimeout=3,
                                      timeout=60)
        protImport.setObjLabel('import 20 mics (streaming)')
        self.proj.launchProtocol(protImport, wait=False)
        self._waitOutput(protImport, 'outputMicrographs')

        # Now estimate CTF on the micrographs with ctffind
        print("Performing CTFfind...")
        protCTF = self.newProtocol(ProtCTFFind,
                                   useCtffind4=True,
                                   lowRes=0.02, highRes=0.45,
                                   minDefocus=1.2, maxDefocus=3,
                                   runMode=1,
                                   numberOfMpi=1, numberOfThreads=1)
        protCTF.inputMicrographs.set(protImport.outputMicrographs)
        protCTF.setObjLabel('CTF ctffind')
        self.proj.launchProtocol(protCTF, wait=False)
        
        # Now pick particles on the micrographs with sparx
        print("Performing Sparx Autopicking...")
        protPick = self.newProtocol(SparxGaussianProtPicking,
                                    boxSize=50,
                                    lowerThreshold=0.9,
                                    higherThreshold=15,
                                    gaussWidth=1.2)
        protPick.inputMicrographs.set(protImport.outputMicrographs)
        protPick.setObjLabel('Streaming Auto-picking')
        self.proj.launchProtocol(protPick, wait=False)

        self._waitOutput(protPick, 'outputCoordinates')
        self._waitOutput(protCTF, 'outputCTF')
        
        protExtract = self.newProtocol(ProtRelionExtractParticles,
                                       objLabel='extract box=64',
                                       boxSize=64,
                                       doInvert=True
                                       )
        protExtract.inputCoordinates.set(protPick.outputCoordinates)
        protExtract.ctfRelations.set(protCTF.outputCTF)
        self.launchProtocol(protExtract)
        
        x, y, _ = protExtract.outputParticles.getDim()
        self.assertEqual(protExtract.outputParticles.getDim(), (64, 64, 1),
                         "Dimension of the particles should be 64 x 64 and it "
                         "is %d x %d" % (x, y))


class TestRelionPickStreaming(TestBaseRelionStreaming):
    def testRisosome(self):
        print "Importing 2D averages (subset of 4)"
        ih = ImageHandler()
        classesFn = self.ds.getFile('import/classify2d/extra/'
                                    'relion_it015_classes.mrcs')
    
        outputName = 'input_averages.mrcs'
        inputTmp = os.path.abspath(self.proj.getTmpPath())
        outputFn = self.proj.getTmpPath(outputName)
    
        for i, index in enumerate([5, 16, 17, 18, 24]):
            ih.convert((index, classesFn), (i + 1, outputFn))
    
        protAvgs = self.newProtocol(ProtImportAverages,
                                    objLabel='avgs - 5',
                                    filesPath=inputTmp,
                                    filesPattern=outputName,
                                    samplingRate=7.08
                                    )
        self.launchProtocol(protAvgs)
        
        # First, import a set of micrographs
        print "Importing a set of micrographs..."
        protImport = self.newProtocol(ProtImportMicrographs,
                                      filesPath=os.path.abspath(self.proj.getTmpPath()),
                                      filesPattern="*%s" % self.ext,
                                      samplingRateMode=1,
                                      magnification=79096,
                                      scannedPixelSize=56, voltage=300,
                                      sphericalAberration=2.0,
                                      dataStreaming=True,
                                      fileTimeout=10,
                                      timeout=60)
        protImport.setObjLabel('import 20 mics (streaming)')
        self.proj.launchProtocol(protImport, wait=False)
        self._waitOutput(protImport, 'outputMicrographs')
        
        # Now estimate CTF on the micrographs with ctffind
        print "Performing CTFfind..."
        protCTF = self.newProtocol(ProtCTFFind,
                                   useCtffind4=True,
                                   lowRes=0.02, highRes=0.45,
                                   minDefocus=1.2, maxDefocus=3,
                                   runMode=1,
                                   numberOfMpi=1, numberOfThreads=1)
        protCTF.inputMicrographs.set(protImport.outputMicrographs)
        protCTF.setObjLabel('CTF ctffind')
        self.proj.launchProtocol(protCTF, wait=False)
        self._waitOutput(protCTF, 'outputCTF')
        
        self._waitUntilMinSize(protCTF.outputCTF)

        # Select some good averages from the iterations mrcs a
        protPick = self.newProtocol(ProtRelion2Autopick,
                                    objLabel='autopick refs',
                                    runType=0,
                                    micrographsNumber=3,
                                    referencesType=0,
                                    refsHaveInvertedContrast=True,
                                    particleDiameter=380
                                    )
        protPick.inputMicrographs.set(protImport.outputMicrographs)
        protPick.ctfRelations.set(protCTF.outputCTF)
        protPick.inputReferences.set(protAvgs.outputAverages)
        self.launchProtocol(protPick)
        
        protPick.runType.set(1)
        self.launchProtocol(protPick)


class TestFrameStacking(BaseTest):
    """ Test the cases where the input movies are input as individual frames.
    """

    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.ds = DataSet.getDataSet('movies')

    @classmethod
    def _createFrames(cls, delay=0):
        # Create a test folder path
        pattern = cls.ds.getFile('ribo/Falcon*mrcs')
        files = glob(pattern)

        nFiles = len(files)
        nMovies = MOVS
        ih = ImageHandler()

        for i in range(nMovies):
            # Loop over the number of input movies if we want more for testing
            f = files[i % nFiles]
            _, _, _, nFrames = ih.getDimensions(f)

            for j in range(1, nFrames + 1):
                outputFramePath = cls.proj.getTmpPath('movie%06d_%03d.mrc'
                                                      % (i+1, j))
                ih.convert((j, f), outputFramePath)
                time.sleep(delay)

    def test_noStream(self):
        """ Test that we can input individual frames even if not
        processing in streaming.
        """
        self._createFrames()

        # ----------- IMPORT MOVIES -------------------
        protImport = self.newProtocol(ProtImportMovies,
                                      objLabel='import stack no stream',
                                      importFrom=ProtImportMovies.IMPORT_FROM_FILES,
                                      filesPath=os.path.abspath(self.proj.getTmpPath()),
                                      filesPattern="movie*.mrc",
                                      amplitudConstrast=0.1,
                                      sphericalAberration=2.,
                                      voltage=300,
                                      samplingRate=3.54,
                                      dataStreaming=False,
                                      inputIndividualFrames=True,
                                      numberOfIndividualFrames=16,
                                      stackFrames=True,
                                      writeMoviesInProject=True,
                                      deleteFrames=True)
        self.launchProtocol(protImport)
        self.assertSetSize(protImport.outputMovies, MOVS, msg="Wrong output set size!!")


    def test_Stream(self):
        # Create a separated thread to simulate real streaming with
        # individual frames
        thread = threading.Thread(name="createFrames",
                                  target=lambda: self._createFrames(delay=1))
        thread.start()
        time.sleep(5)

        # ----------- IMPORT MOVIES -------------------
        protImport = self.newProtocol(ProtImportMovies,
                                      objLabel='import stack streaming',
                                      importFrom=ProtImportMovies.IMPORT_FROM_FILES,
                                      filesPath=os.path.abspath(self.proj.getTmpPath()),
                                      filesPattern="movie*.mrc",
                                      amplitudConstrast=0.1,
                                      sphericalAberration=2.,
                                      voltage=300,
                                      samplingRate=3.54,
                                      dataStreaming=True,
                                      timeout=60,
                                      fileTimeout=5,
                                      inputIndividualFrames=True,
                                      numberOfIndividualFrames=16,
                                      stackFrames=True,
                                      writeMoviesInProject=True,
                                      deleteFrames=False)
        self.launchProtocol(protImport)
        self.assertSetSize(protImport.outputMovies, MOVS, msg="Wrong output set size!!")
        thread.join()

class TestStreamingSocket(BaseTest):
    """ Test import movies (both as movies and frames)
        in streaming mode via socket
    """

    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.ds = DataSet.getDataSet('movies')

    @classmethod
    def _sendFrames(cls, delay=0, port=5000):
        # start with a delay so the protocol has already launched the
        # socket server when we send the first file
        time.sleep(10)
        # Create a test folder path
        pattern = cls.ds.getFile('ribo/Falcon*mrcs')
        files = glob(pattern)
        nFiles = len(files)
        nMovies = MOVS
        ih = ImageHandler()
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = ''
        clientSocket.connect((host, port))

        for i in range(nMovies):
            # Loop over the number of input movies if we want more for testing
            f = files[i % nFiles]
            _, _, _, nFrames = ih.getDimensions(f)
            paths = ""
            print("Writing frame stack for movie %d..." % (i+1))
            for j in range(1, nFrames + 1):
                outputFramePath = cls.proj.getTmpPath('movie%06d_%03d.mrc'
                                                      % (i + 1, j))
                print("%d : %s" % (j, outputFramePath))
                ih.convert((j, f), outputFramePath)
                paths += os.path.abspath(outputFramePath)+'\n'
                time.sleep(delay)
            try:
                print("Sending movie stack %d" %(i+1))
                clientSocket.sendall(paths)
            except socket.error as err:
                # Send failed
                print('Failed to send file: %s' % paths)
                print(err)
                print('Trying to reconnect...')
                clientSocket.shutdown(socket.SHUT_WR)
                clientSocket.close()
                time.sleep(2)
                clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                clientSocket.connect((host, port))
        # Everything sent, lets wait until server has read all files
        serverConnected = True
        lastFile = paths.strip().split('\n')[-1]
        print('Waiting for server socket to finish...')
        print('Last file sent: %s' % lastFile)
        while serverConnected:
            reply = clientSocket.recv(4096)
            if reply:
                if lastFile in reply:
                    serverConnected = False
                time.sleep(delay)
            else:
                serverConnected = False
        print('Finished! Closing client socket')
        clientSocket.shutdown(socket.SHUT_WR)
        clientSocket.close()

    @classmethod
    def _sendMovies(cls, delay=0, port=5000):
        time.sleep(10)  # wait so the server socket is launched
        # Create a test folder path
        pattern = PATTERN if PATTERN else cls.ds.getFile('ribo/Falcon*mrcs')
        files = glob(pattern)
        nFiles = len(files)
        nMovies = MOVS
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = ''
        print("Connecting to server socket...")
        clientSocket.connect((host, port))
        for i in range(nMovies):
            # Loop over the number of input movies if we want more for testing
            f = files[i % nFiles]
            _, cls.ext = os.path.splitext(f)
            moviePath = cls.proj.getTmpPath('movie%06d%s' % (i + 1, cls.ext))
            print("Creating movie %d link..." %(i+1))
            pwutils.createAbsLink(f, moviePath)
            absPath = os.path.abspath(moviePath)+'\n'
            try:
                clientSocket.sendall(absPath)
                time.sleep(delay)
            except socket.error as err:
                # Send failed
                print('Failed to send file: %s' % absPath)
                print(err)
                print('Trying to reconnect...')
                clientSocket.shutdown(socket.SHUT_WR)
                clientSocket.close()
                time.sleep(2)
                clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                clientSocket.connect((host, port))

        serverConnected = True
        print('Last file sent: %s' % absPath)
        print('Waiting for server socket to finish reading...')
        while serverConnected:
            reply = clientSocket.recv(4096)
            if reply:
                if absPath in reply:
                    serverConnected = False
                time.sleep(delay)  # wait a bit to check for reply
            else:
                serverConnected = False
        print('Finished! Disconnecting client...')
        clientSocket.shutdown(socket.SHUT_WR)
        clientSocket.close()

    def test_StreamMovies(self):
        thread = threading.Thread(name="sendMovies",
                                  target=lambda: self._sendMovies(delay=1))
        thread.start()
        protImport = self.newProtocol(ProtImportMovies,
                                      objLabel='import movies',
                                      importFrom=ProtImportMovies.IMPORT_FROM_FILES,
                                      filesPath=os.path.abspath(self.proj.getTmpPath()),
                                      filesPattern="movie*",
                                      amplitudConstrast=0.1,
                                      sphericalAberration=2.,
                                      voltage=300,
                                      samplingRate=3.54,
                                      dataStreaming=True,
                                      streamingSocket=True,
                                      timeout=TIMEOUT)

        self.proj.launchProtocol(protImport, wait=True)
        self.assertSetSize(protImport.outputMovies, MOVS, msg="Wrong output set size")
        thread.join()

    def test_StreamStack(self):
        # Create a separated thread to simulate real streaming with
        # individual frames
        thread = threading.Thread(name="sendFrames",
                                  target=lambda: self._sendFrames(delay=1))
        thread.start()
        # --------------- IMPORT MOVIES -------------------
        protImport = self.newProtocol(ProtImportMovies,
                                      objLabel='import frame stack',
                                      importFrom=ProtImportMovies.IMPORT_FROM_FILES,
                                      filesPath=os.path.abspath(self.proj.getTmpPath()),
                                      filesPattern="movie*.mrc",
                                      expertLevel=LEVEL_ADVANCED,
                                      amplitudConstrast=0.1,
                                      sphericalAberration=2.,
                                      voltage=300,
                                      samplingRate=3.54,
                                      dataStreaming=True,
                                      timeout=120,
                                      fileTimeout=10,
                                      streamingSocket=True,
                                      inputIndividualFrames=True,
                                      numberOfIndividualFrames=16,
                                      stackFrames=True,
                                      writeMoviesInProject=True,
                                      deleteFrames=False)
        self.launchProtocol(protImport)
        self.assertSetSize(protImport.outputMovies, MOVS, msg="Wrong output set size")
        thread.join()

# -*- coding: utf-8 -*-
# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (jmdelarosa@cnb.csic.es)
# *
# * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
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
# *
# **************************************************************************

import os
import numpy
from datetime import datetime
from collections import OrderedDict
from pyworkflow.protocol.params import PointerParam, BooleanParam
from pyworkflow.em.constants import ALIGN_2D, ALIGN_3D, ALIGN_PROJ, ALIGN_NONE
from pyworkflow.em.data import Coordinate, SetOfParticles, SetOfMicrographs
from pyworkflow.em.protocol import ProtParticlePicking
import pyworkflow.utils as pwutils


class ProtExtractCoords(ProtParticlePicking):
    """ 
    Extract the coordinates information from a set of particles.
    
    This protocol is useful when we want to re-extract the particles
    (maybe resulting from classification and cleaning) with the 
    original dimensions. It can be also handy to visualize the resulting
    particles in their location on micrographs.
    """
    # TESTS: 
    # scipion test tests.em.protocols.test_protocols_xmipp_mics.TestXmippExtractParticles
    
    _label = 'extract coordinates'

    #--------------------------- DEFINE param functions ------------------------
    def _defineParams(self, form):
        form.addSection(label='Input')

        form.addParam('inputParticles', PointerParam,
                      pointerClass='SetOfParticles',
                      label='Input particles', important=True,
                      help='Select the particles from which you want\n'
                           'to extract the coordinates and micrographs.')
        
        form.addParam('inputMicrographs', PointerParam,
                      pointerClass='SetOfMicrographs',
                      label='Input micrographs', important=True,
                      help='Select the micrographs to which you want to\n'
                           'associate the coordinates from the particles.')

        form.addParam('applyShifts', BooleanParam, default=False,
                      label='Apply particle shifts?',
                      help='Apply particle shifts from 2D alignment to '
                           'recalculate new coordinates. This can be useful '
                           'for re-centering particle coordinates.')
        
        form.addParallelSection(threads=0, mpi=0)

    #--------------------------- INSERT steps functions ------------------------

    def _insertAllSteps(self):
        self.partDone = {}
        # self.partDict = OrderedDict()
        # self.micDict = OrderedDict()
        self.insertedDict = {}
        #
        # pwutils.makeFilePath(self._getAllDone())
        #
        # partDict, self.streamClosed = self._loadInputList()
        stepsIds = self._insertNewSteps(self.insertedDict,
                                        self.getInputParticles())

        self._insertFinalSteps(stepsIds)

    def _insertFinalSteps(self, micSteps):
        """ Override this function to insert some steps after the
        picking micrograph steps.
        Receive the list of step ids of the picking steps. """
        self._insertFunctionStep('createOutputStep',
                                 prerequisites=micSteps, wait=True)

    def _getPickArgs(self):
        """ Should be implemented in sub-classes to define the argument
        list that should be passed to the picking step function.
        """
        return []

    def _insertPickMicrographStep(self, mic, prerequisites, *args):
        """ Basic method to insert a picking step for a given micrograph. """
        micStepId = self._insertFunctionStep('pickMicrographStep',
                                             mic.getMicName(), *args,
                                             prerequisites=prerequisites)
        return micStepId

    def pickMicrographStep(self, micName, *args):
        """ Step function that will be common for all picking protocols.
        It will take care of re-building the micrograph object from the micDict
        argument and perform any conversion if needed. Then, the function
        _pickMicrograph will be called, that should be implemented by each
        picking protocol.
        """
        mic = self.micDict[micName]
        micDoneFn = self._getMicDone(mic)
        micFn = mic.getFileName()

        if self.isContinued() and os.path.exists(micDoneFn):
            self.info("Skipping micrograph: %s, seems to be done" % micFn)
            return

        # Clean old finished files
        pwutils.cleanPath(micDoneFn)

        self.info("Picking micrograph: %s " % micFn)
        self._pickMicrograph(mic, *args)

        # Mark this mic as finished
        open(micDoneFn, 'w').close()

    def _pickMicrograph(self, mic, *args):
        """ This function should be implemented by subclasses in order
        to picking the given micrograph. """
        pass

    # Group of functions to pick several micrographs if the batch size is
    # defined. In some programs it might be more efficient to pick many
    # at once and not one by one

    def _insertPickMicrographListStep(self, micList, prerequisites, *args):
        """ Basic method to insert a picking step for a given micrograph. """
        micNameList = [mic.getMicName() for mic in micList]
        micStepId = self._insertFunctionStep('pickMicrographListStep',
                                             micNameList, *args,
                                             prerequisites=prerequisites)
        return micStepId

    def pickMicrographListStep(self, micNameList, *args):
        micList = []

        for micName in micNameList:
            mic = self.micDict[micName]
            micDoneFn = self._getMicDone(mic)
            micFn = mic.getFileName()
            if self.isContinued() and os.path.exists(micDoneFn):
                self.info("Skipping micrograph: %s, seems to be done" % micFn)

            else:
                # Clean old finished files
                pwutils.cleanPath(micDoneFn)
                self.info("Picking micrograph: %s " % micFn)
                micList.append(mic)

        self._pickMicrographList(micList, *args)

        for mic in micList:
            # Mark this mic as finished
            open(self._getMicDone(mic), 'w').close()

    def _pickMicrographList(self, micList, *args):
        """ This function can be implemented by subclasses if it is a more
        effcient way to pick many micrographs at once.
         Default implementation will just call the _pickMicrograph
        """
        for mic in micList:
            self._pickMicrograph(mic, *args)

    # --------------------------- UTILS functions ----------------------------

    def _stepsCheck(self):
        # To allow streaming picking we need to detect:
        #   1) new micrographs ready to be picked
        #   2) new output coordinates that have been produced and add then
        #      to the output set.
        self._checkNewInput()
        self._checkNewOutput()

    def _insertNewSteps(self, insertedDict, partsToProcess):
        """ Insert steps to process new parts (from streaming)
        Params:
            insertedDict: contains already processed parts
            inputParts: input parts set to be check
        """
        deps = []
        # For each partBatch, insert a step to process it
        for part in partsToProcess:
            partId = part.getObjId()
            stepId = self._insertFunctionStep('_extractCoord', partId,
                                              prerequisites=[])
            deps.append(stepId)
            insertedDict[ctfId] = stepId
        return deps

    def _loadSet(self, inputSet, SetClass, getKeyFunc):
        """ Load a given input set if their items are not already present
        in the self.micDict.
        This can be used to load new micrographs for picking as well as
        new CTF (if used) in streaming.
        """
        setFn = inputSet.getFileName()
        self.debug("Loading input db: %s" % setFn)
        updatedSet = SetClass(filename=setFn)
        updatedSet.loadAllProperties()
        newItemDict = OrderedDict()
        for item in updatedSet:
            micKey = getKeyFunc(item)
            if micKey not in self.micDict:
                newItemDict[micKey] = item.clone()
        streamClosed = updatedSet.isStreamClosed()
        updatedSet.close()
        self.debug("Closed db.")

        return newItemDict, streamClosed

    def _loadParts(self, micSet):
        return self._loadSet(micSet, SetOfParticles,
                        lambda part: part.getObjId())

    def _loadMics(self, micSet):
        return self._loadSet(micSet, SetOfMicrographs,
                        lambda mic: mic.getMicName())

    def getInputParticlesPointer(self):
        return self.inputParticles

    def getInputParticles(self):
        return self.inputParticles().get()

    def _loadInputList(self):
        """ Load the input set of micrographs that are ready to be picked. """
        return self._loadParts(self.getInputParticles())

    def _checkNewInput(self):
        # Check if there are new particles to process from the input set
        localFile = self.getInputMicrographs().getFileName()
        now = datetime.now()
        self.lastCheck = getattr(self, 'lastCheck', now)
        mTime = datetime.fromtimestamp(os.path.getmtime(localFile))
        self.debug('Last check: %s, modification: %s'
                  % (pwutils.prettyTime(self.lastCheck),
                     pwutils.prettyTime(mTime)))
        # If the input micrographs.sqlite have not changed since our last check,
        # it does not make sense to check for new input data
        if self.lastCheck > mTime and hasattr(self, 'listOfMics'):
            return None

        self.lastCheck = now

        # Open input micrographs.sqlite and close it as soon as possible
        micDict, self.streamClosed = self._loadInputList()
        newMics = micDict.values()
        outputStep = self._getFirstJoinStep()

        if newMics:
            fDeps = self._insertNewSteps(newMics)
            if outputStep is not None:
                outputStep.addPrerequisites(*fDeps)
            self.updateSteps()

    def _checkNewOutput(self):
        if getattr(self, 'finished', False):
            return

        # Load previously done items (from text file)
        doneList = self._readDoneList()
        # Check for newly done items
        listOfMics = self.micDict.values()
        nMics = len(listOfMics)
        newDone = [m for m in listOfMics
                   if m.getObjId() not in doneList and self._isMicDone(m)]

        # Update the file with the newly done mics
        # or exit from the function if no new done mics
        self.debug('_checkNewOutput: ')
        self.debug('   listOfMics: %s, doneList: %s, newDone: %s'
                   % (nMics, len(doneList), len(newDone)))

        allDone = len(doneList) + len(newDone)
        # We have finished when there is not more input mics (stream closed)
        # and the number of processed mics is equal to the number of inputs
        self.finished = self.streamClosed and allDone == nMics
        streamMode = Set.STREAM_CLOSED if self.finished else Set.STREAM_OPEN
        self.debug('   streamMode: %s newDone: %s' % (streamMode,
                                                      not(newDone == [])))
        if newDone:
            newDoneUpdated = self._updateOutputCoordSet(newDone, streamMode)
            self._writeDoneList(newDoneUpdated)
        elif not self.finished:
            # If we are not finished and no new output have been produced
            # it does not make sense to proceed and updated the outputs
            # so we exit from the function here

            # Maybe it would be good idea to take a snap to avoid
            # so much IO if this protocol does not have much to do now
            if allDone == nMics:
                self._streamingSleepOnWait()

            return

        self.debug('   finished: %s ' % self.finished)
        self.debug('        self.streamClosed (%s) AND' % self.streamClosed)
        self.debug('        allDone (%s) == len(self.listOfMics (%s)'
                   % (allDone, nMics))

        if self.finished:  # Unlock createOutputStep if finished all jobs
            self._updateStreamState(streamMode)
            outputStep = self._getFirstJoinStep()
            if outputStep and outputStep.isWaiting():
                outputStep.setStatus(STATUS_NEW)

    def _micIsReady(self, mic):
        """ Function to check if a micrograph (although reported done)
        is ready to update the coordinates from it. An practical use of this
        function will be for protocols that need to wait for the CTF of that
        micrograph to be ready as well.
        """
        return True

    def readCoordsFromMics(self, outputDir, micDoneList, outputCoords):
        """ This method should be implemented in subclasses to read
        the coordinates from a given list of micrographs.
        """
        pass

    def _updateOutputCoordSet(self, micList, streamMode):
        micDoneList = [mic for mic in micList if self._micIsReady(mic)]

        # Do no proceed if there is not micrograph ready
        if not micDoneList:
            return []

        outputName = 'outputCoordinates'
        outputDir = self.getCoordsDir()
        outputCoords = getattr(self, outputName, None)

        # If there are not outputCoordinates yet, it means that is the first
        # time we are updating output coordinates, so we need to first create
        # the output set
        firstTime = outputCoords is None

        if firstTime:
            micSetPtr = self.getInputMicrographsPointer()
            outputCoords = self._createSetOfCoordinates(micSetPtr)
        else:
            outputCoords.enableAppend()

        self.info("Reading coordinates from mics: %s" % ','.join([mic.strId() for mic in micList]))
        self.readCoordsFromMics(outputDir, micDoneList, outputCoords)
        self.debug(" _updateOutputCoordSet Stream Mode: %s " % streamMode)
        self._updateOutputSet(outputName, outputCoords, streamMode)

        if firstTime:
            self._defineSourceRelation(self.getInputMicrographsPointer(),
                                       outputCoords)

        return micDoneList

    def _updateStreamState(self, streamMode):

        outputName = 'outputCoordinates'
        outputCoords = getattr(self, outputName, None)

        # If there are not outputCoordinates yet, it means that is the first
        # time we are updating output coordinates, so we need to first create
        # the output set
        firstTime = outputCoords is None

        if firstTime:
            micSetPtr = self.getInputMicrographsPointer()
            outputCoords = self._createSetOfCoordinates(micSetPtr)
        else:
            outputCoords.enableAppend()

        self.debug(" _updateStreamState Stream Mode: %s " % streamMode)
        self._updateOutputSet(outputName, outputCoords, streamMode)

    def _getMicDone(self, mic):
        return self._getExtraPath('DONE', 'mic_%06d.TXT' % mic.getObjId())

    def _isMicDone(self, mic):
        """ A mic is done if the marker file exists. """
        return os.path.exists(self._getMicDone(mic))

    def _getAllDone(self):
        return self._getExtraPath('DONE', 'all.TXT')

    def _readDoneList(self):
        """ Read from a text file the id's of the items that have been done. """
        doneFile = self._getAllDone()
        doneList = []
        # Check what items have been previously done
        if os.path.exists(doneFile):
            with open(doneFile) as f:
                doneList += [int(line.strip()) for line in f]

        return doneList

    def _writeDoneList(self, micList):
        """ Write to a text file the items that have been done. """
        doneFile = self._getAllDone()

        if not os.path.exists(doneFile):
            pwutils.makeFilePath(doneFile)

        with open(doneFile, 'a') as f:
            for mic in micList:
                f.write('%d\n' % mic.getObjId())

    def _getFirstJoinStepName(self):
        # This function will be used for streaming, to check which is
        # the first function that need to wait for all micrographs
        # to have completed, this can be overwritten in subclasses
        # (eg in Xmipp 'sortPSDStep')
        return 'createOutputStep'

    def _getFirstJoinStep(self):
        for s in self._steps:
            if s.funcName == self._getFirstJoinStepName():
                return s
        return None

    def createOutputStep(self):
        # Not really required now
        #self._createOutput(self._getExtraPath())
        # pass
        print(" < < < self.outputCoordinates: %s" % self.outputCoordinates)
        print(" < < < self.outputCoordinates._micrographsPointer: %s" % self.outputCoordinates._micrographsPointer)
        print(" < < < self.outputCoordinates._micrographsPointer.get(): %s" % self.outputCoordinates._micrographsPointer.get())

























    def _insertAllSteps(self):
        self._insertFunctionStep('createOutputStep')

    def createOutputStep(self):
        inputParticles = self.inputParticles.get()
        inputMics = self.inputMicrographs.get()
        outputCoords = self._createSetOfCoordinates(inputMics)
        alignType = inputParticles.getAlignment()

        scale = inputParticles.getSamplingRate() / inputMics.getSamplingRate()
        print "Scaling coordinates by a factor *%0.2f*" % scale
        newCoord = Coordinate()
        firstCoord = inputParticles.getFirstItem().getCoordinate()
        hasMicName = firstCoord.getMicName() is not None

        # Create the micrographs dict using either micName or micId
        micDict = {}

        for mic in inputMics:
            micKey = mic.getMicName() if hasMicName else mic.getObjId()
            if micKey in micDict:
                print ">>> ERROR: micrograph key %s is duplicated!!!" % micKey
                print "           Used in micrographs:"
                print "           - %s" % micDict[micKey].getLocation()
                print "           - %s" % mic.getLocation()
                raise Exception("Micrograph key %s is duplicated!!!" % micKey)
            micDict[micKey] = mic.clone()

        for particle in inputParticles:
            coord = particle.getCoordinate()
            micKey = coord.getMicName() if hasMicName else coord.getMicId()
            mic = micDict.get(micKey, None)  
            
            if mic is None: 
                print "Skipping particle, key %s not found" % micKey
            else:
                newCoord.copyObjId(particle)
                x, y = coord.getPosition()
                if self.applyShifts:
                    shifts = self.getShifts(particle.getTransform(), alignType)
                    xCoor, yCoor = x - int(shifts[0]), y - int(shifts[1])
                    newCoord.setPosition(xCoor*scale, yCoor*scale)
                else:
                    newCoord.setPosition(x*scale, y*scale)

                newCoord.setMicrograph(mic)
                outputCoords.append(newCoord)
        
        boxSize = inputParticles.getXDim() * scale
        outputCoords.setBoxSize(boxSize)
        
        self._defineOutputs(outputCoordinates=outputCoords)
        self._defineSourceRelation(self.inputParticles, outputCoords)
        self._defineSourceRelation(self.inputMicrographs, outputCoords)

    #--------------------------- INFO functions --------------------------------
    def _summary(self):
        summary = []
        ps1 = self.inputParticles.get().getSamplingRate()
        ps2 = self.inputMicrographs.get().getSamplingRate()
        summary.append(u'Input particles pixel size: *%0.3f* (Å/px)' % ps1)
        summary.append(u'Input micrographs pixel size: *%0.3f* (Å/px)' % ps2)
        summary.append('Scaling coordinates by a factor of *%0.3f*' % (ps1/ps2))
        if self.applyShifts:
            summary.append('Applied 2D shifts from particles')
        
        if hasattr(self, 'outputCoordinates'):
            summary.append('Output coordinates: *%d*'
                           % self.outputCoordinates.getSize())
            
        return summary 

    def _methods(self):
        # No much to add to summary information
        return self._summary()

    def _validate(self):
        """ The function of this hook is to add some validation before the
        protocol is launched to be executed. It should return a list of errors.
        If the list is empty the protocol can be executed.
        """
        errors = [ ]
        inputParticles = self.inputParticles.get()
        first = inputParticles.getFirstItem()
        if first.getCoordinate() is None:
            errors.append('The input particles do not have coordinates!!!')

        if self.applyShifts and not inputParticles.hasAlignment():
            errors.append('Input particles do not have alignment information!')
        
        return errors

    #--------------------------- UTILS functions ------------------------------
    def getShifts(self, transform, alignType):
        """
        is2D == True-> matrix is 2D (2D images alignment)
                otherwise matrix is 3D (3D volume alignment or projection)
        invTransform == True  -> for xmipp implies projection
                              -> for xmipp implies alignment
        """
        if alignType == ALIGN_NONE:
            return None

        inverseTransform = alignType == ALIGN_PROJ
        # only flip is meaningful if 2D case
        # in that case the 2x2 determinant is negative
        flip = False
        matrix = transform.getMatrix()
        if alignType == ALIGN_2D:
            # get 2x2 matrix and check if negative
            flip = bool(numpy.linalg.det(matrix[0:2, 0:2]) < 0)
            if flip:
                matrix[0, :2] *= -1.  # invert only the first two columns keep x
                matrix[2, 2] = 1.  # set 3D rot
            else:
                pass

        elif alignType == ALIGN_3D:
            flip = bool(numpy.linalg.det(matrix[0:3, 0:3]) < 0)
            if flip:
                matrix[0, :4] *= -1.  # now, invert first line including x
                matrix[3, 3] = 1.  # set 3D rot
            else:
                pass

        else:
            pass
            # flip = bool(numpy.linalg.det(matrix[0:3,0:3]) < 0)
            # if flip:
            #    matrix[0,:4] *= -1.#now, invert first line including x
        shifts = self.geometryFromMatrix(matrix, inverseTransform)

        return shifts

    def geometryFromMatrix(self, matrix, inverseTransform):
        from pyworkflow.em.transformations import translation_from_matrix
        if inverseTransform:
            matrix = numpy.linalg.inv(matrix)
            shifts = -translation_from_matrix(matrix)
        else:
            shifts = translation_from_matrix(matrix)
        return shifts

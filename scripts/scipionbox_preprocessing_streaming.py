#!/usr/bin/env python
# **************************************************************************
# *
# * Authors:     Pablo Conesa (pconesa@cnb.csic.es)
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
from __future__ import print_function

"""
Creates a scipion workflow file (json formatted) base on a template.
The template may have some ~placeholders~ that will be overwritten with values
Template may look like this, separator is "~" and within it you can define:
~title|value|type~
Template string sits at the end of the file ready for a running streaming demo.
"""
import os
import re
import Tkinter as tk
import tempfile
import tkFont

import datetime
import pyworkflow.utils as pwutils
from pyworkflow.gui import Message, Icon
from pyworkflow.config import ProjectSettings

import pyworkflow.gui as pwgui
from pyworkflow.gui.project.base import ProjectBaseWindow
from pyworkflow.gui.widgets import HotButton, Button

import traceback

FIELD_SEP = '~'
VIEW_WIZARD = 'wizardview'

# Session id
PROJECT_NAME = 'Project name'
MESSAGE = 'Message'

# Project regex to validate the session id name
PROJECT_PATTERN = "^\w{2}\d{4,6}-\d+$"
PROJECT_REGEX = re.compile(PROJECT_PATTERN)


class BoxWizardWindow(ProjectBaseWindow):
    """ Windows to manage all projects. """

    def __init__(self, **kwargs):
        try:
            title = '%s (%s on %s)' % ('Workflow template customizer',
                                       pwutils.getLocalUserName(),
                                       pwutils.getLocalHostName())
        except Exception:
            title = Message.LABEL_PROJECTS

        settings = ProjectSettings()
        self.generalCfg = settings.getConfig()

        ProjectBaseWindow.__init__(self, title, minsize=(400, 550), **kwargs)
        self.viewFuncs = {VIEW_WIZARD: BoxWizardView}
        self.switchView(VIEW_WIZARD)


class BoxWizardView(tk.Frame):
    def __init__(self, parent, windows, **kwargs):
        tk.Frame.__init__(self, parent, bg='white', **kwargs)
        self.windows = windows
        self.root = windows.root
        self.vars = {}
        self.checkvars = []

        bigSize = pwgui.cfgFontSize + 2
        smallSize = pwgui.cfgFontSize - 2
        fontName = pwgui.cfgFontName

        self.bigFont = tkFont.Font(size=bigSize, family=fontName)
        self.bigFontBold = tkFont.Font(size=bigSize, family=fontName,
                                       weight='bold')

        self.projDateFont = tkFont.Font(size=smallSize, family=fontName)
        self.projDelFont = tkFont.Font(size=smallSize, family=fontName,
                                       weight='bold')
        # Header section
        headerFrame = tk.Frame(self, bg='white')
        headerFrame.grid(row=0, column=0, sticky='new')
        headerText = "Enter your desired values"

        label = tk.Label(headerFrame, text=headerText,
                         font=self.bigFontBold,
                         borderwidth=0, anchor='nw', bg='white',
                         fg=pwgui.Color.DARK_GREY_COLOR)
        label.grid(row=0, column=0, sticky='nw', padx=(20, 5), pady=10)

        # Body section
        bodyFrame = tk.Frame(self, bg='white')
        bodyFrame.grid(row=1, column=0, sticky='news')
        self._fillContent(bodyFrame)

        # Add the create project button
        btnFrame = tk.Frame(self, bg='white')
        btn = HotButton(btnFrame, text="Start demo",
                        font=self.bigFontBold,
                        command=self._onAction)
        btn.grid(row=0, column=1, sticky='ne', padx=10, pady=10)

        # Add the Import project button
        btn = Button(btnFrame, Message.LABEL_BUTTON_CANCEL,
                     Icon.ACTION_CLOSE,
                     font=self.bigFontBold,
                     command=self.windows.close)
        btn.grid(row=0, column=0, sticky='ne', padx=10, pady=10)

        btnFrame.grid(row=2, column=0, sticky='sew')
        btnFrame.columnconfigure(0, weight=1)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    def _fillContent(self, frame):
        labelFrame = tk.LabelFrame(frame, text=' General ', bg='white',
                                   font=self.bigFontBold)
        labelFrame.grid(row=0, column=0, sticky='nw', padx=20)

        defaultProjectName = "demo_" + datetime.datetime.now().strftime("%I%M%S")
        self._addPair(PROJECT_NAME, 1, labelFrame, value=defaultProjectName)
        self._addPair(MESSAGE, 4, labelFrame, widget='label')

        labelFrame.columnconfigure(0, weight=1)
        labelFrame.columnconfigure(0, minsize=120)
        labelFrame.columnconfigure(1, weight=1)

        labelFrame2 = tk.LabelFrame(frame, text=' Acquisition values ', bg='white',
                                    font=self.bigFontBold)

        labelFrame2.grid(row=1, column=0, sticky='nw', padx=20, pady=10)
        labelFrame2.columnconfigure(0, minsize=120)

        self.addFieldsFromTemplate(labelFrame2)

        frame.columnconfigure(0, weight=1)

    def _addPair(self, text, r, lf, widget='entry', traceCallback=None,
                 mouseBind=False, value=None):
        label = tk.Label(lf, text=text, bg='white',
                         font=self.bigFont)
        label.grid(row=r, column=0, padx=(10, 5), pady=2, sticky='ne')

        if not widget:
            return

        var = tk.StringVar()

        if value is not None:
            var.set(value)

        if widget == 'entry':
            widget = tk.Entry(lf, width=30, font=self.bigFont,
                              textvariable=var)
            if traceCallback:
                if mouseBind:  # call callback on click
                    widget.bind("<Button-1>", traceCallback, "eee")
                else:  # call callback on type
                    var.trace('w', traceCallback)
        elif widget == 'label':
            widget = tk.Label(lf, font=self.bigFont, textvariable=var)

        self.vars[text] = var
        widget.grid(row=r, column=1, sticky='nw', padx=(5, 10), pady=2)

    def _addCheckPair(self, label, r, lf, col=1):

        var = tk.IntVar()

        cb = tk.Checkbutton(lf, text=label, font=self.bigFont, bg='white',
                            variable=var)
        self.vars[label] = var
        self.checkvars.append(label)
        cb.grid(row=r, column=col, padx=5, sticky='nw')

    def addFieldsFromTemplate(self, labelFrame2):

        self._template = getTemplateSplit()

        self._fields = getFields(self._template)

        row = 2
        for field in self._fields.values():
            self._addPair(field.getTitle(), row, labelFrame2,
                          value=field.getValue())
            row += 1

    def _getVar(self, varKey):
        return self.vars[varKey]

    def _getValue(self, varKey):
        return self.vars[varKey].get()

    def _setValue(self, varKey, value):
        return self.vars[varKey].set(value)

    # noinspection PyUnusedLocal
    def _onAction(self, e=None):
        errors = []

        # Check the entered data
        for field in self._fields.values():
            newValue = self._getValue(field.getTitle())
            field.setValue(newValue)
            if not field.validate():
                errors.append("%s value does not validate. Value: %s, Type: %s"
                              % (field.getTitle(), field.getValue(),
                                 field.getType()))

        # Do more checks only if there are not previous errors
        if errors:
            errors.insert(0, "*Errors*:")
            self.windows.showError("\n  - ".join(errors))
        else:

            workflow = self._createTemplate()
            if workflow is not None:
                # Create the project
                self.createProjectFromWorkflow(workflow)

                self.windows.close()
                return

    def createProjectFromWorkflow(self, workflow):

        projectName = self._getValue(PROJECT_NAME)

        scipion = os.path.join(os.environ.get('SCIPION_HOME'), 'scipion')
        scriptsPath = os.path.join(os.environ.get('SCIPION_HOME'), 'scripts')

        # Download the required data
        # pwutils.runCommand(scipion +
        #                     " testdata --download jmbFalconMovies")

        # Create the project
        createProjectScript = os.path.join(scriptsPath, 'create_project.py')
        pwutils.runCommand(scipion + " python " + createProjectScript + " " +
                           projectName + " " + workflow)

        # Schedule the project
        scheduleProjectScript = os.path.join(scriptsPath, 'schedule_project.py')
        pwutils.runCommand(scipion + " python " + scheduleProjectScript + " " +
                           projectName)

        # Launch scipion
        pwutils.runCommand(scipion + " project " + projectName)

    def _createTemplate(self):

        try:
            # Where to write the json file.
            (fileHandle, path) = tempfile.mkstemp()

            replaceFields(self._fields.values(), self._template)

            finalJson = "".join(self._template)

            os.write(fileHandle, finalJson)
            os.close(fileHandle)

            print("New workflow saved at " + path)

        except Exception as e:
            self.windows.showError(
                "Couldn't create the template.\n" + e.message)
            traceback.print_exc()
            return None

        return path


class FormField(object):
    def __init__(self, index, title, value=None, varType=None):
        self._index = index
        self._title = title
        self._value = value
        self._type = varType

    def getTitle(self):
        return self._title

    def getIndex(self):
        return self._index

    def getType(self):
        return self._type

    def getValue(self):
        return self._value

    def setValue(self, value):
        self._value = value

    def validate(self):
        return validate(self._value, self._type)


""" FIELDS VALIDATION """
""" FIELDS TYPES"""
FIELD_TYPE_STR = "0"
FIELD_TYPE_BOOLEAN = "1"
FIELD_TYPE_PATH = "2"
FIELD_TYPE_INTEGER = "3"
FIELD_TYPE_DECIMAL = "4"


""" VALIDATION METHODS"""
def validate(value, fieldType):
    if fieldType == FIELD_TYPE_BOOLEAN:
        return validBoolean(value)
    elif fieldType == FIELD_TYPE_DECIMAL:
        return validDecimal(value)
    elif fieldType == FIELD_TYPE_INTEGER:
        return validInteger(value)
    elif fieldType == FIELD_TYPE_PATH:
        return validPath(value)
    elif fieldType == FIELD_TYPE_STR:
        return validString(value)

    else:
        print("Type %s for %snot recognized. Review the template." \
              % (type, value))
        return


def validString(value):
    return value is not None


def validInteger(value):
    return value.isdigit()


def validPath(value):
    return os.path.exists(value)


def validDecimal(value):

    try:
        float(value)
        return True
    except Exception as e:
        return False


def validBoolean(value):
    return value is True or value is False


def getFields(template):

    def fieldStr2Field(fieldIndex, fieldString):
        fieldLst = fieldString.split('|')

        title = fieldLst[0]
        defaultValue = fieldLst[1] if len(fieldLst) >= 2 else None
        varType = fieldLst[2] if len(fieldLst) >= 3 else None

        return FormField(fieldIndex, title, defaultValue, varType)

    fields = {}
    # For each field found in the template
    for index in xrange(1, len(template), 2):
        field = fieldStr2Field(index, template[index])
        fields[field.getTitle()] = field

    return fields


def replaceFields(fields, template):

    for field in fields:
        template[field.getIndex()] = field.getValue()


def getTemplateSplit():
    # Get the fields definition from the template
    templateStr = getTemplate()

    # Split the template by the field separator
    return templateStr.split(FIELD_SEP)


def getTemplate():

    template = """[
    {
        "object.className": "ProtImportMovies",
        "object.id": "2",
        "object.label": "Import movies",
        "object.comment": "",
        "runName": null,
        "runMode": 0,
        "importFrom": 0,
        "filesPath": "~Movie's folder|%(SCIPION_HOME)s/data/tests/relion13_tutorial/betagal/Micrographs|2~",
        "filesPattern": "*.mrcs",
        "copyFiles": false,
        "haveDataBeenPhaseFlipped": false,
        "acquisitionWizard": null,
        "voltage": ~Voltage|300|4~,
        "sphericalAberration": ~Spherical aberration|2|4~,
        "amplitudeContrast": ~Amplitude contrast|0.1|4~,
        "magnification": 59000,
        "samplingRateMode": 0,
        "samplingRate": ~Sampling rate|3.54|4~,
        "scannedPixelSize": 7.0,
        "doseInitial": 0.0,
        "dosePerFrame": ~Dose per frame|0.0|4~,
        "gainFile": null,
        "darkFile": null,
        "dataStreaming": true,
        "timeout": 7200,
        "fileTimeout": 30,
        "inputIndividualFrames": false,
        "numberOfIndividualFrames": null,
        "stackFrames": false,
        "writeMoviesInProject": false,
        "movieSuffix": "_frames.mrcs",
        "deleteFrames": false,
        "streamingSocket": false,
        "socketPort": 5000
    },
    {
        "object.className": "XmippProtMovieGain",
        "object.id": "313",
        "object.label": "xmipp3 - movie gain",
        "object.comment": "",
        "runName": null,
        "runMode": 0,
        "frameStep": 30,
        "movieStep": ~Gain estimation movie step|1|4~,
        "useExistingGainImage": false,
        "hostName": "localhost",
        "numberOfThreads": 1,
        "numberOfMpi": 1,
        "inputMovies": "2.outputMovies"
    },
    {
        "object.className": "ProtMotionCorr",
        "object.id": "56",
        "object.label": "Motioncorr",
        "object.comment": "",
        "runName": null,
        "runMode": 0,
        "gpuMsg": "True",
        "GPUIDs": "0",
        "alignFrame0": 1,
        "alignFrameN": 0,
        "useAlignToSum": true,
        "sumFrame0": 1,
        "sumFrameN": 0,
        "binFactor": 1.0,
        "cropOffsetX": 0,
        "cropOffsetY": 0,
        "cropDimX": 0,
        "cropDimY": 0,
        "doSaveAveMic": true,
        "doSaveMovie": false,
        "doComputePSD": false,
        "doComputeMicThumbnail": false,
        "computeAllFramesAvg": false,
        "extraParams": "",
        "useMotioncor2": true,
        "doApplyDoseFilter": false,
        "patchX": 5,
        "patchY": 5,
        "group": 1,
        "tol": 0.5,
        "doMagCor": false,
        "useEst": true,
        "scaleMaj": 1.0,
        "scaleMin": 1.0,
        "angDist": 0.0,
        "defectFile": null,
        "extraParams2": "",
        "doSaveUnweightedMic": true,
        "hostName": "localhost",
        "numberOfThreads": 1,
        "numberOfMpi": 1,
        "inputMovies": "2.outputMovies"
    },
    {
        "object.className": "ProtCTFFind",
        "object.id": "118",
        "object.label": "Ctffind",
        "object.comment": "",
        "runName": null,
        "runMode": 0,
        "recalculate": false,
        "sqliteFile": null,
        "ctfDownFactor": 1.0,
        "useCtffind4": true,
        "astigmatism": 100.0,
        "findPhaseShift": false,
        "minPhaseShift": 0.0,
        "maxPhaseShift": 3.15,
        "stepPhaseShift": 0.2,
        "resamplePix": true,
        "lowRes": 0.05,
        "highRes": 0.35,
        "minDefocus": 0.25,
        "maxDefocus": 4.0,
        "windowSize": 256,
        "hostName": "localhost",
        "numberOfThreads": 1,
        "numberOfMpi": 1,
        "inputMicrographs": "56.outputMicrographs"
    },
    {
        "object.className": "ProtMonitorSummary",
        "object.id": "164",
        "object.label": "Summary Monitor",
        "object.comment": "",
        "runName": null,
        "runMode": 0,
        "inputProtocols": ["2","56","118","313"],
        "samplingInterval": 60,
        "stddevValue": 0.04,
        "ratio1Value": 1.15,
        "ratio2Value": 4.5,
        "maxDefocus": 40000.0,
        "minDefocus": 1000.0,
        "astigmatism": 2000.0,
        "monitorTime": 30000.0,
        "cpuAlert": 101.0,
        "memAlert": 101.0,
        "swapAlert": 101.0,
        "doGpu": false,
        "gpusToUse": "0",
        "doNetwork": false,
        "netInterfaces": 1,
        "doDiskIO": false,
        "doMail": true,
        "emailFrom": "noreply-biocomp@cnb.csic.es",
        "emailTo": "user@domain",
        "smtp": "localhost",
        "publishCmd": ""
    },
    {
        "object.className": "SparxGaussianProtPicking",
        "object.id": "284",
        "object.label": "eman2 - sparx gaussian picker",
        "object.comment": "",
        "runName": null,
        "runMode": 0,
        "boxSize": 64,
        "lowerThreshold": 1.0,
        "higherThreshold": 1.4,
        "gaussWidth": 1.0,
        "inputMicrographs": "56.outputMicrographs"
    },
    {
        "object.className": "XmippProtExtractParticles",
        "object.id": "323",
        "object.label": "xmipp3 - extract particles",
        "object.comment": "",
        "runName": null,
        "runMode": 0,
        "downsampleType": 0,
        "downFactor": 1.0,
        "boxSize": 64,
        "doBorders": true,
        "doRemoveDust": true,
        "thresholdDust": 5.0,
        "doInvert": true,
        "doFlip": true,
        "doNormalize": true,
        "normType": 2,
        "backRadius": -1,
        "hostName": "localhost",
        "numberOfThreads": 4,
        "numberOfMpi": 1,
        "ctfRelations": "118.outputCTF",
        "inputCoordinates": "284.outputCoordinates"
    }
]"""
    # Replace environment variables
    template = template % os.environ

    return template


if __name__ == "__main__":
    wizWindow = BoxWizardWindow()
    wizWindow.show()


# ---------------------------------------------------------------------

from pyworkflow.tests import BaseTest

# Please set if your system is able to run CUDA devices #
hasCUDA = False
schedule = True
# ----------------------------------------------------- #

class TestPreprocessingWorkflowInStreaming(BaseTest):
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
                                  movieStep=20)
        protMG.inputMovies.set(protImport.outputMovies)
        protMG.useExistingGainImage.set(False)
        self.proj._registerProt(protMG)

        # ----------- MOTIONCOR ----------------------------
        if hasCUDA:
            protMC = self.newProtocol(ProtMotionCorr,
                                      objLabel='motioncor2')
            protMC.inputMovies.set(protImport.outputMovies)
            self._registerProt(protMC, 'outputMovies')

        # ----------- MAX SHIFT -----------------------------
            protMax1 = self.newProtocol(XmippProtMovieMaxShift,
                                       objLabel='max shift')
            protMax1.inputMovies.set(protMC.outputMovies)
            self._registerProt(protMax1, 'outputMicrographs')

            alignedMics = protMax1.outputMicrographs

        else:
        # ----------- CORR ALIGN ----------------------------
            protCA = self.newProtocol(XmippProtMovieCorr,
                                      objLabel='corr allignment')
            protCA.inputMovies.set(protImport.outputMovies)
            self.proj.launchProtocol(protCA, wait=False)
            self._waitOutput(protCA, 'outputMovies')

        # ----------- MAX SHIFT -----------------------------
            protMax2 = self.newProtocol(XmippProtMovieMaxShift,
                                       objLabel='max shift')
            protMax2.inputMovies.set(protCA.outputMovies)
            self.proj.launchProtocol(protMax2, wait=False)
            self._waitOutput(protMax2, 'outputMicrographs')

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
            protOF.inputMovies.set(protMax2.outputMovies)
            self.proj.launchProtocol(protOF, wait=False)
            self._waitOutput(protOF, 'outputMicrographs')

            alignedMics = protOF.outputMicrographs

        # --------- PREPROCESS MICS ---------------------------
        protInv = self.newProtocol(XmippProtPreprocessMicrographs,
                                    objLabel='invert contrast',
                                    # doDownsample=True, downFactor=1.5,
                                    doInvert=True, doCrop=False, runMode=1)
        protInv.inputMicrographs.set(alignedMics)
        self.proj.launchProtocol(protInv, wait=False)
        self._waitOutput(protInv, 'outputMicrographs')

        # --------- CTF ESTIMATION 1 ---------------------------
        protCTF1 = self.newProtocol(XmippProtCTFMicrographs,
                                    objLabel='XMIPP ctf estimation')
        protCTF1.inputMicrographs.set(protInv.outputMicrographs)
        self.proj.launchProtocol(protCTF1, wait=False)

        # --------- CTF ESTIMATION 2 ---------------------------
        protCTF2 = self.newProtocol(ProtCTFFind,
                                    objLabel='CTFFIND estimation')
        protCTF2.inputMicrographs.set(protInv.outputMicrographs)
        self.proj.launchProtocol(protCTF2, wait=False)

        # --------- CTF ESTIMATION 3 ---------------------------
        if hasCUDA:
            protCTF3 = self.newProtocol(ProtGctf,
                                        objLabel='gCTF estimation')
            protCTF3.inputMicrographs.set(protInv.outputMicrographs)
            self.proj.launchProtocol(protCTF3, wait=False)

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
        protCONS.inputCTF.set(protCTF1.outputCTF)
        protCONS.inputCTF2.set(protCTF2.outputCTF)
        self.proj.launchProtocol(protCONS, wait=False)
        self._waitOutput(protCONS, 'outputMicrographs')

        if hasCUDA:
            self._waitOutput(protCONS, 'outputCTF')
            # --------- CTF CONSENSUS 2 ---------------------------
            protCONS2 = self.newProtocol(XmippProtCTFConsensus,
                                        objLabel='ctf consensus',
                                        useDefocus=False,
                                        useAstigmatism=False,
                                        resolution=17.0,
                                        minConsResol=15.0
                                        )
            protCONS2.inputCTF.set(protCONS.outputCTF)
            protCONS2.inputCTF2.set(protCTF3.outputCTF)
            self.proj.launchProtocol(protCONS2, wait=False)
            self._waitOutput(protCONS2, 'outputMicrographs')

            # # ---------- INTERSECTION CTF CONSENSUS -----------------
            # protGoodCtfs = self.newProtocol(ProtSubSet,
            #                            setOperation=ProtSubSet.SET_INTERSECTION)
            # protGoodCtfs.inputFullSet.set(protCONS.outputMicrographs)
            # protGoodCtfs.inputSubSet.set(protCONS2.outputMicrographs)
            # self.proj.launchProtocol(protGoodCtfs, wait=False)
            # self._waitOutput(protGoodCtfs, 'outputMicrographs')

            goodCtfs = protCONS2

        else:
            goodCtfs = protCONS

        # FIXME: CTFconsensus doesn't works fine...
        #        The next two lines is to keep ahead without ctfConsensus
        goodCtfs.outputCTF = protCTF2.outputCTF
        goodCtfs.outputMicrographs = protInv.outputMicrographs
        # ---------------------------------------------------------------

        # --------- PARTICLE PICKING 1 ---------------------------
        protPP1 = self.newProtocol(SparxGaussianProtPicking,
                                  objLabel='SPARX particle picking',
                                  boxSize=80)
        protPP1.inputMicrographs.set(goodCtfs.outputMicrographs)
        self.proj.launchProtocol(protPP1, wait=False)

        # --------- PARTICLE PICKING 2 ---------------------------
        protPP2 = self.newProtocol(DogPickerProtPicking,
                                  objLabel='DOGPICKER particle picking',
                                  diameter=3.54*80)
        protPP2.inputMicrographs.set(goodCtfs.outputMicrographs)
        self.proj.launchProtocol(protPP2, wait=False)

        self._waitOutput(protPP1, 'outputCoordinates')
        self._waitOutput(protPP2, 'outputCoordinates')
        # --------- CONSENSUS PICKING ---------------------------
        protCP = self.newProtocol(XmippProtConsensusPicking,
                                  objLabel='consensus picking')
        protCP.inputCoordinates.set([protPP1.outputCoordinates,
                                     protPP2.outputCoordinates])
        self.proj.launchProtocol(protCP, wait=False)
        self._waitOutput(protCP, 'consensusCoordinates')

        # --------- EXTRACT PARTICLES ---------------------------
        protExtract = self.newProtocol(ProtRelionExtractParticles,  # Change to Xmipp extract when it works fine
                                       objLabel='extract particles',
                                       boxSize=80,
                                       downsampleType=1,
                                       doRemoveDust=True,
                                       doNormalize=True,
                                       doInvert=False,
                                       doFlip=False)
        protExtract.inputCoordinates.set(protPP1.outputCoordinates)  # protCP.consensusCoordinates-----------------------
        protExtract.inputMicrographs.set(protInv.outputMicrographs)
        # protExtract.ctfRelations.set(goodCtfs.outputCTF)           # uncomment this when ctfConsensus work fine
        self.proj.launchProtocol(protExtract, wait=False)
        self._waitOutput(protExtract, 'outputParticles')

        # --------- ELIM EMPTY PARTS ---------------------------
        protEEP = self.newProtocol(XmippProtEliminateEmptyParticles,
                                   objLabel='elim empty particles',
                                   inputType=0)
        protEEP.inputParticles.set(protExtract.outputParticles)
        self.proj.launchProtocol(protEEP, wait=False)
        self._waitOutput(protEEP, 'outputParticles')

        # --------- TRIGGER PARTS ---------------------------
        protTRIG = self.newProtocol(XmippProtTriggerData,
                                    objLabel='trigger data',
                                    outputSize=1000, delay=30,
                                    allParticles=True,
                                    splitParticles=False)
        protTRIG.inputParticles.set(protEEP.outputParticles)
        self.proj.launchProtocol(protTRIG, wait=False)
        self._waitOutput(protTRIG, 'outputParticles')
        #
        # --------- SCREEN PARTS ---------------------------
        protSCR = self.newProtocol(XmippProtScreenParticles,
                                    objLabel='screen particles')
        protSCR.inputParticles.set(protTRIG.outputParticles)
        protSCR.autoParRejection.set(XmippProtScreenParticles.REJ_MAXZSCORE)
        protSCR.autoParRejectionSSNR.set(XmippProtScreenParticles.REJ_PERCENTAGE_SSNR)
        protSCR.autoParRejectionVar.set(XmippProtScreenParticles.REJ_NONE)  # Change this to REJ_VARIANCE when Extraction is done by Xmipp!!
        self.proj.launchProtocol(protSCR, wait=False)
        self._waitOutput(protSCR, 'outputParticles')

        # --------- TRIGGER PARTS ---------------------------
        protTRIG2 = self.newProtocol(XmippProtTriggerData,
                                     objLabel='another trigger data',
                                     outputSize=2000, delay=30,
                                     allParticles=False,
                                     splitParticles=False)
        protTRIG2.inputParticles.set(protSCR.outputParticles)
        self.proj.launchProtocol(protTRIG2, wait=False)
        self._waitOutput(protTRIG2, 'outputParticles')


        # CL2Ds could be run in parallel, potential problem with
        # convertion to averages: "set of averages 1" should be
        # run after "cl2d 1" is finished and the same for
        # "set of averages 2", additional checks are needed

        # --------- CL2D 1 ---------------------------
        protCL = self.newProtocol(XmippProtCL2D, objLabel='cl2d',
                                  numberOfClasses=16, numberOfMpi=8)
        protCL.inputParticles.set(protTRIG2.outputParticles)
        self.proj.launchProtocol(protCL, wait=False)

        # --------- Relion 2D classify ---------------------------
        protCL2 = self.newProtocol(ProtRelionClassify2D,
                                   objLabel='relion 2D classification',
                                   numberOfClasses=16, numberOfMpi=8)
        protCL2.inputParticles.set(protTRIG2.outputParticles)
        self.proj.launchProtocol(protCL2, wait=False)

        self._waitOutput(protCL, 'outputClasses')
        # --------- CONVERT TO AVERAGES 1---------------------------
        protAVER1 = self.newProtocol(ProtUserSubSet,
                                     objLabel='set of averages 1',
                                     outputClassName="SetOfAverages",
                                     sqliteFile=os.path.join(
                                         protCL._getPath(),
                                         "classes2D_stable_core.sqlite,"))
        protAVER1.inputObject.set(protCL.outputClasses)
        self.proj.launchProtocol(protAVER1, wait=False)
        self._waitOutput(protAVER1, 'outputRepresentatives')

        self._waitOutput(protCL2, 'outputClasses')
        # --------- CONVERT TO AVERAGES 2---------------------------
        protAVER2 = self.newProtocol(ProtUserSubSet,
                                     objLabel='set of averages 2',
                                     outputClassName="SetOfAverages",
                                     sqliteFile=os.path.join(
                                         protCL2._getPath(),
                                         "classes2D.sqlite,"))
        protAVER2.inputObject.set(protCL2.outputClasses)
        self.proj.launchProtocol(protAVER2, wait=False)
        self._waitOutput(protAVER2, 'outputRepresentatives')

        # --------- JOIN SETS ---------------------------
        protJOIN = self.newProtocol(ProtUnionSet, objLabel='join sets')
        protJOIN.inputSets.append(protAVER1.outputRepresentatives)
        protJOIN.inputSets.append(protAVER2.outputRepresentatives)
        self.proj.launchProtocol(protJOIN, wait=False)
        self._waitOutput(protJOIN, 'outputSet')

        # --------- AUTO CLASS SELECTION ---------------------------
        protCLSEL = self.newProtocol(XmippProtEliminateEmptyParticles,
                                     objLabel='auto class selection',
                                     inputType=1,
                                     threshold=8.0)
        protCLSEL.inputParticles.set(protJOIN.outputSet)
        protCLSEL.inputAverages.set(protJOIN.outputSet)
        self.proj.launchProtocol(protCLSEL, wait=False)
        self._waitOutput(protCLSEL, 'outputParticles')

        # --------- INITIAL VOLUME ---------------------------
        protINITVOL = self.newProtocol(EmanProtInitModel,
                                       objLabel='Eman initial vol',
                                       symmetryGroup='d2')
        protINITVOL.inputSet.set(protCLSEL.outputParticles)
        self.proj.launchProtocol(protINITVOL, wait=True)

        # --------- RECONSTRUCT SIGNIFICANT ---------------------------
        protSIG = self.newProtocol(XmippProtReconstructSignificant,
                                   objLabel='Reconstruct significant',
                                   symmetryGroup='d2',
                                   iter=30)  # iter=15)
        protSIG.inputSet.set(protCLSEL.outputParticles)
        self.proj.launchProtocol(protSIG, wait=True)

        # --------- RECONSTRUCT RANSAC ---------------------------
        protRAN = self.newProtocol(XmippProtRansac,
                                   objLabel='Ransac significant',
                                   symmetryGroup='d2',
                                   iter=30)  # iter=15)
        protRAN.inputSet.set(protRAN.outputParticles)
        self.proj.launchProtocol(protCLSEL, wait=True)

        # --------- CREATING AN ALIGNED SET OF VOLUMES -----------
        protAVOL = self.newProtocol(XmippProtAlignVolume,
                                     objLabel='Join and align volumes',
                                     iter=30)  # iter=15)
        protAVOL.inputReference.set(protSIG.outputVolume)
        protAVOL.inputVolumes.append(protRAN.outputVolumes)
        protAVOL.inputVolumes.append(protINITVOL.outputVolumes)
        protAVOL.inputVolumes.append(protSIG.outputVolume)
        self.proj.launchProtocol(protAVOL, wait=True)


        # --------- SWARM CONSENSUS INITIAL VOLUME ---------------
        protSWARM = self.newProtocol(XmippProtReconstructSwarm,
                                     objLabel='Swarm initial volume',
                                     symmetryGroup='d2')
                                     # iter=30)  # iter=15)
        protSWARM.inputParticles.set(protTRIG2.outputParticles)
        protSWARM.inputVolumes.set(protAVOL.outputVolumes)
        self.proj.launchProtocol(protSWARM, wait=True)



#!/usr/bin/env python
# **************************************************************************
# *
# * Authors:     David Maluenda (dmaluenda@cnb.csic.es)
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
import sys
import re
import Tkinter as tk
import tkFileDialog
import tkMessageBox
import ttk
import tkFont
import time
from collections import OrderedDict
from ConfigParser import SafeConfigParser
import argparse

import pyworkflow as pw
import pyworkflow.utils as pwutils
from pyworkflow.gui.dialog import MessageDialog
from pyworkflow.manager import Manager
from pyworkflow.gui import Message, Icon
from pyworkflow.config import ProjectSettings
import pyworkflow.em as em

import pyworkflow.gui as pwgui
from pyworkflow.gui.project.base import ProjectBaseWindow
from pyworkflow.gui.widgets import HotButton, Button
import subprocess
from pyworkflow.object import Pointer
from pyworkflow.em.protocol import (ProtImportMovies, ProtMonitorSummary,
                                    ProtImportMicrographs, ProtImportAverages,
                                    ProtSubSet, ProtUnionSet, ProtUserSubSet,
                                    ProtExtractCoords, ProtMonitor2dStreamer)

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


VIEW_WIZARD = 'wizardview'


PROJECT_NAME = "PROJECT_NAME"
FRAMES = "FRAMES"
# FRAME0 = 'FRAME0'
# FRAMEN = 'FRAMEN'
DOSE0 = 'DOSE0'
DOSEF = 'DOSEF'
MICS2PICK = 'MICS2PICK'
PARTSIZE = 'PARTSIZE'
SYMGROUP = 'SYMGROUP'

# Protocol's contants
GPU_USAGE = 'GPU_USAGE'
# MOTIONCORR = "MOTIONCORR"
MOTIONCOR2 = "MOTIONCOR2"
OPTICAL_FLOW = "OPTICAL_FLOW"
# SUMMOVIE = "SUMMOVIE"
# CTFFIND4 = "CTFFIND4"
GCTF = "GCTF"
# EMAIL_NOTIFICATION = "EMAIL_NOTIFICATION"
# HTML_REPORT = "HTML_REPORT"
# GRIDS = "GRIDS"
# CS = "CS"
# MAG = "MAG"
CRYOLO = 'CRYOLO'
RELION = 'RELION'
GL2D = 'GL2D'

# Some related environment variables
DATA_FOLDER = 'DATA_FOLDER'
USER_NAME = 'USER_NAME'
SAMPLE_NAME = 'SAMPLE_NAME'
# MICROSCOPE = 'MICROSCOPE'
# DATA_BACKUP = 'DATA_BACKUP'
# PATTERN = 'PATTERN'
# PUBLISH = 'PUBLISH'
# SMTP_SERVER = 'SMTP_SERVER'
# SMTP_FROM = 'SMTP_FROM'
# SMTP_TO = 'SMTP_TO'

# PROTOCOLS = "Protocols"
# MONITORS = "Monitors"
# MICROSCOPE = "Microscope"


# - conf - #
DEPOSITION_PATH = 'DEPOSITION_PATH'
PATTERN = 'PATTERN'
SCIPION_PROJECT = 'SCIPION_PROJECT'
SIMULATION = 'SIMULATION'
RAWDATA_SIM = 'RAWDATA_SIM'
AMP_CONTR = 'AMP_CONTR'
SPH_AB = 'SPH_AB'
VOL_KV = 'VOL_KV'
SAMPLING = 'SAMPLING'
TIMEOUT = 'TIMEOUT'
blackOnWhite = 'blackOnWhite'
highCPUusage = 'highCPUusage'
partsToClass = 'partsToClass'


# Define some string constants for the form
LABELS = {
    # DATA_FOLDER: "Data folder",
    USER_NAME: "User name",
    SAMPLE_NAME: "Sample name",
    # DATA_BACKUP: 'Data Backup Dir',
    PROJECT_NAME: "Project name",
    FRAMES: "Frames range",
    # FRAME0: "First",
    # FRAMEN: "Last",
    DOSE0: "Initial dose",
    DOSEF: "Dose per frame",
    MICS2PICK: "Number of mics to manual pick",
    PARTSIZE: "Estimated particle size",
    SYMGROUP: "Estimated symmetry group",
    
    # Protocol's contants
    # GPU_USAGE: "Indicate the GPU id",
    # MOTIONCORR: "MotionCorr",
    MOTIONCOR2: "MotionCor2",
    CRYOLO: "Cryolo",
    RELION: "Relion",
    OPTICAL_FLOW: "Optical Flow",
    # SUMMOVIE: "Summovie",
    # CTFFIND4: "Ctffind4",
    GCTF: "gCtf",
    GL2D: "GL2D"
    # EMAIL_NOTIFICATION: "Email notification",
    # HTML_REPORT: "HTML Report"
}

# desired casting for the parameters (form and config)
formatConfParameters = {SIMULATION: bool,
                        RAWDATA_SIM: str,
                        AMP_CONTR: float,
                        SPH_AB: float,
                        VOL_KV: float,
                        SAMPLING: float,
                        TIMEOUT: 'splitTimesFloat',
                        blackOnWhite: bool,
                        highCPUusage: int,
                        partsToClass: int}

formatsParameters = {PARTSIZE: int,
                     SYMGROUP: str,
                     FRAMES: 'splitInt',
                     DOSE0: float,
                     DOSEF: float,
                     OPTICAL_FLOW: bool,
                     MICS2PICK: int,
                     MOTIONCOR2: int,
                     GCTF: int,
                     CRYOLO: int,
                     RELION: int,
                     GL2D: int}

class BoxWizardWindow(ProjectBaseWindow):
    """ Windows to manage all projects. """
    
    def __init__(self, config, **kwargs):
        try:
            title = '%s (%s on %s)' % (Message.LABEL_PROJECTS,
                                       pwutils.getLocalUserName(),
                                       pwutils.getLocalHostName())
        except Exception:
            title = Message.LABEL_PROJECTS
        
        settings = ProjectSettings()
        self.generalCfg = settings.getConfig()
        
        self.config = config
        ProjectBaseWindow.__init__(self, title, minsize=(400, 550), **kwargs)
        self.viewFuncs = {VIEW_WIZARD: BoxWizardView}
        self.manager = Manager()
        self.switchView(VIEW_WIZARD)


class BoxWizardView(tk.Frame):
    def __init__(self, parent, windows, **kwargs):
        tk.Frame.__init__(self, parent, bg='white', **kwargs)
        self.windows = windows
        self.manager = windows.manager
        self.root = windows.root
        self.vars = {}
        self.checkvars = []
        self.microscope = None
        # Regular expression to validate username and sample name
        self.re = re.compile('\A[a-zA-Z][a-zA-Z0-9_-]+\Z')
        
        # tkFont.Font(size=12, family='verdana', weight='bold')
        bigSize = pwgui.cfgFontSize + 2
        smallSize = pwgui.cfgFontSize - 2
        fontName = pwgui.cfgFontName
        
        self.bigFont = tkFont.Font(size=bigSize, family=fontName)
        self.bigFontBold = tkFont.Font(size=bigSize, family=fontName,
                                       weight='bold')
        
        self.projDateFont = tkFont.Font(size=smallSize, family=fontName)
        self.projDelFont = tkFont.Font(size=smallSize, family=fontName,
                                       weight='bold')
        self.manager = Manager()
        
        # Header section
        headerFrame = tk.Frame(self, bg='white')
        headerFrame.grid(row=0, column=0, sticky='new')
        headerText = "Create New Session"
        
        headerText += "  %s" % pwutils.prettyTime(dateFormat='%Y-%m-%d')
        
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
        btn = HotButton(btnFrame, text="Create New Session",
                        font=self.bigFontBold,
                        command=self._onAction)
        btn.grid(row=0, column=1, sticky='ne', padx=10, pady=10)
        
        # Add the Cancel project button
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

        def _addPair(key, r, lf, entry='text', traceCallback=None, mouseBind=False,
                     color='white', width=5, col=0, t1='', t2='', default=''):
            t = LABELS.get(key, key)
            label = tk.Label(lf, text=t, bg='white', font=self.bigFont)
            sti = 'nw' if col == 1 else 'e'
            label.grid(row=r, column=col, padx=(10, 5), pady=2, sticky=sti)
            
            if entry == 'text':
                var = tk.StringVar(value=default)
                entry = tk.Entry(lf, width=width, font=self.bigFont,
                                 textvariable=var, bg=color)
                if traceCallback:
                    if mouseBind:  # call callback on click
                        entry.bind("<Button-1>")#, traceCallback, "eee")
                    else:  # call callback on type
                        var.trace('w', traceCallback)
                self.vars[key] = var
                entry.grid(row=r, column=1, sticky='nw', padx=(5, 10), pady=2)

            elif entry == 'checkbox':
                var = tk.IntVar()

                cb = tk.Checkbutton(lf, font=self.bigFont, bg='white',
                                    variable=var)
                self.vars[key] = var
                self.checkvars.append(key)

                cb.grid(row=r, column=1, padx=5, sticky='nw')

            elif t1 != '':
                label1 = tk.Label(lf, text=t1, bg='white',
                                  font=self.bigFont)
                label1.grid(row=r, column=1, sticky='nw', padx=(5, 10), pady=2)

            if t2 != '':
                label2 = tk.Label(lf, text=t2, bg='white',
                             font=self.bigFont)
                label2.grid(row=r, column=2, sticky='nw', padx=(5, 10), pady=2)


        labelFrame = tk.LabelFrame(frame, text=' General ', bg='white',
                                   font=self.bigFontBold)
        labelFrame.grid(row=0, column=0, sticky='nw', padx=20)

        _addPair(PROJECT_NAME, 0, labelFrame, width=30, default=self._getProjectName(),
                 color='lightgray', traceCallback=self._onInputChange)
        _addPair(USER_NAME, 1, labelFrame, width=30, traceCallback=self._onInputChange)
        _addPair(SAMPLE_NAME, 2, labelFrame, width=30, traceCallback=self._onInputChange)
        
        labelFrame.columnconfigure(0, weight=1)
        labelFrame.columnconfigure(0, minsize=120)
        labelFrame.columnconfigure(1, weight=1)


        labelFrame2 = tk.LabelFrame(frame, text=' Pre-processing ', bg='white',
                                    font=self.bigFontBold)
        
        labelFrame2.grid(row=1, column=0, sticky='nw', padx=20, pady=10)
        labelFrame2.columnconfigure(0, minsize=120)

        _addPair(PARTSIZE, 0, labelFrame2, t2='Angstroms')
        _addPair(SYMGROUP, 1, labelFrame2, t2='(if unknown, set at c1)', default='c1')
        _addPair(FRAMES, 2, labelFrame2, t2='ex: 2-15 (left empty to take all frames)')
        _addPair(DOSE0, 3, labelFrame2, default='0', t2='e/A^2')
        _addPair(DOSEF, 4, labelFrame2, default='0', t2='(if 0, no dose weight is applied)')
        _addPair(OPTICAL_FLOW, 5, labelFrame2, entry='checkbox')
        _addPair(MICS2PICK, 6, labelFrame2, t2='(if 0, only automatic picking is done)')


        labelFrame3 = tk.LabelFrame(frame, text=' GPU usage ', bg='white',
                                    font=self.bigFontBold)

        labelFrame3.grid(row=2, column=0, sticky='nw', padx=20, pady=10)
        labelFrame3.columnconfigure(0, minsize=120)

        _addPair("Protocols", 0, labelFrame3, entry="else", t1='GPU id', t2="(-1 to use the alternative below)")
        _addPair(MOTIONCOR2, 1, labelFrame3, t2="(if not, Xmipp will be used)", default='-1')
        _addPair(GCTF, 2, labelFrame3, t2="(if not, ctfFind4 will be used)", default='-1')
        _addPair(CRYOLO, 3, labelFrame3, t2="(if not, there are other pickers)", default='-1')
        _addPair(RELION, 4, labelFrame3, t2="(if not, Relion with CPU will be used)", default='-1')
        _addPair(GL2D, 5, labelFrame3, t2="(if not, no reclasification will be done)", default='-1')

        frame.columnconfigure(0, weight=1)


    def _getConfValue(self, key, default=''):
        return self.windows.config.get(key, default)
    
    def _getValue(self, varKey):
        try:
            value = self.vars[varKey].get()
        except:
            value = None
        return value
    
    def _setValue(self, varKey, value):
        return self.vars[varKey].set(value)

    def get(self, varKey, default=None):
        return getattr(self, varKey, default)

    def _getProjectName(self):
        try:
            usr = self._getValue(USER_NAME)
        except:
            usr = ''
        try:
            sam = self._getValue(SAMPLE_NAME)
        except:
            sam = ''
        return '%s_%s_%s' % (pwutils.prettyTime(dateFormat='%Y%m%d'), usr, sam)

    def _onInputChange(self, *args):
        # Quick and dirty trick to skip this function first time
        # if SAMPLE_NAME not in self.vars:
        #     return
        self._setValue(PROJECT_NAME, self._getProjectName())

    def _createDataFolder(self, projPath, scipionProjPath):
        def _createPath(p):
            # Create the project path
            sys.stdout.write("Creating path '%s' ... " % p)
            pwutils.makePath(p)
            sys.stdout.write("DONE\n")

        # _createPath(projPath)

        # if self._getConfValue(GRIDS) == '1':
        #     for i in range(12):
        #         gridFolder = os.path.join(projPath, 'GRID_%02d' % (i + 1))
        #         _createPath(os.path.join(gridFolder, 'ATLAS'))
        #         _createPath(os.path.join(gridFolder, 'DATA'))

        _createPath(scipionProjPath)

    def castParameters(self, errors):
        for var, cast in formatsParameters.iteritems():
            try:
                value = self._getValue(var)
                if cast == 'splitInt':
                    if value == '':
                        aux = ['1', '0']
                    elif '-' in value:
                        aux = value.split('-')
                    else:
                        aux = ['0', '0']
                        errors.append("'%s' is not well formated (ie. 2-15)"
                                      % LABELS.get(var))
                    newvar = []
                    for item in aux:
                        newvar.append(int(item))
                else:
                    if value == '':
                        value = 0
                    newvar = cast(value)

                setattr(self, var, newvar)
            except ValueError as e:
                if cast == int:
                    errors.append("'%s' should be an integer" % LABELS.get(var))
                elif cast == float:
                    errors.append("'%s' should be a float" % LABELS.get(var))
                else:
                    errors.append("'%s': %s" % (LABELS.get(var), str(e)))

        return errors

    def castConf(self):
        for var, cast in formatConfParameters.iteritems():
            value = self._getConfValue(var)
            # print(" -> %s: %s %s" % (var, type(value), value))
            if cast == 'splitTimesFloat':
                if "*" in value:
                    newvar = reduce(lambda x, y: float(x)*float(y), value.split('*'))
                else:
                    newvar = float(value)
            elif cast == bool:
                newvar = True if value.lower() == 'True'.lower() else False
            else:
                newvar = cast(value)

            setattr(self, var, newvar)

            # print("    %s: %s %s" % (var, type(getattr(self, var)), getattr(self, var)))
    
    def _onAction(self, e=None):

        errors = []

        # Check form parameters
        dataFolder = pwutils.expandPattern(self._getConfValue(DEPOSITION_PATH))
        if not os.path.exists(dataFolder):
            errors.append("Data folder '%s' does not exists. \n"
                          "Check config file" % dataFolder)

        userName = self._getValue(USER_NAME)
        if self.re.match(userName.strip()) is None:
            errors.append("Wrong username")
        
        sampleName = self._getValue(SAMPLE_NAME)
        if self.re.match(sampleName.strip()) is None:
            errors.append("Wrong sample name")

        errors = self.castParameters(errors)

        # Do more checks only if there are not previous errors
        if not errors:
            if self.get(PARTSIZE) == 0:
                errors.append("'%s' should be larger than 0"
                              % LABELS.get(PARTSIZE))



            projName = self._getProjectName()
            dataPath = os.path.join(dataFolder, projName)

            # if not len(pwutils.glob(os.path.join(dataPath,
            #                                     self._getConfValue(PATTERN)))):
            #     errors.append("No file found in %s.\n"
            #                   "Make sure that the acquisition has been started."
            #                   % os.path.join(dataPath, self._getConfValue(PATTERN)))

            scipionProjPath = pwutils.expandPattern(self._getConfValue(SCIPION_PROJECT))
            if not errors:
                if os.path.exists(os.path.join(scipionProjPath, projName)):
                    errors.append("Project path '%s' already exists.\n"
                                  "Change User or Sample name" % projName)

        if errors:
            errors.insert(0, "*Errors*:")
            self.windows.showError("\n  - ".join(errors))
        else:
            # self._createDataFolder(dataPath, scipionProjPath)
            # command = os.path.join(os.getenv("SCIPION_HOME"),
            #                        "scripts/mirror_directory.sh")
            # if doBackup:
            #     subprocess.Popen([command, dataFolder, projName, backupFolder],
            #                      stdout=open('logfile_out.log', 'w'),
            #                      stderr=open('logfile_err.log', 'w')
            #                      )
            # print projName, dataPath, scipionProjPath

            self._createScipionProject(projName, dataPath, scipionProjPath)
            self.windows.close()

    
    def _createScipionProject(self, projName, dataPath, scipionProjPath):

        print(">>> HERE <<<")
        print("projName: %s" % projName)
        print("dataPath: %s" % dataPath)
        print("scipionProjPath: %s" % scipionProjPath)

        self.castConf()

        if self.get(SIMULATION):
            rawData = os.path.join(pwutils.expanduser(
                        self._getConfValue(RAWDATA_SIM)),
                        self._getConfValue(PATTERN))

            os.system('%s python %s "%s" %s %d&' % (pw.getScipionScript(),
                            pw.getScipionPath('scripts/simulate_acquisition.py'),
                            rawData, dataPath, self.get(TIMEOUT)))

        manager = Manager()
        project = manager.createProject(projName, location=scipionProjPath)

        # smtpServer = self._getConfValue(SMTP_SERVER, '')
        # smtpFrom = self._getConfValue(SMTP_FROM, '')
        # smtpTo = self._getConfValue(SMTP_TO, '')
        # doMail = self._getValue(EMAIL_NOTIFICATION)
        # doPublish = self._getValue(HTML_REPORT)

        count = 1
        while not len(pwutils.glob(os.path.join(dataPath,
                                                self._getConfValue(PATTERN)))):
            if count == 6:
                self.windows.close()

            string = ("No file found in %s.\n"
                      "Make sure that the acquisition has been started.\n\n"
                      % os.path.join(dataPath, self._getConfValue(PATTERN)))
            if count < 5:
                str2 = "Retrying... (%s/5)" % count
            else:
                str2 = "Last try..."

            self.windows.showInfo(string + str2)

            time.sleep(self.get(TIMEOUT) / 10)
            count += 1

        self.defineWorkflow(project, projName, dataPath, scipionProjPath)

        os.system('%s python %s %s &' % (pw.getScipionScript(),
                                         pw.getScipionPath('scripts/schedule_project.py'),
                                         projName))
        
        os.system('%s project %s &' % (pw.getScipionScript(), projName))
        
        self.windows.close()

    def defineWorkflow(self, project, projName, dataPath, scipionProjPath):
        def _registerProt(prot, output=None):
            project.saveProtocol(prot)

            if output is not None:
                self.summaryList.append(prot)
                self.summaryExt.append(output)

        def setExtendedInput(protDotInput, lastProt, extended):
            if isinstance(lastProt, list):
                for idx, prot in enumerate(lastProt):
                    inputPointer = Pointer(prot, extended=extended[idx])
                    protDotInput.append(inputPointer)
            else:
                protDotInput.set(lastProt)
                protDotInput.setExtended(extended)

        self.summaryList = []
        self.summaryExt = []

        # ***********   MOVIES   ***********************************************
        doDose = False if self.get(DOSEF) == 0 else True
        # ----------- IMPORT MOVIES -------------------
        protImport = project.newProtocol(ProtImportMovies,
                                  objLabel='import movies',
                                  importFrom=ProtImportMovies.IMPORT_FROM_FILES,
                                  filesPath=dataPath,
                                  filesPattern=self._getConfValue(PATTERN),
                                  amplitudeContrast=self.get(AMP_CONTR),
                                  sphericalAberration=self.get(SPH_AB),
                                  voltage=self.get(VOL_KV),
                                  samplingRate=self.get(SAMPLING),
                                  doseInitial=self.get(DOSE0),
                                  dosePerFrame=self.get(DOSEF),
                                  dataStreaming=True,
                                  timeout=self.get(TIMEOUT))
        _registerProt(protImport, 'outputMovies')

        # ----------- MOVIE GAIN --------------------------
        protMG = project.newProtocol(XmippProtMovieGain,
                                  objLabel='Xmipp - movie gain',
                                  frameStep=20,
                                  movieStep=20,
                                  useExistingGainImage=False)
        setExtendedInput(protMG.inputMovies, protImport, 'outputMovies')
        _registerProt(protMG, 'outputImages')

        # ----------- MOTIONCOR ----------------------------
        if self.get(MOTIONCOR2) > -1 and ProtMotionCorr is not None:
            protMA = project.newProtocol(ProtMotionCorr,
                                         objLabel='MotionCor2 - movie align.',
                                         gpuList=self._getValue(MOTIONCOR2),
                                         doApplyDoseFilter=doDose,
                                         patchX=9, patchY=9)
            setExtendedInput(protMA.inputMovies, protImport, 'outputMovies')
            _registerProt(protMA, 'outputMovies')
        else:
            # ----------- CORR ALIGN ----------------------------
            protMA = project.newProtocol(XmippProtMovieCorr,
                                         objLabel='Xmipp - corr. align.',
                                         alignFrame0=self.get(FRAMES)[0],
                                         alignFrameN=self.get(FRAMES)[1])
            setExtendedInput(protMA.inputMovies, protImport, 'outputMovies')
            _registerProt(protMA, 'outputMovies')

        # ----------- MAX SHIFT -----------------------------
        protMax = project.newProtocol(XmippProtMovieMaxShift,
                                      objLabel='Xmipp - max shift')
        setExtendedInput(protMax.inputMovies, protMA, 'outputMovies')
        _registerProt(protMax, 'outputMovies')

        # ----------- OF ALIGNMENT --------------------------
        if self._getValue(OPTICAL_FLOW):
            protOF = project.newProtocol(XmippProtOFAlignment,
                                         objLabel='Xmipp - OF align.',
                                         doApplyDoseFilter=doDose, # --------------- ASK ---------------
                                         applyDosePreAlign=False)  # -----------------------------------
            setExtendedInput(protOF.inputMovies, protMax, 'outputMovies')
            _registerProt(protOF, 'outputMicrographs')

            alignedMicsLastProt = protOF
        else:
            alignedMicsLastProt = protMax


        # *********   CTF ESTIMATION   *****************************************

        # --------- CTF ESTIMATION 1 ---------------------------
        protCTF1 = project.newProtocol(XmippProtCTFMicrographs,
                                       objLabel='Xmipp - ctf estimation')
        setExtendedInput(protCTF1.inputMicrographs,
                         alignedMicsLastProt, 'outputMicrographs')
        _registerProt(protCTF1, 'outputCTF')

        # --------- CTF ESTIMATION 2 ---------------------------
        if self.get(GCTF) > -1:
            protCTF2 = project.newProtocol(ProtGctf,
                                           objLabel='gCTF estimation',
                                           gpuList=self._getValue(GCTF))
            setExtendedInput(protCTF2.inputMicrographs,
                             alignedMicsLastProt, 'outputMicrographs')
            _registerProt(protCTF2)

        else:
            protCTF2 = project.newProtocol(ProtCTFFind,
                                           objLabel='GrigorieffLab - CTFfind')
            setExtendedInput(protCTF2.inputMicrographs,
                             alignedMicsLastProt, 'outputMicrographs')
            _registerProt(protCTF2)


        # --------- CTF CONSENSUS 1 ---------------------------
        protCTFs = project.newProtocol(XmippProtCTFConsensus,
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
        _registerProt(protCTFs, 'outputMicrographs')

        # *************   PICKING   ********************************************
        # Resizing to a sampling rate larger than 3A/px
        downSampPreMics = self.get(SAMPLING) / 3 if self.get(SAMPLING) < 3 else 1
        # Fixing an even boxsize big enough: int(x/2+1)*2 = ceil(x/2)*2 = even!
        bxSize = int(self.get(PARTSIZE) / self.get(SAMPLING)
                     / downSampPreMics / 2 + 1) * 2

        # --------- PREPROCESS MICS ---------------------------
        protPreMics = project.newProtocol(XmippProtPreprocessMicrographs,
                                          objLabel='Xmipp - preprocess Mics',
                                          doRemoveBadPix=True,
                                          doInvert=self.get(blackOnWhite),
                                          doDownsample=self.get(SAMPLING) < 3,
                                          downFactor=downSampPreMics)
        setExtendedInput(protPreMics.inputMicrographs,
                         protCTFs, 'outputMicrographs')
        _registerProt(protPreMics)

        # --------- PARTICLE PICKING 1 ---------------------------
        protPP1 = project.newProtocol(SparxGaussianProtPicking,
                                   objLabel='Eman - Sparx auto-picking',
                                   boxSize=bxSize)
        setExtendedInput(protPP1.inputMicrographs, protPreMics, 'outputMicrographs')
        _registerProt(protPP1, 'outputCoordinates')

        # --------- PARTICLE PICKING 2 ---------------------------
        if self.get(CRYOLO) > -1:
            protPP2 = project.newProtocol(SparxGaussianProtPicking,  # ------------------- Put CrYolo here!!
                                          objLabel='Sphire - CrYolo auto-picking',
                                          # gpuList=self._getValue(CRYOLO),
                                          boxSize=bxSize)
            setExtendedInput(protPP2.inputMicrographs, protPreMics, 'outputMicrographs')
            _registerProt(protPP2)

        if self.get(MICS2PICK) > 0:
            # -------- TRIGGER MANUAL-PICKER ---------------------------
            protTRIG0 = project.newProtocol(XmippProtTriggerData,
                                            objLabel='Xmipp - trigger some mics',
                                            outputSize=self.get(MICS2PICK),
                                            delay=30,
                                            allImages=False)
            setExtendedInput(protTRIG0.inputImages, protPreMics, 'outputMicrographs')
            _registerProt(protTRIG0)

            # -------- XMIPP MANUAL-PICKER -------------------------
            protPPman = project.newProtocol(XmippProtParticlePicking,
                                            objLabel='Xmipp - manual picking',
                                            doInteractive=False)
            setExtendedInput(protPPman.inputMicrographs,
                             protTRIG0, 'outputMicrographs')
            _registerProt(protPPman)

            # -------- XMIPP AUTO-PICKING ---------------------------
            protPPauto = project.newProtocol(XmippParticlePickingAutomatic,
                                             objLabel='Xmipp - auto picking',
                                             xmippParticlePicking=protPPman,
                                             micsToPick=1  # other
                                             )
            protPPauto.addPrerequisites(protPPman.getObjId())
            setExtendedInput(protPPauto.inputMicrographs,
                             protPreMics, 'outputMicrographs')
            _registerProt(protPPauto)

        # --------- CONSENSUS PICKING -----------------------
        pickers = [protPP1]
        pickersOuts = ['outputCoordinates']
        if self.get(CRYOLO) > -1:
            pickers.append(protPP2)
            pickersOuts.append('outputCoordinates')
        if self.get(MICS2PICK) > 0:
            pickers.append(protPPauto)
            pickersOuts.append('outputCoordinates')

        if len(pickers) > 1:
            # --------- CONSENSUS PICKING AND -----------------------
            protCPand = project.newProtocol(XmippProtConsensusPicking,
                                            objLabel='Xmipp - consensus picking (AND)',
                                            consensus=-1,
                                            consensusRadius=0.1*bxSize)
            setExtendedInput(protCPand.inputCoordinates, pickers, pickersOuts)
            _registerProt(protCPand, 'consensusCoordinates')

            # --------- CONSENSUS PICKING OR -----------------------
            protCPor = project.newProtocol(XmippProtConsensusPicking,
                                           objLabel='Xmipp - consensus picking (OR)',
                                           consensus=1,
                                           consensusRadius=0.1*bxSize)

            setExtendedInput(protCPor.inputCoordinates, pickers, pickersOuts)
            _registerProt(protCPor, 'consensusCoordinates')
            finalPicker = protCPor
            outputCoordsStr = 'consensusCoordinates'

        else:
            finalPicker = pickers[0]
            outputCoordsStr = pickersOuts[0]

        # ---------------------------------- OR/SINGLE PICKING BRANCH ----------

        # --------- EXTRACT PARTICLES OR ----------------------
        ORstr = ' (OR)' if len(pickers) > 1 else ''
        protExtraOR = project.newProtocol(XmippProtExtractParticles,
                                          objLabel='Xmipp - extract particles%s'%ORstr,
                                          boxSize=bxSize,
                                          downsampleType=0,  # Same as picking
                                          doRemoveDust=True,
                                          doNormalize=True,
                                          doInvert=False,
                                          doFlip=True)
        setExtendedInput(protExtraOR.inputCoordinates,
                         finalPicker, outputCoordsStr)
        setExtendedInput(protExtraOR.ctfRelations, protCTF1, 'outputCTF')
        _registerProt(protExtraOR, 'outputParticles')

        # ***********   PROCESS PARTICLES   ************************************

        # --------- ELIM EMPTY PARTS OR ---------------------------
        protEEPor = project.newProtocol(XmippProtEliminateEmptyParticles,
                                        objLabel='Xmipp - Elim. empty part.%s'%ORstr,
                                        inputType=0,
                                        threshold=1.1)
        setExtendedInput(protEEPor.inputParticles, protExtraOR, 'outputParticles')
        _registerProt(protEEPor, 'outputParticles')

        # --------- TRIGGER PARTS OR ---------------------------
        protTRIGor = project.newProtocol(XmippProtTriggerData,
                                         objLabel='Xmipp - trigger data to stats%s'%ORstr,
                                         outputSize=1000, delay=30,
                                         allImages=True,
                                         splitImages=False)
        setExtendedInput(protTRIGor.inputImages, protEEPor, 'outputParticles')
        _registerProt(protTRIGor)

        # --------- SCREEN PARTS OR ---------------------------
        protSCRor = project.newProtocol(XmippProtScreenParticles,
                                        objLabel='Xmipp - Screen particles%s'%ORstr)
        protSCRor.autoParRejection.set(XmippProtScreenParticles.REJ_MAXZSCORE)
        protSCRor.autoParRejectionSSNR.set(XmippProtScreenParticles.REJ_PERCENTAGE_SSNR)
        protSCRor.autoParRejectionVar.set(XmippProtScreenParticles.REJ_VARIANCE)
        setExtendedInput(protSCRor.inputParticles, protTRIGor, 'outputParticles')
        _registerProt(protSCRor, 'outputParticles')

        # ----------------------------- END OF OR/SINGLE PICKING BRANCH --------

        # ----------------------------- AND PICKING BRANCH ---------------------
        if len(pickers) < 2:  # if so, Elim. Empty and Screen are the same of above
            protSCR = protSCRor
        else:
            # --------- EXTRACT PARTICLES AND ----------------------
            protExtract = project.newProtocol(XmippProtExtractParticles,
                                              objLabel='Xmipp - extract particles (AND)',
                                              boxSize=bxSize,
                                              downsampleType=0,  # Same as picking
                                              doRemoveDust=True,
                                              doNormalize=True,
                                              doInvert=False,
                                              doFlip=True)
            setExtendedInput(protExtract.inputCoordinates,
                             protCPand, 'consensusCoordinates')
            setExtendedInput(protExtract.ctfRelations, protCTF1, 'outputCTF')
            _registerProt(protExtract, 'outputParticles')

            # --------- ELIM EMPTY PARTS AND ---------------------------
            protEEP = project.newProtocol(XmippProtEliminateEmptyParticles,
                                          objLabel='Xmipp - Elim. empty part. (AND)',
                                          inputType=0,
                                          threshold=1.1)
            setExtendedInput(protEEP.inputParticles, protExtract, 'outputParticles')
            _registerProt(protEEP, 'outputParticles')

            # --------- TRIGGER PARTS AND  ---------------------------
            protTRIG = project.newProtocol(XmippProtTriggerData,
                                           objLabel='Xmipp - trigger data to stats (AND)',
                                           outputSize=1000, delay=30,
                                           allImages=True,
                                           splitImages=False)
            setExtendedInput(protTRIG.inputImages, protEEP, 'outputParticles')
            _registerProt(protTRIG)

            # --------- SCREEN PARTS AND  ---------------------------
            protSCR = project.newProtocol(XmippProtScreenParticles,
                                          objLabel='Xmipp - screen particles (AND)')
            protSCR.autoParRejection.set(XmippProtScreenParticles.REJ_MAXZSCORE)
            protSCR.autoParRejectionSSNR.set(XmippProtScreenParticles.REJ_PERCENTAGE_SSNR)
            protSCR.autoParRejectionVar.set(XmippProtScreenParticles.REJ_VARIANCE)
            setExtendedInput(protSCR.inputParticles, protTRIG, 'outputParticles')
            _registerProt(protSCR, 'outputParticles')

        # ************   CLASSIFY 2D   *****************************************

        # --------- TRIGGER PARTS ---------------------------
        protTRIG2 = project.newProtocol(XmippProtTriggerData,
                                        objLabel='Xmipp - trigger data to classify',
                                        outputSize=self.get(partsToClass),
                                        delay=30,
                                        allImages=False)
        setExtendedInput(protTRIG2.inputImages, protSCR, 'outputParticles')
        _registerProt(protTRIG2)

        # --------- XMIPP CL2D ---------------------------
        protCL = project.newProtocol(XmippProtCL2D,
                                     objLabel='Xmipp - Cl2d',
                                     doCore=False,
                                     numberOfClasses=16,
                                     numberOfMpi=int(self.get(highCPUusage) / 2))
        setExtendedInput(protCL.inputParticles, protTRIG2, 'outputParticles')
        _registerProt(protCL)

        # --------- AUTO CLASS SELECTION I---------------------------
        protCLSEL1 = project.newProtocol(XmippProtEliminateEmptyClasses,
                                         objLabel='Xmipp - Auto class selection I',
                                         threshold=8.0)
        setExtendedInput(protCLSEL1.inputClasses, protCL, 'outputClasses')
        _registerProt(protCLSEL1, 'outputAverages')

        # --------- Relion 2D classify ---------------------------
        protCL2 = project.newProtocol(ProtRelionClassify2D,
                                      objLabel='Relion - 2D classifying',
                                      doGpu=self.get(RELION) > -1,
                                      gpusToUse=self._getValue(RELION),
                                      numberOfClasses=16,
                                      numberOfMpi=int(self.get(highCPUusage) / 2))
        setExtendedInput(protCL2.inputParticles, protTRIG2, 'outputParticles')
        _registerProt(protCL2)

        # --------- AUTO CLASS SELECTION I---------------------------
        protCLSEL2 = project.newProtocol(XmippProtEliminateEmptyClasses,
                                         objLabel='Xmipp - Auto class selection II',
                                         threshold=8.0)
        setExtendedInput(protCLSEL2.inputClasses, protCL2, 'outputClasses')
        _registerProt(protCLSEL2, 'outputAverages')

        # --------- JOIN SETS ---------------------------
        protJOIN = project.newProtocol(ProtUnionSet, objLabel='Scipion - Join sets')
        setExtendedInput(protJOIN.inputSets,
                         [protCLSEL1, protCLSEL2],
                         ['outputAverages', 'outputAverages'])
        _registerProt(protJOIN)

        # ***************   INITIAL VOLUME   ***********************************

        # --------- EMAN INIT VOLUME ---------------------------
        protINITVOL = project.newProtocol(EmanProtInitModel,
                                          objLabel='Eman - Initial vol',
                                          symmetryGroup=self.get(SYMGROUP),
                                          numberOfThreads=int(self.get(highCPUusage)/4))
        setExtendedInput(protINITVOL.inputSet, protJOIN, 'outputSet')
        _registerProt(protINITVOL)

        # --------- RECONSTRUCT SIGNIFICANT ---------------------------
        protSIG = project.newProtocol(XmippProtReconstructSignificant,
                                      objLabel='Xmipp - Recons. significant',
                                      symmetryGroup=self.get(SYMGROUP),
                                      numberOfMpi=int(self.get(highCPUusage)/2))
        setExtendedInput(protSIG.inputSet, protJOIN, 'outputSet')
        _registerProt(protSIG)

        # --------- RECONSTRUCT RANSAC ---------------------------
        protRAN = project.newProtocol(XmippProtRansac,
                                      objLabel='Xmipp - Ransac significant',
                                      symmetryGroup=self.get(SYMGROUP),
                                      numberOfThreads=int(self.get(highCPUusage)/4))
        setExtendedInput(protRAN.inputSet, protJOIN, 'outputSet')
        _registerProt(protRAN)

        # --------- CREATING AN ALIGNED SET OF VOLUMES -----------
        protAVOL = project.newProtocol(XmippProtAlignVolume,
                                       objLabel='Xmipp - Join/Align volumes',
                                       numberOfThreads=self.get(highCPUusage))
        setExtendedInput(protAVOL.inputReference, protSIG, 'outputVolume')
        setExtendedInput(protAVOL.inputVolumes,
                         [protINITVOL, protRAN, protSIG],
                         ['outputVolumes', 'outputVolumes', 'outputVolume'])
        _registerProt(protAVOL)

        # --------- SWARM CONSENSUS INITIAL VOLUME ---------------
        protSWARM = project.newProtocol(XmippProtReconstructSwarm,
                                        objLabel='Xmipp - Swarm init. vol.',
                                        symmetryGroup=self.get(SYMGROUP),
                                        numberOfMpi=self.get(highCPUusage))
        setExtendedInput(protSWARM.inputParticles, protTRIG2, 'outputParticles')
        setExtendedInput(protSWARM.inputVolumes, protAVOL, 'outputVolumes')
        _registerProt(protSWARM, 'outputVolume')

        # --------- RESIZE THE INITIAL VOL TO FULL SIZE ----------
        protVOLfull = project.newProtocol(XmippProtCropResizeVolumes,
                                          objLabel='Resize volume - FULL FIZE',
                                          doResize=True,
                                          resizeOption=0,  # fix samplig rate
                                          resizeSamplingRate=self.get(SAMPLING))
        setExtendedInput(protVOLfull.inputVolumes, protSWARM, 'outputVolume')
        _registerProt(protVOLfull)

        # ************   FINAL PROTOCOLS   *************************************

        # --------- ADDING 2D CLASSIFIERS -------------------------
        protStreamer = project.newProtocol(ProtMonitor2dStreamer,
                                           objLabel='Scipion - Streamer',
                                           input2dProtocol=protCL2,
                                           batchSize=2000,
                                           startingNumber=self.get(partsToClass),
                                           samplingInterval=1)
        setExtendedInput(protStreamer.inputParticles, protSCRor, 'outputParticles')
        protStreamer.addPrerequisites(protCL2.getObjId())
        _registerProt(protStreamer)

        # -------------------------- FULL SIZE PARTICLES -----
        # --------- EXTRACT COORD ----------------------------
        protExtraC = project.newProtocol(ProtExtractCoords,
                                         objLabel='Scipion - extrac coord.')
        setExtendedInput(protExtraC.inputParticles, protSCRor, 'outputParticles')
        setExtendedInput(protExtraC.inputMicrographs, protPreMics, 'outputMicrographs')
        _registerProt(protExtraC)

        # --------- EXTRACT FULL SIZE PART ------------------
        fullBoxSize = int(self.get(PARTSIZE) / self.get(SAMPLING)) + 1
        protExtraFull = project.newProtocol(XmippProtExtractParticles,
                                            objLabel='Xmipp - extract part. FULL SIZE',
                                            boxSize=fullBoxSize,
                                            downsampleType=1,  # other mics
                                            doRemoveDust=True,
                                            doNormalize=True,
                                            doInvert=self.get(blackOnWhite),
                                            doFlip=True)
        setExtendedInput(protExtraFull.inputCoordinates,
                         protExtraC, 'outputCoordinates')
        setExtendedInput(protExtraFull.inputMicrographs,
                         protCTFs, 'outputMicrographs')
        setExtendedInput(protExtraFull.ctfRelations, protCTFs, 'outputCTF')
        _registerProt(protExtraFull, 'outputParticles')



        # # --------- GL2D in streaming --------------------
        # if self.get(GL2D) > -1:
        #     protGL2D = project.newProtocol(XmippProtStrGpuCrrSimple,
        #                                 objLabel='Xmipp - GL2D static',
        #                                 gpuList=self._getValue(GL2D))
        #     setExtendedInput(protGL2D.inputRefs, protJOIN, 'outputSet')
        #     setExtendedInput(protGL2D.inputParticles, protSCRor, 'outputParticles')
        #     _registerProt(protGL2D, 'outputClasses')

        # --------- SUMMARY MONITOR -----------------------
        protMonitor = project.newProtocol(ProtMonitorSummary,
                                       objLabel='Scipion - Summary Monitor')
        setExtendedInput(protMonitor.inputProtocols,
                         self.summaryList, self.summaryExt)
        _registerProt(protMonitor)


def createDictFromConfig():
    """ Read the configuration from scipion/config/scipionbox.conf.
     A dictionary will be created where each key will be a section starting
     by MICROSCOPE:, all variables that are in the GLOBAL section will be
     inherited by default.
    """
    # Read from config file.
    confDict = {}
    cp = SafeConfigParser()

    cp.optionxform = str  # keep case (stackoverflow.com/questions/1611799)
    
    confFile = pw.getConfigPath("scipionbox.conf")
    
    print "Reading conf file: ", confFile
    cp.read(confFile)

    for section in cp.sections():
        for opt in cp.options(section):
            confDict[opt] = cp.get(section, opt)

    return confDict


if __name__ == "__main__":
    confDict = createDictFromConfig()
    
    wizWindow = BoxWizardWindow(confDict)
    wizWindow.show()

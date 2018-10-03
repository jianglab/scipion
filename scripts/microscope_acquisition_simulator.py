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

import os
import time
import pyworkflow.utils as pwutils

TIMESTEP = 1*60  # time in seconds between imported files

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
        time.sleep(TIMESTEP)




if __name__ == "__main__":
    full
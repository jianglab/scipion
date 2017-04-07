/***************************************************************************
 *
 * Authors:    Amaya Jimenez      ajimenez@cnb.csic.es (2002)
 *
 * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
 * 02111-1307  USA
 *
 *  All comments concerning this program package may be sent to the
 *  e-mail address 'xmipp@cnb.csic.es'
 ***************************************************************************/

#include "gpu_rotate_image.h"



void transformationMatrixCuda(const MDRow &imageGeo, Matrix2D<double> &A, bool isVol, int splineDegree){

    double psi = 0, rot = 0., tilt = 0., shiftX = 0., shiftY = 0., shiftZ=0., scale=1.;
    bool flip;
    int dim = A.Xdim() - 1;

    imageGeo.getValue(MDL_ANGLE_PSI, psi);
    imageGeo.getValue(MDL_SHIFT_X, shiftX);
    imageGeo.getValue(MDL_SHIFT_Y, shiftY);
    imageGeo.getValue(MDL_SCALE, scale);
    imageGeo.getValue(MDL_FLIP, flip);

    psi = realWRAP(psi, 0., 360.);

    //AJ to make shifts in the same direction as transform_geometry
    if (splineDegree<BSPLINE3){
    	shiftX=-shiftX;
    	shiftY=-shiftY;
    }

    if(isVol){
    	imageGeo.getValue(MDL_ANGLE_ROT, rot);
    	imageGeo.getValue(MDL_ANGLE_TILT, tilt);
    	imageGeo.getValue(MDL_SHIFT_Z, shiftZ);
    	//AJ to make shifts in the same direction as transform_geometry
    	if(splineDegree<BSPLINE3){
    		shiftZ=-shiftZ;
    	}
    	//AJ the - sign in the angles is to make rotations in the same direction as transform_geometry
    	Euler_angles2matrix(-rot, -tilt, -psi, A, true);
    	dMij(A, 2, dim) = shiftZ;
    }else{
    	//AJ the - sign in the angle is to make rotations in the same direction as transform_geometry
    	rotation2DMatrix(-psi, A, true);
    }
    dMij(A, 0, dim) = shiftX;
    dMij(A, 1, dim) = shiftY;

    if (scale != 1.){
    	if (scale==0.) // Protection against badly formed metadatas
    		scale=1.0;
        if (dim == 2){
            M3x3_BY_CT(A, A, (double)1/scale);
        }
        else if (dim == 3){
        	M4x4_BY_CT(A, A, (double)1/scale);
        }
        dMij(A, dim, dim) = 1.;
    }

    if (flip){
    	dMij(A, 0, 0) *= -1.;
    	dMij(A, 0, 1) *= -1.;
        if (dim == 3)
        	dMij(A, 0, 2) *= -1.;
    }

}


//CUDA functions
void cuda_rotate_image(float *image, float *rotated_image, size_t Xdim,
		size_t Ydim, size_t Zdim, double* ang, int interp, int wrap, int first_call){

	if (interp == BSPLINE3)
		cuda_rotate_image_bspline(image, rotated_image, Xdim, Ydim, Zdim, ang, wrap, first_call);
	else
	{
	    if (interp == NEAREST)
	    	interp = CUDA_NEAREST;
	    else if (interp == LINEAR)
	    	interp = CUDA_LINEAR;
	    else
	    	REPORT_ERROR(ERR_PARAM_INCORRECT,"Non supported interpolation type");
		cuda_rotate_image_linear_nearest(image, rotated_image, Xdim, Ydim, Zdim, ang, interp, wrap, first_call);

	}
}


// Read arguments ==========================================================
void ProgGpuRotateImage::readParams()
{

    XmippMetadataProgram::readParams();
    String degree = getParam("--interp");
    if (degree == "spline")
        splineDegree = BSPLINE3;
    else if (degree == "linear")
        splineDegree = LINEAR;
    else if (degree == "nearest")
        splineDegree =  NEAREST;
    else
    	REPORT_ERROR(ERR_PARAM_INCORRECT,"Non supported interpolation type");

    String mode = getParam("--wrap");
    if (mode == "border")
    	wrapMode = CUDA_BORDER;
    else if (mode == "clamp")
        wrapMode = CUDA_CLAMP;
    else if (mode == "wrap")
        wrapMode =  CUDA_WRAP;
    else
        REPORT_ERROR(ERR_PARAM_INCORRECT,"Non supported wrap mode");

    String useMD = getParam("--use_md");
    if (useMD == "md")
        use_md = USE_MD;
    else if (useMD == "command")
    	use_md = USE_COMMAND;
    else if (useMD == "both")
    	use_md =  USE_BOTH;
    else
        REPORT_ERROR(ERR_PARAM_INCORRECT,"Non supported wrap mode");

    flip = checkParam("--flip");
    first_call=0;
}

// Show ====================================================================
/*
void ProgGpuRotateImage::show()
{
    std::cout
	<< "Input:          " << fnRef    << std::endl
	<< "Output:          " << fnOut    << std::endl
	<< "Interpolation method: " << splineDegree    << std::endl
    ;
}
*/
// usage ===================================================================
void ProgGpuRotateImage::defineParams()
{
    each_image_produces_an_output = true;
    save_metadata_stack = true;
    keep_input_columns = true;
    allow_apply_geo = true;
    isMd = false;
    XmippMetadataProgram::defineParams();
    addUsageLine("Computes the rotation of an image or a volume with CUDA in GPU");
    addParamsLine("[--rotate <ang=0>]         : Inplane rotation in 2D images.");
    addParamsLine("                           : Positive angle is a clockwise rotation");
    addParamsLine("[--rotate_volume <rot> <tilt> <psi>]   : Rotation of volumes.");
    addParamsLine("                                       : Rotate with these Euler angles (ZYZ convention)");
    addParamsLine("[--interp <interpolation_type=spline>] : Interpolation type to be used. ");
    addParamsLine("      where <interpolation_type>");
    addParamsLine("        spline          : Use spline interpolation");
    addParamsLine("        linear          : Use bilinear/trilinear interpolation");
    addParamsLine("        nearest         : Use nearest neighbor interpolation");
    addParamsLine("[--shift <x=0> <y=0> <z=0>]            : Shift by x, y and z");
    addParamsLine("[--scale <factor=1>]                   : Perform Scaling. Factor 0.5 halves and 2 doubles");
    addParamsLine("[--flip]                               : Flip images, only valid for 2D");
    addParamsLine("[--wrap <wrap_type=clamp>] : Wrapping type to be used");
    addParamsLine("      where <wrap_type>");
    addParamsLine("        border          : Padding with zero values");
    addParamsLine("        clamp           : Padding with the border pixel values");
    addParamsLine("        wrap            : Padding with the image repeated, only valid for non-spline interpolation ");
    addParamsLine("[--use_md <use_md=command>] : Choose between use the transformation parameters in the metadata, by command line, or a combination of both");
    addParamsLine("      where <use_md>");
    addParamsLine("        md              : Use metadata parameters");
    addParamsLine("        command         : Use the command line parameters");
    addParamsLine("        both            : Use a combination between metadata and command line parameters");
}


void ProgGpuRotateImage::preProcess()
{


	std::cout << "wrapMode = " << wrapMode << std::endl;

    //If zdimOut greater than 1, is a volume
    isVol = (zdimOut > 1);
    dim = isVol ? 3 : 2;

    //if(wrapMode==CUDA_WRAP &&  isVol)
    		//REPORT_ERROR(ERR_PARAM_INCORRECT,"Non supported wrap mode with volumes");

    if(wrapMode==CUDA_WRAP &&  splineDegree == BSPLINE3)
        	REPORT_ERROR(ERR_PARAM_INCORRECT,"Non supported wrap mode spline interpolation");

    A.initIdentity(dim+1);


    if(use_md!=USE_MD){
    	if(use_md==USE_BOTH){
    		isMd=true;
    	}else if(use_md==USE_COMMAND){
    		isMd=false;
    	}
    	MDRow rowGeo;
    	if (checkParam("--shift")){
    		rowGeo.setValue(MDL_SHIFT_X, getDoubleParam("--shift", 0));
    		rowGeo.setValue(MDL_SHIFT_Y, getDoubleParam("--shift", 1));
    		if(isVol){
    			rowGeo.setValue(MDL_SHIFT_Z, getDoubleParam("--shift", 2));
    		}
    	}

    	if (checkParam("--scale")){
    		rowGeo.setValue(MDL_SCALE, getDoubleParam("--scale"));
    	}

    	if (isVol){
    		if (checkParam("--rotate_volume")){
    			rowGeo.setValue(MDL_ANGLE_ROT, getDoubleParam("--rotate_volume", 0));
    			rowGeo.setValue(MDL_ANGLE_TILT, getDoubleParam("--rotate_volume", 1));
    			rowGeo.setValue(MDL_ANGLE_PSI, getDoubleParam("--rotate_volume", 2));
    		}
    	}else{
    		if (checkParam("--rotate")){
    			rowGeo.setValue(MDL_ANGLE_PSI, getDoubleParam("--rotate"));
    		}
    	}

    	//Here A has the information about shift and rotation if they are supplied by command line
    	transformationMatrixCuda(rowGeo, A, isVol, splineDegree);

    	if (flip){
    		MAT_ELEM(A, 0, 0) *= -1.;
    		MAT_ELEM(A, 0, 1) *= -1.;
    		if (dim == 3)
    			MAT_ELEM(A, 0, 2) *= -1.;
    	}

    }//end if(use_md!=USE_MD)
    else if(use_md==USE_MD){
    	isMd=true;
    }
}


//#define DEBUG
// Compute distance --------------------------------------------------------
void ProgGpuRotateImage::processImage(const FileName &fnRef, const FileName &fnImgOut, const MDRow &rowIn, MDRow &rowOut)
{

//#define TIME
#ifdef TIME
	clock_t t_ini1, t_fin1;
	double secs1;
	t_ini1 = clock();
#endif

	first_call++;

	dim = isVol ? 3 : 2;

	R.initIdentity(dim+1);

    Image<float> Iref, Iout;
    Iref.read(fnRef);
    size_t Xdim, Ydim, Zdim, Ndim;
    Iref.getDimensions(Xdim, Ydim, Zdim, Ndim);

    if (Ndim>1){
    	REPORT_ERROR(ERR_MATRIX_DIM,"This program does not handle stacks");
    }

    if(isMd){
    	transformationMatrixCuda(rowOut, R, isVol, splineDegree);
    }

    R = A * R;

    double *rot_vector = MATRIX2D_ARRAY(R);

    MultidimArray<float> rotated_image(Zdim,Ydim,Xdim);

    float *original_image_gpu = MULTIDIM_ARRAY(Iref());
    float *rotated_image_gpu = MULTIDIM_ARRAY(rotated_image);

	cuda_rotate_image(original_image_gpu, rotated_image_gpu, Xdim, Ydim, Zdim, rot_vector, splineDegree, wrapMode, first_call);

	Iout() = rotated_image;
    Iout.write(fnImgOut);

#ifdef TIME
    t_fin1 = clock();
    secs1 = (double)(t_fin1 - t_ini1) / CLOCKS_PER_SEC;
    printf("Total: %.16g milisegundos\n", secs1 * 1000.0);
#endif

}


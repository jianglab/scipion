/***************************************************************************
 *
 * Authors:     Carlos Oscar S. Sorzano (coss@cnb.uam.es)
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
 *  e-mail address 'xmipp@cnb.uam.es'                                  
 ***************************************************************************/

#include "../Prog_microscope.hh"
#include <XmippData/xmippArgs.hh>

/* Read parameters --------------------------------------------------------- */
void Prog_Microscope_Parameters::read(int argc, char **argv) {
   Prog_parameters::read(argc,argv);
   fn_ctf=get_param(argc,argv,"-ctf","");
   sigma=AtoF(get_param(argc,argv,"-noise","0"));
   low_pass_before_CTF=AtoF(get_param(argc,argv,"-low_pass","0"));
   fn_after_ctf=get_param(argc,argv,"-after_ctf","");
   defocus_change=AtoF(get_param(argc,argv,"-defocus_change","0"));
   fn_out_pure_ctf=get_param(argc,argv,"-out_pure_ctf","");
   
   produce_side_info();
}

/* Usage ------------------------------------------------------------------- */
void Prog_Microscope_Parameters::usage() {
   Prog_parameters::usage();
   cerr << "  [-ctf <CTF file>]         : a Xmipp Fourier Image or a CTF description\n"
        << "  [-defocus_change <v=0%>]  : change in the defocus value\n"
	<< "  [-low_pass <w=0>]         : low pass filter for noise before CTF\n"
        << "  [-noise <stddev=0>]       : noise to be added\n"
	<< "  [-after_ctf <spectrum>]   : a Xmipp Fourier Image or a CTF description with\n"
	<< "                              the root squared spectrum of noise\n"
	<< "                              after the CTF\n"
        << "  [-out_pure_ctf <filename>]: If provided the pure CTF component will\n"
        << "                              be written in this file\n"
   ;
}

/* Show -------------------------------------------------------------------- */
void Prog_Microscope_Parameters::show() {
   Prog_parameters::show();
   cout << "CTF file: " << fn_ctf << endl
        << "Noise: " << sigma << endl
        << "Noise before: " << sigma_before_CTF << endl
	<< "Noise after: " << sigma_after_CTF << endl
	<< "Low pass freq: " << low_pass_before_CTF << endl
	<< "After CTF noise spectrum: " << fn_after_ctf << endl
        << "Defocus change: " << defocus_change << endl
        << "Output Pure CTF: " << fn_out_pure_ctf << endl
   ;
}


/* Produce side information ------------------------------------------------ */
//#define DEBUG
void Prog_Microscope_Parameters::produce_side_info() {
   int Zdim;
   get_input_size(Zdim,Ydim,Xdim);
   matrix2D<double> aux;

   double before_power=0, after_power=0;
   
   if (fn_ctf!="") {
      if (Is_FourierImageXmipp(fn_ctf)) {
         ctf.read_mask(fn_ctf);
         ctf.resize_mask(Ydim,Xdim);
      } else {
         ctf.FilterBand=CTF;
         ctf.ctf.read(fn_ctf);
         ctf.ctf.enable_CTFnoise=false;
         ctf.ctf.Produce_Side_Info();
         aux.resize(Ydim,Xdim); aux.set_Xmipp_origin();
         ctf.generate_mask(aux);
         if (fn_out_pure_ctf!="")
            ctf.write_mask(fn_out_pure_ctf,2);
      }

      #ifdef DEBUG
	 ctf.write_amplitude("PPP.xmp");
      #endif
      before_power=ctf.mask2D_power();
   }

   if (low_pass_before_CTF!=0) {
      lowpass.FilterBand=LOWPASS;
      lowpass.FilterShape=RAISED_COSINE;
      lowpass.w1=low_pass_before_CTF;
   }   

   if (fn_after_ctf!="") {
      if (Is_FourierImageXmipp(fn_ctf)) {
         after_ctf.read_mask(fn_after_ctf);
         after_ctf.resize_mask(Ydim,Xdim);
      } else {
         after_ctf.FilterBand=CTF;
         after_ctf.ctf.read(fn_after_ctf);
         after_ctf.ctf.enable_CTF=false;
         after_ctf.ctf.Produce_Side_Info();
         aux.resize(Ydim,Xdim); aux.set_Xmipp_origin();
         after_ctf.generate_mask(aux);
      }
      #ifdef DEBUG
	 after_ctf.write_amplitude("PPPafter.xmp");
      #endif
      after_power=after_ctf.mask2D_power();
   }

   // Compute noise balance
   if (after_power!=0 || before_power!=0) {
      double p=after_power/(after_power+before_power);
      double K=1/sqrt(p*after_power+(1-p)*before_power);
      sigma_after_CTF=sqrt(p)*K*sigma;
      sigma_before_CTF=sqrt(1-p)*K*sigma;
   } else if (sigma!=0) {
      sigma_before_CTF=sigma;
      sigma_after_CTF=0;
   }
}
#undef DEBUG

/* Apply ------------------------------------------------------------------- */
//#define DEBUG
void Prog_Microscope_Parameters::apply(matrix2D<double> &I) {
   // Add noise before CTF
   matrix2D<double> noisy;
   noisy.resize(I);
   noisy.init_random(0,sigma_before_CTF,"gaussian");
   if (low_pass_before_CTF!=0) lowpass.apply_mask_Space(noisy);
   I += noisy;

   // Check if the mask is a defocus changing CTF
   // In that case generate a new mask with a random defocus
   if (defocus_change!=0) {
      double old_DefocusU=ctf.ctf.DeltafU;
      double old_DefocusV=ctf.ctf.DeltafV;
      matrix2D<double> aux;
      ctf.ctf.DeltafU*=rnd_unif(1-defocus_change/100,1+defocus_change/100);
      ctf.ctf.DeltafV*=rnd_unif(1-defocus_change/100,1+defocus_change/100);
      aux.init_zeros(Ydim,Xdim);
      ctf.generate_mask(aux);
      ctf.ctf.DeltafU=ctf.ctf.DeltafU;
      ctf.ctf.DeltafV=ctf.ctf.DeltafV;
      #ifdef DEBUG
         ctf.write_amplitude("PPP_particular.xmp");
         char c; cout << "Press any key\n"; cin >> c;
      #endif
   }

   // Apply CTF
   if (fn_ctf!="") ctf.apply_mask_Space(I);

   // Add noise after CTF
   noisy.init_random(0,sigma_after_CTF,"gaussian");
   if (fn_after_ctf!="") after_ctf.apply_mask_Space(noisy);
   I += noisy;
}
#undef DEBUG

package pairpicker.model;

import java.awt.Color;
import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.FileHandler;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.logging.SimpleFormatter;

import picker.model.Micrograph;

import xmipp.MDLabel;
import xmipp.MetaData;





public class ParticlePairPicker {
	
	private static Logger logger;
	private String outputdir = ".";
	private static String rundir = ".";
	private boolean changed;
	private int size;
	protected List<MicrographPair> micrographs;
	private Color color = Color.green;
	
	public ParticlePairPicker(String pairsfile, String outputdir) {
		
		this.outputdir = outputdir;
		this.micrographs = new ArrayList<MicrographPair>();
		loadData(pairsfile);
	}
	
	private void loadData(String pairsfile) {
		MetaData md = new MetaData();
		md.readPlain(pairsfile, "image tilted_image");
		micrographs.clear();
		MicrographPair micrograph;
		String image, tiltedimage;
		try {
			long[] ids = md.findObjects();
			for (long id : ids) {

				image = md.getValueString(MDLabel.MDL_IMAGE, id);
				tiltedimage = md.getValueString(MDLabel.MDL_IMAGE_TILTED, id);
				micrograph = new MicrographPair(image, tiltedimage);
				micrographs.add(micrograph);
			}
			if (micrographs.size() == 0)
				throw new IllegalArgumentException(String.format(
						"No micrographs specified on %s", pairsfile));

		} catch (Exception e) {
			getLogger().log(Level.SEVERE, e.getMessage(), e);
			throw new IllegalArgumentException(e);
		}
		
	}

	public void setChanged(boolean changed) {
		this.changed = changed;
	}

	public boolean isChanged() {
		return changed;
	}
	
	public int getSize() {
		return size;
	}
	
	public Color getColor() {
		return color;
	}
	
	public static Logger getLogger() {
		try {
			if (logger == null) {
				FileHandler fh = new FileHandler("PPicker.log", true);
				fh.setFormatter(new SimpleFormatter());
				logger = Logger.getLogger("PPickerLogger");
				logger.addHandler(fh);
			}
			return logger;
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return null;
	}

	public String getOutputPath(String file) {
		return outputdir + File.separator + file;
	}

	public int getNextFreeMicrograph() {
		int count = 0;
		for (MicrographPair m : micrographs) {
			if (m.isEmpty())
				return count;
			count++;
		}
		return -1;
	}
	
	public List<MicrographPair> getMicrographs() {
		return micrographs;
	}

	public void setColor(Color color) {
		this.color = color;
		
	}

	public void resetMicrograph() {
		// TODO Auto-generated method stub
		
	}

	public int getParticlesNumber() {
		// TODO Auto-generated method stub
		return 0;
	}

	public void saveData() {
		// TODO Auto-generated method stub
		
	}

	public void setSize(int size2) {
		// TODO Auto-generated method stub
		
	}
	
	



}

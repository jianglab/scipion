package xmipp.particlepicker.tiltpair.gui;

import ij.IJ;
import ij.ImagePlus;
import ij.gui.ImageWindow;

import java.awt.Color;
import java.awt.Dimension;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.Image;
import java.awt.Point;
import java.awt.Rectangle;
import java.awt.event.MouseEvent;
import java.awt.event.MouseWheelEvent;
import java.awt.event.MouseWheelListener;

import javax.swing.JOptionPane;
import javax.swing.SwingUtilities;

import xmipp.particlepicker.Micrograph;
import xmipp.particlepicker.ParticlePickerCanvas;
import xmipp.particlepicker.ParticlePickerJFrame;
import xmipp.particlepicker.tiltpair.model.TiltPairPicker;
import xmipp.particlepicker.tiltpair.model.TiltedParticle;
import xmipp.particlepicker.tiltpair.model.UntiltedMicrograph;
import xmipp.particlepicker.tiltpair.model.UntiltedParticle;
import xmipp.particlepicker.training.model.TrainingParticle;
import xmipp.utils.XmippWindowUtil;
import xmipp.utils.XmippMessage;
import xmipp.jni.Particle;

public class UntiltedMicrographCanvas extends ParticlePickerCanvas
{

	private TiltPairPickerJFrame frame;
	private UntiltedParticle active;
	private TiltPairPicker pppicker;
	private UntiltedMicrograph um;
	private boolean reload = false;

	@Override
	public ParticlePickerJFrame getFrame()
	{
		return frame;
	}

	public TiltedParticle getActiveTiltedParticle()
	{
		if (active == null)
			return null;
		return active.getTiltedParticle();
	}

	public UntiltedParticle getActiveParticle()
	{
		return active;
	}

	public boolean hasActiveParticle()
	{
		return active != null;
	}

	@Override
	public Micrograph getMicrograph()
	{
		return um;
	}

	public UntiltedMicrographCanvas(TiltPairPickerJFrame frame)
	{
		super(frame.getMicrograph().getImagePlus(frame.getParticlePicker().getFilters()));
		this.um = frame.getMicrograph();

		this.frame = frame;

		this.pppicker = frame.getParticlePicker();
		um.runImageJFilters(pppicker.getFilters());

	}

	public void updateMicrograph()
	{
		this.um = frame.getMicrograph();
		updateMicrographData();
		if (!um.getParticles().isEmpty())
			refreshActive(um.getParticles().get(um.getParticles().size() - 1));
		else
			refreshActive(null);
	}

	/**
	 * Adds particle or updates its position if onpick. If ondeletepick removes
	 * particle. Considers owner for selection to the first particle containing
	 * point. Sets dragged if onpick
	 */

	public void mousePressed(MouseEvent e)
	{
		super.mousePressed(e);

		int x = super.offScreenX(e.getX());
		int y = super.offScreenY(e.getY());

		if (isDragImage(e))
			frame.getTiltedCanvas().mousePressed(x, y);
		else if (frame.isPickingAvailable(e))
		{
//			if (frame.isEraserMode())
//			{
//				um.removeParticles(x, y);
//				active = getLastParticle();
//				refresh();
//
//				return;
//			}
			if (active != null && !active.isAdded() && active.getTiltedParticle() != null)
				um.addParticleToAligner(active, true);
			UntiltedParticle p = um.getParticle(x, y, (int) (frame.getParticleSize()));

			if (p != null)
			{
				if (SwingUtilities.isLeftMouseButton(e) && e.isShiftDown())
					removeParticle(p);
				else if (SwingUtilities.isLeftMouseButton(e))
					refreshActive(p);
			}
			else if (SwingUtilities.isLeftMouseButton(e) && um.fits(x, y, frame.getParticleSize()))
				addParticle(x, y);
		}
	}

	private UntiltedParticle getLastParticle()
	{
		if (um.getParticles().isEmpty())
			return null;
		return um.getParticles().get(um.getParticles().size() - 1);
	}

	public void mouseReleased(MouseEvent e)
	{

		super.mouseReleased(e);
		if (reload)// added particle on matrix has been moved. Matrix changed
					// and tilted particle has to be recalculated
		{
			um.getTiltedMicrograph().removeParticle(active.getTiltedParticle());
			active.setAdded(false);
			um.initAligner();
			um.setAlignerTiltedParticle(active);
			frame.getTiltedCanvas().repaint();
		}
		reload = false;
	}

	@Override
	public void mouseDragged(MouseEvent e)
	{
		super.mouseDragged(e);

		int x = super.offScreenX(e.getX());
		int y = super.offScreenY(e.getY());
		if (isDragImage(e))
		{
			frame.getTiltedCanvas().mouseDragged(e.getX(), e.getY());
			return;
		}
		if (frame.isPickingAvailable(e))
		{
//			if (frame.isEraserMode())
//			{
//				um.removeParticles(x, y);
//				active = getLastParticle();
//				refresh();
//
//				return;
//			}
			
			if (active != null && um.fits(x, y, frame.getParticleSize()))

			{
				moveActiveParticle(x, y);
				if (active.isAdded())
					reload = true;
			}
		}
		frame.setChanged(true);
		repaint();

	}

	@Override
	public void mouseWheelMoved(MouseWheelEvent e)
	{
		super.mouseWheelMoved(e);
		if (!e.isShiftDown())
			return;
		int x = e.getX();
		int y = e.getY();
		frame.getTiltedCanvas().setMagnification(magnification);
		int rotation = e.getWheelRotation();
		if (rotation < 0)
			zoomIn(x, y);
		else
			zoomOut(x, y);
		if (getMagnification() <= 1.0)
			imp.repaintWindow();
		frame.getTiltedCanvas().mouseWheelMoved(x, y, rotation);
	}

	public void paint(Graphics g)
	{
		Graphics offgc;
		Image offscreen = null;
		Dimension d = getSize();

		// create the offscreen buffer and associated Graphics
		offscreen = createImage(d.width, d.height);
		offgc = offscreen.getGraphics();

		super.paint(offgc);
		Graphics2D g2 = (Graphics2D) offgc;
		g2.setColor(frame.getColor());
		int index = 0;

		for (TrainingParticle p : um.getParticles())
		{
			drawShape(g2, p, index == (um.getParticles().size() - 1));
			index++;
		}
		if (active != null)
		{
			g2.setColor(Color.red);
			drawShape(g2, active, true);
		}
		if (frame.drawAngles())
			drawLine(Math.toRadians(um.getUntiltedAngle()), g2);
		g.drawImage(offscreen, 0, 0, this);
	}

	private void addParticle(int x, int y)
	{
		try
		{
			Particle tp = um.getAlignerTiltedParticle(x, y);
			if (!um.getTiltedMicrograph().fits(tp.getX(), tp.getY(), pppicker.getFamily().getSize()))
				throw new IllegalArgumentException(XmippMessage.getOutOfBoundsMsg("Tilted Pair Coordinates"));
			UntiltedParticle p = new UntiltedParticle(x, y, um, pppicker.getFamily());

			um.addParticle(p);

			if (um.getAddedCount() >= 4)
				um.setAlignerTiltedParticle(p);
			refreshActive(p);
			frame.updateMicrographsModel();
			frame.setChanged(true);
		}
		catch (Exception e)
		{
			JOptionPane.showMessageDialog(this, e.getMessage());
		}

	}

	private void removeParticle(UntiltedParticle p)
	{
		um.removeParticle(p);
		
		if (active != null && active.equals(p))
		{
			if (!um.getParticles().isEmpty())
				refreshActive(um.getParticles().get(um.getParticles().size() - 1));
			else
				refreshActive(null);
		}

		if (p.isAdded())
			um.initAligner();
		refresh();
		frame.getTiltedCanvas().repaint();
	}

	public void refreshActive(TrainingParticle up)
	{
		active = (UntiltedParticle) up;
		if (active != null)
		{
			TiltedParticle tp = active.getTiltedParticle();
			if (tp != null)
			{
				Rectangle srcrect = frame.getTiltedCanvas().getSrcRect();
				int xrect = (int) ((tp.getX() - srcrect.getX()));
				int yrect = (int) ((tp.getY() - srcrect.getY()));

				if (tp != null && !um.fits(xrect, yrect, tp.getFamily().getSize()))
					frame.getTiltedCanvas().moveTo(tp);
			}
		}
		repaint();
		frame.getTiltedCanvas().repaint();
	}

	@Override
	public TrainingParticle getActive()
	{
		return active;
	}

}

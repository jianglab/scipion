/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package browser.imageitems.listitems;

import browser.Cache;
import browser.ICONS_MANAGER;
import browser.LABELS;
import browser.imageitems.ImageDimension;
import ij.ImagePlus;
import ij.process.ImageStatistics;
import java.io.File;
import java.text.DecimalFormat;
import xmipp.ImageDouble;

/**
 *
 * @author Juanjo Vega
 */
public abstract class AbstractImageItem extends FileItem {

    protected final static DecimalFormat decimalFormatter = new DecimalFormat("#.###");
    protected ImageDimension dimension;
    protected Cache cache;
    protected ImageStatistics statistics;

    public AbstractImageItem(File file, Cache cache) {
        super(file);

        this.cache = cache;

        if (exists()) {
            loadImageData();
        }
    }

    protected void loadImageData() {
        try {
            ImageDouble image = new ImageDouble();
            image.readHeader(file.getAbsolutePath());

            dimension = new ImageDimension(image);
        } catch (Exception ex) {
            //throw new RuntimeException(ex);
            System.out.println(ex.getMessage() + ": " + file.getAbsolutePath());
        }
    }

    public abstract ImagePlus getImagePlus();

    public ImagePlus getPreview(int w, int h) {
        ImagePlus preview;

        if (getWidth() > 0 && getHeight() > 0) {
            // Tries to load from cache.
            preview = (ImagePlus) cache.get(getKey());

            // If not in cache.
            if (preview == null) {
//                System.out.println("Reading from disk: " + getKey());
                preview = loadPreview(w, h);

                if (preview != null) {
                    cache.put(getKey(), preview);
                }
            }

            // Preview might be loaded if it's referenced by another item, 
            // but statistics, might be still null.
            if (statistics == null) {
                statistics = preview.getStatistics();
            }
        } else {    // Null preview.
            preview = ICONS_MANAGER.MISSING_ITEM;
        }

        return preview;
    }

    public String getKey() {
        return file.getAbsolutePath() + "_" + getHeight() + "_" + getWidth();
    }

    public int getWidth() {
        return dimension != null ? dimension.getWidth() : 0;
    }

    public int getHeight() {
        return dimension != null ? dimension.getHeight() : 0;
    }

    public int getDepth() {
        return dimension != null ? dimension.getDepth() : 0;
    }

    public long getNImages() {
        return dimension != null ? dimension.getNimages() : 0;
    }

    public boolean isSingleImage() {
        return !isStack() && !isVolume();
    }

    public boolean isStack() {
        return getNImages() > 1;
    }

    public boolean isVolume() {
        return getDepth() > 1;
    }

    public ImageStatistics getStatistics() {
        return statistics;
    }

    //public abstract String getImageInfo();
    public String getImageInfo() {
        String strMin = decimalFormatter.format(statistics.min);
        String strMax = decimalFormatter.format(statistics.max);
        String strMean = decimalFormatter.format(statistics.mean);
        String strStdDev = decimalFormatter.format(statistics.stdDev);

        return "<html>"
                + LABELS.LABEL_WIDTH + dimension.getWidth() + "<br>"
                + LABELS.LABEL_HEIGHT + dimension.getHeight() + "<br>"
                + (isVolume() ? LABELS.LABEL_DEPTH + dimension.getDepth() + "<br>" : "")
                + (isStack() ? LABELS.LABEL_NIMAGES + dimension.getNimages() : "")
                + "<br>" + "<br>"
                + "Min=" + strMin + "<br>"
                + "Max=" + strMax + "<br>"
                + "Mean=" + strMean + "<br>"
                + "Std. dev.=" + strStdDev + "<br>"
                + "</p>"
                + "</html>";
    }

    protected abstract ImagePlus loadPreview(int w, int h);
}

package xmipp;

import java.io.File;

public class Filename {

    public final static String SEPARATOR = "@";
    private final static String EXTENSION_XMP = ".xmp";
    private final static String EXTENSION_IMG = ".img";
    private final static String EXTENSION_HED = ".hed";
    private final static String EXTENSION_PSD = ".psd";
    private final static String EXTENSION_SER = ".ser";
    private final static String EXTENSION_DM3 = ".dm3";
    private final static String EXTENSION_RAW = ".raw";
    private final static String EXTENSION_INF = ".inf";
    private final static String EXTENSION_SPE = ".spe";
    private final static String EXTENSION_MRC = ".mrc";
    private final static String EXTENSION_MRCS = ".mrcs";
    private final static String EXTENSION_STK = ".stk";
    private final static String EXTENSION_SEL = ".sel";
    private final static String EXTENSION_VOL = ".vol";
    private final static String EXTENSION_XMD = ".xmd";
    private final static String EXTENSION_SPI = ".spi";
    private final static String EXTENSION_TIF = ".tif";
    // Types of images contained by each file type.
    private final static String[] SINGLE_IMAGES = new String[]{
        EXTENSION_XMP,
        EXTENSION_IMG,
        EXTENSION_HED,
        EXTENSION_PSD,
        EXTENSION_SER,
        EXTENSION_DM3,
        EXTENSION_RAW,
        EXTENSION_INF,
        EXTENSION_SPE,
        EXTENSION_SPI,
        EXTENSION_TIF
    };
    private final static String[] VOLUMES = new String[]{
        EXTENSION_MRC,
        EXTENSION_VOL
    };
    private final static String[] STACKS = new String[]{
        EXTENSION_MRCS,
        EXTENSION_STK
    };
    private final static String[] METADATAS = new String[]{
        EXTENSION_SEL,
        EXTENSION_XMD
    };

    public static boolean isPSD(String filename) {
        return filename.endsWith(EXTENSION_PSD);
    }

    public static boolean isSingleImage(String filename) {
        return filename.contains(SEPARATOR) || isFileType(filename, SINGLE_IMAGES);
    }

    public static boolean isVolume(String filename) {
        return isFileType(filename, VOLUMES);
    }

    public static boolean isStack(String filename) {
        return isFileType(filename, STACKS);
    }

    public static boolean isStackOrVolume(String filename) {
        return isStack(filename) || isVolume(filename);
    }

    public static boolean isMetadata(String filename) {
        return isFileType(filename, METADATAS);
    }

    private static boolean isFileType(String filename, String filetypes[]) {
        for (int i = 0; i < filetypes.length; i++) {
            if (filename.endsWith(filetypes[i])) {
                return true;
            }
        }

        return false;
    }

    public static boolean isXmippType(String filename) {
        return isSingleImage(filename) || isStackOrVolume(filename) || isMetadata(filename);
    }

    // Auxiliary methods.
    public static String fixPath(String workdir, String filename) {
        String fixed = filename;

        if (!filename.startsWith(File.separator)) { // Absolute path?
            String name = getFilename(filename);
            String strimage = "";

            if (filename.contains(SEPARATOR)) { // Has #image?
                long image = getNimage(filename);
                strimage = image + SEPARATOR;
            }

            if (!name.startsWith(File.separator)) { // In 'image@name', is name absolute?
                String aux = getAbsPath(workdir, name);
                fixed = strimage + aux;
            }
        }

        return fixed;
    }

    public static long getNimage(String filename) {
        long nimage = ImageDouble.ALL_IMAGES;

        if (filename.contains(SEPARATOR)) {
            String str = filename.split(SEPARATOR)[0];
            if (!str.isEmpty()) {
                // str may have a string prefix before the number, so
                // grab the rightmost part
                int i=str.length()-1;
                while(i>=0){
                        if(Character.isDigit(str.charAt(i)) == false)
                                break;
                        i--;
                }
                String rightPart=str.substring(i+1,str.length());

                nimage = Long.valueOf(rightPart);
            }
        }

        return nimage;
    }

    public static String getFilename(String filename) {
        if (filename.contains(SEPARATOR)) {
            return filename.split(SEPARATOR)[1];
        }

        return filename;
    }

    private static String getAbsPath(String baseDir, String filename) {
        String[] tokensDir = baseDir.split(File.separator);
        String[] tokensFile = filename.split(File.separator);

        int indexDir = tokensDir.length - 1;
        int indexFile = 0;

        while (indexFile < tokensFile.length && indexDir >= 0) {
            String dirToken = tokensDir[indexDir];
            String fileToken = tokensFile[indexFile];
            if (!dirToken.equals(fileToken)) {
                break;
            }
            indexDir--;
            indexFile++;
        }

        // Builds result path.
        String path = "";
        // Dir
        for (int i = 0; i < tokensDir.length; i++) {
            path += tokensDir[i] + File.separator;
        }

        // File
        for (int i = indexFile; i < tokensFile.length - 1; i++) {
            path += tokensFile[i] + File.separator;
        }
        path += tokensFile[tokensFile.length - 1];  // Last item (to avoid "/" at the end)

        return path;
    }
}

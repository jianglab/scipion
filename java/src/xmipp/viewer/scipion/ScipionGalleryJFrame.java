/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package xmipp.viewer.scipion;

import java.awt.Color;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.MouseEvent;
import java.io.File;
import java.util.HashMap;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.swing.JButton;
import xmipp.ij.commons.XmippUtil;
import xmipp.jni.Filename;
import xmipp.jni.MetaData;
import xmipp.utils.XmippDialog;
import xmipp.utils.XmippQuestionDialog;
import xmipp.utils.XmippWindowUtil;
import xmipp.viewer.windows.GalleryJFrame;

/**
 *
 * @author airen
 */
public class ScipionGalleryJFrame extends GalleryJFrame {

    private String type;
    private String script;
    private String projectid;
    private JButton cmdbutton;
    private String selfile;
    private JButton classcmdbutton;

    private String python;
    private String inputid;
    private HashMap<String, String> msgfields;
    private final String runNameKey = "Run name:";
    
   

    public ScipionGalleryJFrame(String filename, ScipionMetaData md, ScipionParams parameters) {
        super(filename, md, parameters);
        readScipionParams(parameters);
        data.setWindow(this);
    }
    
      public ScipionGalleryJFrame(ScipionGalleryData data) {
        super(data);
        readScipionParams((ScipionParams)data.parameters);
        data.setWindow(this);
    }

    protected void readScipionParams(ScipionParams parameters)
    {
        try {
            type = parameters.type;
            python = parameters.python;
            script = parameters.script;
            projectid = parameters.projectid;
            inputid = parameters.inputid;
            selfile = String.format("%s%sselection%s", projectid, File.separator, data.getFileExtension());
            msgfields = new HashMap<String, String>();
            msgfields.put(runNameKey, "ProtUserSubset");

            initComponents();
        } catch (Exception ex) {
            Logger.getLogger(ScipionGalleryJFrame.class.getName()).log(Level.SEVERE, null, ex);
            throw new IllegalArgumentException(ex.getMessage());
        }
    }
    private void initComponents() {
        JButton closebt = getScipionButton("Close", new ActionListener() {

            @Override
            public void actionPerformed(ActionEvent ae) {
                close();
            }
        });
        buttonspn.add(closebt);
        if (type != null) {
            final String output = data.hasClasses()? "Particles": type;   
            cmdbutton = getScipionButton("Create " + output, new ActionListener() {

                @Override
                public void actionPerformed(ActionEvent ae) {
                    int size;
                    MetaData imagesmd = null;    
                    if(data.hasClasses())
                        imagesmd = data.getEnabledClassesImages();
                    else
                        imagesmd = data.getMd(data.getEnabledIds());
                    size = imagesmd.size();
                    String question = String.format("<html>Are you sure you want to create a new set of %s with <font color=red>%s</font> %s?", output, size, (size > 1)?"elements":"element");
                    ScipionMessageDialog dlg = new ScipionMessageDialog(ScipionGalleryJFrame.this, "Question", question, msgfields);
                    int create = dlg.action;
                    if (create == ScipionMessageDialog.OK_OPTION) 
                    {
                        String[] command = new String[]{python, script, msgfields.get(runNameKey), selfile, type, output, projectid, inputid};
                        createSubset(command);
                    }
                }
            });
            if(data.hasClasses())
            {
                classcmdbutton = getScipionButton("Create Classes", new ActionListener() {

                    @Override
                    public void actionPerformed(ActionEvent ae) {
                        MetaData md = data.getMd(data.getEnabledIds());
                        int size = md.size();
                        String msg = String.format("<html>Are you sure you want to create a new set of Classes with <font color=red>%s</font> %s?", size, (size > 1)?"elements":"element");
                        ScipionMessageDialog dlg = new ScipionMessageDialog(ScipionGalleryJFrame.this, "Question", msg, msgfields);
                        int create = dlg.action;
                        if (create == ScipionMessageDialog.OK_OPTION) {
                            String[] command = new String[]{python, script, dlg.getFieldValue(runNameKey), selfile, type, type, projectid, inputid};
                            createSubset(command);
                            
                        }

                    }
                });
                
                buttonspn.add(classcmdbutton);
            }
            
            buttonspn.add(cmdbutton);
            pack();
            enableActions();
            jcbBlocks.addActionListener(new ActionListener() {

                @Override
                public void actionPerformed(ActionEvent ae) {
                    enableActions();
                }
            });
        }

    }

    

    public JButton getScipionButton(String text, ActionListener listener) {

        JButton button = new JButton(text);
        button.addActionListener(listener);

        return button;
    }

    public void selectItem(int row, int col) {
        super.selectItem(row, col);
        enableActions();

    }

    protected void tableMouseClicked(MouseEvent evt) {
        super.tableMouseClicked(evt);
        enableActions();
    }

    protected void enableActions() {
        boolean isenabled = data.allowGallery();
        Color color = Color.decode(isenabled ? ScipionMessageDialog.firebrick : ScipionMessageDialog.lightgrey);
        Color forecolor = isenabled ? Color.WHITE : Color.GRAY;
        if(cmdbutton != null)
        {
            cmdbutton.setEnabled(isenabled);
            cmdbutton.setBackground(color);
            cmdbutton.setForeground(forecolor);
        }
        if(classcmdbutton != null)
        {
            isenabled = data.hasClasses();
            color = Color.decode(isenabled? ScipionMessageDialog.firebrick: ScipionMessageDialog.lightgrey); 
            forecolor = isenabled? Color.WHITE: Color.GRAY;
            classcmdbutton.setEnabled( isenabled);
            classcmdbutton.setBackground(color);
            classcmdbutton.setForeground(forecolor);
        }
    }

  
    	public boolean proceedWithChanges()
	{
            return true;//without asking for changes
	}
    
   protected void createSubset(final String[] command) 
    {
        XmippWindowUtil.blockGUI(ScipionGalleryJFrame.this, "Creating set ...");
        new Thread(new Runnable() {

            @Override
            public void run() {

                try {
                    ((ScipionGalleryData)data).overwrite(selfile);
                    String output = XmippUtil.executeCommand(command);
                    XmippWindowUtil.releaseGUI(ScipionGalleryJFrame.this.getRootPane());
                    if (output != null && !output.isEmpty()) {
                        System.out.println(output);
                        XmippDialog.showInfo(ScipionGalleryJFrame.this, output);
                        
                    }

                } catch (Exception ex) {
                    throw new IllegalArgumentException(ex.getMessage());
                }

            }
        }).start();
    }
        


}

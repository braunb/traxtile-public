import os
import platform
import Trackmodel
from Tkinter import *
import tkFileDialog
import ttk
import csv
import re


def center(win):
    """ from http://stackoverflow.com/questions/3352918/how-to-center-a-window-on-the-screen-in-tkinter """
    win.update_idletasks()
    frm_width = win.winfo_rootx() - win.winfo_x()
    win_width = win.winfo_width() + (frm_width*2)
    titlebar_height = win.winfo_rooty() - win.winfo_y()
    win_height = win.winfo_height() + (titlebar_height + frm_width)
    x = (win.winfo_screenwidth() / 2) - (win_width / 2)
    y = (win.winfo_screenheight() / 2) - (win_height / 2)
    geom = (win.winfo_width(), win.winfo_height(), x, y) # see note
    win.geometry('{0}x{1}+{2}+{3}'.format(*geom))


def importTrackmodel(trackapp):

    class MontageFileImportController:
        def __init__(self, trackapp):
            self.trackapp = trackapp
            self.tm = None  # trackmodel
            self.status = FALSE
            self.imageCsvFile = ''
            self.objectCsvFile = ''
            self.panelImageDir = ''
            self.configuredFields = [{
                                    'var': 'ParentGroupIndex',
                                    'default': 'ParentImageNumber',
                                    'prompt': 'Parent Image Number'},
                                     {
                                    'var': 'ParentObjectNumber',
                                    'default': 'ParentObjectNumber',
                                    'prompt': 'Parent Object Number'
                                     },
                                     {
                                    'var': 'FrameIndex',
                                    'default': 'Time',
                                    'prompt': 'Time Index'
                                     }]
            self.mfiv = MontageFileImportView(self)
            if "Darwin" in platform.system():
                os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
            # self.mfiv.root.mainloop()

        def csvFields(self, csvFname):
            csvFile = open(csvFname, 'rU')
            reader = csv.DictReader(csvFile)
            return reader.fieldnames

        def imageCsvFileButPress(self):
            # print 'file'
            fullname = tkFileDialog.askopenfilename(filetypes=[("csv", "*.csv"), ("All files", "*.*")],
                                                    title="Open Image Data CSV File",
                                                    parent=self.mfiv.root)
            if fullname == '':
                # print "none selected"
                pass
            else:
                print fullname
                self.imageCsvFile = fullname
                self.mfiv.updateImageCsvFileText()
                # print self.csvFields(fullname)

        def objectCsvFileButPress(self):
            # print 'file'
            fullname = tkFileDialog.askopenfilename(filetypes=[("csv", "*.csv"), ("All files", "*.*")],
                                                    title="Open Object Data CSV File",
                                                    parent=self.mfiv.root)
            if fullname == '':
                # print "none selected"
                pass
            else:
                self.objectCsvFile = fullname
                self.mfiv.updateObjectCsvFileText()
                fields = self.csvFields(fullname)
                # tm.KEYNAME_ParentGroupIndex = 'TrackObjects_ParentImageNumber'
                # tm.KEYNAME_ParentObjectNumber = 'TrackObjects_ParentObjectNumber'
                # parentImageNumberFields = [f for f in fields if 'ParentImageNumber' in f]
                # parentObjectNumberFields = [f for f in fields if 'ParentObjectNumber' in f]
                # self.mfiv.updateObjectParentGroupIndexPicker(fields,
                #                     default=parentImageNumberFields[0] if len(parentImageNumberFields) > 0 else fields[0])
                # self.mfiv.updateObjectParentObjectIndexPicker(fields,
                #                     default=parentObjectNumberFields[0] if len(parentObjectNumberFields) > 0 else fields[0])
                for cf in self.configuredFields:
                    defaultFields = [f for f in fields if cf['default'] in f]
                    newValue = defaultFields[0] if len(defaultFields) > 0 else fields[0]
                    self.mfiv.updateFieldPicker(cf, fields, default=newValue)

        def panelImageButPress(self):
            fullname = tkFileDialog.askopenfilename(filetypes=[("gif", "*.gif")], title="Open Panel Image File",
                                                    parent=self.mfiv.root)
            if fullname == '':
                print "none selected"
            else:
                self.panelImageDir = os.path.dirname(fullname)
                base = os.path.basename(fullname)
                fname = os.path.splitext(base)[0]
                fext = os.path.splitext(base)[1]
                # search for time string
                matchObj = re.search(r'(.*t)(\d{4})(.*)', fname)  # TODO: not just 4 n's. Note leading (.*) is greedy
                if not matchObj:
                    matchObj = re.search(r'(.*t)(\d{4})(.*)', fname)
                if matchObj:
                    pre = matchObj.group(1)
                    num = matchObj.group(2)
                    post = matchObj.group(3)
                panelNameDict = {'dir': self.panelImageDir, 'pre': pre, 'num': num, 'post': post, 'ext': fext}
                self.mfiv.updatePanelName(panelNameDict)

        def wholeImageButPress(self):
            fullname = tkFileDialog.askopenfilename(filetypes=[("gif", "*.gif")], title="Open Panel Image File",
                                                    parent=self.mfiv.root)
            if fullname == '':
                print "none selected"
            else:
                self.panelImageDir = os.path.dirname(fullname)
                base = os.path.basename(fullname)
                fname = os.path.splitext(base)[0]
                fext = os.path.splitext(base)[1]
                # search for time string
                matchObj = re.search(r'(.*t)([0-9]{4})(.*)', fname)  # TODO: not just 4 n's
                if not matchObj:
                    matchObj = re.search(r'(.*t)([0-9]{4})(.*)', fname)
                if matchObj:
                    pre = matchObj.group(1)
                    num = matchObj.group(2)
                    post = matchObj.group(3)
                d = {'dir': self.panelImageDir, 'pre': pre, 'num': num, 'post': post, 'ext': fext}
                self.mfiv.updateWholeName(d)

        def quit(self):
            # print 'quit MontageFile with status:', self.status
            self.mfiv.root.destroy()
            # print 'quitted MontageFile'

        def oKpress(self):
            # print "pressed OK"
            # TODO: validation checking...
            valid = TRUE

            # create TrackModel instance
            self.tm = Trackmodel.MontageSession()
            # data files
            self.tm.imageCsvFilename = self.imageCsvFile
            self.tm.objectCsvFilename = self.objectCsvFile
            # self.tm.KEYNAME_ParentGroupIndex = self.mfiv.objectParentGroupIndexVar.get()
            # self.tm.KEYNAME_ParentObjectNumber = self.mfiv.objectParentObjectIndexVar.get()
            for cf in self.configuredFields:
                var = cf['var']
                self.tm.set_keyname(var, self.mfiv.fieldVars[var].get())
            # data for montage panel images
            self.tm.panelImageDir = self.mfiv.panelImageFileVar[0].get()
            self.tm.panelImgFilenameBase = self.mfiv.panelImageFileVar[1].get()
            # print self.mfiv.panelImageFileVar[2].get() # nnnn
            self.tm.panelImgFilenamePost = self.mfiv.panelImageFileVar[3].get()
            self.tm.panelImgExt = self.mfiv.panelImageFileVar[4].get()
            # data for whole images; may be the same as panels or not
            wivars = []
            if self.mfiv.wholeImageSame.get():
                wivars = self.mfiv.panelImageFileVar
            else:
                wivars = self.mfiv.wholeImageFileVar
            self.tm.wholeImageDir = wivars[0].get()
            self.tm.imgFileNameBase = wivars[1].get()
            self.tm.wholeImgFilenamePost = wivars[3].get()
            self.tm.wholeImgExt = wivars[4].get()
            # and wrap it up
            self.status = True  # indicates that there is a value
            self.tm.setup()
            self.trackapp.setModel(self.tm)  # callback - set the model in the app
            self.quit()

    class MontageFileImportView(object):  # a window for the import dialog
        def __init__(self, controller):
            #Canvas.__init__(self)
            self.controller = controller
            # self.fieldVars = []
            # self.fieldPickers = []
            self.fieldVars = dict()
            self.fieldPickers = dict()
            self.root = Toplevel()
            self.root.lower()

            s = ttk.Style()
            # s.configure('My.TFrame', background='red')

            content = ttk.Frame(self.root, width=500, height=300, padding=[20, 20])  #, style='My.TFrame')
            frm = ttk.Frame(content, width=500, height=300, relief='flat', borderwidth=2)  #, style='My.TFrame')
            frm.config()
            # frm.pack(expand=True, fill='both')

            # self.frame = ttk.Frame(self.root)
            # self.labelFont = 'Helvetica 14'
            self.imageCsvFileLabel = ttk.Label(frm, text='CSV file for Image information:')
            self.imageCsvFileText = ttk.Label(frm, text='...', width=80)
            self.imageCsvFileBut = ttk.Button(frm, text='Browse', command=self.controller.imageCsvFileButPress)

            self.objectCsvFileLabel = ttk.Label(frm, text='CSV file for Object information:')
            self.objectCsvFileText = ttk.Label(frm, text='...')
            self.objectCsvFileBut = ttk.Button(frm, text='Browse', command=self.controller.objectCsvFileButPress)

            self.objectParentGroupIndexVar = StringVar()
            self.objectParentGroupIndexVar.set('...')
            self.objectParentGroupIndexPicker = OptionMenu(frm, self.objectParentGroupIndexVar, ('...'))

            self.objectParentObjectIndexVar = StringVar()
            self.objectParentObjectIndexVar.set('...')
            self.objectParentObjectIndexPicker = OptionMenu(frm, self.objectParentObjectIndexVar, ('...'))

            self.panelImageBut = ttk.Button(frm, text='Browse', command=self.controller.panelImageButPress)
            self.panelImageFileVar = list()
            for i in range(5):
                self.panelImageFileVar.append(StringVar())
            self.panelImageFileVar[0].set('...')
            self.panelImageDirLabel = ttk.Label(frm, textvariable=self.panelImageFileVar[0])
            self.panelImagePreEntry = ttk.Entry(frm, textvariable=self.panelImageFileVar[1])
            self.panelImageNumLabel = ttk.Label(frm, textvariable=self.panelImageFileVar[2])
            self.panelImagePostEntry = ttk.Entry(frm, textvariable=self.panelImageFileVar[3])
            self.panelImageExtEntry = ttk.Entry(frm, textvariable=self.panelImageFileVar[4])

            s = ttk.Style()
            # s.configure('My.TEntry', disabledforeground='maroon')
            s.map("My.TEntry", foreground=[('disabled', 'gray')])
            s.map("My.TLabel", foreground=[('disabled', 'gray')])

            self.wholeImageSame = BooleanVar()
            self.wholeImageSame.set(0)
            self.wholeImageBut = ttk.Button(frm, text='Browse', command=self.controller.wholeImageButPress)
            self.wholeImageFileVar = list()
            for i in range(5):
                self.wholeImageFileVar.append(StringVar())
            self.wholeImageFileVar[0].set('...')
            self.wholeImageDirLabel = ttk.Label(frm, textvariable=self.wholeImageFileVar[0], style='My.TLabel')
            self.wholeImagePreEntry = ttk.Entry(frm, textvariable=self.wholeImageFileVar[1], style='My.TEntry')
            self.wholeImageNumLabel = ttk.Label(frm, textvariable=self.wholeImageFileVar[2], style='My.TLabel')
            self.wholeImagePostEntry = ttk.Entry(frm, textvariable=self.wholeImageFileVar[3], style='My.TEntry')
            self.wholeImageExtEntry = ttk.Entry(frm, textvariable=self.wholeImageFileVar[4], style='My.TEntry')

            # tm.workDir = "/Users/bbraun/Box Documents/montage/130530/data"
            #
            # # input files
            # tm.imageCsvFilename = "TrackOUT_Image.csv"
            # tm.objectCsvFilename = "TrackOUT_cells.csv"

            # # configure keys which may vary depending on the CellProfiler run
            # tm.KEYNAME_ParentGroupIndex = 'TrackObjects_ParentImageNumber'
            # tm.KEYNAME_ParentObjectNumber = 'TrackObjects_ParentObjectNumber'

            #panelImageDir = ttk.Label(root, text='Directory for images:')

            # # images
            # tm.panelImageDir = "/Users/bbraun/Box Documents/montage/130530/gif"
            # tm.imgFileNameBase = "subtracted_2x_s1_t"  # used for whole image viewer
            # tm.panelImgFilenameBase = "subtracted_2x_s1_t"  # used for montage panels; may be the same or different

            content.grid(row=0, column=0)
            frm.grid(row=0, column=0)

            # ttk.Label(frm, text='Image information:').grid(row=5, column=0)
            self.imageCsvFileLabel.grid(row=10, column=0, columnspan=4, sticky='W')
            self.imageCsvFileBut.grid(row=10, column=1, sticky='W')
            self.imageCsvFileText.grid(row=20, column=1, columnspan=4, sticky='W')

            ttk.Separator(frm, orient=HORIZONTAL).grid(row=25, column=0, columnspan=5, sticky="EW")

            self.objectCsvFileLabel.grid(row=30, column=0, columnspan=4, sticky='W')
            self.objectCsvFileBut.grid(row=30, column=1, sticky='W')
            self.objectCsvFileText.grid(row=40, column=1, columnspan=4, sticky='W')

            r = 50
            for f in self.controller.configuredFields:
                r += 1
                key = f['var']
                ttk.Label(frm, text='Field name for %s:' % f['prompt']).grid(row=r, column=0, sticky="W")
                self.fieldVars[key] = StringVar()
                self.fieldVars[key].set('...')
                self.fieldPickers[key] = OptionMenu(frm, self.fieldVars[key], '...')
                self.fieldPickers[key].grid(row=r, column=1, columnspan=2, sticky="W")
            ttk.Separator(frm, orient=HORIZONTAL).grid(row=r+1, column=0, columnspan=5, sticky="EW")

            ttk.Label(frm, text='Images to use for display:').grid(row=70, column=0, columnspan=4, sticky="W")
            ttk.Label(frm, text='Montage tiles:').grid(row=80, column=0, columnspan=1, sticky="E")
            self.panelImageBut.grid(row=80, column=1, sticky="W")
            self.panelImageDirLabel.grid(row=85, column=1, columnspan=4, sticky="EW")
            ttk.Label(frm, text='prefix').grid(row=87, column=1)
            ttk.Label(frm, text='image #').grid(row=87, column=2)
            ttk.Label(frm, text='suffix').grid(row=87, column=3)
            ttk.Label(frm, text='extension').grid(row=87, column=4)

            self.panelImagePreEntry.grid(row=90, column=1, sticky="EW")
            self.panelImageNumLabel.grid(row=90, column=2)
            self.panelImagePostEntry.grid(row=90, column=3, sticky="EW")
            self.panelImageExtEntry.grid(row=90, column=4, sticky="EW")
            ttk.Separator(frm, orient=HORIZONTAL).grid(row=95, column=1, columnspan=4, sticky="EW")

            ttk.Label(frm, text='Whole images:').grid(row=100, column=0, columnspan=1, sticky="E")
            ttk.Checkbutton(frm, text='Same as montage tile images',
                            variable=self.wholeImageSame,
                            onvalue=TRUE, offvalue=FALSE,
                            command=self.setWholeImages).grid(row=100, column=1, sticky="W", )
            self.wholeImageBut.grid(row=110, column=1, sticky="W")
            self.wholeImageDirLabel.grid(row=120, column=1, columnspan=4, sticky="EW")
            ttk.Label(frm, text='prefix').grid(row=130, column=1)
            ttk.Label(frm, text='image #').grid(row=130, column=2)
            ttk.Label(frm, text='suffix').grid(row=130, column=3)
            ttk.Label(frm, text='extension').grid(row=130, column=4)

            self.wholeImagePreEntry.grid(row=140, column=1, sticky="EW")
            self.wholeImageNumLabel.grid(row=140, column=2)
            self.wholeImagePostEntry.grid(row=140, column=3, sticky="EW")
            self.wholeImageExtEntry.grid(row=140, column=4, sticky="EW")
            ttk.Separator(frm, orient=HORIZONTAL).grid(row=150, column=0, columnspan=5, sticky="EW")

            okfrm = ttk.Frame(frm, padding=[10, 10])
            okfrm.grid(row=160, column=0, columnspan=5)
            cancelBut = ttk.Button(okfrm, text="Cancel", command=self.controller.quit)
            okBut = ttk.Button(okfrm, text="OK", command=self.controller.oKpress)
            cancelBut.grid(row=10, column=0)
            okBut.grid(row=10, column=1)

            # make default to use same images for tiles and whole images, and update display accordingly
            self.wholeImageSame.set(1)
            self.setWholeImages()

            center(self.root)
            # self.root.update()
            self.root.lift()
            #panelImageDir.grid(row=4, column=0)

        def updateImageCsvFileText(self):
            self.imageCsvFileText.configure(text=self.controller.imageCsvFile)
            # self.imageCsvFileText.configure(text='/directory/for/data/'+os.path.basename(self.controller.imageCsvFile))

        def updateObjectCsvFileText(self):
            self.objectCsvFileText.configure(text=self.controller.objectCsvFile)
            # self.objectCsvFileText.configure(text='/directory/for/data/'+os.path.basename(self.controller.objectCsvFile))

        def updateFieldPicker(self, config, optionList, default):
            key = config['var']
            picker = self.fieldPickers[key]
            var = self.fieldVars[key]
            menu = picker['menu']
            var.set(default)
            menu.delete(0, menu.index(END))  # remove all current options
            for opt in optionList:
                menu.add_command(label=opt, command=lambda value=opt: var.set(value))

        def updatePanelName(self, panelNameDict):
            # print "update"
            # panelNameDict = {'dir': self.panelImageDir, 'pre': pre, 'num': num, 'post': post, 'ext': fext}
            self.panelImageFileVar[0].set(panelNameDict['dir'])
            self.panelImageFileVar[1].set(panelNameDict['pre'])
            self.panelImageFileVar[2].set('n' * len(panelNameDict['num']))
            self.panelImageFileVar[3].set(panelNameDict['post'])
            self.panelImageFileVar[4].set(panelNameDict['ext'])
            # self.panelImageFileVar[0].set('/directory/for/gifs/')

        def updateWholeName(self, panelNameDict):
            # print "update"
            # panelNameDict = {'dir': self.panelImageDir, 'pre': pre, 'num': num, 'post': post, 'ext': fext}
            self.wholeImageFileVar[0].set(panelNameDict['dir'])
            self.wholeImageFileVar[1].set(panelNameDict['pre'])
            self.wholeImageFileVar[2].set('n' * len(panelNameDict['num']))
            self.wholeImageFileVar[3].set(panelNameDict['post'])
            self.wholeImageFileVar[4].set(panelNameDict['ext'])
            # self.wholeImageFileVar[0].set('/directory/for/gifs/')

        def setWholeImages(self):
            newstate = NORMAL if not self.wholeImageSame.get() else DISABLED
            self.wholeImageBut.configure(state=newstate)
            self.wholeImageDirLabel.configure(state=newstate)
            self.wholeImagePreEntry.configure(state=newstate)
            self.wholeImageNumLabel.configure(state=newstate)
            self.wholeImagePostEntry.configure(state=newstate)
            self.wholeImageExtEntry.configure(state=newstate)


    mfic = MontageFileImportController(trackapp)
    # print 'got it:', mfic.status
    if mfic.status:
        return mfic.tm
    else:
        return None


class MontageReport(Toplevel):

    def __init__(self, displayText, titleText=""):
        Toplevel.__init__(self)
        if "Darwin" in platform.system():
            accel = 'Command'
        else:
            accel = 'Alt'
        self.bind_class("Text", "<Command-a>", self.selectall)
        s = ttk.Style()
        s.configure('My.TFrame', foreground='red')
        self.bind("<"+accel+"-w>", self.cancel)
        self.bind("<Escape>", self.cancel)
        self.title(titleText)
        frm = ttk.Frame(self, relief='flat', borderwidth=2, style='My.TFrame')
        frm.config()
        okfrm = ttk.Frame(self, padding=[10, 10])

        self.txt = Text(frm, width=100, height=35, wrap='none')
        self.txt.insert(1.0, displayText)
        scrlY = Scrollbar(frm, command=self.txt.yview)
        scrlX = Scrollbar(frm, command=self.txt.xview, orient=HORIZONTAL)
        self.txt.config(yscrollcommand=scrlY.set)
        self.txt.config(xscrollcommand=scrlX.set)
        saveBut = ttk.Button(okfrm, text="Save...", command=self.save)
        okBut = ttk.Button(okfrm, text="OK", command=self.cancel)

        frm.pack(anchor='n', expand=YES, fill=BOTH)
        okfrm.pack(side=BOTTOM, expand=NO, fill=X)  # remove 'fill' parameter to place in center
        scrlY.pack(side=RIGHT, expand=NO, fill=Y)
        self.txt.pack(expand=YES, fill=BOTH)
        scrlX.pack(side=LEFT, expand=YES, fill=X)
        okBut.pack(side=RIGHT, expand=NO)
        saveBut.pack(side=RIGHT, expand=NO)

        center(self)
        self.txt.focus_set()

    def cancel(self, event=None):
        """
        close the window
        @param event: an optional triggering event, needed when called by keypress events
        """
        # print 'cancel'
        self.destroy()

    def save(self):
        thetext = self.txt.get('1.0', 'end')
        # print 'save'
        savefilename = tkFileDialog.asksaveasfilename(defaultextension='.txt')
        if savefilename:
            savefile = open(savefilename, mode='w')
            savefile.write(thetext)
            savefile.close()
        # self.cancel()

    def selectall(self, event):
        event.widget.tag_add("sel", "1.0", "end")

if __name__ == "__main__":
    bigroot = Tk()
    bigroot.mainloop()
    newtm = importTrackmodel()
    if newtm is not None:
        # print newtm.__dict__
        pass
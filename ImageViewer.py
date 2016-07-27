#!/usr/bin/env python
# encoding: utf-8
"""
ImageViewer.py

Created by Ben Braun on 2012-08-15.
Copyright (c) 2012 __MyCompanyName__. All rights reserved.
"""

import os
import platform
import glob
from Tkinter import *
import ttk
import Trackmodel


from Tkinter import *


class ToolTip(object):

    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text, x=None, y=None):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        # x, y, cx, cy = self.widget.bbox("insert")
        # x = x + self.widget.winfo_rootx() + 27  # rootx get screen coordinate
        # y = y + cy + self.widget.winfo_rooty() +27
        x = x or 50
        y = y or 50
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        try:
            # For Mac OS
            tw.tk.call("::tk::unsupported::MacWindowStyle",
                       "style", tw._w,
                       "help", "noActivates")
        except TclError:
            pass
        label = Label(tw, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1,
                      font=("arial", "20", "normal"))
        label.pack(ipadx=1)
        wx = x - (label.winfo_reqwidth() / 2)
        wy = y - label.winfo_reqheight() - 3
        tw.wm_geometry("+%d+%d" % (wx, wy))  # sets screen coordinates of tooltip window (top left corner)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class ImageViewController(object):
    def __init__(self,  trackapp, firstTarget, highlightBox):
        self.trackapp = trackapp
        self.tm = trackapp.tm
        self.mc = trackapp.mc  # link to talk back to MontageController; maybe not needed, could go through trackapp
        firstImgIndex = int(self.tm.imageForKey(firstTarget))
        self.highlightBox = highlightBox  # (0, 0, 0, 0)
        self.iv = ImageOverlay(self, self.tm.wholeImageFilenameForIndex(firstImgIndex), highlightBox)
        # self.imgIndex = firstImgIndex  # a numeric index indicating the current image in the list
        self.imgIndex = firstImgIndex
        self.setImage(self.imgIndex)
        # self.current_selection = None
        # self.setModel(trackModel)

    def setModel(self, trackModel):  # unused?
        self.tm = trackModel
        # self.current_selection = ""

    def setImage(self, imageIndex, recenter=True):  # leaves highlightbox unchanged
        imgFilename = self.tm.wholeImageFilenameForIndex(imageIndex)
        if imgFilename is not None:
            self.imgIndex = imageIndex
            cells = self.tm.cellsForImage(self.imgIndex)
            splits = self.tm.cellsForImage(self.imgIndex, ['splits'])
            tips = self.tm.cellsForImage(self.imgIndex, ['tips'])  # TODO
            self.iv.drawImageOverlay(imgFilename, self.highlightBox, cells, recenter=recenter)
            self.iv.showCells(splits, r=3, fill='green2', outline='black')
            self.iv.showCells(tips, r=3, fill='red', outline='black')
            self.iv.lift()
            self.iv.focus_force()

    def setTarget(self, targetKey, highlightBox):
        self.highlightBox = highlightBox
        self.setImage(int(self.tm.imageForKey(targetKey)))

    def advance(self, delta):
        self.setImage(self.imgIndex + delta, recenter=False)

    def addKeyForReview(self, newKey):
        newIndex = self.trackapp.addKeyForReview(newKey)
        print newIndex
        self.trackapp.setReviewKeyIndex(newIndex)
        self.highlightBox = self.iv.highlightBox = self.mc.mgc.mgv.panelBbox()
        self.iv.updateHighlghtBox()


class ImageViewer(Toplevel, object):
    def __init__(self, imgFileList):
        Toplevel.__init__(self)
        self.imgFileList = imgFileList  # a list of file names, one for each image in the series
        self.imgIndex = 0  # a numeric index indicating the current image in the list (self.imgFileList)
        self.highlightBox = (0, 0, 0, 0)
        self.currentFile = ""
        self.frame = Frame(self,  bg="red")
        self.frame.grid(column=0, row=0, sticky=N+S+E+W)
        self.xscrollbar = Scrollbar(self.frame, orient=HORIZONTAL)
        self.xscrollbar.grid(row=1, column=0, sticky=E+W)
        self.yscrollbar = Scrollbar(self.frame)
        self.yscrollbar.grid(row=0, column=1, sticky=N+S)
        self.canvas = Canvas(self.frame, width=550, height=550,  bg="gray", xscrollcommand=self.xscrollbar.set, yscrollcommand=self.yscrollbar.set)
        if len(imgFileList) > 0:
            self.updateImg()
        self.canvas.grid(column=0, row=0, sticky=N+S+E+W)
        self.xscrollbar.config(command=self.canvas.xview)
        self.yscrollbar.config(command=self.canvas.yview)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        self.navFrame = ttk.Frame(self)
        self.navFrame.grid(column=0, row=1)
        self.butPrev = ttk.Button(self.navFrame, text='Prev', command=self.prior)
        self.butPrev.pack(side="left")
        self.butNext = ttk.Button(self.navFrame, text='Next', command=self.advance)
        self.butNext.pack()
        # createToolTip(self.butNext, 'hello')
        # key bindings
        self.bind("<Right>", self.keyPress)
        self.bind("<Left>", self.keyPress)
        if "Darwin" in platform.system():
            accel = 'Command'
        else:
            accel = 'Alt'
        self.bind('<'+accel+'-w>', lambda e: self.destroy())
        self.focus_force()
        #print "init - frame",self.frame.winfo_manager(), self.frame.winfo_width(), self.frame.winfo_reqheight()

    def keyPress(self, e):
        #print e.keysym
        if e.keysym == "Right":
            self.advance()
        elif e.keysym == "Left":
            self.prior()

    def setImage(self, imageName, highlightBox):
        if imageName in self.imgFileList:
            self.imgIndex = self.imgFileList.index(imageName)
            self.highlightBox = highlightBox
            self.updateImg()

    def advance(self):
        if self.imgIndex < len(self.imgFileList)-1:
            self.imgIndex += 1
            self.updateImg()

    def prior(self):
        if self.imgIndex > 0:
            self.imgIndex -= 1
            self.updateImg()

    def updateHighlghtBox(self):
        # (re)draw highlight box
        linecolor="green"
        self.canvas.delete("highlight")
        (x1, y1, x2, y2) = self.highlightBox
        # need to convert from image to canvas coordinates?
        rect = self.canvas.create_polygon(x1, y1, x1, y2, x2, y2, x2, y1, fill="", outline=linecolor, width="2", tag="highlight")
        self.canvas.tag_lower(rect)
        self.canvas.tag_lower(self.canvas.gettags('image'))

    def centerImg(self):
        # scroll to put cell of interest in center
        (x1, y1, x2, y2) = self.highlightBox
        self.frame.update_idletasks()
        fw = self.frame.winfo_width()
        fh = self.frame.winfo_height()
        cw = self.canvas.bbox(ALL)[2] - self.canvas.bbox(ALL)[0]
        ch = self.canvas.bbox(ALL)[3] - self.canvas.bbox(ALL)[1]
        cx = (x1+x2)/2.0
        cy = (y1+y2)/2.0
        xoffset = (cx - (fw/2.0)) / cw
        yoffset = (cy - (fh/2.0)) / ch
        self.canvas.xview_moveto(xoffset)
        self.canvas.yview_moveto(yoffset)

    def updateImg(self, recenter=True):
        gifFile = self.imgFileList[self.imgIndex]
        self.title(gifFile.rpartition('/')[2])
        imgobj = PhotoImage(file=gifFile)
        self.canvas.delete("image")
        image = self.canvas.create_image(0, 0, image=imgobj, anchor="nw", tag="image")
        self.canvas.tag_lower(image)
        self.canvas.config(scrollregion=self.canvas.bbox(ALL))
        self.canvas.img = imgobj  # need assignment to prevent garbage collection of PhotoImage object
        self.updateHighlghtBox()
        if recenter:
            self.centerImg()


class ImageOverlay(ImageViewer):
    def __init__(self, imageViewController, firstImgFile, firstHighlightBox):
        self.cells = {}
        imgFileList = [firstImgFile]
        self.ivc = imageViewController
        ImageViewer.__init__(self, imgFileList)
        ImageViewer.setImage(self, firstImgFile, firstHighlightBox)
        self.toolTip = ToolTip(self.canvas)

    def drawImageOverlay(self, imageName, highlightBox, cells, recenter=True):
        self.imgFileList = [imageName]
        self.imgIndex = self.imgFileList.index(imageName)
        self.highlightBox = highlightBox
        self.cells = cells
        self.updateImg(recenter)

    def updateImg(self, recenter=True):
        if len(self.imgFileList) > 0:
            super(ImageOverlay, self).updateImg(recenter=recenter)
        if len(self.cells) > 0:
            self.removeCells()
            self.showCells(self.cells, fill='black')

    def showCells(self, cells, r=2, fill='green', outline='black'):
        for cellKey, cell in cells.iteritems():
            (x, y) = (cell['cellX'], cell['cellY'])
            dot = self.canvas.create_oval(x-r, y-r, x+r, y+r, outline=outline, fill=fill, tags=("cell", cellKey))
            # self.toolTip = ToolTip(self.canvas)
            # self.canvas.tag_bind(dot, "<Enter>", lambda e: self.mydot(e, cellKey))
            self.canvas.tag_bind(dot, "<Enter>", lambda e: self.dotEnter(e))
            self.canvas.tag_bind(dot, "<Leave>", lambda e: self.dotLeave(e))
            self.canvas.tag_bind(dot, "<Double-Button-1>", lambda e: self.dotDoubleClick(e))

    def dotEnter(self, event):
        r = 10
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        dotIds = self.canvas.find_enclosed(x - r, y - r, x + r, y + r)
        # for r in [5,7,10,15]:
        #     print r, self.canvas.find_enclosed(x - r, y - r, x + r, y + r)
        thisKey = self.canvas.gettags(max(dotIds))[1]  # 2nd tag is cell key
        # print thisKey
        tipx = event.x + self.canvas.winfo_rootx()
        tipy = event.y + self.canvas.winfo_rooty()
        self.toolTip.showtip(thisKey, tipx, tipy)

    def dotLeave(self, event):
        self.toolTip.hidetip()

    def dotDoubleClick(self, event):
        r = 10
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        dotIds = self.canvas.find_enclosed(x - r, y - r, x + r, y + r)
        thisKey = self.canvas.gettags(max(dotIds))[1]  # 2nd tag is cell key
        print thisKey
        self.ivc.addKeyForReview(thisKey)

    def removeCells(self):
        self.canvas.delete("cell")

    def advance(self):
        self.ivc.advance(+1)

    def prior(self):
        self.ivc.advance(-1)



# def main():
#     workDir = "/Users/bbraun/Dropbox/python/4-28_Test_LAP"
#     os.chdir(workDir)
#     imgFileList = glob.glob("*Outline*.gif")
#     root = Tk()
#     iv = ImageViewer(imgFileList)
#     root.mainloop()
#     pass
#
#
# if __name__ == '__main__':
#     main()


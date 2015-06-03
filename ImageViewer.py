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


class ImageViewer(Toplevel):
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
        self.canvas.grid(column=0, row=0, sticky=N+S+E+W)
        self.xscrollbar.config(command=self.canvas.xview)
        self.yscrollbar.config(command=self.canvas.yview)
        self.updateImg()
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

    def updateImg(self):
        gifFile = self.imgFileList[self.imgIndex]
        self.title(gifFile.rpartition('/')[2])
        imgobj = PhotoImage(file=gifFile)
        self.canvas.delete("image")
        image = self.canvas.create_image(0, 0, image=imgobj, anchor="nw", tag="image")
        self.canvas.tag_lower(image)
        self.canvas.config(scrollregion=self.canvas.bbox(ALL))
        self.canvas.img = imgobj  # need assignment to prevent garbage collection of PhotoImage object
        # (re)draw highlight box
        linecolor="green"
        self.canvas.delete("highlight")
        x1 = self.highlightBox[0]
        y1 = self.highlightBox[1]
        x2 = self.highlightBox[2]
        y2 = self.highlightBox[3]
        # need to convert from image to canvas coordinates?
        rect = self.canvas.create_polygon(x1, y1, x1, y2, x2, y2, x2, y1, fill="", outline=linecolor, width="2", tag="highlight")
        # scroll to put cell of interest in center
        # currentScrollPosX = self.xscrollbar.get()
        self.update_idletasks()
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


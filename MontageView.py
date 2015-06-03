# load required modules
from collections import *
from Tkinter import *
import ttk
import ImageViewer
import platform


class LimitedSizeDict(OrderedDict):
    """from http://stackoverflow.com/questions/2437617/limiting-the-size-of-a-python-dictionary"""
    def __init__(self, *args, **kwds):
        self.size_limit = kwds.pop("size_limit", None)
        OrderedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=False)


class MontageController(object):
    def __init__(self, trackapp, tk_root):
        self.trackapp = trackapp
        self.mv = MontageView(self, tk_root)
        self.tm = self.mgc = self.current_selection = self.editMode = None
        # self.setModel(trackModel)

    def setModel(self, trackModel):
        self.tm = trackModel
        if self.mgc is None:
            self.mgc = MontageGridController(self.tm, self, self.mv)
        else:
            self.mgc.setModel(self.tm)
        self.current_selection = ""
        self.editMode = "Edit"

    def setEditMode(self, newMode):
        self.editMode = newMode

    def setMontage(self, m):
        self.mgc.setMontage(m)
        self.current_selection = ''
        self.setEditMode("Edit")
        self.mv.update_idletasks()
        # TODO: should this be where the current cell is selected, list boxes updated, etc?

    def makeMontage(self, objKey):
        return self.mgc.makeMontage(objKey)

    def updateListBoxes(self, selectedKey):
        self.mv.listboxParents.delete(0, END)
        self.mv.listboxChildren.delete(0, END)
        if selectedKey is not None and selectedKey != '':
            for parentKey in self.tm.cellForKey(selectedKey)['ParentKeys']:
                self.mv.listboxParents.insert(END, parentKey)
            for childKey in self.tm.cellForKey(selectedKey)['ChildKeys']:
                self.mv.listboxChildren.insert(END, childKey)
            self.mv.listboxParents.selection_set(0)
            self.mv.listboxChildren.selection_set(0)
            rootList = list(self.tm.rootListForCell(selectedKey))
            if len(rootList) > 7:
                rootList = rootList[0:6]
                rootList.append("...")
            tipList = list(self.tm.tipListForCell(selectedKey))
            if len(tipList) > 7:
                tipList = tipList[0:6]
                tipList.append("...")
            self.mv.tipListLabel.configure(text="\n".join(tipList))
            self.mv.rootListLabel.configure(text="\n".join(rootList))
            self.mv.ancestorKeyLabel.configure(text=self.tm.ancestorForCell(selectedKey), justify=CENTER)
            self.mv.descendantKeyLabel.configure(text=self.tm.descendantForCell(selectedKey))
            if selectedKey in self.tm.tipKeyList:
                self.mv.tipTypeEnabled(True)
                if self.tm.isDeath(selectedKey):
                    self.mv.tipTypeVar.set(0)
                elif self.tm.isDisappearance(selectedKey):
                    self.mv.tipTypeVar.set(1)
                else:
                    self.mv.tipTypeVar.set(-1)
            else:
                self.mv.tipTypeVar.set(-1)
                self.mv.tipTypeEnabled(False)
    #		print "Selection: ",selectedKey
    #		print "\tAncestor  :", ancestorForCell(selectedKey)
    #		print "\tDescendant:", descendantForCell(selectedKey)
    #		print "\tRoots     :", rootList
    #		print "\tTips      :", tipList

    def tipTypeChange(self, varname, varindex, mode):
        val = self.mv.tipTypeVar.get()
        # print "tip type", val
        # print self.tm.deathList
        # print self.tm.disappearList
        if val == 0:
            self.tm.makeDeath(self.current_selection, True)
            self.tm.makeDisappearance(self.current_selection, False)
        elif val == 1:
            self.tm.makeDeath(self.current_selection, False)
            self.tm.makeDisappearance(self.current_selection, True)
        else:
            self.tm.makeDeath(self.current_selection, False)
            self.tm.makeDisappearance(self.current_selection, False)

    def selectCell(self, selectedKey):
        if not self.tm.hasKey(selectedKey):  # not in self.tm.objectDictionary:
            if selectedKey != '':
                print "key selected but not found:", selectedKey
            else:
                self.mgc.deselectAll()
            # self.current_selection = ''
            self.setEditMode("Edit")
        else:
            currentKey = self.current_selection
            if self.editMode == "AddParent":
                if self.tm.linkCells(selectedKey, currentKey):
                    self.mgc.mgv.updateSpots(currentKey)
                    self.updateListBoxes(currentKey)
                self.setEditMode("Edit")
            elif self.editMode == "AddChild":
                if self.tm.linkCells(currentKey, selectedKey):
                    self.mgc.mgv.updateSpots(currentKey)
                    self.updateListBoxes(currentKey)
                self.setEditMode("Edit")
            else:
                self.mv.cellKeyLabel.configure(text=selectedKey)
                if currentKey != '':
                    self.mgc.deselect(currentKey)  # TODO: move this logic into the view
                self.mgc.showSelection(selectedKey)
                self.current_selection = selectedKey
                self.updateListBoxes(selectedKey)

    def deleteCellClick(self):
        delKey = self.current_selection
        print 'del: ', delKey
        if self.tm.hasKey(delKey):
            deleted = self.tm.cellForKey(delKey)
            if deleted['ChildCount'] > 0:
                selectKey = deleted['ChildKeys'][0]
            else:
                selectKey = ''
            self.tm.deleteCell(delKey)  # delete it from the model
            self.trackapp.removeKeyFromMontages(delKey)  # delete from montages
            self.mgc.deleteCell(delKey)  # delete it from the grid view
            self.selectCell(selectKey)

    def addCell(self, new_frame, new_x, new_y):
        self.tm.addCell(new_frame, new_x, new_y)

    def unlinkParentClick(self):
        cKey = self.current_selection
        parent_selection = self.mv.listboxParents.curselection()
        if len(parent_selection) == 0:
            print "no selection"
            self.mv.listboxParents.selection_set(0)
            parent_selection = self.mv.listboxParents.curselection()
        print parent_selection
        if len(parent_selection) > 0:
            pKeys = self.mv.listboxParents.get(parent_selection)
            if len(parent_selection) == 1:
                pKeys = [pKeys]
            for pKey in pKeys:
                print "unlink", pKey, "to", cKey
                self.tm.unlinkCells(pKey, cKey)
            self.updateListBoxes(cKey)
            self.mgc.mgv.updateSpots(self.current_selection)  # was: redrawMontage()

    def unlinkChildClick(self):
        pKey = self.current_selection
        selection = self.mv.listboxChildren.curselection()
        if len(selection) == 0:
            self.mv.listboxChildren.selection_set(0)
            selection = self.mv.listboxChildren.curselection()
        if len(selection) > 0:
            cKeys = self.mv.listboxChildren.get(selection)
            if len(selection) == 1:
                cKeys = [cKeys]
            for cKey in cKeys:
                print "unlink", pKey, "to", cKey
                self.tm.unlinkCells(pKey, cKey)
            self.updateListBoxes(pKey)
            self.mgc.mgv.updateSpots(self.current_selection)

    def linkClick(self, linkTarget):
        # create a link if NOT LINKED ALREADY...
        if not self.tm.linked(linkTarget, self.current_selection):
            if self.tm.linkCells(linkTarget, self.current_selection):
                self.mgc.mgv.updateSpots(self.current_selection)
                self.updateListBoxes(self.current_selection)
        # ...and undo a link if one exists
        else:
            # print "already linked"
            self.tm.unlinkCells(linkTarget, self.current_selection)
            self.mgc.mgv.updateSpots(self.current_selection)
            self.updateListBoxes(self.current_selection)

    def addParentClick(self):
        self.setEditMode("AddParent")

    def addChildClick(self):
        self.setEditMode("AddChild")

    def openImages(self):
        global iv
        ifl = self.tm.wholeImageFileList()
        iv = ImageViewer.ImageViewer(ifl)
        #iv.protocol("WM_DELETE_WINDOW", closeImageViewer)
        targetKey = self.current_selection
        imgFilename = self.tm.wholeImageFilenameForKey(targetKey)
        iv.setImage(imgFilename, self.mgc.mgv.panelBbox())
        iv.lift()
        iv.focus_force()

    ### methods that deal with application level logic ###
    # def newickOutput(self):
    #     newickList = self.tm.newickListFromRoots()
    #     print len(newickList), "lineages found"
    #     print ",".join(newickList)
    #     newickList.sort(key=lambda k: len(k), reverse=True)
    #     for newick in newickList:
    #         print newick
        ### consider ETE module for drawing tree
        # web viewer at: http:/ete.cgenomics.org/treeview
        # or treeviewx software (google code)
        # or Biopython http://biopython.org/wiki/Phylo#Displaying_trees

        ### or R module 'ape'
        # t4 = read.tree(text="(9-1:6,(9-2:3,9-3:3)6-2:3)3-1:3;")
        # plot(t4,show.node.label=TRUE,root.edge=TRUE)
        # for multiple, can just concatenate strings, or:
        # l<-c(tree,tree3)
        # plot(l,layout=2, show.node.label=TRUE,root.edge=TRUE)
        # also can lay out with
        #layout(matrix(1:6, 3, 2)) or grid graphics, etc.

    def nextMontage(self):
        self.trackapp.nextMontage()

    def priorMontage(self):
        self.trackapp.priorMontage()

    def setReviewKeyIndex(self, newIndex):
        self.trackapp.setReviewKeyIndex(newIndex)

    def goToMontage(self):
        self.trackapp.goToMontage()

    # def recalculateReviewKeyList(self):
    #     self.trackapp.recalculateReviewKeyList()

    # def saveSession(self):
    #     self.trackapp.saveSession()
    #
    # def loadSession(self):
    #     self.trackapp.loadSession()


class MontageGridController(object):  # interacts with model on behalf of view
    def __init__(self, trackModel, montageController, montageView):
        self.tm = trackModel
        self.montage = []  # a list of panels
        self.imgList = []
        self.selectedKey = ''
        self.targetKey = ''
        self.mgv = MontageGridView(self, montageView.montageFrame)  # make a new view, with me as controller
        montageView.setMontageGridView(self.mgv)  # add this view to the app window
        self.mc = montageController  # None  # to be filled in later
        # self.times=[]

    def setModel(self, trackModel):
        self.tm = trackModel

    def spotForKey(self, spottedKey):
        # returns "spot" data: dictionary with x, y, label and key
        spotted = self.tm.cellForKey(spottedKey)  # objectDictionary[spottedKey]
        newSpot = dict()
        newSpot['x'] = spotted['cellX']
        newSpot['y'] = spotted['cellY']
        newSpot['label'] = spotted['ObjectNumber']
        newSpot['key'] = spottedKey
        return newSpot

    def labelForKey(self, labelKey):
        # returns a label structure for a specified cell (a dictionary with items: x,y,label,key)
        labelled = self.tm.cellForKey(labelKey)  # objectDictionary[labelKey]
        newLabel = dict()
        newLabel['x'] = labelled['cellX']
        newLabel['y'] = labelled['cellY']
        newLabel['label'] = labelled['ObjectNumber']
        newLabel['key'] = labelKey
        return newLabel

    def calcSpotsForCell(self, spotKey):
        # add spot coordinates for cells in selected lineage to each panel in the montage
        # note - this gets called any time a new cell is selected
        if spotKey in self.tm.objectDictionary:
            firstPanel = self.montage[0]
            lastPanel = self.montage[len(self.montage)-1]
            startIndex = firstPanel['frame']
            endIndex = lastPanel['frame']
            lineageKeySet = self.tm.lineageByFrames(spotKey, startIndex, endIndex)
            #print "lineage:",lineageKeySet
            for panel in self.montage:
                spotList = []  # list of highlight spots (x,y) for this panel
                tipSpotList = []  # list of tips fo special highlighting
                for lineageKey in lineageKeySet:
                    if panel['frame'] == int(self.tm.cellForKey(lineageKey)['ImageNumber']):
                        # check for special keys
                        if lineageKey in self.tm.tipKeyList:
                            tipSpotList.append(self.spotForKey(lineageKey))
                        else:
                            spotList.append(self.spotForKey(lineageKey))
                panel['spots'] = spotList
                panel['tipspots'] = tipSpotList

    def childSpotsForKey(self, parentKey):
        return self.tm.childrenForKey(parentKey)

    def parentSpotsForKey(self, childKey):
        return self.tm.parentsForKey(childKey)

    # def prof(self, times, message=""):
    #     # profile execution time
    #     times.append(time.time())
    #     if len(times)>1:
    #         print "%.6f \t %s" % (times[-1] - times[-2], message)
    #         pass
    #     else:
    #         pass
    #         print "%.6f \t %s" % (0.0, message)

    def makeMontage(self, objKey):
        """create a 'montage' data structure for the cell having the specified key
            a montage is a list of panels
            a panel is a dictionary of: image filename, cropping info, & list of cell locations in the cropped image
                'targetKey': the key of the cell at the focus of the montage (same for all panels)
                'frame': the index of the image for this panel in the whole series (frame number)
                'imgFile': filename for the image used in this panel
                'cx': x coordinate in image for center of panel
                'cy': y coordinate in image for center of panel
                'w': half-width of panel, in pixels
                'h': half-height of panel, in pixels
                'spots': a list of spots which indicate cells to be circled in this panel (i.e. linked to selected cell)
                'labels': the list of cell labels that appear in this panel
            Note that the number of panels in a montage, specified by 2*margin+1, is currently hard coded with margin=10
            and panel size is hard coded with w = h = 40 pixels
        """
        # mytimes = []
        # self.prof(mytimes, 'start')

        target = self.tm.cellForKey(objKey)
        #childKeys  = target['ChildKeys']
        #parentKeys = target['ParentKeys']
        #print "(%s) -> [%s] -> (%s)" %(parentKeys, objKey, childKeys )
        targetImageNumber = int(target['ImageNumber'])
        targetX = target['cellX']
        targetY = target['cellY']
        width = 40
        height = 40
        minX = targetX - width
        maxX = targetX + width
        minY = targetY - height
        maxY = targetY + height
        #targetImage = imageDictionary[target]
        margin = 10  # number of frames to show on either side of the target
        startIndex = max(targetImageNumber - margin, 1)
        endIndex = min(startIndex + 2 * margin, len(self.tm.imageDictionary))
        montage = []
        # self.prof(mytimes, 'pre-loop')
        for i in range(startIndex, endIndex+1, 1):
            imgFilename = self.tm.panelImageFilenameForIndex(i)
            spotList = []  # list of highlighted spots (x,y) in this panel; calculated on cell selection
            imgData = self.tm.imageDictionary[i]
            cellKeys = [ck for ck in imgData['objectKeys'] if self.tm.hasKey(ck)]
            filteredKeys = [ck for ck in cellKeys if minX < self.tm.cellForKey(ck)['cellX'] < maxX and
                                                     minY < self.tm.cellForKey(ck)['cellY'] < maxY]
            # self.prof(mytimes, 'filtered keys')
            labelList = [self.labelForKey(ck) for ck in filteredKeys]
            panel = {'targetKey': objKey, 'frame': i, 'imgFile': imgFilename, 'cx': targetX, 'cy': targetY, 'w': width,
                     'h': height, 'spots': spotList, 'labels': labelList}
            montage.append(panel)
            # self.prof(mytimes, 'loop')
        # self.prof(mytimes, 'end')
        return montage

    def setMontage(self, new_montage):
        self.montage = new_montage
        self.mgv.montage = new_montage
        self.mgv.placeImages()
        #self.placeSpots()  # spots placed on cell selection
        self.mgv.placeLabels()

    def showSelection(self, selectedKey):
        self.mgv.showSelection(selectedKey)

    def deselect(self, deselectKey):
        self.mgv.deselect(deselectKey)

    def deselectAll(self):
        self.selectedKey = ''
        self.mgv.deselectAll()

    def selectCell(self, selectedKey):
        self.mc.selectCell(selectedKey)

    def deleteCell(self, delKey):
        # easiest (and fast enough) to update display by redrawing all the labels
        self.mgv.placeLabels()

    def addCell(self, clicked_frame, new_x, new_y):
        self.mc.addCell(clicked_frame, new_x, new_y)
        # m = self.makeMontage(self.montage[0]['targetKey'])
        m = self.mc.trackapp.fetchMontageForKey(self.montage[0]['targetKey'])
        self.setMontage(m)  # redraw
        pass

    def linkClick(self, linkTarget):
        self.mc.linkClick(linkTarget)


class MontageGridView(Canvas):  # a canvas for the grid of panels in the montage
    def __init__(self, controller, canvas_parent, **canvas_options):
        Canvas.__init__(self, canvas_parent, **canvas_options)
        self.mgc = controller
        self.montage = []  # a list of panels
        self.imgList = []
        self.imgCacheSize = 30  # should be larger than number of panels in grid
        self.imgCache = LimitedSizeDict(size_limit=self.imgCacheSize)
        self.configure(width=1200, height=510)
        self.spotRadius = 10
        self.labelColor = "green2"  # "red"
        self.labelBackground = "black"  # "red"
        self.selectedLabelColor = "yellow"  # "red"
        self.spotColor = "cyan"  # "blue"
        self.padx = 10
        self.pady = self.padx
        self.maxStripWidth = 1200
        self.zoomFactor = 2  # integer only; number of screen pixels for each original image pixel
        self.bind("<ButtonRelease-1>", self.montageClick)
        self.selectedKey = ''

    @staticmethod
    def subimage(src, l, t, r, b):
        dst = PhotoImage()
        dst.tk.call(dst, 'copy', src, '-from', l, t, r, b, '-to', 0, 0)
        return dst
        # from http://tkinter.unpythonic.net/wiki/PhotoImage

    def getImage(self, filename):
        """
        create a Photo image object or retrieve it from the cache
        """
        if filename in self.imgCache.keys():
            imgobj = self.imgCache[filename]
        else:
            imgobj = PhotoImage(file=filename)
            self.imgCache[filename] = imgobj
        return imgobj

    def placeImages(self):
        """
        display the cropped images for each panel in the current montage
        """
        # remove old images and image numbers using canvas tags
        self.delete("panelImage")
        self.delete("frameNumber")
        # undo any current selection
        self.selectedKey = ''
        padx = self.padx
        pady = self.pady
        panelx = padx  # coordinates for placement of the top left corner of the panel
        panely = pady  # in the window
        zoomFactor = self.zoomFactor
        for panel in self.montage:
            # calculate cropping coordinates
            imgobj = self.getImage(panel['imgFile'])
            left = panel['cx'] - panel['w']
            right = left + panel['w']*2
            top = panel['cy'] - panel['h']
            bottom = top + panel['h']*2

            # adjust cropping coordinates to image boundaries if needed
            left = max(left, 0)
            right = min(right, imgobj.width())
            top = max(top, 0)
            bottom = min(bottom, imgobj.height())

            subimgobj = self.subimage(imgobj, left, top, right, bottom)
            subimgobj = subimgobj.zoom(zoomFactor)
            image = self.create_image(panelx, panely, image=subimgobj, anchor="nw", tag="panelImage")
            panel['panelx'] = panelx
            panel['panely'] = panely
            panel['canvasImage'] = image
            self.imgList.append(subimgobj)
            self.tag_lower(image)
            # add frame number labels
            frameTxt = self.create_text(panelx, panely+subimgobj.height(), text=panel['frame'], fill="white", anchor='sw', tag="frameNumber")
            self.create_rectangle(self.bbox(frameTxt), fill="black", outline="white", width=1, tag="frameNumber")
            self.tag_raise(frameTxt)
            # update panel position for next iteration
            panelx = self.bbox(image)[2] + padx
            # if next panel will put it off the right side...reset x to 0 and increment y for next row
            if panelx+subimgobj.width() > self.maxStripWidth:
                panelx = padx
                panely = self.bbox(image)[3] + pady

    def placeLabels(self):
        """
        show labels for every cell in each panel of the current montage
        """
        # remove labels using canvas tags
        self.delete("cellNumber")
        labelColor = self.labelColor

        # import random
        # r = lambda: random.randint(0,255)
        # labelColor = '#%02X%02X%02X' % (r(),r(),r())

        zoomFactor = self.zoomFactor
        # padx = self.padx
        r = self.spotRadius
        for panel in self.montage:
            panelx = panel['panelx']
            panely = panel['panely']
            # image  = panel['canvasImage']
            #panelWidth  = self.bbox(image)[2] - self.bbox(image)[0]
            #panelHeight = self.bbox(image)[3] - self.bbox(image)[1]
            panelOffsetX = max(panel['cx'] - panel['w'], 0)
            panelOffsetY = max(panel['cy'] - panel['h'], 0)
            # add cell labels
            for labelItem in panel['labels']:
                #print labelItem
                cellX = labelItem['x']
                cellY = labelItem['y']
                cellOffsetX = zoomFactor*(cellX - panelOffsetX)
                cellOffsetY = zoomFactor*(cellY - panelOffsetY)
                labelX = panelx + cellOffsetX
                labelY = panely + cellOffsetY
                if self.labelBackground is not 'none':
                    bgoval = self.create_oval(labelX-r+4, labelY-r+4,
                                              labelX+r-4, labelY+r-4,
                                              fill=self.labelBackground, width=2, tag="cellNumber")
                self.create_text(panelx+cellOffsetX, panely+cellOffsetY, text=labelItem['label'],
                                 fill=labelColor, activefill="blue", anchor='center',
                                 tags=(labelItem['key'], "cellNumber"))
        self.update_idletasks()

    def placeSpots(self):
        """
        highlight any cells in lineage of selected cell with spots (i.e. circles) & lines
        spot locations have already been calculated in mgc.calcSpotsForCell()
        """
        # remove old spots & lines using canvas tags
        self.delete('spot')
        self.delete('line')
#       # add spots & lines; MUST come after image placement or geometry will not be defined
        spotColor = self.spotColor  # "blue"
        zoomFactor = self.zoomFactor
        padx = self.padx
        r = self.spotRadius
        #last_panely = -1
        for panel in self.montage:  # step through each image panel
            panelx = panel['panelx']
            panely = panel['panely']
            image = panel['canvasImage']
            panelWidth = self.bbox(image)[2] - self.bbox(image)[0]
            panelHeight = self.bbox(image)[3] - self.bbox(image)[1]
            panelOffsetX = max(panel['cx'] - panel['w'], 0)
            panelOffsetY = max(panel['cy'] - panel['h'], 0)
            for spot in panel['spots']:
                spotX = panelx + zoomFactor*(spot['x'] - panelOffsetX)
                spotY = panely + zoomFactor*(spot['y'] - panelOffsetY)
                oval = self.create_oval(spotX-r, spotY-r, spotX+r, spotY+r, outline=spotColor, width=2, tag='spot')
                # bgoval = self.create_oval(spotX-r+4, spotY-r+4, spotX+r-4, spotY+r-4, fill="black", width=2, tag='spot')
                # spotTarget = tm.cellForKey(spot['key'])  #tm.objectDictionary[spot['key']]
                # draw a line from this spot to any children
                children = self.mgc.childSpotsForKey(spot['key'])
                for spotChild in children:
                    #spotChild = tm.cellForKey(spotChildKey)  # objectDictionary[spotChildKey]
                    frameInterval = int(spotChild['ImageNumber']) - int(panel['frame'])
                    childx = spotChild['cellX']
                    childy = spotChild['cellY']
                    destx = panelx + zoomFactor*(childx - panelOffsetX) - r + (panelWidth + padx)*frameInterval
                    desty = panely + zoomFactor*(childy - panelOffsetY)
                    childLine = self.create_line(spotX+r, spotY, destx, desty, fill=spotColor, width=3, tag='line')
                    #  if the line goes off the right edge, draw a line off the left edge on the next line
                    if destx > self.maxStripWidth:
                        if self.montage.index(panel) + frameInterval < len(self.montage):
                            parentLine = self.create_line(spotX+r-self.maxStripWidth+self.padx, spotY+panelHeight+self.pady,
                                                          destx-self.maxStripWidth+self.padx, desty+panelHeight+self.pady,
                                                          fill=spotColor, width=3, tag='line')
            # add special spots for tips
            for spot in panel['tipspots']:
                spotX = panelx + zoomFactor*(spot['x'] - panelOffsetX)
                spotY = panely + zoomFactor*(spot['y'] - panelOffsetY)
                # rect = self.create_rectangle(spotX-r, spotY-r, spotX+r, spotY+r, outline=spotColor, width=2, tag='spot')
                dmd = self.create_line(spotX-r*2, spotY,
                                       spotX, spotY-r*2,
                                       spotX+r*2, spotY,
                                       spotX, spotY+r*2,
                                       spotX-r*2, spotY,
                                       # dash=(4, 4),
                                       fill=spotColor, width=2, tag='spot')
        self.update_idletasks()

    def panelBbox(self):
        panel = self.montage[0]
        return panel['cx']-panel['w'], panel['cy']-panel['h'], panel['cx']+panel['w'], panel['cy']+panel['h']

    def montageClick(self, event):
        # print "state", format(event.state, '08x'), bin(event.state)
        canvas = event.widget
        x = canvas.canvasx(event.x)
        y = canvas.canvasy(event.y)
        newMode = (event.state & 0x0004) > 0  # check for Ctl-click
        if newMode:
            print "ctl-click"
            items = canvas.find_overlapping(x-1, y-1, x+1, y+1)
            print items
            for item in items:
                tags = canvas.gettags(item)
                if 'panelImage' in tags:
                    # bbx = canvas.bbox(item)
                    panel_coords = canvas.coords(item)
                    clicked_panels = [p for p in self.montage if p['panelx'] == panel_coords[0] and
                                                                 p['panely'] == panel_coords[1]]
                    clicked_panel = clicked_panels[0]
                    # TODO: move some of this stuff into the controller
                    clicked_frame = clicked_panel['frame']
                    # clicked_file = clicked_panel
                    dx = x - clicked_panel['panelx']  # distance from left edge in canvas coord
                    dy = y - clicked_panel['panely']
                    new_x = max(clicked_panel['cx'] - clicked_panel['w'], 0) + dx/self.zoomFactor
                    new_y = max(clicked_panel['cy'] - clicked_panel['w'], 0) + dy/self.zoomFactor
                    self.mgc.addCell(clicked_frame, new_x, new_y)
            pass
        else:
            if "Windows" in platform.system():
                linkMode = (event.state & 0x20000) > 0  # this seems to be required in Win 7 for Alt key state
            else:
                linkMode = (event.state & 0x008) > 0
                # http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/event-handlers.html
            item = canvas.find_closest(x, y)
            selectedTag = canvas.gettags(item)[0]
            if selectedTag != 'panelImage' and selectedTag != 'frameNumber':
                if linkMode:
                    self.mgc.linkClick(selectedTag)
                else:
                    print selectedTag, " selected"
                    self.mgc.selectCell(selectedTag)

    def updateSpots(self, selectedKey):
        self.mgc.calcSpotsForCell(selectedKey)  # redefine spot list of each panel
        self.placeSpots()  # redraw

    def showSelection(self, selectedKey):
        #print "select", selectedKey
        selectedLabelItem = self.find_withtag(selectedKey)
        self.itemconfig(selectedLabelItem, fill=self.selectedLabelColor)
        if selectedKey != self.selectedKey:
            self.selectedKey = selectedKey
            self.updateSpots(selectedKey)

    def deselect(self, deselectKey):
        deselectedLabelItem = self.find_withtag(deselectKey)
        self.itemconfig(deselectedLabelItem, fill=self.labelColor)

    def deselectAll(self):
        #self.selectedKey = ''
        self.delete('spot')
        self.delete('line')


class MontageView(Frame):  # a main window for the whole app
    def __init__(self, montageController, root_tk):
        Frame.__init__(self)
        self.mc = montageController
        self.root = root_tk
        # self.root.bind("<Key>", self.keyPress)
        self.root.bind("<BackSpace>", lambda e: self.mc.deleteCellClick())
        self.root.bind("<Left>", lambda e: self.mc.priorMontage())
        self.root.bind("<Right>", lambda e: self.mc.nextMontage())

        # define widgets
        # the info panels are divided into 3 frames:
        #   cellInspectorFrame: viewing and editing data for the selected cell
        #   utilFrame:          navigation and utility buttons
        #   fileFrame:          application level functions, e.g. open/save/reports (currently empty)
        self.cellInspectorFrame = ttk.Frame(self.root, height=150, width=1200)
        self.utilFrame = ttk.Frame(self.root)
        self.fileFrame = ttk.Frame(self.root)

        self.cellKeyLabel = Label(self.cellInspectorFrame, text='cell', width=15, justify=CENTER, relief=GROOVE, font='Helvetica 18 bold')
        self.butDelete = ttk.Button(self.cellInspectorFrame, text='Delete', command=self.mc.deleteCellClick)
        self.butPrev = ttk.Button(self.utilFrame, text='<', command=self.mc.priorMontage)
        # self.butRedraw = ttk.Button(self.utilFrame, text='Redraw', command=self.testGo)
        # self.butImages = ttk.Button(self.utilFrame, text='Images', command=self.testGo)
        self.butNext = ttk.Button(self.utilFrame, text='>', command=self.mc.nextMontage)
        self.butGo = ttk.Button(self.utilFrame, text='Go To', command=self.mc.goToMontage)

        if 'Darwin' in platform.system():
            font_label = 'Helvetica 14 bold'
        else:
            font_label = 'Helvetica 11 bold'

        self.ancestorLabel = ttk.Label(self.cellInspectorFrame, text='Prior Branch', font=font_label)
        self.ancestorKeyLabel = ttk.Label(self.cellInspectorFrame, text='ancestorKey', font=font_label)
        self.rootsLabel = ttk.Label(self.cellInspectorFrame, text='  Roots  ', font=font_label)
        self.rootListLabel = ttk.Label(self.cellInspectorFrame, text='Roots', font=font_label, justify=CENTER)
        #self.listboxRoots = Listbox(self.cellInspectorFrame, height=3)

        self.parentsListLabel = ttk.Label(self.cellInspectorFrame, text='Parents', font=font_label)
        self.listboxParents = Listbox(self.cellInspectorFrame, height=3)
        self.unlinkParentButton = ttk.Button(self.cellInspectorFrame, text='Unlink Parent', command=self.mc.unlinkParentClick)
        self.addParentButton = ttk.Button(self.cellInspectorFrame, text='Add Parent', command=self.mc.addParentClick)

        self.childrenListLabel = ttk.Label(self.cellInspectorFrame, text='Children', font=font_label)
        self.listboxChildren = Listbox(self.cellInspectorFrame, height=3)
        self.unlinkChildButton = ttk.Button(self.cellInspectorFrame, text='Unlink Child', command=self.mc.unlinkChildClick)
        self.addChildButton = ttk.Button(self.cellInspectorFrame, text='Add Child', command=self.mc.addChildClick)

        self.descendantLabel = ttk.Label(self.cellInspectorFrame, text='Next Branch', font=font_label)
        self.descendantKeyLabel = ttk.Label(self.cellInspectorFrame, text='descendant', font=font_label)
        self.tipsLabel = ttk.Label(self.cellInspectorFrame, text='  Tips  ', font=font_label)
        self.tipListLabel = ttk.Label(self.cellInspectorFrame, text='Roots', font=font_label, justify=CENTER)
        #self.listboxTips = Listbox(self.cellInspectorFrame, height=3)

        self.heightHolder = ttk.Frame(self.cellInspectorFrame, height=150, width=1)

        self.sep1Label = ttk.Label(self.cellInspectorFrame, text='   ')
        self.sep2Label = ttk.Label(self.cellInspectorFrame, text='   ')

        s = ttk.Style()
        s.configure('My.TRadiobutton')
        s.map('My.TRadiobutton', foreground=[('disabled', 'gray')])
        self.tipTypeVar = IntVar()
        self.tipTypeVar.set(None)
        self.tipTypeDeath = ttk.Radiobutton(self.cellInspectorFrame,
                                            text="Death", variable=self.tipTypeVar, value=0,
                                            style='My.TRadiobutton')
        self.tipTypeDisappear = ttk.Radiobutton(self.cellInspectorFrame,
                                                text="Disappear", variable=self.tipTypeVar, value=1,
                                                style='My.TRadiobutton')
        self.tipTypeVar.trace('w', self.mc.tipTypeChange)
        # place widgets using grid
        self.rootsLabel.grid(row=0, column=0)
        self.rootListLabel.grid(row=1, column=0, columnspan=1, rowspan=2, sticky=N)
        self.ancestorLabel.grid(row=0, column=1)
        self.ancestorKeyLabel.grid(row=1, column=1, sticky=N)

        self.parentsListLabel.grid(row=0, column=2, columnspan=2, sticky=N)
        self.listboxParents.grid(row=1, column=2, columnspan=2)
        self.unlinkParentButton.grid(row=2, column=2)
        self.addParentButton.grid(row=2, column=3)

        self.sep1Label.grid(row=0, column=2)
        self.sep2Label.grid(row=0, column=4)

        self.cellKeyLabel.grid(row=1, column=5, columnspan=2)
        self.butDelete.grid(row=2, column=5, columnspan=2)

        # ttk.Label(self.cellInspectorFrame, text=' ', font='Helvetica 18 bold').grid(row=3, column=5, sticky=N)

        self.childrenListLabel.grid(row=0, column=7, columnspan=2)
        self.listboxChildren.grid(row=1, column=7, columnspan=2)
        self.unlinkChildButton.grid(row=2, column=7)
        self.addChildButton.grid(row=2, column=8)

        self.descendantLabel.grid(row=0, column=9)
        self.descendantKeyLabel.grid(row=1, column=9, sticky=N)
        self.tipsLabel.grid(row=0, column=10)
        self.tipListLabel.grid(row=1, column=10, columnspan=1, rowspan=2, sticky=N)

        self.heightHolder.grid(row=1, column=11, rowspan=3)

        self.tipTypeDeath.grid(row=3, column=5)
        self.tipTypeDisappear.grid(row=3, column=6)

        self.butPrev.grid(row=0, column=0)
        self.butGo.grid(row=0, column=1)
        self.butNext.grid(row=0, column=2)
        # self.butRedraw.grid(row=1, column=0)
        # self.butImages.grid(row=1, column=2)
        #print butNext.keys()

        # self.butRecalc = ttk.Button(self.fileFrame, text='Recalc', command=self.testGo)
        # self.butNewick = ttk.Button(self.fileFrame, text='Newick', command=self.testGo)
        # self.butOpen = ttk.Button(self.fileFrame, text='Open', command=self.testGo)
        # self.butSave = ttk.Button(self.fileFrame, text='Save', command=self.testGo)

        # self.butRecalc.grid(row=0, column=0)
        # self.butNewick.grid(row=0, column=1)
        # self.butOpen.grid(row=0, column=2)
        # self.butSave.grid(row=0, column=3)

        # lay out frames
        self.cellInspectorFrame.grid(row=1, column=0, sticky=N+S)
        self.montageFrame = ttk.Frame(self.root, width=1200, height=510)
        self.montageFrame.grid(row=0, column=0)
        self.utilFrame.grid(row=3, column=0)
        self.fileFrame.grid(row=4, column=0)

    def setMontageGridView(self, mgv):
        mgv.pack(side='left')
        #self.montageFrame.configure(width=mgv.bbox(ALL)[2])
        self.montageFrame.configure(width=mgv.config()['width'][4])
        self.montageFrame.grid(row=0, column=0)

    def tipTypeEnabled(self, value):
        if value:
            self.tipTypeDeath.configure(state=NORMAL)
            self.tipTypeDisappear.configure(state=NORMAL)
        else:
            self.tipTypeDeath.configure(state=DISABLED)
            self.tipTypeDisappear.configure(state=DISABLED)

    def keyPress(self, e):
        print e.keysym, " (in view)"
        if e.keysym == "BackSpace":  # NOT USED
            self.mc.deleteCellClick()
        elif e.keysym == "Tab":
            pass
        else:
            print "(key code: ", e.keycode, ")"

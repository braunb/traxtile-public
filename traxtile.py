# load required modules
import os                          # operating system tasks
from Tkinter import *
import ttk
import tkSimpleDialog
import tkFileDialog
import Trackmodel
import MontageView
import MontageFile
import Trax_io_isbi
import platform


try:
    import cPickle as pickle
except ImportError:
    import pickle

import sys
sys.setrecursionlimit(2000)  # default 1000


# class Worker(multiprocessing.Process):
#     def __init__(self, queue, outQueue, commandQueue, montageController):
#         self.__queue = queue
#         self.commandQueue = commandQueue
#         self.outQueue = outQueue
#         self.processItems = True
#         self.mc = montageController
#         multiprocessing.Process.__init__(self)
#
#     def drain(self): # flush the input queue
#         self.processItems = False
#         # woops! this is permanent - only call before shutdown
#
#     def run(self):
#         #global montageList
#         # global mc
#         p = multiprocessing.current_process()
#         print 'Starting:', p.name, p.pid
#         sys.stdout.flush()
#         running = True
#         while running:
#             if not self.commandQueue.empty():
#                 # warning - command will not be used if it is blocked on the regular queue
#                 command = self.commandQueue.get(False)  # nonblocking check for command
#                 if command == "drain":
#                     self.drain()
#                 elif command == "reset":
#                     while not self.__queue.empty():
#                         item = self.__queue.get(False)
#                         print "resetted", item
#             item = self.__queue.get()
#             if item != 'dummy':
#                 print item, "found by", p.name, p.pid
#                 # print "my mc:", self.mc
#                 if item is None:
#                     print "None found", p.pid
#                     #break # reached end of queue
#                     running = False
#                 elif self.processItems == True:
#                     newMontage = self.mc.makeMontage(item)  # TODO: ACK!! no shared memory for multiprocessing!!!!
#                     self.outQueue.put(newMontage)
#                 else:
#                     print item, "drained"
#                     running = False
#         self.outQueue.close()  #### new 8/28 #####
#         print 'Exiting :', p.name, p.pid
#         sys.stdout.flush()


class Trackapp():

    def __init__(self):
        global root
        self.tm = None
        self.iv = None
        self.root = None
        self.mc = None
        self.montageDictionary = dict()  # a repository for previously made montages
        self.montageIndex = 0
        self.montageList = []
        self.reviewKeyList = []
        self.mc = MontageView.MontageController(self, root)
        # self.commandQueueList = []
        # self.montageQueue = None
        # self.keyQueue = None
        # self.priorityKeyQueue = None
        # self.WORKERS = 2
        # self.BUFFER_SIZE = 20
        # self.workers = []
        # self.workerPidList = []
        # set up view and main Tk window/event loop
        # root = Tk()

    def testTm(self):
        ttm = Trackmodel.MontageSession()
        # input files
        ttm.imageCsvFilename = "/Users/bbraun/Box Documents/montage/130530/data/TrackOUT_Image.csv"
        ttm.objectCsvFilename = "/Users/bbraun/Box Documents/montage/130530/data/TrackOUT_cells 100.csv"
        # ttm.objectCsvFilename = "/Users/bbraun/Box Documents/montage/130530/data/TrackOUT_cells.csv"
        ttm.imageCsvFilename = "/Users/bbraun/Box Documents/montage/130530/data/LAP_1st_phase/DefaultOUT_Image.csv"
        ttm.objectCsvFilename = "/Users/bbraun/Box Documents/montage/130530/data/LAP_1st_phase/1st_phase_edited.csv"
        # images
        ttm.panelImageDir = "/Users/bbraun/Box Documents/montage/130530/gif"
        ttm.wholeImageDir = "/Users/bbraun/Box Documents/montage/130530/gif"
        ttm.panelImgFilenameBase = "subtracted_2x_s1_t"  # used for montage panels; may be the same or different
        ttm.wholeImgFileNameBase = "subtracted_2x_s1_t"  # used for whole image viewer
        ttm.panelImgExt = ".gif"
        ttm.wholeImgExt = ".gif"

        # configure keys which may vary depending on the CellProfiler run
        ttm.keyname['ParentGroupIndex'] = 'TrackObjects_ParentImageNumber'
        ttm.keyname['ParentObjectNumber'] = 'TrackObjects_ParentObjectNumber'
        ttm.keyname['FrameIndex'] = 'Metadata_Time'

        ttm.saveFilename = "130530_s1_montage.pickle"  # saveFilename
        ttm.setup()
        return ttm

    def setModel(self, trackModel):
        global root
        # set up session and build model data structures
        # # tm.workDir = "/Users/bbraun/Box Documents/montage/130530/data"
        #
        # # output files
        # self.tm.saveFilename = "130530_s1_montage.pickle"  # saveFilename

        # DEATH AT 354-111

        # tm.workDir = "/Users/bbraun/Dropbox/python/5-4_C09/C09_wh_GIF"
        # tm.panelImageDir = ""
        # tm.imageCsvFilename = "C09_LAP_OUT_Image.csv"
        # tm.objectCsvFilename = "C09_LAP_OUT_FilteredCells.csv"
        # tm.wholeImgFileNameBase = "clc120504-001004_c09 mut d +gm wh_t"
        # tm.panelImgFilenameBase = "clc120504-001004_c09 mut d +gm wh_t"
        # # output files
        # tm.objectOutputFilename = "C09_new_cells.csv"
        # tm.saveFilename = saveFilename
        # # configure keys which may vary depending on the CellProfiler run
        # tm.KEYNAME_ParentGroupIndex   = 'TrackObjects_ParentGroupIndex'
        # tm.KEYNAME_ParentObjectNumber = 'TrackObjects_ParentObjectNumber'
        #

        # change to model's working directory
        #os.chdir(tm.workDir)
        #TODO: make sense of working directories, if any

        # set up model
        self.tm = trackModel
        # self.tm.setup()
        self.buildReviewKeyList()
        # print self.reviewKeyList
        # self.tm.summary()
        # for t in self.tm.times: print t

        self.mc.setModel(self.tm)

        # set up queues for montage generation
        # self.keyQueue = multiprocessing.Queue(0)
        # self.priorityKeyQueue = multiprocessing.Queue(0)
        # self.montageQueue = multiprocessing.Queue(0)
        # # self.montageList = []
        # # self.montageDictionary = dict()
        # # self.WORKERS = 2
        # # self.BUFFER_SIZE = 20
        # # self.workers = []
        # # self.workerPidList = []
        # # self.commandQueueList = []
        #
        # # Uh-oh, Worker gets a clone of the space including an empty mc
        #
        # for i in range(self.WORKERS):
        #     commandQueue = multiprocessing.Queue(0)
        #     if i == 0:
        #         workerProcess = Worker(self.priorityKeyQueue, self.montageQueue, commandQueue, self.mc)
        #     else:
        #         workerProcess = Worker(self.keyQueue, self.montageQueue, commandQueue, self.mc)
        #     # probably should be a daemon...
        #     workerProcess.start()  # start a worker
        #     self.workerPidList.append(workerProcess.pid)
        #     self.workers.append(workerProcess)
        #     self.commandQueueList.append(commandQueue)
        #
        # # self.notify("review splits")
        #
        # # reset queue and put in new review key list
        # #commandQueueList[0].put("reset")
        #
        # for reviewKey in self.reviewKeyList[0:self.BUFFER_SIZE-1]:
        #     self.keyQueue.put(reviewKey)
        # m = self.montageQueue.get(True, 20)
        m = self.fetchMontageForKey(self.reviewKeyList[0])
        self.montageDictionary[m[0]['targetKey']] = m
        self.montageIndex = 0
        self.mc.setMontage(m)
        self.mc.selectCell(self.reviewKeyList[0])  # start with the first cell selected

    @staticmethod
    def notify(alert):
        print "### " + alert + " ###"

#   def setTarget(self, targetKey):
#        self.targetKey = targetKey

    def buildReviewKeyList(self):
        # start with all splits & merges
        self.reviewKeyList = self.tm.splitKeyList + self.tm.mergeKeyList
        # add roots not in first frame
        # self.reviewKeyList += [k for k in self.tm.rootKeyList if k.partition("-")[0] != "1"]
        firstFrameString = self.tm.firstFrame()
        self.reviewKeyList += [k for k in self.tm.rootKeyList if k.partition("-")[0] != firstFrameString]
        # add tips not in last frame
        lastFrameString = self.tm.lastFrame()
        reviewTipKeyList = [k for k in self.tm.tipKeyList if k.partition("-")[0] != lastFrameString]  # last frame
        self.reviewKeyList += reviewTipKeyList
        # sort
        # self.reviewKeyList.sort(key=lambda k: self.tm.keySorter(k))
        self.reviewKeyList.sort(key=self.tm.keySorter)
        print "total", len(self.reviewKeyList), "to review"

    def saveSession(self, filename=None):
        if filename is None:
            filename = self.tm.saveFilename
        else:
            self.tm.saveFilename = filename
        #montageSession = MontageSession.fromObjects(objectDictionary, imageDictionary, sortedObjectKeys)
        #montageSession.dump(saveFilename)
        # print "splits: ", self.tm.splitKeyList
        self.tm.dump(filename)

    def loadSession(self, filename=None):
        if filename is None and self.tm is not None:
            filename = self.tm.saveFilename
        #montageSession   = MontageSession.load(saveFilename)
        #objectDictionary = montageSession.objectDictionary
        #imageDictionary  = montageSession.imageDictionary
        #sortedObjectKeys = montageSession.sortedObjectKeys
        if filename is not None:
            new_tm = Trackmodel.MontageSession.load(filename)
            self.setModel(new_tm)
            self.tm.saveFilename = filename
        # print "splits: ", self.tm.splitKeyList
        # self.buildReviewKeyList()
        # set up 1st screen and put new montages in the queue
        # self.montageIndex = -1
        # self.nextMontage()

    def removeKeyFromMontages(self, delKey):
        # remove label for deleted cell from all the panels of all the montages that have been created
        # TODO: this really belongs in a GUI controller
        for montKey, mont in self.montageDictionary.items():
            # TODO: THIS DOES NOT ACCOUNT FOR FUTURE LISTS QUEUED BUT NOT YET MADE
            # however, the drawing routine could check to see if each key is valid before drawing the label
            # TODO: refactor these using list comprehensions?
            # print "del from:", mont[0]['targetKey']
            for panel in mont:
                for spot in panel['spots']:
                    if spot['key'] == delKey:
                        panel['spots'].remove(spot)
                for labelItem in panel['labels']:
                    if labelItem['key'] == delKey:
    #					print "remove %s from %s" %(labelItem,panel)
                        panel['labels'].remove(labelItem)

    def fetchMontageForKey(self, requestedKey):
        m = self.mc.makeMontage(requestedKey)
        self.montageDictionary[requestedKey] = m
        # if requestedKey in self.montageDictionary.keys():
        #     # this montage has already been loaded, so just set it as current
        #     m = self.montageDictionary[requestedKey]
        # else:
        #     print "from queue", requestedKey  # ,"not in",montageDictionary.keys()
        #     # pull in all the ones waiting on the queue and see if the requested one is there
        #     # fetchedKey=''
        #     while not self.montageQueue.empty():
        #         m = self.montageQueue.get()
        #         fetchedKey = m[0]['targetKey']
        #         self.montageDictionary[fetchedKey] = m
        #     if requestedKey in self.montageDictionary.keys():
        #         print "montage %s found in queue" % requestedKey
        #         m = self.montageDictionary[requestedKey]
        #     else:
        #         print "not found in queue...requesting"
        #         # put a new request on the queue - high priority - and wait for it to come back
        #         # at this time, the multiprocessing library does not have a PriorityQueue in Python 2.7
        #         self.priorityKeyQueue.put(requestedKey)
        #         fetchedKey = ''
        #         while fetchedKey != requestedKey:
        #             m = self.montageQueue.get(True, 20)
        #             fetchedKey = m[0]['targetKey']
        #             print "got montage:", fetchedKey
        #             self.montageDictionary[fetchedKey] = m
        return m

    def nextMontage(self):
        # print "advance to: #%s of %s" % (self.montageIndex+1, len(self.reviewKeyList))
        if self.montageIndex >= len(self.reviewKeyList)-1:
            print "at end"
        else:
            self.montageIndex += 1
            requestedKey = self.reviewKeyList[self.montageIndex]
            # print "\tcurrent key: ", requestedKey
            if self.tm.hasKey(requestedKey):
                m = self.fetchMontageForKey(requestedKey)
                # editMode = "Edit"
                self.mc.setMontage(m)
                #currentKey = reviewKeyList[montageIndex]
                currentKey = m[0]['targetKey']  # this should be the same as requestedKey
                if self.tm.hasKey(currentKey):
                    # print "selecting key", currentKey
                    self.mc.selectCell(currentKey)
                else:
                    self.mc.selectCell('')
                # if self.montageIndex == 0:
                #     queueKeyList = self.reviewKeyList[0:min(len(self.reviewKeyList), self.BUFFER_SIZE)]
                #     print "queuing:", queueKeyList
                #     for qk in queueKeyList:
                #         #if qk not in montageDictionary.keys():
                #         self.keyQueue.put(qk)
                # if (self.montageIndex + self.BUFFER_SIZE) < len(self.reviewKeyList)-1:
                #     reviewKey = self.reviewKeyList[self.montageIndex + self.BUFFER_SIZE]
                #     self.keyQueue.put(reviewKey)
                #print "out",m
            else:
                # key is invalid, so try to go to the next one
                self.nextMontage()

    def priorMontage(self):
        if self.montageIndex > 0:
            # print "prior: #%s of %s" % (self.montageIndex-1, len(self.reviewKeyList))
            self.montageIndex -= 1
            requestedKey = self.reviewKeyList[self.montageIndex]
            if self.tm.hasKey(requestedKey):
                m = self.fetchMontageForKey(requestedKey)
                self.mc.setMontage(m)
                currentKey = m[0]['targetKey']
                if self.tm.hasKey(currentKey):  # in self.tm.objectDictionary:  # this should always be true (?)
                    self.mc.selectCell(currentKey)
                else:
                    self.mc.selectCell('')
            else:
                # invalid key, e.g. cell deleted, so keep going
                self.priorMontage()
        else:
            print "at beginning"

    def setReviewKeyIndex(self, newIndex):
        if newIndex < 0 or newIndex > len(self.reviewKeyList)-1:
            return
        self.montageIndex = newIndex
        requestedKey = self.reviewKeyList[self.montageIndex]
        m = self.fetchMontageForKey(requestedKey)
        # editMode = "Edit"
        self.mc.setMontage(m)
        #currentKey = reviewKeyList[montageIndex]
        currentKey = m[0]['targetKey']  # this should be the same as requestedKey
        if self.tm.hasKey(currentKey):  # in self.tm.objectDictionary:
            print "selecting key", currentKey
            self.mc.selectCell(currentKey)
        else:
            self.mc.selectCell('')
        # queueKeyList = self.reviewKeyList[self.montageIndex:min(len(self.reviewKeyList),
        #                                   self.montageIndex+self.BUFFER_SIZE)]
        # print "queuing:", queueKeyList
        # for qk in queueKeyList:
        #     #if qk not in montageDictionary.keys():
        #     self.keyQueue.put(qk)

    def goToMontage(self):
        # get a montage index to go to
        maxIndex = len(self.reviewKeyList)-1
        newIndex = tkSimpleDialog.askinteger("Go to montage", "Montage Index Number:", minvalue=0, maxvalue=maxIndex)
        print "go to:", newIndex
        if newIndex is not None:
            self.setReviewKeyIndex(newIndex)

    def recalculateReviewKeyList(self):
        currentKey = self.reviewKeyList[self.montageIndex]
        self.tm.identifySpecialNodes()
        self.buildReviewKeyList()
        # retain only those montages that are still in reviewKeyList
        self.montageDictionary = {k: v for k, v in self.montageDictionary.iteritems() if k in self.reviewKeyList}
        #update the current montage index; try to stay put
        if currentKey in self.reviewKeyList:
            self.montageIndex = self.reviewKeyList.index(currentKey)
            print "at: #%s of %s" % (self.montageIndex+1, len(self.reviewKeyList))
        else:
            # our current montage was deleted, so just go to the start
            self.montageIndex = 1
            self.priorMontage()
        print self.tm.summary()

    def cleanUp(self):
        global root
        print "cleanup"
    #     # flush key queues by telling one of the workers to pull any available keys without processing them
    #     self.commandQueueList[0].put("drain")
    # #	for cq in commandQueueList:
    # #		cq.close()
    # #	for w in workers:
    # #		w.join()
    #     # flush montage queue
    #     while not self.montageQueue.empty():
    #         m = self.montageQueue.get_nowait()
    #     # add end-of-queue markers, which causes worker processes to end
    #     for i in range(self.WORKERS):
    #         self.keyQueue.put(None)
    #     for w in self.workers:
    #         w.terminate()
    #     #keyQueue.close()
        root.destroy()


if __name__ == "__main__":
    root = Tk()
    root.title("Traxtile")
    #root.bind("<Key>", keyPress)

    def file_open(event=None):
        print 'open'
        fname = tkFileDialog.askopenfilename(defaultextension='.txl')  # TODO: validation check!!!
        if fname is not None:
            # newModel = trackapp.tm.load(fname)
            # trackapp.setModel(newModel)
            trackapp.loadSession(fname)
        else:
            print "cancel"

    def file_save(event=None):
        print 'save'
        saveFname = tkFileDialog.asksaveasfilename(defaultextension='.txl')
        if saveFname is not None:
            trackapp.saveSession(saveFname)

    def file_import(event=None):
        print 'import'
        newModel = MontageFile.importTrackmodel(trackapp)  # this actually sets the new model in trackapp
        print "new model:", newModel  # goes here right away; does not block on dialog
        if newModel is not None:
            pass
            # trackapp.setModel(newModel)

    def file_export(event=None):
        print 'export'
        exportFname = tkFileDialog.asksaveasfilename()
        trackapp.tm.saveObjectCsv(exportFname)

    def file_export_isbi12(event=None):
        print 'export isbi12'
        # exportFname = tkFileDialog.asksaveasfilename()
        Trax_io_isbi.isbi12_export(trackapp.tm)

    def recalc(event=None):
        if trackapp.tm is not None:
            trackapp.recalculateReviewKeyList()

    def report_summary(event=None):
        if trackapp.tm is not None:
            MontageFile.MontageReport(trackapp.tm.summary(), "Summary")

    def report_counts(event=None):
        if trackapp.tm is not None:
            r = MontageFile.MontageReport(trackapp.tm.frameCounts(), "Cells per frame")

    def report_newick(event=None):
        if trackapp.tm is not None:
            newickList = trackapp.tm.newickListFromRoots()
            t = "%d lineages found" % len(newickList)
            newickList.sort(key=lambda k: len(k), reverse=True)
            newickText = "\n".join(newickList)
            r = MontageFile.MontageReport(newickText, "Newick Format")

    def men2(event=None):
        print "bye"

    def close(event=None):
        quit()  # will invoke cleanup() through event binding, which includes root.destroy()

    def minimize(event=None):
        root.iconify()

    def openImages(event=None):
        if trackapp.tm is not None:
            trackapp.mc.openImages()

    root.option_add('*tearOff', FALSE)
    if "Darwin" in platform.system():
        accel = 'Command'
    else:
        accel = 'Alt'
    menubar = Menu(root)
    root['menu'] = menubar

    menu_file = Menu(menubar)
    menubar.add_cascade(menu=menu_file, label='File')
    menu_file.add_command(label='Open...', command=file_open, accelerator=accel+"-O")
    root.bind('<'+accel+'-o>', file_open)

    menu_file.add_command(label='Import CSV...', command=file_import, accelerator=accel+"-N")
    root.bind('<'+accel+'-n>', file_import)
    menu_file.add_separator()
    menu_file.add_command(label='Save...', command=file_save, accelerator=accel+"-S")
    root.bind('<'+accel+'-S>', file_save)
    menu_file.add_command(label='Export CSV...', command=file_export, accelerator=accel+"-E")
    menu_file.add_command(label="Export ISBI '12...", command=file_export_isbi12)
    menu_file.add_command(label='Close', command=close, accelerator=accel+"-W")
    root.bind('<'+accel+'-w>', close)

    menu_analyze = Menu(menubar)
    menubar.add_cascade(menu=menu_analyze, label='Analyze')
    menu_analyze.add_command(label='Recalculate', command=recalc)
    menu_analyze.add_command(label='Summary', command=report_summary, accelerator=accel+"-R")
    root.bind('<'+accel+'-r>', report_summary)
    menu_analyze.add_command(label='Counts', command=report_counts)
    menu_analyze.add_command(label='Newick tree format', command=report_newick)

    menu_window = Menu(menubar)
    menubar.add_cascade(menu=menu_window, label='Window')
    menu_window.add_command(label='Images', command=openImages, accelerator=accel+"-I")
    root.bind('<'+accel+'-i>', openImages)
    menu_window.add_command(label='Minimize', command=minimize, accelerator=accel+"-M")
    root.bind('<'+accel+'-m>', minimize)


    # MAC help menu
    if 'Darwin' in platform.system():
        # hm = Menu(menubar, name='help')
        # menubar.add_cascade(label='Help', menu=hm)
        # hm.add_command(label='hi', command=men2)
        # menubar.add_cascade(menu=help)
        pass

    trackapp = Trackapp()
#    trackapp.setModel(trackapp.testTm())
    root.focus_set()
    root.focus_force()
    #atexit.register(cleanUp)
    root.protocol("WM_DELETE_WINDOW", trackapp.cleanUp)

    try:
        if "Darwin" in platform.system():
            os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
        root.mainloop()
    except SystemExit:
        trackapp.cleanUp()
        #root.destroy()
        #raise

# TODO: resolution independence; actually won't be horrible as basic drawing & selection works
#    need to adjust tile # (margin) and label size too

# TODO: reconfigure image directories as needed
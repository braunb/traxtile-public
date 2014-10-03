# load required modules
import glob                        # wildcard file search
import os                          # file/path naming utilities
import csv                         # read/write .csv files
import math                        # required for exponential functions
import itertools                   # required for list flattening
import re                          # regex
import Trax_io_icy              # Icy file import
import Trax_io_trackmate
# import time

try:
    import cPickle as pickle
except ImportError:
    import pickle


class MontageSession(object):
    def __init__(self):
        # core data structures
        self.objectDictionary = dict()  # holds info about each cell (object), parents and children
        self.imageDictionary = dict()   # holds info about each frame in the series
        # imageDictionary does 2 things:
        #  (1) translates from a frame index to a file time #, which can differ when an input file for CP is missing
        #  (2) holds the list of keys for objects present in each frame, used for spots & labels
        self.keyTree = dict()    # used for building concise trees in Newick format
        # lists of 'special' cells, maintained to reduce need to query self.objectDictionary, which is costly
        self.rootKeyList = []    # a node that starts a lineage
        self.splitKeyList = []   # a node that splits
        self.branchKeyList = []  # a node at the top of a branch (branch point); i.e. produced by a split
        self.mergeKeyList = []   # a node that is produced by a merge
        self.tipKeyList = []     # a branch tip, i.e. end of a lineage
        self.deathList = []      # a cell death (a type of tip)
        self.disappearList = []  # a disappearance (a type of tip)
        # input files & directories
        self.panelImageDir = ""
        # self.imageCsvFilename = ""  # TODO: make this more flexible for variation in file format NOT!
        # self.objectCsvFilename = ""  # TODO: make this more flexible for variation in file format NOT!
        self.panelImgFilenameBase = ""  # used for montage panels; may be the same or different
        self.panelImgFilenamePost = ""
        self.panelImgExt = ""
        self.wholeImageDir = ""
        self.wholeImgFileNameBase = ""  # used for whole image viewer
        self.wholeImgFilenamePost = ""
        self.wholeImgExt = ""
        # output files
        self.saveFilename = ""
        # configure those keys which may vary depending on the input file from CellProfiler
        self.keyname = dict()
        self.keyname['ParentGroupIndex'] = ''
        self.keyname['ParentObjectNumber'] = ''
        self.keyname['FrameIndex'] = ''
        self.times = []

    def set_keyname(self, name, value):
        """
        configures key names for data model that can vary among different input files
        @param name: the standard internal name for this key, e.g. ParentGroupIndex or ParentObjectNumber
        @param value: the name of the corresponding column in the input file
        """
        self.keyname[name] = value

    # @classmethod
    # def fromObjects(cls, objectDictionary, imageDictionary, sortedObjectKeys):
    #     newObject = cls()
    #     newObject.objectDictionary = objectDictionary
    #     newObject.imageDictionary = imageDictionary
    #     newObject.sortedObjectKeys = sortedObjectKeys
    #     return newObject

    # @classmethod
    def notify(self, message):
        """
        log debug messages to console
        """
        # self.times.append(time.time())
        # if len(self.times)>1: print self.times[-1] - self.times[-2]
        print "### " + message + " ###"
        pass

    @classmethod
    def keySorter(cls, k):
        """
        utility for sorting object keys in the format [frame]-[object]
        @param k: the key
        @return: a float representation of the key that maintains sort order: [frame].000[object]
        """
        p = k.partition("-")
        return float(p[0]) + float(p[2]) / 10000

    def firstFrame(self):
        """
        get a string representing the first frame in the series
        @return: a string for the min frame among all the object keys
        """
        ff_int = min([int(k.partition("-")[0]) for k in self.objectDictionary.keys()])
        return str(ff_int)

    def lastFrame(self):
        """
        get a string representing the last frame in the series
        @return: a string for the max frame among all the object keys
        """
        lf_int = max([int(k.partition("-")[0]) for k in self.objectDictionary.keys()])
        return str(lf_int)

    def makeDeath(self, deathKey, value):
        """
        record the indicated object as a death event
        @param deathKey: key for the object that dies (the tip)
        @param value: TRUE to register as death, FALSE to register as not a death
        @return:
        """
        if value and not self.isDeath(deathKey):
            self.deathList.append(deathKey)
        elif not value and self.isDeath(deathKey):
            self.deathList.remove(deathKey)

    def isDeath(self, tipKey):
        """
        report whether the indicated object is a death
        @param tipKey: key for the tip object to be queried
        @return: TRUE if death, FALSE if not death
        """
        return tipKey in self.deathList

    def makeDisappearance(self, disKey, value):
        """
        record the indicated object as a disappearance event
        @param disKey: key for the object that disappears (the tip)
        @param value: TRUE to register as disappearance, FALSE to register as not a disappearance
        @return:
        """
        if value and not self.isDisappearance(disKey):
            self.disappearList.append(disKey)
        elif not value and self.isDisappearance(disKey):
            self.disappearList.remove(disKey)

    def isDisappearance(self, tipKey):
        """
        report whether the indicated object is a disappearance
        @param tipKey: key for the tip object to be queried
        @return: TRUE if disappearance, FALSE if not disappearance
        """
        return tipKey in self.disappearList

    def dump(self, filename):
        """
        save a binary file with the data model
        @param filename: name of saved file
        """
        data = self
        outFile = open(filename, 'wb')
        # print "saving data..."
        pickle.dump(data, outFile, pickle.HIGHEST_PROTOCOL)
        # print "done saving."

    @classmethod
    def load(cls, filename):
        """
        load a binary file with data model
        @param filename: file to be loaded; created with MontageSession.dump
        @return: a MontageSession object
        """
        new_ms_object = cls()
        inFile = open(filename, 'rb')
        if inFile != '':
            new_ms_object = pickle.load(inFile)
            # cls.notify("done loading.")
            new_ms_object.identifySpecialNodes()
            #parentChildCompleteness()
            new_ms_object.notify("Adding descendants to roots")
            for rootKey in new_ms_object.rootKeyList:
                new_ms_object.updateDescentBranch(rootKey)
            new_ms_object.notify("Adding descendants to branches")
            for branchKey in new_ms_object.branchKeyList:
                new_ms_object.updateDescentBranch(branchKey)
        return new_ms_object

    @staticmethod
    def saveCsv(saveDict, filename):
        """
        write a dictionary of dictionaries to CSV format, 1 row per entry, 1 column per field
        @param saveDict: dictionary of dictionaries; field names defined by keys in 1st entry
        @param filename: name of saved file
        """
        fieldList = saveDict[saveDict.keys()[0]].keys()
        # print "fieldList", fieldList
        objectOutFile = open(filename, 'wb')
        objectCsvWriter = csv.DictWriter(objectOutFile, fieldnames=fieldList, quoting=csv.QUOTE_NONNUMERIC)
        objectCsvWriter.writeheader()
        for key, item in saveDict.iteritems():
            objectCsvWriter.writerow(item)
        objectOutFile.close()

    # def saveObjectCsv(self, filename):  # NOT USED
    #     for k, v in self.objectDictionary.iteritems():
    #         self.objectDictionary[k]['Death'] = k in self.deathList
    #         self.objectDictionary[k]['Disappearance'] = k in self.disappearList
    #         parentGroupKey = self.keyname['ParentGroupIndex']
    #         parentObjectKey = self.keyname['ParentObjectNumber']
    #         self.objectDictionary[k][parentGroupKey] = int(v['ParentKeys'][0].partition("-")[0])
    #         self.objectDictionary[k][parentObjectKey] = int(v['ParentKeys'][0].partition("-")[2])
    #         # what if multiple parents? What does CP do?
    #         #  "For a merge, the child will have the label of the closest parent."
    #         # NOTE - this means some data is lost on CSV export; better to dump when possible
    #     self.saveCsv(self.objectDictionary, filename)

    #  def loadCsv(self):
    #  # may not use this - better to use pickle or json
    #      global objectOutputFilename
    #      objectOutFile = open(objectOutputFilename, 'rb')
    #      objectCsvReader = csv.DictReader(objectOutFile)
    #      objectDataList  = list(objectCsvReader)
    #      self.objectDictionary = dict()
    #      self.objectDictionary.clear()
    #      for item in objectDataList:
    #          objectKey = item['ImageNumber'] + "-" + item['ObjectNumber']
    #          # enter into object dictionary
    #          objectDictionary[objectKey] = item
    #      self.identifySpecialNodes()

    def imageDictionaryFromCsv(self, imageCsvFilename):  # THIS IS USED IN setup() ***
        """
        read a database of images, from file listed in self.imageCsvFilename (CellProfiler image data file)
        the key for imageDictionary is the image number, i.e. the nth file in the file list
        each item in imageDictionary requires these fields:
            objectKeys:
                a list of keys in objectDictionary, indicating all the objects in this particular image
            a frame indicator, which is stored in self.keyname['FrameIndex']:
                this stores the time step number associated with this image; e.g. image #2 may hold time step #5 if
                there are missing image files for time steps #2, #3 & #4.
        """
        # imageCsvFile = open(self.imageCsvFilename, 'rU')
        imageCsvFile = open(imageCsvFilename, 'rU')
        imageDataReader = csv.DictReader(imageCsvFile)
        imageDataList = list(imageDataReader)
        #filenameList = [ item['FileName_subtracted'] for item in imageDataList]
        for item in imageDataList:
        #	frameNumber = int(item['Metadata_Frame'])
            imageNumber = int(item['ImageNumber'])
            item['objectKeys'] = []
            #imageDictionary[frameNumber] = item
            # self.imageDictionary[imageNumber] = item
            # store item in imageDictionary, keeping only needed fields
            self.imageDictionary[imageNumber] = {k: item[k] for k in ['objectKeys', self.keyname['FrameIndex']]}

    def objectDictionaryFromCsv(self, objectCsvFilename):   # THIS IS USED IN setup() ***
        """
        read database of objects, from file listed in self.objectCsvFilename (CellProfiler object data file) OR
        a csv file exported by Traxtile
        """
        self.objectDictionary.clear()
        # objectCsvFile = open(self.objectCsvFilename, 'rU')
        objectCsvFile = open(objectCsvFilename, 'rU')
        objectDataReader = csv.DictReader(objectCsvFile)
        objectDataList = list(objectDataReader)
        # build the object dictionary - a dictionary of dictionaries
        # 	each object is identified by a key, and is itself a dictionary where each key is a field
        # 	this is like a SQL result, where the objectDictionary key is like the SQL primary key and points to a row
        keptKeys = ['ImageNumber', 'Location_Center_X', 'Location_Center_Y', 'ObjectNumber', self.keyname['FrameIndex'],
                    self.keyname['ParentGroupIndex'], self.keyname['ParentObjectNumber'], 'Death', 'Disappearance']
        for rawItem in objectDataList:
            item = {k: v for k, v in rawItem.iteritems() if k in keptKeys}  # keep only needed fields to conserve memory
            objectKey = item['ImageNumber'] + "-" + item['ObjectNumber']
            # get numeric values for cell location
            item['cellX'] = int(float(item['Location_Center_X']))
            item['cellY'] = int(float(item['Location_Center_Y']))
            # initialize extra fields with placeholder values
            if 'ChildKeys' in rawItem:
                item['ChildKeys'] = re.findall("\d+-\d+", rawItem['ChildKeys'])
            else:
                item['ChildKeys'] = []
            # import list of parents if present; otherwise, create it
            if 'ParentKeys' in rawItem:
                item['ParentKeys'] = re.findall("\d+-\d+", rawItem['ParentKeys'])
            else:
                item['ParentKeys'] = []
                parentGroup = str(int(float(item[self.keyname['ParentGroupIndex']])))
                parentObject = str(int(float(item[self.keyname['ParentObjectNumber']])))
                parentKey = parentGroup + "-" + parentObject
                if parentKey != '0-0' and self.hasKey(parentKey):
                    item['ParentKeys'].append(parentKey)
                    # item['ParentCount'] += 1
                    self.objectDictionary[parentKey]['ChildCount'] += 1
                    self.objectDictionary[parentKey]['ChildKeys'].append(objectKey)
            item['ChildCount'] = len(item['ChildKeys'])
            item['ParentCount'] = len(item['ParentKeys'])
            item['DescendantKey'] = ''
            item['BranchLength'] = 0
            item['AncestorKey'] = ''
            # enter the item into object dictionary
            self.objectDictionary[objectKey] = item
            # add reference to image data
            self.imageDictionary[int(item['ImageNumber'])]['objectKeys'].append(objectKey)
            # add special tip values
            # TODO: move assigning children to here, with data loading, since disk is probably rate limiting

    # def assignChildren(self):   # UNUSED????
    #     # count & assign children; 'ChildKeys' is a list of indices in objectDictionary
    #     for key, item in self.objectDictionary.items():
    #         parentGroup = str(int(float(item[self.keyname['ParentGroupIndex']])))
    #         parentObject = str(int(float(item[self.keyname['ParentObjectNumber']])))
    #         parentKey = parentGroup + "-" + parentObject
    #         if parentKey != '0-0' and self.hasKey(parentKey):
    #             item['ParentKeys'].append(parentKey)
    #             item['ParentCount'] += 1
    #             self.objectDictionary[parentKey]['ChildCount'] += 1
    #             self.objectDictionary[parentKey]['ChildKeys'].append(key)

    def parentChildCompleteness(self):
        """
        check that all parent-child relationships are reciprocal
        @return: TRUE if all relationships are OK, or FALSE if there are non-reciprocal links
        """
        self.notify("check parent/child completeness")
        errorList = []
        numCells = len(self.objectDictionary.keys())
        i = 0
        for key, item in self.objectDictionary.items():
            i += 1
            # percentDone = float(i) / float(numCells) * 100
            # print "checking key %s (%s %%)" % (key, percentDone)
            #make sure counts are accurate
            if item['ParentCount'] != len(item['ParentKeys']) and item['ParentKeys'] != ['0-0']:
                errorList.append({'key': key, 'err': 'bad count',
                                  'details': "parents %s (%s)" % (item['ParentKeys'], item['ParentCount'])})
            if item['ChildCount'] != len(item['ChildKeys']):
                errorList.append({'key': key, 'err': 'bad count',
                                  'details': "children %s (%s)" % (item['ChildKeys'], item['ChildCount'])})
                # do my parents think I'm their child?
            for pKey in item['ParentKeys']:
                if pKey not in self.objectDictionary:
                    errorList.append({'key': key, 'err': 'parent ' + pKey + ' did not exist'})
                    item['ParentKeys'].remove(pKey)
                    item['ParentCount'] = len(item['ParentKeys'])
                else:
                    parent = self.objectDictionary[pKey]
                    if key not in parent['ChildKeys']:
                        errorList.append({'key': key, 'err': 'parent ' + pKey + ' does not claim ' + key + ' as child'})
                # do my children think I'm their parent?
            for cKey in item['ChildKeys']:
                if cKey not in self.objectDictionary:
                    errorList.append({'key': key, 'err': 'child ' + cKey + ' does not exist'})
                else:
                    child = self.objectDictionary[cKey]
                    if key not in child['ParentKeys']:
                        errorList.append(
                            {'key': key, 'err': 'child  ' + cKey + ' does not claim  ' + key + ' as parent'})
        for e in errorList:
            self.notify(e)
        return len(errorList) == 0

    def blipCount(self):
        """
        count objects that have no parents of children (lifetime of 1 frame); some may be real but many will be noise
        @return: the number of blips in the data set
        """
        # if no parents, and no children, it is a blip
        blipDict = {k: v for k, v in self.objectDictionary.iteritems() if
                    (v['ParentCount'] == 0 and v['ChildCount'] == 0)}
        return len(blipDict)

    def blipPurge(self):
        """
        remove objects that appear out of nowhere and have no children; some may be real but many will be noise
        """
        self.objectDictionary = {k: v for k, v in self.objectDictionary.iteritems() if
                                 not (v['ParentCount'] == 0 and v['ChildCount'] == 0)}

    def gapList(self, parentKey):
        """
        for the given object, list the lengths of the intervals to its children
        @param parentKey: key for the object of interest
        @return: a list of gap lengths; 1 indicates no gap, i.e. the child is in the next frame
        """
        parent = self.objectDictionary[parentKey]
        parentFrame = int(parentKey.partition("-")[0])
        intervals = [int(k.partition("-")[0]) - parentFrame for k in parent['ChildKeys']]
        return intervals

    def hasGap(self, parentKey):
        """
        test whether an object had any children with gap > 1
        @param parentKey: key for the object of interest
        @return: TRUE if any gaps > 1 frame
        """
        return len([g for g in self.gapList(parentKey) if g > 1]) > 0  # TODO:  test or discard hasGap()

    @staticmethod
    def flatten(lofl):
        """
        flatten a list of lists
        @param lofl: list of lists
        @return: a simple list with all the elements in lofl, and no nested lists
        """
        return [val for sublist in lofl for val in sublist]

    def gapSummary(self):
        """
        summarize the gap lengths in the data set
        @return: a dictionary with keys 0, 1, 2, 3... and values equal to the number of gaps with length of the key
        """
        # make a dummy dictionary to hold distribution of gap sizes
        d = {gap_length: 0 for gap_length in range(0, 101)}  # key is gap length, value is count (initially 0)
        for k in self.objectDictionary.keys():
            for g in self.gapList(k):  # a list of the gap sizes for object k
                d[g] += 1
        maxGap = max({k: v for k, v in d.iteritems() if v > 0}.keys())
        # return "Gap sizes: " + str({k: v for k, v in d.iteritems() if 0 < k <= maxGap})
        gaps = {k: v for k, v in d.iteritems() if 0 < k <= maxGap}
        return "Gaps:\n" + self.formatTable([[" ", "size", "No."]] + [["", str(a), str(b)] for (a, b) in gaps.items()])

    def hasKey(self, queryKey):
        """
        check to see if a given key is valid for this data model
        @param queryKey: the key to be validated
        @return: TRUE if the object dictionary includes this key, otherwise FALSE
        """
        return queryKey in self.objectDictionary

    def cellForKey(self, targetKey):
        """
        return the cell data for a given object key
        @param targetKey: the key for the object
        @return: a dictionary holding data for the indicated object
        """
        return self.objectDictionary[targetKey]  # TODO: check for key validity in Tm.cellForKey

    def setCellForKey(self, newKey, newCell):
        """
        replace all the  data for the object identified by the given key
        @param newKey: the key in the object dictionary
        @param newCell: a dictionary containing the new object data
        """
        self.objectDictionary[newKey] = newCell

    def updateCellForKey(self, targetKey, attributeName, value):
        targetCell = self.cellForKey(self, targetKey)
        targetCell[attributeName] = value

    def parentsForKey(self, childKey):
        child = self.cellForKey(childKey)
        parentList = [self.cellForKey(pk) for pk in child['ParentKeys']]
        return parentList

    def childrenForKey(self, parentKey):
        parent = self.cellForKey(parentKey)
        childList = [self.cellForKey(ck) for ck in parent['ChildKeys']]
        return childList

    def panelImageFilenameForIndex(self, i):
        # TODO: less hard coding of image filenames...zfill(4) requires exactly 4 digits
        # TODO: consider eliminating imageDictionary altogether, if filenames can be in objectDictionary
        imgData = self.imageDictionary[i]
        #imageNumber = imgData['ImageNumber']
        timeNumber = imgData[self.keyname['FrameIndex']]  # imgData['Metadata_Time']  # get time number
        imgFilename = "{0}/{1}{2}{3}{4}".format(self.panelImageDir, self.panelImgFilenameBase, str(timeNumber).zfill(4),
                                                self.panelImgFilenamePost, self.panelImgExt)
        return imgFilename

    def panelImageFilenameForKey(self, targetKey):
        target = self.objectDictionary[targetKey]
        targetImageNumber = int(target['ImageNumber'])  # get image number from objectDictionary
        return self.panelImageFilenameForIndex(targetImageNumber)  # look up & return file name for that image number

    def wholeImageFileList(self):
        pass
        filename_template = "{0}/{1}*{2}{3}".format(self.wholeImageDir, self.wholeImgFileNameBase,
                                                    self.wholeImgFilenamePost, self.wholeImgExt)
        return [os.path.abspath(x) for x in glob.glob(filename_template)]

    def wholeImageFilenameForIndex(self, i):  # note - file for whole image may differ from montage panels
        # TODO: less hard coding of image filenames
        imgData = self.imageDictionary[i]
        #imageNumber = imgData['ImageNumber']
        timeNumber = imgData[self.keyname['FrameIndex']]  # imgData['Metadata_Time']
        imgFilename = "{0}/{1}{2}{3}{4}".format(self.wholeImageDir, self.wholeImgFileNameBase, str(timeNumber).zfill(4),
                                                self.wholeImgFilenamePost, self.wholeImgExt)
        return os.path.abspath(imgFilename)

    def wholeImageFilenameForKey(self, targetKey):
        target = self.objectDictionary[targetKey]
        targetImageNumber = int(target['ImageNumber'])
        return self.wholeImageFilenameForIndex(targetImageNumber)

    def ancestorForCell(self, targetKey):
        target = self.objectDictionary[targetKey]
        #print "descent for",targetKey,"with parents:",target['ParentKeys'], "(",target['ParentCount'],")"
        if target['ParentCount'] == 1:
            parentKey = target['ParentKeys'][0]
            if parentKey not in self.objectDictionary:
                print "Error:", parentKey, "not in self.objectDictionary"
                print "child:", targetKey
                print "parent count:", target['ParentCount']
                print "parent list:", target['ParentKeys']
                target['ParentKeys'].remove(parentKey)
                target['ParentCount'] = len(target['ParentKeys'])
                return targetKey
            parent = self.objectDictionary[parentKey]
            # walk up to root
            objKey = targetKey
            obj = target
            while obj['ParentCount'] == 1 and parent['ChildCount'] == 1:
                objKey = obj['ParentKeys'][0]
                obj = self.objectDictionary[objKey]
                if obj['ParentCount'] == 1:
                    parentKey = obj['ParentKeys'][0]
                    parent = self.objectDictionary[parentKey]
                    if parent['ChildCount'] > 1:
                        break  # the new parent is a splitter, so we are already at the top of the branch
                else:
                    break  # the object is a root
            rootKey = objKey
        else:
            # target is either a root or the product of a merge
            rootKey = targetKey
        return rootKey

    def descendantForCell(self, targetKey):
        # TODO: consider how to handle merge events for descendant call
        # only used for MV display purposes though? No...also for reporting imputed frame counts
        objKey = targetKey
        obj = self.objectDictionary[targetKey]
        while obj['ChildCount'] == 1:  # TODO: and ParentCount == 1 ?
            objKey = obj['ChildKeys'][0]
            obj = self.objectDictionary[objKey]
        return objKey

    def rootSetForCell(self, targetKey):
        # return a set of roots derived from a target (can be many due to merges)
        rootSet = set()
        if targetKey in self.objectDictionary:
            target = self.objectDictionary[targetKey]
            if target['ParentCount'] > 0:
                for parentKey in target['ParentKeys']:
                    rootSet |= self.rootSetForCell(parentKey)  # union operator
            else:
                rootSet.add(targetKey)
        return rootSet

    def rootListForCell(self, targetKey):
        return sorted(self.rootSetForCell(targetKey), key=lambda k: self.keySorter(k))

    def tipSetForCell(self, targetKey):
        # return a set of tips derived from a target
        tipSet = set()
        if targetKey in self.objectDictionary:
            target = self.objectDictionary[targetKey]
            if target['ChildCount'] > 0:
                for childKey in target['ChildKeys']:
                    tipSet |= self.tipSetForCell(childKey)  # union operator
            else:
                tipSet.add(targetKey)
        return tipSet

    def tipListForCell(self, targetKey):
        return sorted(self.tipSetForCell(targetKey), key=lambda k: self.keySorter(k))

    # procedure to update objects with ancestors, descendants & branch lengths
    def updateDescentBranch(self, targetKey):
        # find the appropriate root for the target key
        ancestorKey = self.ancestorForCell(targetKey)
        descendantKey = ''
        root = self.objectDictionary[ancestorKey]
        obj = root
        #print rootKey, "->", root['ChildKeys'], "(",root['ChildCount'],")"
        if root['ChildCount'] == 1:  # >0??? hard to handle split->split->split
            # walk down the tree of descent as long as there are no branches (ChildCount > 1) or tips (ChildCount=0)
            while obj['ChildCount'] == 1:
                obj['AncestorKey'] = ancestorKey # let every cell point to the top of its branch
                if obj['ChildKeys'][0] in self.objectDictionary:
                    descendantKey = obj['ChildKeys'][0]
                    descendant = self.objectDictionary[descendantKey]
                    #print "->", descendantKey, "(", descendant['ChildCount'], ")",
                    obj = descendant
                else:
                    obj['ChildKeys'].remove(obj['ChildKeys'][0])
                    obj['ChildCount'] = len(obj['ChildKeys'])
                # now update database with branch length info
            # note - according to Newick format, branch length belongs with descendant (i.e. distance from parent)
            root['DescendantKey'] = descendantKey
            descendant['AncestorKey'] = ancestorKey
            branchLength = int(descendant['ImageNumber']) - int(root['ImageNumber']) + 1
            descendant['BranchLength'] = branchLength
            #print "From %s to %s: %s to %s (%s)" %(ancestorKey, descendantKey, root['ImageNumber'], descendant['ImageNumber'], branchLength)
        else:
            #print "From %s: %s children" %(ancestorKey, root['ChildCount'])
            root['BranchLength'] = 1
            root['DescendantKey'] = ancestorKey
            root['AncestorKey'] = ancestorKey

    #	retval = {'branchLength':branchLength, 'DescendantKey':descendantKey}

    def identifySpecialNodes(self):
        #identify special nodes
        # empty current lists
        self.rootKeyList = []    # a node that starts a lineage
        self.splitKeyList = []   # a node that splits
        self.branchKeyList = []  # a node at the top of a branch (branch point); i.e. produced by a split
        self.mergeKeyList = []   # a node that is produced by a merge
        self.tipKeyList = []     # a branch tip
        # now fill them by going through each key one at a time
        # sortedObjectKeys = sorted(self.objectDictionary.keys(), key=lambda k: self.keySorter(k))
        # self.rootKeyList = [k for k in sortedObjectKeys if self.objectDictionary[k]['ParentCount'] == 0]
        # self.mergeKeyList = [k for k in sortedObjectKeys if self.objectDictionary[k]['ParentCount'] > 1]
        # self.tipKeyList = [k for k in sortedObjectKeys if self.objectDictionary[k]['ChildCount'] == 0]
        # self.splitKeyList = [k for k in sortedObjectKeys if self.objectDictionary[k]['ChildCount'] > 1]
        # branchKeyListOfLists = [self.objectDictionary[k]['ChildKeys'] for k in self.splitKeyList]
        # self.branchKeyList = list(itertools.chain.from_iterable(branchKeyListOfLists))  # flatten branchKey list

        self.rootKeyList = [k for k in self.objectDictionary.keys() if self.objectDictionary[k]['ParentCount'] == 0]
        self.mergeKeyList = [k for k in self.objectDictionary.keys() if self.objectDictionary[k]['ParentCount'] > 1]
        self.tipKeyList = [k for k in self.objectDictionary.keys() if self.objectDictionary[k]['ChildCount'] == 0]
        self.splitKeyList = [k for k in self.objectDictionary.keys() if self.objectDictionary[k]['ChildCount'] > 1]
        branchKeyListOfLists = [self.objectDictionary[k]['ChildKeys'] for k in self.splitKeyList]
        self.branchKeyList = list(itertools.chain.from_iterable(branchKeyListOfLists))  # flatten branchKey list

        self.rootKeyList.sort(key=self.keySorter)
        self.mergeKeyList.sort(key=self.keySorter)
        self.tipKeyList.sort(key=self.keySorter)
        self.splitKeyList.sort(key=self.keySorter)
        self.branchKeyList.sort(key=self.keySorter)

        # print self.rootKeyList
        # for key in sortedObjectKeys:
        #     item = self.objectDictionary[key]
        # if item['ParentCount'] == 0:
        #     self.rootKeyList.append(key)
        # if item['ChildCount'] > 1:
        #     self.splitKeyList.append(key)
        #     self.branchKeyList += item['ChildKeys']
        # if item['ParentCount'] > 1:
        #     self.mergeKeyList.append(key)
        # if item['ChildCount'] == 0:
        #     self.tipKeyList.append(key)
        #print "roots:",rootKeyList
        #print "branch heads:", branchKeyList
        #print "tips:",tipKeyList
        #print "merges:",mergeKeyList
        #print "splits:", self.splitKeyList

    # utilities for making & breaking parent/child links between cells in different frames
    def linked(self, key1, key2):
        retval = False
        pKey = min(key1, key2, key=self.keySorter)
        cKey = key2 if pKey == key1 else key1
        if self.hasKey(pKey) and self.hasKey(cKey):
            parent = self.cellForKey(pKey)
            child = self.cellForKey(cKey)
            retval = cKey in parent['ChildKeys'] or pKey in child['ParentKeys']
        return retval

    def unlinkCells(self, aKey, bKey):
        if self.hasKey(aKey) and self.hasKey(bKey):
            parentKey = aKey
            childKey = bKey
            parent = self.objectDictionary[parentKey]
            child = self.objectDictionary[childKey]
            if int(parent['ImageNumber']) > int(child['ImageNumber']):  # swap parent & child if 'child' is older
                parentKey, childKey = bKey, aKey
                parent, child = child, parent
            # remove the child from the parent's list
            if childKey in parent['ChildKeys']:
                parent['ChildKeys'].remove(childKey)
                parent['ChildCount'] = len(parent['ChildKeys'])
            # remove the parent from the child's list
            if parentKey in child['ParentKeys']:
                child['ParentKeys'].remove(parentKey)
                child['ParentCount'] = len(child['ParentKeys'])
            # update special records
            # the parent might have lost its splitter status (2 children -> 1)
            if parent['ChildCount'] == 1 and parentKey in self.splitKeyList:
                self.splitKeyList.remove(parentKey)
            # the parent might now be a tip (1 child -> 0)
            if parent['ChildCount'] == 0 and parentKey not in self.tipKeyList:
                self.tipKeyList.append(parentKey)
            # the child might have lost its merge status (2 parents -> 1)
            if child['ParentCount'] == 1 and childKey in self.mergeKeyList:
                self.mergeKeyList.remove(childKey)
            # the child may now be a root (1 parent ->0)
            if child['ParentCount'] == 0 and childKey not in self.rootKeyList:
                self.rootKeyList.append(childKey)
            self.updateDescentBranch(parentKey)
            self.updateDescentBranch(childKey)
        elif self.hasKey(bKey):  # catch errors in which the parent key is invalid
            child = self.objectDictionary[bKey]
            # remove the (invalid) parent key from the child's list
            if aKey in child['ParentKeys']:
                child['ParentKeys'].remove(aKey)
                child['ParentCount'] = len(child['ParentKeys'])
            self.updateDescentBranch(aKey)
        else:
            print "unable to unlink; bad key"

    def linkCells(self, aKey, bKey):
        print "link", aKey, "to", bKey
        try:
            parentKey = aKey
            childKey = bKey
            parent = self.objectDictionary[parentKey]
            child = self.objectDictionary[childKey]
            if int(parent['ImageNumber']) > int(child['ImageNumber']):  # swap parent & child if frames are reversed
                parentKey, childKey = bKey, aKey
                parent, child = child, parent
            if int(parent['ImageNumber']) < int(child['ImageNumber']):
                parent['ChildKeys'].append(childKey)
                parent['ChildCount'] = len(parent['ChildKeys'])
                child['ParentKeys'].append(parentKey)
                child['ParentCount'] = len(child['ParentKeys'])
                # update special records
                # the child may now be a merge (1 parent -> 2)
                if child['ParentCount'] == 2 and childKey not in self.mergeKeyList:
                    self.mergeKeyList.append(childKey)
                # the child may have lost its root status (0 parents -> 1)
                if child['ParentCount'] == 1 and childKey in self.rootKeyList:
                    self.rootKeyList.remove(childKey)
                # the parent may now be a splitter (1 child -> 2)
                if parent['ChildCount'] == 2 and parentKey not in self.splitKeyList:
                    self.splitKeyList.append(parentKey)
                # the parent may have lost its tip /death / disappearance status (0 children -> 1)
                if parent['ChildCount'] == 1 and parentKey in self.tipKeyList:
                    self.tipKeyList.remove(parentKey)
                    if self.isDeath(parentKey):
                        self.makeDeath(parentKey, False)
                    if self.isDisappearance(parentKey):
                        self.makeDisappearance(parentKey, False)
                self.updateDescentBranch(parentKey)
                self.updateDescentBranch(childKey)
            retval = True
        except KeyError:
            print "key error...no link made"
            retval = False
        return retval

    def deleteCell(self, delKey):
        deleted = self.objectDictionary[delKey]
        # unlink from children
        for cKey in deleted['ChildKeys']:
            self.unlinkCells(delKey, cKey)
        # unlink from parents
        for pKey in deleted['ParentKeys']:
            self.unlinkCells(pKey, delKey)
        # remove from lists
        if delKey in self.rootKeyList:   self.rootKeyList.remove(delKey)
        if delKey in self.splitKeyList:  self.splitKeyList.remove(delKey)
        if delKey in self.branchKeyList: self.branchKeyList.remove(delKey)
        if delKey in self.mergeKeyList:  self.mergeKeyList.remove(delKey)
        if delKey in self.tipKeyList:    self.tipKeyList.remove(delKey)
        if delKey in self.deathList:     self.deathList.remove(delKey)
        if delKey in self.disappearList: self.disappearList.remove(delKey)
        # remove from master object dictionary
        del self.objectDictionary[delKey]

    def lineageBelow(self, targetKey, downLimit):
        # return a set of keys for objects derived from a target, forward to a given image number
        target = self.objectDictionary[targetKey]
        lineageSet = set()
        lineageSet.add(targetKey)
        if target['ChildCount'] > 0 and int(target['ImageNumber']) < downLimit:
            for childKey in target['ChildKeys']:
                lineageSet = lineageSet.union(self.lineageBelow(childKey, downLimit))
        return lineageSet

    def lineageAbove(self, targetKey, upLimit):
        # return a set of keys for objects in the ancestry of a target, back to a given image number
        lineageSet = set()
        if targetKey in self.objectDictionary:
            target = self.objectDictionary[targetKey] # BUG! might have been deleted
            lineageSet.add(targetKey)
            if target['ParentCount'] > 0 and int(target['ImageNumber']) > upLimit:
                for parentKey in target['ParentKeys']:
                    lineageSet = lineageSet.union(self.lineageAbove(parentKey, upLimit))
        return lineageSet

    def lineageContext(self, targetKey, upLevels=1, downLevels=1):
        # assemble a set of parent/child nodes within a given range of the target
        target = self.objectDictionary[targetKey]
        upLimit = int(target['ImageNumber']) - upLevels
        downLimit = int(target['ImageNumber']) + downLevels
        retval = set()
        retval = retval.union(self.lineageAbove(targetKey, upLimit))
        retval = retval.union(self.lineageBelow(targetKey, downLimit))
        return retval

    def lineageByFrames(self, targetKey, firstFrame=1, lastFrame=1):
        # assemble a set of parent/child nodes within a given range of the target
        retval = set()
        retval = retval.union(self.lineageAbove(targetKey, firstFrame))
        retval = retval.union(self.lineageBelow(targetKey, lastFrame))
        return retval

    def lineageBranch(self, targetKey):
        # assemble a set of parent/child nodes in the same branch as the target (bounded by roots, tips, splits)
        # TODO: consider whether to bound also by merges?
        target = self.objectDictionary[targetKey]
        ancestorKey = target['AncestorKey']
        ancestor = self.objectDictionary[ancestorKey]
        #	descendant = ancestor['DescendantKey']
        #	branchLength = descendant['BranchLength']
        retval = set()
        retval.add(ancestorKey)
        obj = ancestor
        while obj['ChildCount'] == 1:
            childKey = obj['ChildKeys'][0]
            retval.add(childKey)
            obj = self.objectDictionary[childKey]
            #upLimit = int(ancestor['ImageNumber'])
        #downLimit = int(descendant['ImageNumber'])
        #retval = retval.union(lineageAbove(targetKey, upLimit))
        #retval = retval.union(lineageBelow(targetKey, downLimit))
        return retval

    def pruneSplitMerges(self):
        # remove objects that arise from a split followed by a merge in the next frame
        # these are hard to find...a node that has 2 children, and each points to a single grandchild
        # the proper resolution is to replace the 2 children with a single node that points to the grandchild
        # this pattern will also find splits where one side is a dead end
        for splitKey in self.splitKeyList:
            splitter = self.objectDictionary[splitKey]
            childKeys = splitter['ChildKeys']
            grandchildSet = set()
            for childKey in childKeys:
                child = self.objectDictionary[childKey]
                grandchildSet = grandchildSet.union(set(child['ChildKeys']))
            if len(grandchildSet) == 1:
                # print "deleted split of",splitKey
                grandchildKey = grandchildSet.pop()
                grandchild = self.objectDictionary[grandchildKey]
                # print "  children:  ",childKeys
                # print "  grandchild:",grandchildKey, "(", grandchild['ParentCount']  ," parents)"
                deletedCellKey = ''
                if grandchild['ParentCount'] == 2:
                    # remove one of the children (an arbitrary one) and grandchild-child relationships
                    deletedCellKey = grandchild['ParentKeys'].pop()
                    grandchild['ParentCount'] = len(grandchild['ParentKeys'])
                    deletedCell = self.objectDictionary[deletedCellKey]
                    deletedCell['ParentKeys'].remove(splitKey)
                    deletedCell['ParentCount'] = len(deletedCell['ParentKeys'])
                    if (deletedCell['ChildKeys']) > 0:
                        deletedCell['ChildKeys'].remove(grandchildKey)
                    deletedCell['ChildCount'] = len(deletedCell['ChildKeys'])
                    splitter['ChildKeys'].remove(deletedCellKey)
                    splitter['ChildCount'] = len(splitter['ChildKeys'])
                    if splitter['ChildCount'] <= 1:
                        self.splitKeyList.remove(splitKey)
                        #print splitKeyList
                        for childKey in childKeys:
                            self.branchKeyList.remove(childKey)
                    self.objectDictionary[deletedCellKey] = deletedCell
                    self.objectDictionary[splitKey] = splitter
                    self.objectDictionary[grandchildKey] = grandchild
                elif grandchild['ParentCount'] == 1:
                    # if the grandchild has 1 parent, then one of the children is a dead end so prune it
                    grandchildsParentKey = grandchild['ParentKeys'][0]
                    # print '  grandchildsParentKey:',grandchildsParentKey
                    # determine which cell to delete - the one with no children
                    #deletedCellKeys = childKeys
                    #deletedCellKeys.remove(grandchild['ParentKeys'][0])
                    #deletedCellKey=deletedCellKeys[0]
                    for childKey in childKeys:
                        child = self.objectDictionary[childKey]
                        if child['ChildCount'] == 0:
                            deletedCellKey = childKey
                        # print '  deletedCellKey:',deletedCellKey
                    #deletedCell = self.objectDictionary[deletedCellKey]
                    self.deleteCell(deletedCellKey)
                    # print '  old splitter ChildKeys:', splitter['ChildKeys']
                    # print '  new splitter ChildKeys:', splitter['ChildKeys']
                    if splitter['ChildCount'] <= 1:
                        #splitKeyList.remove(splitKey) # done in deleteCell(key)
                        #print splitKeyList
                        for childKey in childKeys:
                            self.branchKeyList.remove(childKey)

    def pruneShortBranches(self, min_branch_length):
        # remove very short branches from apparent splits - these are likely artifacts
        # min_branch_length = 2  # remove branches less than this length
        # NOTE - this could cause a problem if there is just a gap; actual length>apparent length
        for tipKey in self.tipKeyList:
            tip = self.objectDictionary[tipKey]
            if tip['BranchLength'] < min_branch_length:
                # note - ancestor is the top of the branch, ie product of split or a root
                # if is a single frame then tip = ancestor = split product
                ancestorKey = tip['AncestorKey']
                ancestor = self.objectDictionary[ancestorKey]
                # print tipKey, tip['BranchLength'], "ancestor:", ancestorKey
                branchSet = self.lineageBranch(tipKey)
                for delKey in branchSet:
                    self.deleteCell(delKey)
                if tipKey != ancestorKey:
                    # remove everything up to the ancestor
                    # print
                    pass
                    # unlink head of branch from the split if there is one ### NEED TO UPDATE DESCENDENT/ANCESTOR DATA IF THIS IS NOW A LINEAR NODE
                if ancestor['ParentCount'] == 1:  # the ancestor was not a root, so it must be a split
                # get the node above the ancestor that underwent the split
                #			splitKey = ancestor['ParentKeys'][0]
                    """
                    splitter = objectDictionary[splitKey]
                    # disconnect the ancestor from its parent, the splitter
                    ancestor['ParentKeys'].remove(splitKey)
                    ancestor['ParentCount'] -= 1
                    # and the inverse
                    splitter['ChildKeys'].remove(ancestorKey)
                    splitter['ChildCount'] -= 1
                    # and remove from the master splitter list
                    if splitter['ChildCount'] <= 1 and splitKey in splitKeyList:
                        #print splitKeyList,splitKey
                        splitKeyList.remove(splitKey)
                    """
                    pass
                    #			unlinkCells(splitKey, ancestorKey)

    # make a new tree (forest, actually) and store in 'self.keyTree' that has only indices for branch points & distances
    def buildTrees(self):
        branchHeadList = self.rootKeyList + self.branchKeyList
        for branchHeadKey in branchHeadList:
            branchHead = self.objectDictionary[branchHeadKey]
            #print branchHead
            branchTailKey = branchHead['DescendantKey']
            # need to catch the dead ends - some roots have no children at all
            if branchTailKey != '':
                branchTail = self.objectDictionary[branchTailKey]
                newNode = {'name': branchTailKey, 'distanceFromParent': branchTail['BranchLength']}
                newNode['childCount'] = branchTail['ChildCount']
                newNode['childList'] = []
                for childKey in branchTail['ChildKeys']:
                    childObject = self.objectDictionary[childKey]
                    childDescendantKey = childObject['DescendantKey']
                    newNode['childList'].append(childDescendantKey)
                self.keyTree[branchTailKey] = newNode

    def toNewick(self, treeRootKey):
        # return a Newick representation for the KeyTree specified by a given "treeRootKey" (and index into keyTree)
        # note that, given the emphasis of Newick format on branch points, the "treeRootKey" here is NOT the
        # same as the rootKey in the objectDictionary. It's really the 1st split (or tip for a tree with no branches)
        # ...the position of the actual start point is given as the branch distance for the "treeRootKey" node
        # also, Newick format does not handle merges at all
        retval = ""
        if treeRootKey != '':
            treeRoot = self.keyTree[treeRootKey]
            #print treeRoot
            if (treeRoot['childCount']) == 0:
                retval = "%s:%s" % (treeRoot['name'], treeRoot['distanceFromParent'])
            else:
                newickList = []
                for childKey in treeRoot['childList']:
                    newickList.append(self.toNewick(childKey))
                retval = "(%s)%s:%s" % (",".join(newickList), treeRoot['name'], treeRoot['distanceFromParent'])
        return retval

    def newickListFromRoots(self):
        # self.notify("Adding descendants to roots")
        for rootKey in self.rootKeyList:
            self.updateDescentBranch(rootKey)
        # self.notify("Adding descendants to branches")
        for branchKey in self.branchKeyList:
            self.updateDescentBranch(branchKey)
        # self.notify("Building trees")
        self.buildTrees()
        # self.notify("making Newick list")
        newickList = []  # hold a Newick representation of each tree in the forest
        for rootKey in self.rootKeyList:
            treeRootKey = self.objectDictionary[rootKey]['DescendantKey']
            if treeRootKey != '':
                newickString = self.toNewick(treeRootKey) + ";"
                newickList.append(newickString)
            #		print newickString
        return newickList

    def summary(self):
        self.identifySpecialNodes()
        observations = 0
        self.notify("Adding descendants to roots & branches")
        for k in self.rootKeyList + self.branchKeyList:
            self.updateDescentBranch(k)
            target = self.objectDictionary[k]
            descendant = self.objectDictionary[target['DescendantKey']]
            #startImageNumber = int(target['ImageNumber'])
            #endImageNumber   = int(descendant['ImageNumber'])
            #duration = endImageNumber-startImageNumber
            duration = descendant['BranchLength'] #- 1
            observations += duration
        # observations += len(self.splitKeyList)  # ????
        # correct for over-counting from merged lineages
        for mkey in self.mergeKeyList:
            merger = self.objectDictionary[mkey]
            descendant = self.objectDictionary[self.descendantForCell(mkey)]
            startFrame = int(merger['ImageNumber'])
            endFrame = int(descendant['ImageNumber'])
            mergeCount = merger['ParentCount']
            observations -= (mergeCount - 1) * (endFrame - startFrame + 1)

        lastFrameString = self.lastFrame()
        reviewTipKeyList = [k for k in self.tipKeyList if k.partition("-")[0] != lastFrameString]  # last frame
        reviewRootKeyList = [k for k in self.rootKeyList if k.partition("-")[0] != "1"]
        float_obs = float(observations)
        otherLoss = len(reviewTipKeyList) - len(self.deathList) - len(self.disappearList)
        gainRate = float(len(self.splitKeyList) + len(reviewRootKeyList)) / float_obs
        lossRate = float(len(reviewTipKeyList) + len(self.mergeKeyList)) / float_obs
        netRate = gainRate - lossRate
        # build up list of lists for table output
        t = []
        # t.append(['cells in list:', str(len(self.objectDictionary)), ''])
        t.append(['cells observed:', str(observations), '(cells x frames)'])
        t.append(['starting number:', str(len([k for k in self.rootKeyList if k.partition("-")[0] == "1"])), ''])
        t.append(['ending number:', str(len([k for k in self.tipKeyList if k.partition("-")[0] == lastFrameString])), ''])
        t.append(['', '', ''])
        t.append(['Ends:', 'Total', 'Reviewing'])
        t.append(['   Roots:', str(len(self.rootKeyList)), str(len(reviewRootKeyList))])
        t.append(['   Tips:', str(len(self.tipKeyList)), str(len(reviewTipKeyList))])
        t.append(['', '', ''])
        t.append(['Gains:', 'No.', 'Rate (no./cell/frame)'])
        t.append(['   splits:', str(len(self.splitKeyList)), str(float(len(self.splitKeyList)) / float_obs)])
        t.append(['   new cells:', str(len(reviewRootKeyList)), str(float(len(reviewRootKeyList)) / float_obs)])
        t.append(['   Total:', str(len(self.splitKeyList) + len(reviewRootKeyList)), str(gainRate)])
        t.append(['', '', ''])
        t.append(['Losses:', 'No.', 'Rate (no./cell/frame)'])
        t.append(['   deaths:', str(len(self.deathList)), str(float(len(self.deathList)) / float_obs)])
        t.append(['   disappearances:', str(len(self.disappearList)), str(float(len(self.disappearList)) / float_obs)])
        t.append(['   merges:', str(len(self.mergeKeyList)), str(float(len(self.mergeKeyList) / float_obs))])
        t.append(['   other:', str(otherLoss), str(float(otherLoss) / float_obs)])
        t.append(['   Total:', str(len(reviewTipKeyList) + len(self.mergeKeyList)), str(lossRate)])
        t.append(['', '', ''])
        t.append(['Net Rate (gains - losses):', '', str(netRate)])

        return self.formatTable(t) + "\n" + self.gapSummary()

    def formatTable(self, listOfRowLists):
        # from http://stackoverflow.com/questions/7136432/data-table-in-python
        retval = ''
        sub1 = [[s.ljust(max(len(i) for i in column)) for s in column] for column in zip(*listOfRowLists)]
        for p in ["\t".join(row) for row in zip(*sub1)]:
            # print p
            retval += p + "\n"
        return retval

    def frameCounts(self):
        # return a count of cell # in each frame, including interpolation of 'missing' cells in gaps
        counts = dict()
        rows = [["Frame", "Cells", "CumCells", "CumSplits", "SplitRate",
                 "CumNew", "NewRate",
                 "CumLoss", "LossRate",
                 "CumMerge", "MergeRate",
                 "NetRate"]]
        self.identifySpecialNodes()
        for k in self.rootKeyList + self.branchKeyList:
            ancestor = self.objectDictionary[k]
            descendant = self.objectDictionary[ancestor['DescendantKey']]
            startFrame = int(ancestor['ImageNumber'])
            endFrame = int(descendant['ImageNumber'])
            # print "%s: to %s: ; Frames: %d to %d" % (k, self.descendantForCell(k), startFrame, endFrame)
            for frame in range(startFrame, endFrame + 1):
                if frame in counts.keys():
                    counts[frame] += 1
                else:
                    counts[frame] = 1
        # correct for over-counting from merged lineages
        for k in self.mergeKeyList:
            ancestor = self.objectDictionary[k]
            descendant = self.objectDictionary[self.descendantForCell(k)]
            startFrame = int(ancestor['ImageNumber'])
            endFrame = int(descendant['ImageNumber'])
            mergeCount = ancestor['ParentCount']
            # print "%s: to %s: ; Frames: %d to %d" % (k, self.descendantForCell(k), startFrame, endFrame)
            for frame in range(startFrame, endFrame + 1):
                if frame in counts.keys():
                    counts[frame] -= (mergeCount - 1)
        splitFrames = [int(k.partition("-")[0]) for k in self.splitKeyList]
        tipFrames = [int(k.partition("-")[0]) for k in self.tipKeyList]
        lastFrameInt = int(self.lastFrame())
        tipFrames = [t for t in tipFrames if t != lastFrameInt]
        rootFrames = [int(k.partition("-")[0]) for k in self.rootKeyList]
        rootFrames = [r for r in rootFrames if r > 1]
        mergeFrames = [int(k.partition("-")[0]) for k in self.mergeKeyList]
        cumulativeCount = 0
        for f in sorted(counts.keys()):
            cumulativeCount += counts[f]
            #splitCount = len([e for e in splitFrames if e = f])
            splitCumulativeCount = len([e for e in splitFrames if e <= f])
            splitRate = float(splitCumulativeCount) / float(cumulativeCount)
            lossCumulativeCount = len([e for e in tipFrames if e <= f])
            lossRate = float(lossCumulativeCount) / float(cumulativeCount)
            mergeCumulativeCount = len([e for e in mergeFrames if e <= f])
            mergeRate = float(mergeCumulativeCount) / float(cumulativeCount)
            newCumulativeCount = len([e for e in rootFrames if e <= f])
            newRate = float(newCumulativeCount) / float(cumulativeCount)
            nextrow = [f, counts[f], cumulativeCount,
                       splitCumulativeCount, "%f" % splitRate,
                       newCumulativeCount, "%f" % newRate,
                       lossCumulativeCount, "%f" % lossRate,
                       mergeCumulativeCount, "%f" % mergeRate,
                       "%f" % ((newRate + splitRate) - (lossRate + mergeRate))
                       ]
            rows.append([str(a) for a in nextrow])
        # fit an exponential curve to the cell counts
        Sx = Sy = Sxx = Syy = Sxy = 0.0
        N = 0
        for f in sorted(counts.keys()):
            N += 1
            x = f
            y = math.log(counts[f])
            Sx += x
            Sy += y
            Sxx += x * x
            Syy += y * y
            Sxy += x * y
        det = Sxx * N - Sx * Sx
        a, b = (Sxy * N - Sy * Sx) / det, (Sxx * Sy - Sx * Sxy) / det
        retval = self.formatTable(rows)
        retval += "\nFitted growth curve n(t) = n0 * exp(a * t):\n"
        retval += "\tn0:\t\t%f\n" % math.exp(b)
        retval += "\texponent (a):\t%g\n" % a
        if a > 0:
            retval += "\tpopulation doubling time: %f frames" % (math.log(2) / a)
        elif a < 0:
            retval += "\tpopulation half-life: %f frames" % (math.log(0.5) / a)
        return retval

    def setup_from_cp_csv(self, config_data):
        self.set_keyname('FrameIndex', config_data['FrameIndex'])
        self.set_keyname('ParentGroupIndex', config_data['ParentGroupIndex'])
        self.set_keyname('ParentObjectNumber', config_data['ParentObjectNumber'])

        self.notify("read image data")
        self.imageDictionaryFromCsv(config_data['imageCsvFile'])

        self.notify("read object data")
        self.objectDictionaryFromCsv(config_data['objectCsvFile'])

    def setup_from_icy(self, config_data):  # TODO: well, yeah
        imp = Trax_io_icy.icy_import(config_data['spot_csv'], config_data['track_xml'], config_data['image_dir'])
        self.imageDictionary = imp['imageDictionary']
        self.objectDictionary = imp['objectDictionary']
        self.set_keyname('FrameIndex', imp['keyname_frameIndex'])

    def setup_from_trackmate(self, config_data):  # TODO: well, yeah
        imp = Trax_io_trackmate.trackmate_import(config_data['trackmate_xml'], config_data['image_dir'])
        self.imageDictionary = imp['imageDictionary']
        self.objectDictionary = imp['objectDictionary']
        self.set_keyname('FrameIndex', imp['keyname_frameIndex'])

    def setup(self, import_config):
        if import_config.import_type == 'CellProfiler':
            self.setup_from_cp_csv(import_config.data)
        elif import_config.import_type == 'Icy':
            print(import_config.data)
            self.setup_from_icy(import_config.data)
        elif import_config.import_type == 'Trackmate':
            print(import_config.data)
            self.setup_from_trackmate(import_config.data)

        # self.notify("assign children")
        # self.assignChildren()

        self.parentChildCompleteness()

        self.notify("pruning blips")
        # print "pre:", self.blipCount(), "blips"
        self.blipPurge()
        # print "post:", self.blipCount(), "blips"

        #self.notify("check parent/child completeness")
        #parentChildCompleteness()

        # sort objects by frame to allow sequential analysis
        # self.notify("sorting keys")
        # self.sortedObjectKeys = sorted(self.objectDictionary.keys(), key=lambda k: self.keySorter(k))

        #from operator import itemgetter, attrgetter
        #sortedObjectKeys = sorted(objectDictionary.keys(), key=int(itemgetter('ObjectNumber')))
        #sortedObjectKeys.sort(objectDictionary.keys(), key=itemgetter('ImageNumber'))  

        self.notify("finding special nodes")
        self.identifySpecialNodes()

        self.notify("pruning split/merges")
        self.pruneSplitMerges()
        #parentChildCompleteness()

        # add branch lengths to Descendant nodes for roots and for new splits
        self.notify("Adding descendants to roots")
        for rootKey in self.rootKeyList:
            self.updateDescentBranch(rootKey)

        self.notify("Adding descendants to branches")
        # print "branch heads:", self.branchKeyList
        for branchKey in self.branchKeyList:
            self.updateDescentBranch(branchKey)

        self.notify("pruning short branches")
        self.pruneShortBranches(2)  # prune branches of length < 2

        self.notify("build new trees")
        self.buildTrees()

        self.notify("setup complete")

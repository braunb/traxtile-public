#  processing Icy files
import csv                          # read/write csv files
import xml.etree.ElementTree as ET  # read/parse xml files
import glob                         # wildcard file search
import os                           # file/path naming utilities
import re                           # reg exp
import tkFileDialog
import Trackmodel


"""
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<root>
<TrackContestISBI2012 SNR="50" density="low med high 50.0" generationDateTime="Sat Jan 17 21:26:25 PST 2015" info="http://bioimageanalysis.org/track/" scenario="NO_SCENARIO">
<particle>
<detection t="0" x="510.613" y="425.434" z="0"/>
<detection t="1" x="509.442" y="422.26" z="0"/>
<detection t="2" x="508.282" y="419.917" z="0"/>
<detection t="3" x="506.88" y="418.174" z="0"/>
<detection t="4" x="505.944" y="415.439" z="0"/>
<detection t="5" x="506.636" y="412.97" z="0"/>
<detection t="6" x="509.259" y="410.774" z="0"/>
</particle>
<particle>
"""


def parseFileName(fullname):
    fdir = os.path.dirname(fullname)
    fbase = os.path.basename(fullname)
    fname = os.path.splitext(fbase)[0]
    fext = os.path.splitext(fbase)[1]
    # search for time string
    matchObj = re.search(r'(.*[Tt])(\d{3,})(.*)', fname)  # note '.*' is greedy; (\d{3,}) gets 3 or more digits
    if matchObj:
        pre = matchObj.group(1)
        num = matchObj.group(2)
        post = matchObj.group(3)
        return {'dir': fdir, 'pre': pre, 'num': num, 'post': post, 'ext': fext}
    else:
        return {}


def isbi_import(isbi_xml_filename, image_dir):
    tree = ET.parse(isbi_xml_filename)
    root = tree.getroot()
    objectDictionary = dict()
    particle_number = 0
    for particle in root.getiterator('particle'):
        particle_number += 1
        spot_number = 0
        for spot in particle.getiterator('detection'):
            spot_number += 1
            x = float(spot.get('x'))
            y = float(spot.get('y'))
            t = int(float((spot.get('t'))))+1  # recast time for 1-indexed instead of 0-indexed
            objectKey = (t * 1000) + particle_number  # int(spot.get('ID'))
            # item = {'spot': objectKey, 'x': x, 'y': y, 't': t}
            item = {'id': objectKey, 'spot': particle_number, 'x': x, 'y': y, 't': t}
            item['cellX'] = int(round(float(item['x'])))
            item['cellY'] = int(round(float(item['y'])))
            item['t'] = int(item['t'])  # note: this is used by spot_for_coord() et al.
            if spot_number > 1:
                item['xml_parent'] = ((t-1) * 1000) + particle_number
            # add placeholders for required fields
            item['ParentKeys'] = []
            item['ChildKeys'] = []
            item['ImageNumber'] = str(item['t'])
            item['ChildCount'] = 0  # len(item['ChildKeys'])
            item['ParentCount'] = 0  # len(item['ParentKeys'])
            item['DescendantKey'] = ''
            item['BranchLength'] = 0
            item['AncestorKey'] = ''
            # enter the item into object dictionary
            objectDictionary[objectKey] = item

    # define new keys for objectDictionary using Traxtile/CellProfiler notation (<frame>-<object>)
    time_list = [cell['t'] for cell in objectDictionary.values()]  # a list of all time points
    times = set(time_list)  # unique time points
    min_spot = dict()
    key_trans = dict()
    # calculate the lowest detection number for each time
    for t in times:
        min_spot[t] = min([cell['spot'] for key, cell in objectDictionary.iteritems() if cell['t'] == t])
    # subtract to make a new object number, with lowest for each time point set to 1
    for k, cell in objectDictionary.iteritems():
        floor = min_spot[cell['t']]  # minimum detection # for this time point
        detection_number = cell['spot']
        new_number = detection_number - floor + 1  # calculate the new object number
        new_key = str(cell['t']) + '-' + str(new_number)  # create the new key
        cell['key'] = new_key  # store the new key as a field in each cell
        cell['ObjectNumber'] = str(new_number)
    # change over the keys
    key_list = objectDictionary.keys()
    for old_key in key_list:
        cell = objectDictionary[old_key]
        new_key = cell['key']
        key_trans[old_key] = new_key  # a dictionary to translate old keys into new keys
        objectDictionary[new_key] = objectDictionary.pop(old_key)
    print()

    # connect parents and children
    for k, cell in objectDictionary.iteritems():
        if 'xml_parent' in cell:
            parent_key = key_trans[cell['xml_parent']]
            child_key = k
        #     # parent_key = spot_for_id(parent_id, objectDictionary)
        #     # child_key = spot_for_id(child_id, objectDictionary)
        #     parent_key = key_trans[parent_id]
        #     child_key = key_trans[child_id]
            print parent_key + " to " + child_key
            objectDictionary[child_key]['ParentKeys'].append(parent_key)
            objectDictionary[child_key]['ParentCount'] += 1
            objectDictionary[parent_key]['ChildKeys'].append(child_key)
            objectDictionary[parent_key]['ChildCount'] += 1

    # create imageDictionary from TIFF file directory
    filename_template = "{0}/*.tif*".format(image_dir)
    file_list = [os.path.abspath(x) for x in glob.glob(filename_template)]
    imageDictionary = dict()
    for f in file_list:
        parsed_file = parseFileName(f)
        imageNumber = file_list.index(f) + 1  # convert to 1-indexed
        item = dict()
        item['time'] = str(int(parsed_file['num']))  # was +1
        item['objectKeys'] = [k for k, v in objectDictionary.iteritems() if int(v['ImageNumber']) == imageNumber]  # []
        imageDictionary[imageNumber] = item
    return {'objectDictionary': objectDictionary, 'imageDictionary': imageDictionary, 'keyname_frameIndex': 'time'}


def isbi12_export(tm):
    assert isinstance(tm, Trackmodel.MontageSession)
    xml_text = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<root>\n'
    start_key_list = tm.rootKeyList + tm.branchKeyList + tm.mergeKeyList
    for start_key in start_key_list:
        # print "start:", start_key
        xml_text += "<particle>\n"
        this_key = start_key
        while (len(tm.childrenForKey(this_key)) == 1) and (this_key not in tm.mergeKeyList):
            this_cell = tm.cellForKey(this_key)
            xml_text += '<detection t="{0}" x="{1}" y="{2}" z="0"/>\n'.format(this_cell['t']-1, this_cell['x'], this_cell['y'])
            this_key = tm.childrenForKey(this_key)[0]['key']
        if this_key not in tm.mergeKeyList:
            this_cell = tm.cellForKey(this_key)
            xml_text += '<detection t="{0}" x="{1}" y="{2}" z="0"/>\n'.format(this_cell['t']-1, this_cell['x'], this_cell['y'])
        xml_text += "</particle>\n"
    xml_text += "</root>\n"
    save_filename = tkFileDialog.asksaveasfilename(defaultextension='.xml')
    if save_filename:
        save_file = open(save_filename, mode='w')
        save_file.write(xml_text)
        save_file.close()



if __name__ == '__main__':
    track_xml = '/Users/bbraun/Box Sync/montage/130530_sample_data/isbi/exportXML.xml'
    isbi_tiff_dir = '/Users/bbraun/Box Sync/montage/130530_sample_data/isbi/isbi_tiff/ISBI_sample'
    imp = isbi_import(track_xml, isbi_tiff_dir)
    print "end"
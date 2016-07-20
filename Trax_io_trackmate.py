# processing Fiji Trackmate files
# import csv                          # read/write csv files
import xml.etree.ElementTree as ET  # read/parse xml files
import glob                         # wildcard file search
import os                           # file/path naming utilities
import re                           # reg exp


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


def spot_for_id(spot_id, objects):
    matches = {k: cell for k, cell in objects.iteritems() if cell['spot'] == spot_id}
    return matches.keys()[0]


def trackmate_import(trackmate_xml_filename, image_dir):
    # trackmate_xml_filename = '/Users/bbraun/Box Sync/montage/130530_sample_data/trakmate/FakeTracks.xml'
    tree = ET.parse(trackmate_xml_filename)
    root = tree.getroot()
    objectDictionary = dict()
    for spot in root.getiterator('Spot'):
        if spot.get('VISIBILITY') == '1':
            x = float(spot.get('POSITION_X'))
            y = float(spot.get('POSITION_Y'))
            t = int(float((spot.get('POSITION_T'))))+1  # recast time for 1-indexed instead of 0-indexed
            objectKey = int(spot.get('ID'))
            # item = {'spot': objectKey, 'x': x, 'y': y, 't': t}
            item = {'spot': objectKey, 'x': x, 'y': y, 't': t}
            item['cellX'] = int(round(float(item['x'])))
            item['cellY'] = int(round(float(item['y'])))
            item['t'] = int(item['t'])  # note: this is used by spot_for_coord() et al.
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
        key_trans[old_key] = new_key
        objectDictionary[new_key] = objectDictionary.pop(old_key)

    for edge in root.getiterator('Edge'):
        # links.append({'from': link.get('from'), 'to': link.get('to')})
        parent_id = int(edge.get('SPOT_SOURCE_ID'))
        child_id = int(edge.get('SPOT_TARGET_ID'))
        # parent_key = spot_for_id(parent_id, objectDictionary)
        # child_key = spot_for_id(child_id, objectDictionary)
        parent_key = key_trans[parent_id]
        child_key = key_trans[child_id]
        # print parent_key+" to "+child_key
        objectDictionary[child_key]['ParentKeys'].append(parent_key)
        objectDictionary[child_key]['ParentCount'] += 1
        objectDictionary[parent_key]['ChildKeys'].append(child_key)
        objectDictionary[parent_key]['ChildCount'] += 1

    # create imageDictionary from GIF file directory
    # icy_tiff_image_dir = '/Users/bbraun/Box Sync/montage/130530_sample_data/tiff'  # TODO: change to GIF dir
    gif_image_dir = image_dir  # TODO: change the parameter name instead of this hack
    filename_template = "{0}/*.gif".format(gif_image_dir)
    file_list = [os.path.abspath(x) for x in glob.glob(filename_template)]
    imageDictionary = dict()
    for f in file_list:
        parsed_file = parseFileName(f)
        imageNumber = file_list.index(f) + 1  # convert to 1-indexed
        item = dict()
        item['time'] = str(int(parsed_file['num']))  # str # the time number included in the file name
        item['objectKeys'] = [k for k, v in objectDictionary.iteritems() if int(v['ImageNumber']) == imageNumber]  # []
        imageDictionary[imageNumber] = item

    print "done"

    return {'objectDictionary': objectDictionary, 'imageDictionary': imageDictionary, 'keyname_frameIndex': 'time'}

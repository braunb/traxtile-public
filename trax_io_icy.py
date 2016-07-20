#  processing Icy files
import csv                          # read/write csv files
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


def spot_for_coord(x, y, t, objects):
    retval = ''
    int_x = int(round(x))
    int_y = int(round(y))
    spot_match = {k: v for k, v in objects.iteritems() if
                  v['t'] == t and v['cellX'] == int_x and v['cellY'] == int_y}
    if len(spot_match) > 0:
        retval = spot_match.keys()[0]
        # print row_list
    else:
        print "match not found: ", x, y, t
        pass
    return retval



def icy_import(spot_csv_filename, track_xml_filename, icy_tiff_image_dir):
    # read file with spots
    # spot_csv_filename = '/Users/bbraun/Box Sync/montage/130530_sample_data/tiff/save/subtracted_2x_s1_t0001.tiff.csv'
    spot_csv_file = open(spot_csv_filename, 'rU')
    line = spot_csv_file.readline()
    while not line.startswith('Detection #') and line != '':  # skip header up until field names
        line = spot_csv_file.readline()
    spot_csv_list = [line] + list(spot_csv_file)  # make a list from the remaining lines, with field names as 1st item
    spot_csv_file.close()

    # parse the csv into a dictionary
    objectDataReader = csv.DictReader(spot_csv_list)
    objectDataList = list(objectDataReader)
    keptKeys = ['Detection #', 'x', 'y', 't']
    objectDictionary = dict()
    for rawItem in objectDataList:
        item = {k: v for k, v in rawItem.iteritems() if k in keptKeys}  # keep only needed fields to conserve memory
        if item['Detection #'].startswith('------'):  # skip delimiter lines
            continue
        objectKey = item['Detection #']  # later will refactor to ['ImageNumber']-['ObjectNumber'] format
        # get numeric values for cell location
        item['cellX'] = int(round(float(item['x'])))
        item['cellY'] = int(round(float(item['y'])))
        item['t'] = int(item['t'])+1  # note: this is used by spot_for_coord() et al.
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
    # calculate the lowest detection number for each time
    for t in times:
        min_spot[t] = min([int(cell['Detection #']) for key, cell in objectDictionary.iteritems() if cell['t'] == t])
    # subtract to make a new object number, with lowest for each time point set to 1
    for k, cell in objectDictionary.iteritems():
        floor = min_spot[cell['t']]  # minimum detection # for this time point
        detection_number = int(cell['Detection #'])
        new_number = detection_number - floor + 1  # calculate the new object number
        new_key = str(cell['t']) + '-' + str(new_number)  # create the new key
        cell['key'] = new_key  # store the new key as a field in each cell
        cell['ObjectNumber'] = str(new_number)
    # change over the keys
    key_list = objectDictionary.keys()
    for old_key in key_list:
        cell = objectDictionary[old_key]
        new_key = cell['key']
        objectDictionary[new_key] = objectDictionary.pop(old_key)

    # # read tracks from csv file
    # track_csv_filename = '/Users/bbraun/Box Sync/montage/130530_sample_data/tiff/trak2.csv'
    # track_csv_file = open(track_csv_filename, 'rU')
    # # track_field_names = ['track # label', 'track', 't', 'x', 'y', 'z']
    # rows = []  # a list of lists
    # line = track_csv_file.readline()
    # prior_row_list = []
    # while line != '':  # could incorporate parent-child annotation into 1st pass through track file
    #     row_list = line.strip('\n').split(',')  # split line into a list
    #     # 0=key;     1=track;     2=frame (time);     3=x;     4=y;     5=z
    #     if row_list[2] == 't' or row_list[1] + row_list[2] == '':  # scrub spacer lines
    #         line = track_csv_file.readline()
    #         continue
    #     if row_list[1] == '':  # fill in blank track numbers as implied by prior rows
    #         row_list[1] = prior_row_list[1]
    #     if row_list[0] != 'track #':
    #         # look up this spot in the spot list
    #         row_list[0] = spot_for_coord(float(row_list[3]), float(row_list[4]), int(row_list[2]), objectDictionary)
    #         if row_list[0] != '':
    #             rows.append(row_list)
    #     # advance the loop to the next line in the file
    #     prior_row_list = row_list
    #     line = track_csv_file.readline()
    # tracks = set([row[1] for row in rows])  # list of unique track numbers
    # for track_num in tracks:
    #     print "track ", track_num
    #     spots = [row for row in rows if row[1] == track_num]  # get the rows in this track
    #     sorted_spots = sorted(spots, key=lambda r: int(r[2]))  # sort by time
    #     for i in range(1, len(sorted_spots)-1):
    #         spot = sorted_spots[i]
    #         key = spot[0]
    #         parent_key = sorted_spots[i-1][0]
    #         objectDictionary[key]['ParentKeys'] = [parent_key]
    #         objectDictionary[parent_key]['ChildKeys'] = [key]
    #         print spot
    # track_csv_file.close()
    # print row_list

    # read tracks from xml file
    # track_xml_filename = '/Users/bbraun/Box Sync/montage/130530_sample_data/tiff/trak2.xml'
    # links
    # <linklist>
    #     <link from="685267754" to="163915899"/> (these are track id from <track id="1710862586">)
    #     <link from="685267754" to="1640134887"/>
    #     <link from="1769865174" to="362175965"/>
    #     <link from="1769865174" to="336965403"/>
    # </linklist>
    tree = ET.parse(track_xml_filename)
    root = tree.getroot()
    tracks = dict()
    for track in root.iter('track'):
        track_id = track.get('id')
        spots = track.findall('detection')
        spot_list = []
        for spot in spots:
            # identify the cell in objectDictionary with these coordinates
            x = float(spot.get('x'))
            y = float(spot.get('y'))
            t = int(spot.get('t'))+1
            detection_type = spot.get('type')
            if detection_type == '1':  # ignore 'virtual' (algorithmically imputed) detections (type=2)
                spot_id = spot_for_coord(x, y, t, objectDictionary)
                if spot_id != '':
                    spot_list.append({'spot': spot_id, 'x': x, 'y': y, 't': t})
        sorted_spots = sorted(spot_list, key=lambda s: int(s['t']))  # sort by time
        # add links to objectDictionary
        for i in range(1, len(sorted_spots)):
            spot = sorted_spots[i]
            key = spot['spot']
            parent_key = sorted_spots[i-1]['spot']
            objectDictionary[key]['ParentKeys'] = [parent_key]
            objectDictionary[key]['ParentCount'] += 1
            objectDictionary[parent_key]['ChildKeys'] = [key]
            objectDictionary[parent_key]['ChildCount'] += 1
        if len(sorted_spots) > 0:
            tracks[track_id] = {'head': sorted_spots[0]['spot'], 'tail': sorted_spots[-1]['spot']}
    links = []
    for linklist in root.iter('linklist'):
        for link in linklist.findall('link'):
            links.append({'from': link.get('from'), 'to': link.get('to')})
            parent_key = tracks[link.get('from')]['tail']
            child_key = tracks[link.get('to')]['head']
            print parent_key+" to "+child_key
            objectDictionary[child_key]['ParentKeys'].append(parent_key)
            objectDictionary[child_key]['ParentCount'] += 1
            objectDictionary[parent_key]['ChildKeys'].append(child_key)
            objectDictionary[parent_key]['ChildCount'] += 1
    for key, obj in objectDictionary.iteritems():
        print key, "p:", obj['ParentKeys'], "c:", obj['ChildKeys']

    # create imageDictionary from TIFF file directory
    # icy_tiff_image_dir = '/Users/bbraun/Box Sync/montage/130530_sample_data/tiff'  # TODO: change to GIF dir
    filename_template = "{0}/*.tif*".format(icy_tiff_image_dir)
    file_list = [os.path.abspath(x) for x in glob.glob(filename_template)]
    imageDictionary = dict()
    for f in file_list:
        parsed_file = parseFileName(f)
        imageNumber = file_list.index(f) + 1  # convert to 1-indexed
        item = dict()
        item['time'] = str(int(parsed_file['num'])+1)  # str
        item['objectKeys'] = [k for k, v in objectDictionary.iteritems() if int(v['ImageNumber']) == imageNumber]  # []
        imageDictionary[imageNumber] = item
    # self.keyname['FrameIndex'] = 'time'

    # create imageDictionary from GIF file directory
    # icy_tiff_image_dir = '/Users/bbraun/Box Sync/montage/130530_sample_data/tiff'  # TODO: change to GIF dir
    icy_gif_image_dir = icy_tiff_image_dir  # TODO: change the parameter name instead of this hack
    filename_template = "{0}/*.gif".format(icy_gif_image_dir)
    file_list = [os.path.abspath(x) for x in glob.glob(filename_template)]
    imageDictionary = dict()
    for f in file_list:
        parsed_file = parseFileName(f)
        imageNumber = file_list.index(f) + 1  # convert to 1-indexed
        item = dict()
        item['time'] = str(int(parsed_file['num']))  # str
        item['objectKeys'] = [k for k, v in objectDictionary.iteritems() if int(v['ImageNumber']) == imageNumber]  # []
        imageDictionary[imageNumber] = item
    # self.keyname['FrameIndex'] = 'time'

    return {'objectDictionary': objectDictionary, 'imageDictionary': imageDictionary, 'keyname_frameIndex': 'time'}

if __name__ == '__main__':
    spot_csv = '/Users/bbraun/Box Sync/montage/130530_sample_data/tiff/save/trak30.csv'
    track_xml = '/Users/bbraun/Box Sync/montage/130530_sample_data/tiff/trak30.xml'
    icy_tiff_dir = '/Users/bbraun/Box Sync/montage/130530_sample_data/tiff'
    imp = icy_import(spot_csv, track_xml, icy_tiff_dir)
    print "end"

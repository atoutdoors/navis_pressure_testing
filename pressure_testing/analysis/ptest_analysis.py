import statistics
import pandas as pd
import numpy as np
import datetime as dt
import regex as re
import seawater as sw

name = 'Aidan' #CHANGE NAME
if name  == 'Kat':
    root = '/Users/katherineparise/Library/CloudStorage/GoogleDrive-katherine.parise@whoi.edu/'
elif name == 'Aidan': 
    root = 'G:/'

def diff_analysis(SN):
    outfile = root + 'Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_results/' + 'combined_test_results' + '/' + str(SN) + '_calcs_' + ".xlsx"
    readfile = root + 'Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_results/' + 'combined_test_results' + '/' + str(SN) + '_pressure_test_results' + ".xlsx"
    data = pd.read_excel(outfile)
    bpdata = pd.read_excel(readfile)
    dat = data
    testdate = str(data['DATE'][0])
    #datdiff = dat-(statistics.median(dat))
    ptd1 = pd.DataFrame(dat)
   # ptd1[param] = dat
   # ptd1[param + '-Median'] = datdiff
    ptd1['Float Number'] = SN + ", Test Start: "+testdate
    ptd1['DATE'] = data['DATE']
    ptd1['Buoyancy Position'] = bpdata['BUOYANCY_POSITION']
    timediff = [0]
    i=0
    for i, timedif in enumerate(data['DATE'][:-1]):
        timediff.append(np.timedelta64(data['DATE'][i+1]-data['DATE'][i], 's'))
    td = np.array(timediff).cumsum() # time after starttime
    td = td.astype(int)
    td = td.tolist()
    mo = re.findall('\d?\d?\d?\d?\d?\d?\d', str(td))
    t = []
    for i in mo:
        t.append(i)
    convert = []
    for i in t:
        f = int(i)/3600
        #f=(dt.timedelta(seconds = int(i)))
        convert.append(f)
    ptd1['PRES'] = data['PRES']
    ptd1['Time Since Test Start (hours)'] = convert
    timediff = [0]
    i=0
    for i, timedif in enumerate(data['DATE'][:-1]):
        timediff.append(np.timedelta64(data['DATE'][i+1]-data['DATE'][i], 's'))
    td = np.array(timediff).cumsum() # time after starttime
    td = td.astype(float)
    # calculate oxygen saturation 
    o2 = []
    for i, j in enumerate(data['PSAL']):
        o2.append(sw.extras.satO2(data['PSAL'][i], data['TEMP'][i]))
    ptd1['o2sol (ml/l)'] = o2
    ptd1['PRES'] = data['PRES']
    ptd1['PTEMP']= data['PTEMP']
    ptd1['Time Since Test Start(s)'] = td
    ptd1.to_excel(root + '/Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_results/' + 'combined_test_results' + '/' + str(SN) + '_calcs_added' + ".xlsx")
    return ptd1

print('Done!')


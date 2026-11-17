import pandas as pd
import matplotlib.pyplot as plt
import os 

# Input parameters - edit these
## Run for all floats individually to create .xlsx file; change float SN
## 'test' should be set to 'valve' 

name = 'Aidan' # WHAT IS YOUR NAME 
SNs = ["2006"]
SN = 2006
test = 'valve'
date = "20260806" #latest date will include all data from test
if name == 'Kat':
    root = '/Users/katherineparise/Library/CloudStorage/GoogleDrive-katherine.parise@whoi.edu/Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_data/' + test + '/' + str(SN) # WHERE TO GRAB DATA
elif name == 'Aidan':
    root = 'G:/Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_data/' + test + '/' + str(SN) # WHERE TO GRAB DATA

#Open and merge data
data = pd.DataFrame()
for sn in SNs:
    crt = pd.read_pickle(root+"/F"+sn+"_"+date+".pkl")
    crt["SN"] = sn
    data = pd.concat([data, crt])

data['HUMIDITY'] = data['HUMIDITY'].astype(float) # ADD HUMIDITY DATA TO THE DATAFRAME

if name == 'Kat':
    filepath = '/Users/katherineparise/Library/CloudStorage/GoogleDrive-katherine.parise@whoi.edu/Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_results/' + test + '/' + str(SN) + '_pressure_test_results_'+ test + '.xlsx'
elif name == 'Aidan':
    filepath = 'G:/Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_results/' + test + '/' + str(SN) + '_pressure_test_results_'+ test + '.xlsx'
print(filepath)
data.to_excel(filepath)

print('file for float ' + str(SN) + ' has been created in the shared Drive') 
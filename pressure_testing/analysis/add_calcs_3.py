import pandas as pd #PANDAS
import gsw
import sys 
sys.path.append('C:/Users/athay/onedrive/documents/repositories/bgc-analysis')
from db_api import get_continuous_one_profile, get_continuous_one_float, get_cal_sn
from calc_sensor import pH_sbe, o2_sbe, mcoms
from datetime import datetime

# Must run for each float individually 
SN =  2006
SNs = str(SN)
name = 'Aidan'

if name == 'Kat':
    root = '/Users/katherineparise/Library/CloudStorage/GoogleDrive-katherine.parise@whoi.edu/'
elif name == 'Aidan':
    root = 'G:/'

# GETTING CALIBRATION COEFFICIENTS

meta = get_cal_sn(SNs)
print(meta)
cal = meta["TRANSISTOR_PH"].PREDEPLOYMENT_CALIB_COEFFICIENT
calO = meta['OPTODE_DOXY'].PREDEPLOYMENT_CALIB_COEFFICIENT
cal1  = meta["FLUOROMETER_CDOM"].PREDEPLOYMENT_CALIB_COEFFICIENT
cal2 = meta["FLUOROMETER_CHLA"].PREDEPLOYMENT_CALIB_COEFFICIENT
cal3 = meta["BACKSCATTERINGMETER_BBP700"].PREDEPLOYMENT_CALIB_COEFFICIENT

# LOCATION TO GET DATA TO PLOT
filelocation = root + 'Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_results/' + 'combined_test_results' + '/' + str(SN) + '_pressure_test_results' + '.xlsx'
outfile = root + 'Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_results/' + 'combined_test_results' + '/' + str(SN) + '_calcs_' + '.xlsx'

# Tank data from Brian; change name
# ptfileloc= root + 'Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_data/tankdata/'
# ptfilename ='PT_1556_1564.xlsx'
# tankdata= pd.read_excel(ptfileloc+ptfilename)

# READING DATA FROM EXCEL FILE

dff = pd.read_excel(filelocation)
data = pd.DataFrame(dff)
data['DATE'] = pd.to_datetime(data['DATE'])
print(data['DATE'])
print(type(data['DATE'][0]))
data.sort_values(by = 'DATE', inplace = True)

# ACCOUNT FOR THE FLOATS WITH K2F'S AND NO K0
try:
    print(cal['K2'])
except:
    cal['K2'] = cal['K2f0']

try:
       print(cal['K0'])
except:
    cal['K0'] = -1.32

# VARIABLES TO PLOT
(x,data["PH_9"]) = pH_sbe(cal,data["PH_VRS"],data["PRES"],data["TEMP"],data["PSAL"]) #PH
time = data['DATE'] #TIME
time= pd.to_datetime(time) # CONVERTING TIME
o2 = o2_sbe(calO, data['O2_PHASE_DELAY'], data['O2_TEMPERATURE_VOLTAGE'], data['PRES'], data['TEMP'], data['PSAL'])
pt = gsw.conversions.pt0_from_t(data['PSAL'], data['TEMP'], data['PRES'])
fcdom = mcoms(scale=(cal1["SCALE_CDOM"]),dark=(cal1["DARK_CDOM"]),counts=(data["MCOMS1"]))
fchla = mcoms(scale=(cal2["SCALE_CHLA"]),dark=(cal2["DARK_CHLA"]),counts=(data["MCOMS2"]))
bbp = mcoms(scale=(cal3["SCALE_BACKSCATTERING700"]),dark=(cal3["DARK_BACKSCATTERING700"]),counts=(data["MCOMS3"]))


# %%
dataout = pd.DataFrame(data['PH_9'])
dataout.insert(1,'PRES', data['PRES'])
dataout.insert(2,'DATE', data['DATE'])
dataout.insert(3, 'PSAL', data['PSAL'])
dataout.insert(4,'TEMP', data['TEMP'])
dataout.insert(5,'OXYGEN', o2[0])
dataout.insert(6,'FCDOM',fcdom)
dataout.insert(7,'FCHLA', fchla)
dataout.insert(8,'BBP', bbp)
dataout.insert(9,'PTEMP', pt)
dataout.insert(10,'rawFCDOM', data['MCOMS1'])
dataout.insert(11,'rawFCHLA', data['MCOMS2'])
dataout.insert(12,'rawBBP', data['MCOMS3'])
dataout.insert(13, 'HUMIDITY', data['HUMIDITY'])
dataout.insert(14, 'PH_VRS', data['PH_VRS'])
dataout.insert(15, 'PH_VK', data['PH_VK'])
dataout.insert(16, 'O2_PHASE_DELAY', data['O2_PHASE_DELAY'])
dataout.insert(17, 'O2_TEMPERATURE_VOLTAGE', data['O2_TEMPERATURE_VOLTAGE'])
dataout.insert(18, 'PH_IK', data['PH_IK'])
dataout.insert(19, 'PH_IB', data['PH_IB'])

dataout.to_excel(outfile)
print('Yay, it worked')

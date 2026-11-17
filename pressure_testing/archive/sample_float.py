import serial
import pandas as pd
import time
import json
from datetime import datetime
import re
from navis_com.com import *

#--------------Parameters---------------------#
run_until = "2030-01-01 00:00" #YYYY-MM-DD HH:MM
save_directory = 'data/flow_through' #Folder of where to save pickle files
#---------------------------------------------#

#Get user input of com port
print("Com port:")
com = input()
print(com)

nc = navis_float_com(com, save_directory)

#Dataframe
data = pd.DataFrame(columns=['DATE','SN','PRES','TEMP','PSAL','O2_PHASE_DELAY','O2_TEMPERATURE_VOLTAGE','MCOMS1','MCOMS2','MCOMS3','PH_VRS'])

now = datetime.now()

nc.ser.reset_output_buffer()

while now < datetime.strptime(run_until,"%Y-%m-%d %H:%M"):
    
    print("     Waiting...")

    while datetime.now().minute not in {0,15,30,45}: #Timing
       time.sleep(1)

    try:
        now = datetime.now()

        #Wake float
        nc.wake_float()

        #Get SN
        time.sleep(0.5)
        nc.ser.write(b'n')
        time.sleep(0.5)

        mo = nc.search_buffer(r"\d+")
        nc.serial_number(mo.group(0))


        #Get sample
        print("     Getting Sample...")
        nc.ser.write(b's')
        time.sleep(0.5)
        nc.ser.write(b'x')
        time.sleep(30)
        mo = nc.search_buffer(r"\[.*\]")
        line = mo.group(0)

        line = line.split(",")
        line = [float(x.translate({ord(c): None for c in '[ dbCPSUusV]'})) for x in line] #Remove characters and convert to float

        #Add serial number and date
        line.insert(0, nc.sn)
        line.insert(0, now)

        #Add to dataframe
        line_series = pd.Series(line, index = data.columns)
        data = data.append(line_series, ignore_index=True)

        #Save data - overwrites
        current_time = now.strftime("%Y%m%d")
        data.to_pickle(save_directory+'/F'+nc.sn+"_"+current_time+'.pkl')

        #Freeze float
        nc.freeze_float()

        print(data.tail())
        
        #Wait additional 30 seconds
        time.sleep(30)
    except:
        pass
    
    

nc.ser.close() #close serial connection
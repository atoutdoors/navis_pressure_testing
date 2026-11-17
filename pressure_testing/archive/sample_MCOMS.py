import pandas as pd
import time
from datetime import datetime
from navis_com.com import *

#--------------Parameters---------------------#
run_until = "2030-04-17 00:00" #YYYY-MM-DD HH:MM
save_directory = 'data/mcoms' #Folder of where to save pickle files
#---------------------------------------------#

#Get user input of com port
print("Com port:")
com = input()

nc = navis_float_com(com, save_directory)

#Dataframe
data = pd.DataFrame(columns=['SN','DATE','MCOMS1','MCOMS2','MCOMS3'])

now = datetime.now()

nc.ser.reset_output_buffer()

#Wake float
nc.wake_float()

#Get SN5
time.sleep(0.5)
nc.ser.write(b'n')
time.sleep(0.5)

mo = nc.search_buffer(r"\d+")
nc.serial_number(mo.group(0))

#Freeze float
nc.freeze_float()

while now < datetime.strptime(run_until,"%Y-%m-%d %H:%M"):
    
    print("     Waiting...")

    while datetime.now().minute not in {0, 15, 30, 45}:   #timing
       time.sleep(1)

    now = datetime.now()

    #Wake float
    nc.wake_float()

    #Get sample
    print("     Getting Sample...")
    nc.ser.write(b'f')
    time.sleep(0.5)
    nc.ser.write(b's')
    time.sleep(15)
    mo = nc.search_buffer(r"ch1, ch2, ch3: (\d*), (\d*), (\d*)")
    ch1 = mo.group(1)
    ch2 = mo.group(2)
    ch3 = mo.group(3)
    print(ch1, ch2, ch3)
    

    #Add serial number and date
    line = [nc.sn, now, int(ch1), int(ch2), int(ch3)]

    #Add to dataframe
    line_series = pd.Series(line, index = data.columns)
    data = data.append(line_series, ignore_index=True)

    #Save data - overwrites
    current_time = now.strftime("%Y%m%d")
    data.to_pickle(save_directory+'/F'+nc.sn+"_"+current_time+'.pkl')


    print(data.tail())

    #Freeze float
    nc.freeze_float()
    
    #Wait additional 30 seconds
    time.sleep(60)
    
    
#Freeze float
nc.freeze_float()

nc.ser.close() #close serial connection
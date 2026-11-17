import serial
import pandas as pd
import time
import json
from datetime import datetime
import re
import os

#Samples buoyancy on set interval

#--------------Parameters---------------------#
run_until = "2030-01-01 00:00" #YYYY-MM-DD HH:MM
interval = 30 #seconds between measurements, 0 = no delay
save_directory = os.getcwd()+'/data/buoyancy_monitoring' #Folder of where to save pickle files
#---------------------------------------------#


#Get user input of com port
print("Com port:")
com = input()

ser = serial.Serial(port='COM'+com, baudrate=9600, bytesize=8, parity='N', stopbits=1)

#Dataframe
data = pd.DataFrame(columns=['DATE','BUOYANCY_POSITION'])

now = datetime.now()

ser.reset_output_buffer()

#Wake float
print("Waking float...")
ser.write(b'n')
time.sleep(1)
ser.write(b'n')
time.sleep(1)
ser.write(b'n')
time.sleep(1)
ser.reset_input_buffer()

if now > datetime.strptime(run_until,"%Y-%m-%d %H:%M"):
    print("Date exceeded, exiting")

while now < datetime.strptime(run_until,"%Y-%m-%d %H:%M"):
    
    #Get measurement of all sensors
    print("Getting measurement...")
    ser.write(b'i')
    time.sleep(0.5)
    ser.write(b'd')
    line = ser.readline()

    match = re.search(r"\d+", line.decode("utf-8")) #Extract counts
    counts = match.group(0)

    data_l = [counts]

    #Add serial number and date
    now = datetime.now()
    data_l.insert(0, now)

    #Add to dataframe
    data_series = pd.Series(data_l, index = data.columns)
    data = data.append(data_series, ignore_index=True)

    #Save data - overwrites
    current_time = now.strftime("%Y%m%d")
    data.to_pickle(save_directory+'/F'+sn+"_"+current_time+'.pkl')

    print(data.tail())
    print("Waiting {interval} seconds...".format(interval=interval))

    time.sleep(interval) #Delay


ser.close() #close serial connection

import pandas as pd
import time
from datetime import datetime, timedelta
import os
import sys
sys.path.append('C:/Users/athay/Documents/Repositories/bgc-testing')
from navis_com.com import *

# Samples buoyancy and exercise HP valve

#--------------Parameters---------------------#
run_until = "2026-12-31 00:00"  # YYYY-MM-DD HH:MMpip
measurement_interval = 0  # minutes between measurements, 0 = no delay
exercise_interval = .5  # hours between exercising the pump
exercise_n = 3  # Number of times to open and close HP valve
# Folder of where to save pickle files
save_directory = 'G://Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_data/valve/'
#---------------------------------------------#
new_position = None
iteration = 0

# Get user input of com port
print("Com port:")
com = input()
nc = navis_float_com(com, save_directory)
## Prior to starting loop make sure float is at buoyancy position of 750
# Reset Buffer
nc.ser.reset_input_buffer()
nc.ser.reset_output_buffer()
# Wake Float
nc.wake_float()

bp = 0


time.sleep(3)

try:
    # Dataframe
    data = pd.DataFrame(columns=['DATE', 'BUOYANCY_POSITION', 'ITERATION', 'HUMIDITY', 'PRES', 'TEMP',
                        'PSAL', 'O2_PHASE_DELAY', 'O2_TEMPERATURE_VOLTAGE', 'MCOMS1', 'MCOMS2', 'MCOMS3', 'PH_VRS1', 'PH_VRS', 'PH_VK', 'PH_IK', 'PH_IB', 'PH_VIN', 'PH_VOUT'])

    nc.ser.reset_output_buffer()
    nc.ser.reset_input_buffer()

    # Wake float
    nc.wake_float()

    # Get SN
    time.sleep(0.5)
    nc.ser.write(b'n')
    time.sleep(0.5)

    mo = nc.search_buffer(r"\d+")
    nc.serial_number(mo.group(0))
    nc.add_log("Float "+str(nc.sn))

    now = datetime.now()
    next_exercise = now
    next_measurement = now

    # Check if pickle file exists
    current_day = now.strftime("%Y%m%d")
    if os.path.isfile(save_directory+'/F'+nc.sn+"_"+current_day+'.pkl'):
        print("Pickle file exists, overwrite? (Y/N)")
        overwrite = input()
        if overwrite != 'Y':
            print("Exiting...")
            quit()

    nc.add_log("Script started")

    while now < datetime.strptime(run_until, "%Y-%m-%d %H:%M"):
        now = datetime.now()
        i = 0
    # Buoyancy measurement
        if now > next_measurement:

            try:
                nc.add_log("Getting measurement")

                # Wake float
                nc.wake_float()

                # Get buoyancy position
                nc.ser.write(b'i')
                time.sleep(0.5)
                nc.ser.write(b'd')
                time.sleep(1)
                mo = nc.search_buffer(r"\d+")
                counts = mo.group(0)

                # Get humidity
                nc.ser.write(b'i')
                time.sleep(0.5)
                nc.ser.write(b'h')
                time.sleep(1)
                mo = nc.search_buffer(r"humT: \[(.{5})%+")
                humidity = mo.group(1)

                # Get sample
                print("      Getting Sample...")
                nc.ser.write(b's')
                time.sleep(0.5)
                nc.ser.write(b'x')
                time.sleep(30)
                mo = nc.search_buffer(r"\[.*\]")
                line = mo.group(0)

                line = line.split(",")

                # Remove characters and convert to float
                line = [
                    float(x.translate({ord(c): None for c in '[ dbCPSUusV]'})) for x in line]

                # Another Sample
                print("       Getting pH Sample...")
                nc.ser.write(b'x')
                time.sleep(.25)
                nc.ser.write(b's')
                time.sleep(10)
                mo = nc.search_buffer(r"-.*Out")
                line2 = mo.group(0)
                line2 = line2.split(",")
                print(line2)
                line2 = [
                    float(x.translate({ord(c): None for c in '[ VrsVkIkIbVbattInVbattOut]'})) for x in line2]

                # Create record
                data_l = [now, counts, iteration, humidity] + line + line2

                # Add to dataframe
                data_series = pd.Series(data_l, index=data.columns)
                data = pd.concat([data, pd.DataFrame([data_series])]) # edited here 

                # Save data - overwrites
                current_time = now.strftime("%Y%m%d")
                data.to_pickle(save_directory+'/F'+nc.sn+"_"+current_time+'.pkl')

                print(data.tail())
                nc.freeze_float()
                nc.add_log("     Waiting {interval} minutes...".format(
                    interval=measurement_interval))

                next_measurement = now + timedelta(minutes=measurement_interval)
            except Exception as e:
                nc.add_log(e)

        # buoyancy exercise
        if now > next_exercise:
            nc.wake_float()
            print('workout')
            time.sleep(3)

            nc.ser.write(b'i')
            time.sleep(.05)
            nc.ser.write(b'd')
            time.sleep(1)
            print('readbp')
            mo = nc.search_buffer(r'Buoyancy position: .\d* counts]?')
            bp = re.findall(r'\d\d\d', str(mo))
            print(bp)

            bp = str(bp)
            bp = int(bp[2:5])


            if bp<200:
                print('increasing buoyancy counts')
                nc.ser.write(b'i')
                time.sleep(0.05)
                nc.ser.write(b'g')
                time.sleep(0.05)
                nc.ser.write(b'7')
                time.sleep(0.05)
                nc.ser.write(b'5') 
                time.sleep(0.05)
                nc.ser.write(b'0')
                time.sleep(0.05)
                nc.ser.write(b'\r')
                time.sleep(1250)
                print('buoyancy counts increased')
            nc.add_log("Exercising HP Valve")

            # Wake float

            # HP Valve exercise
            i = 0
            while i < exercise_n:
                nc.ser.write(b'i')
                time.sleep(0.5)
                nc.ser.write(b'n')  # Open HP valve
                time.sleep(4.0)  # Wait 4 seconds
                nc.ser.write(b'i')
                time.sleep(0.5)
                nc.ser.write(b'm')  # Close HP valve
                time.sleep(4.0)  # Wait 4 seconds
                nc.add_log("     excercise "+str(i)+" complete")
                i += 1

            iteration += 1
            next_exercise = now + timedelta(hours=exercise_interval)
            next_measurement = now

        time.sleep(1)  # slow loop

    nc.add_log("Date exceeded, exiting")
    nc.ser.close()  # close serial connection

except Exception as e:
    nc.add_log(e)
    nc.freeze_float()
    nc.ser.close()

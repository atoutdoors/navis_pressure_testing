import pandas as pd
import time
from datetime import datetime, timedelta
import os

from navis_com.com import *

# Samples buoyancy and exercise HP valve

#--------------Parameters---------------------#
run_until = "2022-09-3 00:00"  # YYYY-MM-DD HH:MM
measurement_interval = 15  # minutes between measurements, 0 = no delay
exercise_interval = 2  # hours between exercising the pump
exercise_n = 3  # Number of times to open and close HP valve
# Folder of where to save pickle files
save_directory = os.getcwd()+'/data/pressure_test/valve'
#---------------------------------------------#

new_position = None
iteration = 0

# Get user input of com port
print("Com port:")
com = input()

nc = navis_float_com(com, save_directory)

try:
    # Dataframe
    data = pd.DataFrame(columns=['DATE', 'BUOYANCY_POSITION', 'ITERATION', 'HUMIDITY', 'PRES', 'TEMP',
                        'PSAL', 'O2_PHASE_DELAY', 'O2_TEMPERATURE_VOLTAGE', 'MCOMS1', 'MCOMS2', 'MCOMS3', 'PH_VRS'])

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
                time.sleep(0.5)
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
                print("     Getting Sample...")
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

                # Create record
                data_l = [now, counts, iteration, humidity] + line

                # Add to dataframe
                data_series = pd.Series(data_l, index=data.columns)
                data = data.append(data_series, ignore_index=True)

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
            nc.add_log("Exercising HP Valve")

            # Wake float
            nc.wake_float()

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

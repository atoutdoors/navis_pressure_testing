# Run if needed? This combine results if both pump and valve test have been run during pressure test? 
# Creates new .xlsx file in combined_test_results folder in pressure_test_results 
import pandas as pd

name = 'Aidan'
floatnum = 1567

if name == 'Kat':
    root = '/Users/katherineparise/Library/CloudStorage/GoogleDrive-katherine.parise@whoi.edu/'
elif name == 'Aidan':
    root = 'G:/'

infilev = root + 'Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_results/valve'
infilep = root + 'Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_results/pump'
#infilepe = root + 'Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_results/ valve'

try:
   # infilev2 = infilev + "/" + str(floatnum) + '_pressure_test_results_valve.csv'
    infilep2 = infilep + "/" + str(floatnum) + '_pressure_test_results_pump.csv'
    valveresults = pd.read_csv(infilev2)
    #pumpresults = pd.read_csv(infilep2)
except:
    infilev = infilev + "/" + str(floatnum) + '_pressure_test_results_valve.xlsx'
    #infilep = infilep + "/" + str(floatnum) + '_pressure_test_results1_valve.xlsx'
    #infileps = infilepe + "/" + str(floatnum) + '_pressure_test_results2_valve.xlsx'
    valveresults = pd.read_excel(infilev)
   # pumpresults = pd.read_excel(infilep)
   # moreresults = pd.read_excel(infileps)
    
results = [valveresults]#, pumpresults]#,moreresults]
results = pd.concat(results)
print(len(results))
for i in [range(0,len(results))]:
    results['Unnamed: 0'] = i

savefile = root + '/Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_results/combined_test_results/' + str(floatnum) + '_pressure_test_results.xlsx'
results.to_excel(savefile)
print('Yay, it worked')
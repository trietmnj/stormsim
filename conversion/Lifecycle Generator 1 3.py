import os
import pandas as pd
import numpy as np
import seaborn as sns
import scipy
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import sklearn.linear_model
import statistics
import statsmodels.api as sm
import itertools
import plotly.express as px
#import pylab
import distfit
import fitter
import random
from datetime import datetime, timedelta

### USER INPUTS
Initialize_date=2033
lifecycle_duration=50
num_LCs=100
min_arrrival_time=[7,4] #[tropical, extratropical]
#Storm_max=12
lam=1.7 #Local storm recurrence rate
InputFile=pd.read_csv(r'C:\Users\RDCRLHPS\Documents\STORMSIM CHART\Relative_probability_bins_Atlantic.csv')
Input_idprob=pd.read_csv(r'C:\Users\RDCRLHPS\Documents\Chart-Python\stormprob.csv')
output_directory=r'C:\Users\RDCRLHPS\Documents\Chart-Python'

### READ PROBABILITY FILE INFO [Month, Day, Daily Probability, Cumulative Probability]
df=pd.DataFrame(InputFile) #Dataframe format of the input file
#df_array=df.to_numpy() #Array format of the input file
Cumulative_probs = df['Cumulative trop prob']
Cumulative_probs_a=Cumulative_probs.to_numpy()
Month=df['Month'].to_numpy()
Day=df['Day'].to_numpy()

### STORM ID AND PROBABILITIES (generated randomly, used for developing code)
# sID=np.random.randint(3000, 4000, 40)
# dfsID=pd.DataFrame(sID, columns=['StormID'])
# prob=np.random.rand(40)
# dfprob=pd.DataFrame(prob, columns=['prob'])
# dfprobsort=dfprob.sort_values(by=['prob'])
# dfprobnorm=dfprobsort/dfprobsort.sum()
# pcdf=np.cumsum(dfprobnorm)
# dfpcdf=pcdf.rename(columns={'prob':'cdf'})
# stormprob=pd.concat([dfsID, dfprobnorm, dfpcdf], axis=1)
# sortedstormprob=stormprob.sort_values(by=['cdf'])

### STORM ID AND PROBABILITIES FROM CHS 
dfstormprob=pd.DataFrame(Input_idprob)
dfprobsort=dfstormprob.sort_values(by=['DSW'])
dfprobsort['cdf']=dfprobsort['DSW']/dfprobsort['DSW'].sum()
pcdf=np.cumsum(dfprobsort) #might be redundant... keeping for now
cdf=pcdf['cdf']
cdf_a=cdf.to_numpy()
id=pcdf['storm_ID']
stormid_a=id.to_numpy()
### GENERATE POISSON DISTRIBUTION - *Moved to inside loop*
# samples=np.random.poisson(lam=lam, size=(lifecycle_duration,1))  #generate n=lifecycle_duration samples with Lambda=lam
# samples=pd.DataFrame(samples)
# f = np.nonzero(samples)[0]

### STORM ID - (generated randomly, used for developing code)
# random_storm_prob=np.random.rand()
# print(random_storm_prob)

### PRODUCTION LOOP - IF HAVE DATES AND CDF (RELATIVE PROB BINS FILE)

    for i in range(0, num_LCs+1):
        StormDates = []

        for ii in range(0, lifecycle_duration):
            samples=np.random.poisson(lam=lam, size=(ii,1))  #generate n=lifecycle_duration samples with Lambda=lam
            samples=pd.DataFrame(samples)
            f = np.nonzero(samples)[0]

            for iii in range(0, len(f)):
                Yr=np.array([Initialize_date + f[iii]])
                samples1=np.random.rand(1, f[iii]+1)
                samples1.sort()

                def find_first_greater_index(arr1, arr2):
                    results = []
                    for iiii, val1 in enumerate(arr1):
                        found = False
                        for j, val2 in enumerate(arr2):
                            if any(val2 > val1):
                                results.append(j)
                                found = True
                                break  # Stop after finding the first greater element
                        if not found:
                            results.append(None)  # No element in arr2 was greater than val1
                    return results
                output_indices = find_first_greater_index(samples1, Cumulative_probs_a)
                #storm_id = 
                Mo = Month[output_indices]
                Da = Day[output_indices]
                Hr = np.random.rand(len(samples1[0]), 1)
                Hr = Hr * 24
                H = Hr[0]

                storm_date = pd.DataFrame({'i': f[iii],'year': Yr, 'month': Mo, 'day': Da, 'hour': H})

                if len(samples1)>1:
                    diff = storm_date[1:, 0] - storm_date[:-1, 0]
                    foo = np.where(diff < min_arrrival_time[0, 0])
                    while foo:
                        samples1 = np.random.rand(1, f[iii] + 1)
                        samples1.sort()

                        def find_first_greater_index(arr1, arr2):
                            results = []
                            for iiii, val1 in enumerate(arr1):
                                found = False
                                for j, val2 in enumerate(arr2):
                                    if any(val2 > val1):
                                        results.append(j)
                                        found = True
                                        break  # Stop after finding the first greater element
                                if not found:
                                    results.append(None)  # No element in arr2 was greater than val1
                            return results

                        output_indices = find_first_greater_index(samples1, Cumulative_probs_a)
                        Mo = Month[output_indices]
                        Da = Day[output_indices]
                        Hr = np.random.rand(len(samples1[0]), 1)
                        Hr = Hr * 24
                        H = Hr[0]

                        storm_date = pd.DataFrame({'iii': f[iii],'year': Yr, 'month': Mo, 'day': Da, 'hour': H})

                else:
                    print('Break')


            ### OUTPUT RESULTS IN TEXT FILE
                    StormDates.append(storm_date)
                    filename=f"EventDate_LC_{ii}.txt"
                    with open(filename, "w") as file:
                        for item in StormDates:
                            file.write(f"{item}\n")


                        print(f"Processing lifecycle: {ii} Duration {iii} ")




### PRODUCTION LOOP WITH STORM ID AND PROBABILITIES (MASTER TRACK FILE AND PROBABILITY FILE)

    for i in range(0, num_LCs+1):
        StormDates = []

        for ii in range(0, lifecycle_duration):
            samples=np.random.poisson(lam=lam, size=(ii,1))  #generate n=lifecycle_duration samples with Lambda=lam
            samples=pd.DataFrame(samples)
            f = np.nonzero(samples)[0]

            for iii in range(0, len(f)):
                Yr=np.array([Initialize_date + f[iii]])
                samples1=np.random.rand(1, f[iii]+1)
                samples1.sort()

                def find_first_greater_index(arr1, arr2):
                    results = []
                    for iiii, val1 in enumerate(arr1):
                        found = False
                        for j, val2 in enumerate(arr2):
                            if any(val2 > val1):
                                results.append(j)
                                found = True
                                break  # Stop after finding the first greater element
                        if not found:
                            results.append(None)  # No element in arr2 was greater than val1
                    return results
                output_indices = find_first_greater_index(samples1, cdf_a) 
                storm_id = stormid_a[output_indices]
                rcdf=cdf_a[output_indices]
                Mo = np.random.randint(1, 12, size=(1,))
                #Mo = Mon[0]
                Da = np.random.randint(1, 31, size=(1,))
                #Da = Day[0]
                Hr = np.random.rand(len(samples1[0]), 1)
                Hr = Hr * 24
                H = Hr[0]

                storm_date = pd.DataFrame({'i': f[iii],'year': Yr, 'month': Mo, 'day': Da, 'hour': H, 'stormid':storm_id, 'cdf':rcdf})

                if len(samples1)>1:
                    diff = storm_date[1:, 0] - storm_date[:-1, 0]
                    foo = np.where(diff < min_arrrival_time[0, 0])
                    while foo:
                        samples1 = np.random.rand(1, f[iii] + 1)
                        samples1.sort()

                        def find_first_greater_index(arr1, arr2):
                            results = []
                            for iiii, val1 in enumerate(arr1):
                                found = False
                                for j, val2 in enumerate(arr2):
                                    if any(val2 > val1):
                                        results.append(j)
                                        found = True
                                        break  # Stop after finding the first greater element
                                if not found:
                                    results.append(None)  # No element in arr2 was greater than val1
                            return results


                        output_indices = find_first_greater_index(samples1, cdf_a)
                        storm_id = stormid_a[output_indices]
                        rcdf=cdf_a[output_indices]
                        Mo = np.random.randint(1, 12, size=(1,))
                        Da = np.random.randint(1, 31, size=(1,))
                        Hr = np.random.rand(len(samples1[0]), 1)
                        Hr = Hr * 24
                        H = Hr[0]

                        storm_date = pd.DataFrame({'i': f[iii],'year': Yr, 'month': Mo, 'day': Da, 'hour': H, 'stormid':storm_id, 'cdf':rcdf})

                else:
                    print('Break')


            ### OUTPUT RESULTS IN TEXT FILE
                    StormDates.append(storm_date)
                    if not os.path.exists(output_directory):
                        os.makedirs(output_directory)

                    filename=f"EventDate_LC_{i}.txt"
                    fullpath=os.path.join(output_directory, filename)
                    with open(fullpath, "w") as file:
                        for item in StormDates:
                            file.write(f"{item}\n")


                        print(f"Processing lifecycle: {i} Duration {ii} ")




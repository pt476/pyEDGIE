import os
import time
import numpy as np
import pandas as pd

from Functions_github import (
    trirnd, Rcalc, loadData
)
    
def main():
    # Load Data
    metaData, waterData, cleanedMFREDdata = loadData()

    # Define parameters
    tic = time.perf_counter()
    batteryDeg =   1     # battery degradation with outside temperature is implemented
    waterheater = 3      # set 1 for resistance 2 for heat pump only 3 for hybrid
    sizing = 3           # set 1 for cooling 2 for heating 3 for max of heating or cooling 
    warmupDays=2         # set number of warmup days
    nDays =7+warmupDays  # total model week length
    ti = 0               # initial time, h
    n1 = 1000            # number of homes (= number of HPs)
    L = n1               # number of water heater
    ft2m2 = 0.092903     # ft^2 to m^2 conversion
    tf = (nDays) * 24    # total hours
    dt = 1               # time step, h
    K = tf / dt          # number of time steps
    #t = (0:dt:tf)'      # time vector, hours ### Adapt this for python
    FutureHeadroom = 1.2 # Future headroom allowance multiplier 

    states = {                              # Dictionary of states
        'MN':'Minnesota',
        #  'DC':'District_of_Columbia',
        #  'AZ':'Arizona',
        #  'AL':'Alabama',
        #  'WI':'Wisconsin',
        #  'NC':'North_Carolina',
        #  'TX':'Texas',
        #  'DE':'Delaware',
        #  'CA':'California',
        #  'GA':'Georgia',
        #  'ID':'Idaho',
        #  'IL':'Illinois',
        #  'IN':'Indiana',
        #  'KY':'Kentucky',
        #  'LA':'Louisiana',
        #  'ME':'Maine',
        #  'MD':'Maryland',
        #  'MA':'Massachusetts',
        #  'MI':'Michigan',
        #  'MS':'Mississippi',
        #  'MO':'Missouri',
        #  'NE':'Nebraska',
        #  'NH':'New_Hampshire',
        #  'NJ':'New_Jersey',
        #  'NM':'New_Mexico',
        #  'NY':'New_York',
        #  'ND':'North_Dakota',
        #  'OH':'Ohio',
        #  'OK':'Oklahoma',
        #  'OR':'Oregon',
        #  'PA':'Pennsylvania',
        #  'RI':'Rhode_Island',
        #  'SC':'South_Carolina',
        #  'SD':'South_Dakota',
        #  'TN':'Tennessee',
        #  'UT':'Utah',
        #  'VT':'Vermont',
        #  'VA':'Virginia',
        #  'WA':'Washington',
        #  'WV':'West_Virginia',
        #  'WY':'Wyoming',
        #  'FL':'Florida',
        #  'CT':'Connecticut',
        #  'NV':'Nevada',
        #  'AR':'Arkansas',
        #  'KS':'Kansas',
        #  'MT':'Montana',
        #  'CO':'Colorado',
        #  'IA':'Iowa',
        }

    headers = [                             # Final results headers
        'State', 
        'County', 
        'City', 
        'lat', 
        'lng',
        'R_detached', 
        'R_attached',
        'Design Temp Heating (F)',
        'Design Temp Cooling (F)',
        'TodaysPeak  (MW)',
        'Electrified Winter peak (MW)',
        'Electrified Summer Peak (MW)',
        'Change in electrified peak (MW)',
        'Today - Future (MW)',
        'Cost',
        'zone',
        'TotalCost',
        'HousingUnits',
        'headroom',
        'CommercialTodaysPeak (MW)',
        'CommercialWinterPeak (MW)',
        'CommercialSummerPeak (MW)',
        'UpgradeReqCommercial (MW)',
        'Commercial Cost',
        'TotaCostCommercial'
        ]
   
    for stateAbbr, stateName in states.items():
        cityData = metaData[metaData["state_id"].str.upper() == stateAbbr] # Extract data for current city
        rows=[] # Defining rows of city data

        #for city in cityData.itertuples(): 
        for city in cityData.iloc[0:3].itertuples():    # debug line to test the first 3 cities

            if city.oneWayCommuteTime < 24.0:
                commuteSpeed = trirnd(15,35,1,1)
            else:
                commuteSpeed = trirnd(40,60,1,1)

            commuteDistance = city.oneWayCommuteTime * commuteSpeed / 60

            # Calculate effective thermal resistance of homes
            RvalueDetached, RvalueAttached, floorAreaDetached, floorAreaAttached = Rcalc(city.Uwall,city.Uwindow,city.floorAreaDetached,city.floorAreaAttached,n1)
            RValueDetached_mean = RvalueDetached.mean()
            RvalueAttached_mean = RvalueAttached.mean()



            




            # Compile results into dataTable
            rows.append({
                "State": stateName,
                "County" : city.countyName,
                "City": city.city_ascii,
                "lat": city.lat,
                "lng": city.lng,
                "R_detached": RValueDetached_mean,
                "R_attached": RvalueAttached_mean,
                "Design Temp Heating (F)": city.heatingTemp,
                "Design Temp Cooling (F)": city.coolingTemp
            })


        # Export results
        dataTable = pd.DataFrame(rows,columns=headers)
        os.makedirs("Final", exist_ok=True)
        outputPath = os.path.join("Final", f"{stateName}.xlsx")
        dataTable.to_excel(outputPath, index=False) # If file is not writing, check if excel sheet is open. Needs to be closed

        toc = time.perf_counter()
        print(f"Elapsed time is {toc-tic:.3f} seconds.")

if __name__ == "__main__":
    main()
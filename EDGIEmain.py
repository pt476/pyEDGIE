import os
import time
import numpy as np
import pandas as pd

from Functions_github import (
    loadGlobalData, loadCityData, Rcalc, getDesignWeek, sliceWindow, buildResidentialLoad
)
    
def main():
    tic = time.perf_counter()
    print("Loading contiguous US data files...")

    #region Define parameters
    batteryDeg =   1     # battery degradation with outside temperature is implemented
    waterheater = 3      # set 1 for resistance 2 for heat pump only 3 for hybrid
    sizing = 3           # set 1 for cooling 2 for heating 3 for max of heating or cooling 
    warmupDays=2         # set number of warmup days
    nDays =7+warmupDays  # total model week length
    ti = 0               # initial time, h
    numHomes = 1000      # number of homes (= number of HPs)
    L = numHomes         # number of water heater
    ft2m2 = 0.092903     # ft^2 to m^2 conversion
    tf = (nDays) * 24    # total hours
    dt = 1               # time step, h
    K = tf / dt          # number of time steps
    t = np.arange(0, tf, dt) # time span, h
    FutureHeadroom = 1.2 # Future headroom allowance multiplier 
    #endregion

    # Load contiguous US data used across all simulations
    metaData, waterData, cleanedMFREDdata = loadGlobalData(warmupDays)
    
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

    print("Complete!")
    toc = time.perf_counter()
    print(f"Elapsed time is {toc-tic:.3f} seconds.")

    for stateAbbr, stateName in states.items():
        finalOutput = [] # Define array for final outputs of city simulation

        # Extract data for current state 
        cityData = metaData[metaData["state_id"].str.upper() == stateAbbr].copy() # Extract data for current city
        
        #for city in cityData.itertuples(): 
        for city in cityData.iloc[26:27].itertuples():    # debug line to test Minneapolis

            #region Get city-specific data 
            # Retiming is done within loadCityData()
            weatherData, pWorkBase, pWorkFuture = loadCityData(stateName, city.countyName, warmupDays)
            #endregion 

            #region Find representative week from temperatures in weather data
            tStartWinter, tEndWinter = getDesignWeek(city.heatingTemp, weatherData[0], warmupDays, 'min') 
            tStartSummer, tEndSummer = getDesignWeek(city.coolingTemp, weatherData[0], warmupDays, 'max') 
            #endregion

            #region Calculate effective thermal resistance of homes
            RvalueDetached, RvalueAttached, floorAreaDetached, floorAreaAttached = Rcalc(city.Uwall,city.Uwindow,city.floorAreaDetached,city.floorAreaAttached,numHomes)
            RValueDetached_mean = RvalueDetached.mean()
            RvalueAttached_mean = RvalueAttached.mean()
            #endregion

            #region Import residential power loads
            resLoadYear, resLoadDetached, resLoadAttached = buildResidentialLoad(cleanedMFREDdata, numHomes, stateName, city.percentAttached, forceColumn=0)
            idx = cleanedMFREDdata.index
            resLoadWinter = sliceWindow(resLoadYear, tStartWinter, tEndWinter, index=idx)
            resLoadSummer = sliceWindow(resLoadYear, tStartSummer, tEndSummer, index=idx)
            resLoadDetachedWinter = sliceWindow(resLoadDetached, tStartWinter, tEndWinter, index=idx)
            resLoadAttachedWinter = sliceWindow(resLoadAttached, tStartWinter, tEndWinter, index=idx)
            resLoadDetachedSummer = sliceWindow(resLoadDetached, tStartSummer, tEndSummer, index=idx)
            resLoadAttachedSummer = sliceWindow(resLoadAttached, tStartSummer, tEndSummer, index=idx)
            #endregion

            #region Import commercial power loads

            #endregion

            # Compile results into dataTable
            finalOutput.append({
                "State"                             : stateName,
                "County"                            : city.countyName,
                "City"                              : city.city_ascii,
                "lat"                               : city.lat,
                "lng"                               : city.lng,
                "R_detached"                        : RValueDetached_mean,
                "R_attached"                        : RvalueAttached_mean,
                "Design Temp Heating (F)"           : city.heatingTemp,
                "Design Temp Cooling (F)"           : city.coolingTemp,
                #"TodaysPeak  (MW)"                 : 
                #"Electrified Winter peak (MW)"     :
                #"Electrified Summer Peak (MW)"     :
                #"Change in electrified peak (MW)"  :
                #"Today - Future (MW)"              :
                #"Cost"                             :
                "zone"                              : city.Zone,
                #"TotalCost"                        :
                "HousingUnits"                      : city.housingUnits,
                "headroom"                          : city.currentHeadroom
                #"CommercialTodaysPeak (MW)"        :
                #"CommercialWinterPeak (MW)"        :
                #"CommercialSummerPeak (MW)"        :
                #"UpgradeReqCommercial (MW)"        :
                #"Commercial Cost"                  :
                #"TotaCostCommercial"               :
            })

            print(f'State: {stateName}, County: {city.countyName}, City: {city.city_ascii}')
            toc = time.perf_counter()
            print(f"Elapsed time is {toc-tic:.3f} seconds.")

        #region Export results
        dataTable = pd.DataFrame(finalOutput,columns=headers)
        os.makedirs("Final", exist_ok=True)
        outputPath = os.path.join("Final", f"{stateName}.xlsx")
        dataTable.to_excel(outputPath, index=False) # If file is not writing, check if excel sheet is open. Needs to be closed

        toc = time.perf_counter()
        print(f"Total Elapsed time is {toc-tic:.3f} seconds.")
        #endregion

if __name__ == "__main__":
    main()
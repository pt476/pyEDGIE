import numpy as np
import pandas as pd
from datetime import datetime
import os

rng = np.random.default_rng(1)

def btu2wh(x):
    """Converts BTU to Watt-hours (Wh).

    Args:
        x (float): Energy value in British Thermal Units (BTU).

    Returns:
        float: Equivalent energy value in Watt-hours (Wh).
    """
    return x * 0.293071

def f2c(x):
    """Converts temperature from Fahrenheit to Celsius.

    Args:
        x (float or int): Temperature in degrees Fahrenheit.

    Returns:
        float: Temperature in degrees Celsius.
    """
    return (x - 32) * 5 / 9

def vecX(X):
    """Vectorizes a matrix by stacking its columns into a column vector.

    Args:
        X (numpy.ndarray): The input matrix or multi-dimensional array.

    Returns:
        numpy.ndarray: A 2D column vector of shape (N, 1) containing 
            the elements of X in Fortran-style (column-major) order.
    """
    return X.flatten(order='F').reshape(-1, 1)

def trirnd(a, c, m, n):
    """Generates a matrix of random numbers from a symmetric triangular distribution.

    Args:
        a (float): Lower limit of the triangular distribution.
        c (float): Upper limit of the triangular distribution.
        m (int): Number of rows in the output matrix.
        n (int): Number of columns in the output matrix.

    Returns:
        numpy.ndarray: An (m, n) matrix of random floating-point values 
            drawn from the specified triangular distribution.
    """
    return rng.triangular(a, (a + c) / 2.0, c, size=(m, n))

def loadGlobalData(warmupDays):
        
    # Define paths
    InputFiles_dir = "InputFiles_github"
    metaData_path = os.path.join(InputFiles_dir, "metaData.xlsx")
    waterData_path = os.path.join(InputFiles_dir, "DHWEventGeneratorOutput.csv")
    cleanedMFREDdata_path = os.path.join(InputFiles_dir, "cleanedMFREDdata.xlsx")
    
    # Read data
    metaData = pd.read_excel(metaData_path)
    waterData = pd.read_csv(waterData_path)
    cleanedMFREDdata = pd.read_excel(cleanedMFREDdata_path)

    #region Process metaData
    metaData= metaData.rename(columns={     # Rename column headers in metaData
            "PeakRatio"             :   "peakRatio",
            "HousingUnits"          :   "housingUnits",
            "Attached home %"       :   "percentAttached",
            "Detached home %"       :   "percentDetached",
            "county_name"           :   "countyName",
            "1%_Cooling Temp. (¡F)" :   "coolingTemp",
            "99%_Heating Temp. (¡F)":   "heatingTemp",
            "ElectricWH%"           :   "electricWH",
            "Mean Commuting Time"   :   "oneWayCommuteTime",
            "Detached floor area"   :   "floorAreaDetached",
            "Attached floor area"   :   "floorAreaAttached"
        })
    n = len(metaData)
    mask = (metaData["oneWayCommuteTime"] < 24.0).to_numpy() # Generate mask for commute times < 24h
    # Define bounds for commute speed distribution
    low  = np.where(mask, 15, 40).reshape(n, 1) 
    high = np.where(mask, 35, 60).reshape(n, 1)
    # Assign commuteSpeed, commuteDistance, currentHeadroom objects to metaData
    metaData["commuteSpeed"]    = trirnd(low, high, n, 1).flatten()
    metaData["commuteDistance"] = metaData["oneWayCommuteTime"] * metaData["commuteSpeed"] / 60
    metaData["currentHeadroom"] = np.round(trirnd(1.15, 1.36, n, 1), 2).flatten() 
    metaData["coolingTemp"] = (metaData["coolingTemp"] - 32) * 5 / 9 # Convert heating/cooling temps to celsius
    metaData["heatingTemp"] = (metaData["heatingTemp"] - 32) * 5 / 9
    #endregion

    cleanedMFREDdata = retimeData(cleanedMFREDdata, warmupDays, 1)

    return metaData, waterData, cleanedMFREDdata

def loadCityData(stateName, countyName, warmupDays):
    # Import raw data
    weatherData = pd.read_csv('ComStock/weather_data/' + stateName + '/' + countyName.replace(" ","_") + "_amy2018.csv", header=0, usecols=[0, 1, 5]) # Read only the timestamp, temperature, and shortwave    
    baselineComStock = pd.read_csv('ComStock/baseline_merged_results/' + stateName + '/' + countyName + ".csv")
    futureComStock = pd.read_csv('ComStock/future_merged_results/' + stateName + '/' + countyName + ".csv")
    
    weatherData = weatherData.rename(columns={     # Rename column headers in metaData
                "Dry Bulb Temperature [°C]"             :   "temperature",
                "Global Horizontal Radiation [W/m2]"    :   "shortwave",
            })
    
    pWorkBase = baselineComStock[[baselineComStock.columns[0]]].copy()
    pWorkBase['total_load_baseline'] = baselineComStock.iloc[:, 1:].sum(axis=1)
    pWorkFuture = futureComStock[[futureComStock.columns[0]]].copy()
    pWorkFuture['total_load_future'] = futureComStock.iloc[:, 1:].sum(axis=1)

    # Clean and retime data
    weatherData = retimeData(weatherData, warmupDays, 0)
    pWorkBase = retimeData(pWorkBase, warmupDays, 2)
    pWorkFuture = retimeData(pWorkFuture, warmupDays, 2)
       
    return weatherData, pWorkBase, pWorkFuture

def retimeData(rawData, warmupDays, checkFile):
    # checkFile = 0 for weather, 1 for cleanedMFREDdata, 2 for baseline/future

    # Adjust time to EST (UTC-5) for cleanedMFREDdata
    if checkFile == 0:
        offsetTime = 0 #1 # Offset the hour-ending timestamps to hour-beginning timestamps NOTE NOTE NOTE NOTE NOTE
    elif checkFile == 1:
        offsetTime = 5  # Offset UTC to EST(=UTC-5)
    else:
        offsetTime = 0

    # Extract time (assumed first column) and convert to datetime format
    timestamps = pd.to_datetime(rawData.iloc[:, 0])

    # Adjust year to match master time vector for non-weather data files
    if checkFile != 0:
        timestamps = timestamps.map(lambda d: d.replace(year=2018)) - pd.Timedelta(hours=offsetTime)

    # Extract power profiles and fill missing values linearly
    data = rawData.iloc[:, 1:].apply(pd.to_numeric, errors='coerce')
    data = data.interpolate(method='linear', limit_direction='both')

    # Create timetable (DataFrame indexed by time)
    data = pd.DataFrame(data.values, index=timestamps)

    # Define master time map (Derived from weather data)
    start_time = pd.Timestamp(2018, 1, 1) - pd.Timedelta(days=warmupDays)
    end_time = pd.Timestamp(2019, 1, 1)
    masterTime = pd.date_range(start=start_time, end=end_time, freq='1h')

    # Retime / Resample to match master time grid
    retimedData = data.reindex(data.index.union(masterTime))

    # Filter to weather_time grid
    retimedData = retimedData.reindex(masterTime)

    # Linear interpolate any missing data
    retimedData = interpLinear(retimedData)

    # Fill 2017 warmup period using early 2018 data
    data_filling_mask = (retimedData.index >= pd.Timestamp(2018, 1, 1)) & \
                        (retimedData.index < pd.Timestamp(2018, 1, 1) + pd.Timedelta(days=warmupDays))
    data_filling = retimedData.loc[data_filling_mask].values
 
    idx_2017 = retimedData.index < pd.Timestamp(2018, 1, 1)

    num_2017_rows = idx_2017.sum()
    if len(data_filling) > 0:
        repeated_filling = np.tile(data_filling, (int(np.ceil(num_2017_rows / len(data_filling))), 1))[:num_2017_rows]
        retimedData.loc[idx_2017] = repeated_filling

    retimedData = interpLinear(retimedData) # Final linear interpolation
    if checkFile == 0:
        retimedData = retimedData.bfill() # backfill the first cell of weather data ONLY BECAUSE OF TIMING MISALIGNMENT
    retimedData = retimedData.round(4) # Align all values to 4 decimal places

    return retimedData

def interpLinear(data):
    value_cols = data.columns 
    x_numeric = data.index.astype('int64') / 1e9 
    
    for col in value_cols:
        col_idx = data.columns.get_loc(col)
        
        for i in range(2, len(data)):
            if pd.isna(data.iloc[i, col_idx]):
                x1, y1 = x_numeric[i-2], data.iloc[i-2, col_idx]
                x2, y2 = x_numeric[i-1], data.iloc[i-1, col_idx]
                x_new = x_numeric[i]
                
                if pd.isna(y1) or pd.isna(y2):
                    continue  # not enough valid prior data yet
                
                slope = (y2 - y1) / (x2 - x1)
                data.iloc[i, col_idx] = y1 + slope * (x_new - x1)
    
    return data

def Rcalc(Uwall,Uwindow,AreaDetached,AreaAttached,n1):
    """Calculates thermal resistance (R-values) and converted areas for detached and attached buildings.

    Converts building areas from square feet to square meters, calculates total exterior wall 
    surface areas based on building geometry, applies random variations to building properties, 
    and computes overall thermal resistance including air infiltration and surface conductance.

    Args:
        Uwall (float): Baseline overall heat transfer coefficient of exterior walls (W/m²K).
        Uwindow (float): Baseline overall heat transfer coefficient of windows (W/m²K).
        AreaDetached (float): Total floor area of the detached building in square feet (sq ft).
        AreaAttached (float): Total floor area of the attached building in square feet (sq ft).
        n1 (int): Number of Monte Carlo simulation samples to generate.

    Returns:
        tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray]:
            - RvalueDetached (numpy.ndarray): Calculated thermal resistance for detached building (K/kW).
            - RvalueAttached (numpy.ndarray): Calculated thermal resistance for attached building (K/kW).
            - AreaDetached (numpy.ndarray): Sampled detached building floor areas in square meters (m²).
            - AreaAttached (numpy.ndarray): Sampled attached building floor areas in square meters (m²).
    """
    oneStoryHeight = 3
    aspectRatio = 1
    numberOfStories = 2
    AreaDetached *= 0.092903
    AreaAttached *= 0.092903
    AreaDetached = trirnd(0.9*AreaDetached,1.1*AreaDetached,n1,1)
    AreaAttached = trirnd(0.9*AreaAttached,1.1*AreaAttached,n1,1)

    AwDetached = 2*oneStoryHeight*(aspectRatio + 1)* np.sqrt(numberOfStories*AreaDetached/aspectRatio)
    AwAttached = 2*oneStoryHeight*(aspectRatio + 1)* np.sqrt(numberOfStories*AreaAttached/(aspectRatio))/2

    lambda_ = trirnd(0.2,0.3,n1,1)

    AreaRoofDetached = AreaDetached/numberOfStories
    AreaRoofAttached = AreaAttached/numberOfStories
    Ur = np.full((n1,1), 0.36)

    density = 1.293; #kg/m3
    Cp = 1005; # J/kgK
    volume = AreaDetached*oneStoryHeight; #m3
    v = trirnd(0.2,1.5,n1,1) # air change per hour

    mdotCp = v*Cp*density*volume/3600
    Uwall = (lambda_*trirnd(0.8*Uwindow,1.2*Uwindow,n1,1) + (1-lambda_)*trirnd(0.8*Uwall,1.2*Uwall,n1,1));

    h_outer = np.full((n1, 1), 22.7) / 1000
    h_inner = np.full((n1, 1), 8.29) / 1000

    RvalueDetached = 1/(mdotCp/1000 + Uwall*AwDetached/1000 + Ur*AreaRoofDetached/1000)
    RvalueAttached = 1/(mdotCp/1000 + Uwall*AwAttached/1000 + Ur*AreaRoofAttached/1000)

    return RvalueDetached, RvalueAttached, AreaDetached, AreaAttached    

def getDesignWeek(designTemp, temps, warmupDays, mode,
                  yearStart="2018-01-01"):
    if isinstance(temps, pd.DataFrame):
        temps = temps.iloc[:, 0]
    t0 = pd.Timestamp(yearStart)
    temps = temps[temps.index >= t0]              # drop warmup padding

    weeks = temps.groupby((temps.index - t0) // pd.Timedelta(days=7))
    extreme = weeks.min() if mode == "min" else weeks.max()
    extreme = extreme[weeks.size() == 168]        # full weeks only

    k = int((extreme - designTemp).abs().idxmin())
    designStart = t0 + pd.Timedelta(days=7 * k)
    return designStart - pd.Timedelta(days=warmupDays), designStart + pd.Timedelta(days=7)

def importElectricity(stateName):
    West = {'Montana', 'Idaho', 'Wyoming' ,'Nevada', 'Utah', 'Colorado', 'Arizona', 'New Mexico','Washington', 'Oregon', 'California', 'Alaska', 'Hawaii'}
    MidWest = {'Ohio', 'Indiana', 'Illinois', 'Michigan', 'Wisconsin','Minnesota', 'Iowa', 'Missouri', 'North Dakota', 'South Dakota', 'Nebraska', 'Kansas'}
    NorthEast ={'Maine', 'New Hampshire', 'Vermont', 'Massachusetts', 'Rhode Island', 'Connecticut','New York', 'Pennsylvania', 'New Jersey'}

    if stateName in West: # https://www.eia.gov/consumption/residential/data/2020/c&e/pdf/ce4.2.pdf
        scaling_detached = (17e9+96e9)/(16.97e6*8760)
        scaling_attached = ((1e9+6e9)/(8760*1.69e6) + (1e9+5e9)/(8760*1.89e6) + (3e9+14e9)/(8760*5.70e6) )/3
    elif stateName in MidWest:
        scaling_detached = (18e9+115e9)/(8760*18.58e6)
        scaling_attached = ((1e9+6e9)/(8760*1.33e6) + (1e9+5e9)/(8760*1.95e6) + (2e9+10e9)/(8760*4.20e6) )/3
    elif stateName in NorthEast:
        scaling_detached = (10e9+66e9)/(11.23e6*8760)
        scaling_attached = ((2e9+8e9)/(8760*1.95e6) + (2e9+8e9)/(8760*3.15e6) + (3e9+11e9)/(8760*5.10e6) )/3
    else:
        scaling_detached = (31e9+205e9)/(30.29e6*8760)
        scaling_attached = ((2e9+11e9)/(8760*2.48e6) + (1e9+8e9)/(8760*2.36e6) + (5e9+26e9)/(8760*7.83e6) )/3



    return P,fullP,P_detached_window,P_attached_window

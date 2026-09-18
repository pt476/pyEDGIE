import numpy as np
import pandas as pd
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

def importWeather(stateName, countyName, t_span):
    # --- import raw data ---
    weather_data = pd.read_csv('ComStock/weather_data/' + stateName + '/' + countyName.replace(" ","_") + "_amy2018.csv")

    # Extract data and convert units
    weather_data['timestamp'] = pd.to_datetime(weather_data.iloc[:,0])

    # Fix year only if it's before 2000 to avoid overflow issues
    mask = weather_data['timestamp'].dt.year < 2000
    weather_data.loc[mask, 'timestamp'] += pd.DateOffset(years=2000)

    #offsetGMT = -5
    #weather_data['timestamp'] += pd.to_timedelta(offsetGMT, unit='h')

    # Extract data and convert units
    temperature = weather_data.iloc[:, 1]  # outdoor air temperature, C
    shortwave = weather_data.iloc[:, 5] / 1000  # total horizontal shortwave irradiance, kW/m^2

    # Fill any missing data
    temperature = temperature.interpolate(method='linear')
    shortwave = shortwave.interpolate(method='linear')

    # pack the data into a timetable object
    tt = pd.DataFrame({
        'temperature': temperature.values,
        'shortwave': shortwave.values,
    }, index=weather_data['timestamp']).sort_index()

    tt = tt.interpolate(method='time')

    tt = tt.ffill()

    return tt['temperature'], tt['shortwave']

def loadData():
        
    # Define paths
    ComStock_dir = "ComStock"
    InputFiles_dir = "InputFiles_github"
    metaData_path = os.path.join(InputFiles_dir, "metaData.xlsx")
    waterData_path = os.path.join(InputFiles_dir, "DHWEventGeneratorOutput.csv")
    cleanedMFREDdata_path = os.path.join(InputFiles_dir, "cleanedMFREDdata.xlsx")
    
    
    # Read data
    metaData = pd.read_excel(metaData_path)
    waterData = pd.read_csv(waterData_path)
    cleanedMFREDdata = pd.read_excel(cleanedMFREDdata_path)

    # Rename headers
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

    return metaData, waterData, cleanedMFREDdata
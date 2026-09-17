import numpy as np
import pandas as pd
import os
rng = np.random.default_rng(1)

def btu2wh(x):  # Convert BTU to wH
    return x * 0.293071

def f2c(x):     # Convert Farenheit to Celsius
    return ((x-32)*5/9)

def vecX(X):
    return X.flatten(order='F').reshape(-1, 1)

def trirnd(a, c, m, n):
    return rng.triangular(a, (a + c) / 2.0, c, size=(m, n))

def Rcalc(Uwall,Uwindow,AreaDetached,AreaAttached,n1):
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

def importWeather(fileName, t):

    
    return temperature, shortwave

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

    return metaData, waterData, cleanedMFREDdata
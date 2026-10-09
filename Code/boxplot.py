import pandas as pd
import glob
import os
import datetime
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as pltimport
import seaborn as sns
#from matplotlib import cm
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from sklearn.metrics import roc_curve, roc_auc_score
import sys
from decimal import Decimal


print("Is this thing on?")

###### --- START BOILERPLATE --- ######
debug: bool = True

### ACCEPTING ARGUMENTS FROM SHELL SCRIPT ###

### DIRECTORY ###
# This should almost never need to change
base_directory = "/projects/standard/rmyoung/shared/mosaiks"
scratch_directory = "/scratch.local" # experimental; will need to alter the shell script.
input_path = base_directory + "/output/intermediate"
output_directory = base_directory + "/output/figures"

# if debug == True:
res = 0.01
location = "US"
parcel_check = False
zeroes = 0.01
suffix = ""
'''
else:
    res = float(sys.argv[1])
    print("Arg 1 is " + str(sys.argv[1]))
    
    location = str(sys.argv[2])
    print("Arg 2 is " + str(sys.argv[2]))
    
    parcel_check = str(sys.argv[3]).lower() == "true"
    print("Arg 3 is " + str(sys.argv[3]))
   
    zeroes = float((sys.argv[4]).replace(",", ""))
    print("Arg 4 is " + str(sys.argv[4]))

    suffix = ""
'''
res_string = str(int(res*100))
zeroes_string = str(int(zeroes*100))

buff = (res*5)/10
round_value = abs((Decimal(res_string).as_tuple().exponent) - 1)

if location == "Minnesota":
    poi_path = base_directory + "/raw/mn_superfund_spreadsheet.csv"
    parcel_path = base_directory + "/mn_parcels/mn_parcels.gpkg"

else:
    poi_path = base_directory + "/raw/federal_superfund_spreadsheet.csv"

#NAMING THE FILE
project_file = location + "_r" + res_string + "_z" + zeroes_string + suffix
results_stem = location + "_r" + res_string

print("Resolution value is " + str(res) + " and the type is " + str(type(res)))
print("Location value is " + str(location) + " and the type is " + str(type(location)))
print("Parcel check value is " + str(parcel_check) + " and the type is " + str(type(parcel_check)))
print("Zeroes value is " + str(zeroes) + " and the type is " + str(type(zeroes)))
print("Suffix value is " + str(suffix) + " and the type is " + str(type(suffix)))


###### --- END BOILERPLATE --- ######




US200_feature_results = "US_r1_z200_rforestfeatures_results.csv"
US200_latlon_results = "US_r1_z200_rforestlatlon_results.csv"

US0_feature_results = "US_r1_z0_rforestfeatures_results.csv"
US0_latlon_results = "US_r1_z0_rforestlatlon_results.csv"

MN200_feature_results = "Minnesota_r1_z200_rforestfeatures_results.csv"
MN200_latlon_results = "Minnesota_r1_z200_rforestlatlon_results.csv"

MN0_feature_results = "Minnesota_r1_z0_rforestfeatures_results.csv"
MN0_latlon_results = "Minnesota_r1_z0_rforestlatlon_results.csv"

US200_feature_df = make_df(US200_feature_results)
US200_latlon_df = make_df(US200_latlon_results)

US0_feature_df = make_df(US0_feature_results)
US0_latlon_df = make_df(US0_latlon_results)

MN200_feature_df = make_dfMN200_feature_results)
MN200_latlon_df = make_df(MN200_latlon_results)

MN0_feature_df = make_df(MN0_feature_results)
MN0_latlon_df = make_df(MN0_latlon_results)



def make_df(results : pd.DataFrame):
    
    feature_path = os.path.join(input_path, results)
    created_csv = pd.read_csv(feature_path)
    
    return created_csv

'''
US200_feature_path = os.path.join(input_path, US200_feature_results)
US200_latlon_path = os.path.join(input_path, US200_latlon_results)

US0_feature_path = os.path.join(input_path, US0_feature_results)
US0_latlon_path = os.path.join(input_path, US0_latlon_results)

MN0_feature_path = os.path.join(input_path, MN0_feature_results)
MN0_latlon_path = os.path.join(input_path, MN0_latlon_results)

MN200_feature_path = os.path.join(input_path, MN200_feature_results)
MN200_latlon_path = os.path.join(input_path, MN200_latlon_results)



US200_feature_df = pd.read_csv(US200_feature_path)
US200_latlon_df = pd.read_csv(US200_latlon_path)

US0_feature_df = pd.read_csv(US0_feature_path)
US0_latlon_df = pd.read_csv(US0_latlon_path)

MN200_feature_df = pd.read_csv(MN200_feature_path)
MN200_latlon_df = pd.read_csv(MN200_latlon_path)

MN0_feature_df = pd.read_csv(MN0_feature_path)
MN0_latlon_df = pd.read_csv(MN0_latlon_path)
'''


    
stats = [
    {
        "label": "US Features \n 200% Zeroes",
        "med": US200_feature_df.loc[0, "Median"],
        "q1": US200_feature_df.loc[0, "Q1"],
        "q3": US200_feature_df.loc[0, "Q3"],
        "whislo": US200_feature_df.loc[0, "Min"],  # Bottom whisker limit
        "whishi": US200_feature_df.loc[0, "Max"], # Top whisker limit
        "fliers": [] # Optional: list of outlier points
    },
    
    {
        "label": "US Lat Lon \n 200% Zeroes",
        "med": US200_latlon_df.loc[0, "Median"],
        "q1": US200_latlon_df.loc[0, "Q1"],
        "q3": US200_latlon_df.loc[0, "Q3"],
        "whislo": US200_latlon_df.loc[0, "Min"],  # Bottom whisker limit
        "whishi": US200_latlon_df.loc[0, "Max"], # Top whisker limit
        "fliers": [] # Optional: list of outlier points
    },
    
     {
        "label": "US Features \n 0% Zeroes",
        "med": US0_feature_df.loc[0, "Median"],
        "q1": US0_feature_df.loc[0, "Q1"],
        "q3": US0_feature_df.loc[0, "Q3"],
        "whislo": US0_feature_df.loc[0, "Min"],  # Bottom whisker limit
        "whishi": US0_feature_df.loc[0, "Max"], # Top whisker limit
        "fliers": [] # Optional: list of outlier points
    },
    
    {
        "label": "US Lat Lon \n 0% Zeroes",
        "med": US0_latlon_df.loc[0, "Median"],
        "q1": US0_latlon_df.loc[0, "Q1"],
        "q3": US0_latlon_df.loc[0, "Q3"],
        "whislo": US0_latlon_df.loc[0, "Min"],  # Bottom whisker limit
        "whishi": US0_latlon_df.loc[0, "Max"], # Top whisker limit
        "fliers": [] # Optional: list of outlier points
    }
        
    {
        
        
        
    }
    
]


print(stats)

fig, ax = plt.subplots(figsize=(10, 10))
plt.ylabel("AUC") 
plt.title("Random Forest Model Performance Comparison")
artists = ax.bxp(bxpstats=stats)



output_filename = "boxplot_test.pdf"
full_path = os.path.join(output_directory, output_filename)
plt.savefig(full_path, dpi=300, bbox_inches='tight')
import os
import shutil
import rasterio
import subprocess
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio.features
import matplotlib.pyplot as plt
import requests
import sys

from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.io import MemoryFile
from exactextract import exact_extract
from matplotlib.patches import Rectangle
from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection
from datetime import date
from datetime import datetime
from decimal import Decimal


debug: bool = False

###### --- PARAMETERS --- ######
# We don't need to change parameters in this script anymore; they can be passed from the shell script.
# I will eventually make each of these a Series and then iterate through them so we can do multiple types at once/

### ACCEPTING ARGUMENTS FROM SHELL SCRIPT ###

### DIRECTORY ###
# This should almost never need to change
base_directory = "/projects/standard/rmyoung/shared/mosaiks"
scratch_directory = "/scratch.local" # experimental; will need to alter the shell script.
output_path = base_directory + "/output"

if debug == True:
    res = 0.1
    location = "Minnesota"
    parcel_check = False
    zeroes = 1.0

else:
    res = float(sys.argv[1])
    location = str(sys.argv[2])
    parcel_check = str(sys.argv[3]).lower() == "true"
    zeroes = float(sys.argv[4])

res_string = str(res)

buff = (res*5)/10
round_value = (Decimal(res_string).as_tuple().exponent) + 1

if location == "Minnesota":
    poi_path = base_directory + "/raw/mn_superfund_spreadsheet.csv"
    parcel_path = base_directory + "/mn_parcels/mn_parcels.gpkg"

else:
    poi_path = base_directory + "/raw/federal_superfund_spreadsheet.csv"

#NAMING THE FILE
project_file = location + res_string.replace('.','_') + "_" + str(zeroes*100)


print("Resolution value is " + str(res) + " and the type is " + str(type(res)))
print("Location value is " + str(location) + " and the type is " + str(type(location)))
print("Parcel check value is " + str(parcel_check) + " and the type is " + str(type(parcel_check)))



pois_grid_count_name = scratch_directory + '/' + project_file + "_pois_grid_count" + ".csv"
region_grid_gdf_name = scratch_directory + '/' + project_file + "_region_grid_gdf" + ".csv"

pois_grid_count = gpd.read_file(pois_grid_count_name)
region_grid_gdf = gpd.read_file(region_grid_gdf_name)




### ----- CONFIGURE POSITIVE AND NEGATIVE LABELS ----- ###
#CREATE 1s AND 0s

#PREPARE POSITIVE LABELS (the 1s)
labels_positive = pois_grid_count.rename(columns={"superfund": "indicator"})
labels_positive['indicator'] = 1
# Create a unique 'lat_lon_key'
labels_positive['lat_lon_key'] = labels_positive['lat'].astype(str) + '_' + labels_positive['lon'].astype(str)
print(f"Loaded {len(labels_positive)} positive (1s) rows.")


# PREPARE RANDOM % OF 0S (I.E. SAMPLE)
# Create the same unique 'lat_lon_key' on the full grid
region_grid_gdf['lat_lon_key'] = region_grid_gdf['lat'].astype(str) + '_' + region_grid_gdf['lon'].astype(str)
# Get the list of keys that are already positive
positive_keys = labels_positive['lat_lon_key'].unique()
# Filter the full grid to find all rows that ARE NOT in the positive list
labels_negative = region_grid_gdf[~region_grid_gdf['lat_lon_key'].isin(positive_keys)].copy()
print(f"Found {len(labels_negative)} negative (0s) rows.")

### USER INPUT: PERCENT OF NEGATIVES TO POSITIVES IN DECIMAL FORM###
percent_negatives = zeroes #(in decimal format; so if you want 50% additional 0s you would input 0.5 here. You can also put 0.)

#Determine negative sample size
sample_size = len(labels_positive) * (percent_negatives)
print(f"Sampling {sample_size} negative (0s) rows...")
#Randomly sample all negatives based on determined sample size
labels_negative_sample = labels_negative.sample(n=int(sample_size), random_state=42)
print(f"Sampled {len(labels_negative_sample)} negative (0s) rows.")
# Add the 'indicator' column with a value of 0
labels_negative_sample['indicator'] = 0

# PREPARE 2-OVER-NEIGHBOR ("SHIFTED") NEGATIVE POINTS
# We manually shift the coordinates west (-) by 0.02 points (i.e. 2 neighbors over)
#You could make this east by inputing + instead of -
labels_negative_neighbors = labels_positive.copy()
labels_negative_neighbors['lon'] = (labels_negative_neighbors['lon'] - 0.02).round(3)

#ADDS ALL NEGATIVE LABELS TOGETHER
labels_negative_points = pd.concat([labels_negative_neighbors, labels_negative_sample])

# Turn the shifted and negative coordinates into actual Point geometries
from shapely.geometry import Point
labels_negative_points['geometry'] = labels_negative_points.apply(
    lambda row: Point(row.lon, row.lat), axis=1
)
labels_negative_points = gpd.GeoDataFrame(labels_negative_points, crs="EPSG:4326")

# VALIDATE AGAINST THE ACTUAL GRID (Spatial Match)
# We use 'sjoin' to find which of our 'shifted' points actually land inside a grid cell.
# This ensures the negative cell is a real cell in your dataset.
valid_negatives = gpd.sjoin(
    labels_negative_points.drop(columns=['lat', 'lon']), # drop to avoid duplicates
    region_grid_gdf[['lat', 'lon', 'geometry']],
    how="inner",
    predicate="intersects"
)

# Clean up: remove any negative that accidentally overlaps with a 1
# This happens if two Superfund sites are next to each other
positive_keys = labels_positive['lat'].astype(str) + labels_positive['lon'].astype(str)
valid_negatives['temp_key'] = valid_negatives['lat'].astype(str) + valid_negatives['lon'].astype(str)
final_negatives = valid_negatives[~valid_negatives['temp_key'].isin(positive_keys)].copy()

final_negatives['indicator'] = 0 #assigns all negative labels to indicator 0

# Combine
final_labels = pd.concat([
    labels_positive[['lat', 'lon', 'indicator']],
    final_negatives[['lat', 'lon', 'indicator']]
]).reset_index(drop=True)

# Check
print(f"Positives found: {len(labels_positive)}")
print(f"Valid Negatives found (after sampling): {len(final_negatives)}")
print(final_labels['indicator'].value_counts())

#See output text: it will tell you how many 1s and 0s your data will have.

### 7. ROUND THE LABELS BASED ON RESOLUTION PARAMETER AND ADDS A COLUMN HEADER TO THE ROW INDEX
final_labels=final_labels.round(round_value)
final_labels.index.name = 'Row_Count' # RY: this adds a column header to the row index
print(final_labels.head())





##### ----- SAVE THE COMBINED LABELS ----- #####
combined_labels_filename = base_directory + "/output/" + project_file + "_combinedlabels" + ".csv"
final_labels.to_csv(combined_labels_filename, index=True)

print("Label creation complete!")


##### ----- PRINT TEST MAP ----- #####
map_test_filename = base_directory + "/output/" + project_file + "_interactivemap" + ".html"

explore_final_labels = gpd.GeoDataFrame(
    final_labels,
    geometry=gpd.points_from_xy(final_labels.lon, final_labels.lat),
    crs="EPSG:4326",
)

map_test = explore_final_labels.explore()
map_test.save(map_test_filename)

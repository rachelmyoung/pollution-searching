### --- IMPORT PACKAGES --- ###
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





###### --- PARAMETERS --- ######

# I will eventually make each of these a Series and then iterate through them so we can do multiple types at once/
# It might make more sense to write a shell script that runs this script multiple times with different values for the parameters.

### RESOLUTION ###
res = float(sys.argv[1]) # 0.1, 0.01, or 0.005
print("Resolution value is " + str(res) + " and the type is " + str(type(res)))

### GEOGRAPHICAL AREA ###
location = str(sys.argv[2]) # Minnesota or US currently supported.
print("Location value is " + str(location) + " and the type is " + str(type(location)))
      
      
### PARCEL CORRECTION ###
# determines whether or not we use the centroids of property parcels that overlap with POIs or just the locations of POIs
# currently only supported for the state of Minnesota
if sys.argv[3]=="True":
    parcel_check = True
else:
    parcel_check = False

print("Parcel check value is " + str(parcel_check) + " and the type is " + str(type(parcel_check)))
      
### DIRECTORY ###
# This should almost never need to change 
base_directory = "/projects/standard/rmyoung/shared/mosaiks"
scratch_directory = "/scratch.local" # experimental; will need to alter the shell script.




##### ----- PARAMETER LOGIC ----- #####
# You generally only need to change parameters, and can ignore this for most configring.

### RESOLUTION LOGIC ###

buff = (res*5)/10

if res == 0.1:
  round_value: int = 2
  file_suffix = "_1"
elif res == 0.01:
  round_value: int = 3
  file_suffix = "_01"
elif res == 0.005:
  round_value: int = 4
  file_suffix = "_005"

###  GEOGRAPHICAL AREA LOGIC ###

file_suffix = file_suffix + "_" + location
if location == "Minnesota":
    poi_path = base_directory + "/raw/mn_superfund_spreadsheet.csv"
    parcel_path = base_directory + "/mn_parcels/mn_parcels.gpkg" 

else:
    poi_path = base_directory + "/raw/federal_superfund_spreadsheet.csv"
    
project_file = os.path.basename(poi_path)
project_file = os.path.splitext(project_file)[0]

if parcel_check==True:
    file_suffix = file_suffix + "_parcels"
else:
    file_suffix = file_suffix + "_noparcels"
    
### LOCATION OF OUTPUT FILES ###
# This shouldn't change often if being run on HPC

output_path = base_directory + "/output"

# this will make it less likely people working concurrently will overwrite each other's work
#file_suffix = file_suffix + "_"+ str(date.today()) + "_" + str(datetime.now().hour) + str(datetime.now().minute)





###### ----- FUNCTIONS ----- ######

# FUNCTION TO CREATE GRID

def create_grid(
    borders,
    resolution: float = res,
    geometry_col: str = "geometry",
    id_col: str = "NAME",
    return_ids: bool = False,
) -> pd.DataFrame:
    """
    Create a grid of latitude and longitude coordinates for one or more geometries.
    It can accept a bounding box, a single polygon (or other Shapely geometry),
    or a GeoDataFrame with a geometry column.

    Parameters
    ----------
    borders : list or tuple or shapely.geometry.BaseGeometry or geopandas.GeoDataFrame
        - If list/tuple of length 4, interpreted as a bounding box: [minx, miny, maxx, maxy].
        - If a Shapely geometry (Polygon, MultiPolygon, etc.), creates a single-row GeoDataFrame.
        - If a GeoDataFrame, the function iterates over its rows.
    resolution : float, optional
        Grid resolution in degrees, default 0.01.
    geometry_col : str, optional
        Column name for the geometry in the resulting GeoDataFrame, by default "geometry".
    id_col : str, optional
        Column name in the GeoDataFrame to use as the ID column, or the name
        for the new column if bounding box / single polygon is provided. Default is "NAME".
    return_ids : bool, optional
        If True, generate and return the unique IDs for each grid cell. This will create a
        column 'unique_id' which follows the pattern 'lon_{lon}__lat_{lat}'. This option slows
        down the overall operation. Default is False.

    Returns
    -------
    pd.DataFrame
        A DataFrame with columns:
        - 'lat': latitude values (Y)
        - 'lon': longitude values (X)
        - `[id_col]`: the identifier for each geometry feature
        - 'unique_id': a string combining [id_col] + lon/lat for uniqueness (optional)
    """

    # 1. Convert input to a GeoDataFrame
    gdf = _to_geodataframe(borders, geometry_col, id_col)

    # 2. Ensure there's an ID column in the GeoDataFrame
    if id_col not in gdf.columns:
        # If user didn't provide an ID col for bounding box or single geometry,
        # assign a placeholder ID. For a multi-row GDF, user is expected to pass
        # an existing column name.
        gdf[id_col] = [f"feature_{i}" for i in range(len(gdf))]

    # 3. Rasterize each geometry and collect points
    result_list = []
    for _, row in gdf.iterrows():
        geom = row[geometry_col]
        this_id = row[id_col]

        if geom.is_empty:
            # Skip empty geometries
            continue

        minx, miny, maxx, maxy = geom.bounds

        # ---- Create arrays for lat and lon values (Note: lat reversed) ----
        # The 0.005 shift ensures that coordinates align on .005
        lats = np.arange(
            np.ceil(maxy / resolution) * resolution - buff, miny, -resolution
        )
        lons = np.arange(
            np.ceil(minx / resolution) * resolution + buff, maxx, resolution
        )

        if len(lats) == 0 or len(lons) == 0:
            # If bounding box is too small or resolution is large, might be empty
            continue

        # ---- Create a meshgrid ----
        lon_grid, lat_grid = np.meshgrid(lons, lats)

        # ---- Rasterize the geometry ----
        out_shape = (len(lats), len(lons))
        transform = rasterio.transform.from_bounds(
            minx, miny, maxx, maxy, out_shape[1], out_shape[0]
        )

        mask = rasterio.features.rasterize(
            [(geom, 1)],
            out_shape=out_shape,
            transform=transform,
            fill=0,
            dtype=np.uint8,
        )

        # ---- Extract the lat and lon values using the mask ----
        lat_values = lat_grid[mask == 1]
        lon_values = lon_grid[mask == 1]

        # ---- Create a DataFrame and append to the result list ----
        temp_df = pd.DataFrame({"lat": lat_values, "lon": lon_values})
        temp_df[id_col] = this_id
        result_list.append(temp_df)

    # 4. Concatenate the results
    if len(result_list) == 0:
        final_result = pd.DataFrame(columns=["lat", "lon", id_col, "unique_id"])
    else:
        final_result = pd.concat(result_list, ignore_index=True)
        if return_ids:
            # --- Create the unique_id column ---
            # e.g. 'lon_-10.005__lat_9.995'
            final_result["lon_rounded"] = final_result["lon"].round(round_value).astype(str)
            final_result["lat_rounded"] = final_result["lat"].round(round_value).astype(str)

            final_result["unique_id"] = (
                "lon_"
                + final_result["lon_rounded"]
                + "__lat_"
                + final_result["lat_rounded"]
            )

            final_result.drop(["lon_rounded", "lat_rounded"], axis=1, inplace=True)

    return final_result

def _to_geodataframe(borders, geometry_col: str, id_col: str) -> gpd.GeoDataFrame:
    """
    Internal helper that converts various input types into a standardized GeoDataFrame.

    Parameters
    ----------
    borders : list/tuple, shapely geometry, or GeoDataFrame
        Bounding box (list/tuple of length 4),
        single Shapely geometry (Polygon, MultiPolygon, etc.),
        or a GeoDataFrame.
    geometry_col : str
        The name of the geometry column to use or create.
    id_col : str
        The column in which to store or look for an ID (if relevant).

    Returns
    -------
    gpd.GeoDataFrame
        A GeoDataFrame with columns [id_col, geometry_col].
    """
    # Case 1: bounding box
    if isinstance(borders, (list, tuple)) and len(borders) == 4:
        minx, miny, maxx, maxy = borders
        geom = box(minx, miny, maxx, maxy)
        gdf = gpd.GeoDataFrame(
            {id_col: ["bbox_1"], geometry_col: [geom]}, crs="EPSG:4326"
        )

    # Case 2: single shapely geometry
    elif isinstance(borders, (Polygon, MultiPolygon, GeometryCollection)):
        gdf = gpd.GeoDataFrame(
            {id_col: ["geom_1"], geometry_col: [borders]}, crs="EPSG:4326"
        )

    # Case 3: GeoDataFrame
    elif isinstance(borders, gpd.GeoDataFrame):
        # If geometry_col does not exist, rename the current geometry column
        # so everything is consistent
        if geometry_col not in borders.columns:
            borders = borders.rename(columns={borders.geometry.name: geometry_col})

        gdf = borders.copy()
        gdf = gdf.set_geometry(geometry_col)

    else:
        raise ValueError(
            "Unsupported input for 'borders'. Must be one of:\n"
            "1) [minx, miny, maxx, maxy]\n"
            "2) A Shapely geometry (Polygon, MultiPolygon, etc.)\n"
            "3) A GeoDataFrame"
        )

    return gdf

### FUNCTION TO STANDARDIZE PARCEL DATA ###

# may need to be cleaned up; not sure if it's strictly necessary

def create_parcel_data(parcel_dataframe) -> gpd.GeoDataFrame:

  parcel_data = {
      "lat": parcel_dataframe.geometry.centroid.y,
      "lon": parcel_dataframe.geometry.centroid.x,
      "parcel_id": range(1, len(parcel_dataframe) + 1),
      "geometry": parcel_dataframe.geometry,
  }

  return gpd.GeoDataFrame(parcel_data, crs=parcel_dataframe.crs)

### FUNCTION TO CREATE TABLE OF SUMMARY STATISTICS ABOUT POI LOCATION CORRECTION USING PARCELS ###

# takes a joined GeoDataFrame with parcels as the left table and POIs as the right table. Determines the distance between parcel centroids and POI locations, then creates a DataFrame with summary statistics.
# This does assume that the the lat and lon coordinates of the parcel GeoDataFrame describe the centroids of the parcels.
# optionally can include an alternate projection

def create_distance_summary(joined_pois_and_parcels, state_crs=None) -> pd.DataFrame:

  parcel_locations = {"geometry": gpd.points_from_xy(joined_pois_and_parcels['lon_left'], joined_pois_and_parcels['lat_left'])}
  parcel_locations_gdf = gpd.GeoDataFrame(parcel_locations, crs=joined_pois_and_parcels.crs)

  pois_locations = {"geometry": gpd.points_from_xy(joined_pois_and_parcels['lon_right'], joined_pois_and_parcels['lat_right'])}
  pois_locations_gdf = gpd.GeoDataFrame(pois_locations, crs=joined_pois_and_parcels.crs)

  distance_change = parcel_locations_gdf.distance(pois_locations_gdf)

  summary = distance_change.describe()

  df_summary = pd.DataFrame()
  original_crs = str(joined_pois_and_parcels.crs)
  df_summary[original_crs] = summary

  if state_crs is not None:
    parcel_locations_state_gdf = parcel_locations_gdf.to_crs(state_crs)
    pos_locations_state_gdf = pois_locations_gdf.to_crs(state_crs)
    state_distance_change = parcel_locations_state_gdf.distance(pos_locations_state_gdf)
    state_summary = state_distance_change.describe()

    alt_crs = str(state_crs)
    df_summary["EPSG:" + alt_crs] = state_summary

  return df_summary






###### ----- GRID CREATION ----- ######

### DOWNLOADING THE GRID

### FOR STATE-SPECIFIC GRIDS ###
if location != "US":
    state_zip_url = "https://www2.census.gov/geo/tiger/TIGER2025/STATE/tl_2025_us_state.zip"
    local_zip_path = "us_states_2025.zip"

    try:
      headers = {
      'User-Agent': 'Mozilla/5.0'
      }

      response = requests.get(state_zip_url, headers=headers)
      response.raise_for_status()

      with open(local_zip_path, 'wb') as f:
        f.write(response.content)

      # 2. Read the national zip file
      all_states_gdf = gpd.read_file(f"zip://{local_zip_path}")

      # 3. FILTER for your target state (Don't change anything here; change the value of location at the start of the script)
      target_state = location
      state_boundary_gdf = all_states_gdf[all_states_gdf['NAME'] == target_state].copy()

        # 4. Standardize CRS to EPSG:4326
      if state_boundary_gdf.crs != "EPSG:4326":
        state_boundary_gdf = state_boundary_gdf.to_crs("EPSG:4326")

      region_gdf = state_boundary_gdf

      print(f"Final CRS: {region_gdf.crs}")
      print(region_gdf[['NAME', 'STUSPS', 'geometry']].head())
      print("THE STATE PART WORKED")

    except Exception as e:
      print(f"THE STATE PART DID NOT WORK. An error occurred: {e}")

else:
    usa_adm0_fp="https://gist.githubusercontent.com/krithin/7d694393e8a0b69dd3bd30336ecd46ad/raw/6a0d564a2dd5da4bfa5f035af25a36f6d35ccdf4/us_lower_48.geo.json"

    region_gdf = gpd.read_file(usa_adm0_fp)

    print(f"Object type: {type(region_gdf)}")
    print(f"CRS: {region_gdf.crs}")
    print(f"Shape (row, col): {region_gdf.shape}")

    region_gdf[["id", "name", "geometry"]]
    
    print(f"Shape (row, col): {region_gdf_gdf.shape}")
    
### CREATING THE GRID ###
region_grid = create_grid(
    region_gdf,
    resolution=res,
    geometry_col="geometry",
    id_col="id",
    return_ids=True,
)
region_grid_gdf = gpd.GeoDataFrame(
    region_grid,
    geometry=gpd.points_from_xy(region_grid.lon, region_grid.lat),
    crs="EPSG:4326",
)

region_grid_gdf.geometry = region_grid_gdf.geometry.buffer(buff, cap_style=3)

print(region_grid_gdf.head())





###### --- LABEL DOWNLOAD AND FORMATTING --- ######
df = pd.read_csv(poi_path, encoding='latin-1')
print("Here's the MN Superfund spreadsheet stuff, which actually worked this time")
print(df.head())

ASSUMED_LAT_COLUMN = 'lat'
ASSUMED_LON_COLUMN = 'lon'

if 'df' in locals():
    try:
        labels_df = df[[
            ASSUMED_LAT_COLUMN,
            ASSUMED_LON_COLUMN
        ]].copy()

        labels_df = labels_df.rename(columns={
            ASSUMED_LAT_COLUMN: 'lat',
            ASSUMED_LON_COLUMN: 'lon'
        })

        labels_df['superfund'] = 1

        # Drop any rows that might be missing coordinates
        labels_df = labels_df.dropna(subset=['lat', 'lon'])

        # 1. Force conversion to numeric, turning text/garbage into NaN
        labels_df['lat'] = pd.to_numeric(labels_df['lat'], errors='coerce')
        labels_df['lon'] = pd.to_numeric(labels_df['lon'], errors='coerce')

        # 2. Drop the rows that were coerced to NaN (this removes the "lon/lat" string rows)
        before_count = len(labels_df)
        labels_df = labels_df.dropna(subset=['lat', 'lon'])
        after_count = len(labels_df)

        if before_count > after_count:
            print(f"Cleaned up {before_count - after_count} rows containing non-numeric text.")

        # 3. Double-check the types
        print(f"Data types:\n{labels_df.dtypes}")

        # You want to see: lat float64, lon float64
        print("--- Successfully processed data. ---")
        print("First 5 rows of your final label file:")
        print(labels_df.head())

        print("\nIndicator counts (all sites are '1'):")
        print(labels_df['superfund'].value_counts())

        ## SAVE THE FINAL LABELS

        output_filename = scratch_directory + '/' + project_file + '_finallabels' + file_suffix + '.csv'

        labels_df.to_csv(output_filename, index=False)

        print(f"\n--- Success! ---")
        print(f"Your final data has been saved to:")
        print(output_filename)

    except KeyError as e:
        print(f"\n--- PROCESSING ERROR ---")
        print(f"A column name was not found: {e}")
        print("Please check your 'ASSUMED_...' variables in Section 1.")
        print("Make sure they *exactly* match the names from your file.")
    except Exception as e:
        print(f"An error occurred: {e}")

else:
    print("--- ERROR ---")
    
    
### TAKES THE SAVED CSV OF LABELS AND CREATES A DATAFRAME
usa_pois_gdf = pd.read_csv(output_filename)

print(f"Object type: {type(usa_pois_gdf)}")

print(f"Shape (row, col): {usa_pois_gdf.shape}")

usa_pois_gdf.head()





###### ----- PLACES POIS ON GRID. INCLUDES PARCEL CORRECTION IF THAT IS SELECTED ----- ######

# FIX THE DATAFRAMES
usa_pois_gdf = gpd.GeoDataFrame(
    usa_pois_gdf,
    geometry=gpd.points_from_xy(usa_pois_gdf['lon'], usa_pois_gdf['lat']),
    crs="EPSG:4326"
)

# CHECK THE CRSs
if region_grid_gdf.crs != usa_pois_gdf.crs:
    print("Point CRS mismatch. Re-projecting...")
    usa_pois_gdf = usa_pois_gdf.to_crs(region_grid_gdf.crs)

# DO PARCEL STUFF IF WE CARE ABOUT IT
if parcel_check==True:

  # LOAD PARCEL DATA
  cleaned_parcel_path = output_path + "Raw/parcels/MN/parcel_27147_2018/parcel_27147_2018.shp"
  parcel_gdf = gpd.read_file(cleaned_parcel_path)
  parcel_gdf = create_parcel_data(parcel_gdf)

  #CHECK PARCEL DATA CRS
  if parcel_gdf.crs != usa_pois_gdf.crs:
      print("Parcel CRS mismatch. Re-projecting...")
      parcel_gdf = parcel_gdf.to_crs(region_grid_gdf.crs)

      print(f"Corrected CRS: {parcel_gdf.crs}")

  # RUN THE POIs AND PARCELS JOIN
  # This determines if the centroid of a POI is located inside of a parcel, and drops any parcels that don't contain a POI location.
  pois_and_parcels_grid = gpd.sjoin(
      parcel_gdf,
      usa_pois_gdf,
      how="inner",
      predicate="intersects"
  )

  # GET THE CENTROIDS OF THE PARCELS THAT CONTAIN POIs
  sites_gdf = gpd.GeoDataFrame(
  geometry=gpd.points_from_xy(pois_and_parcels_grid.geometry.centroid.x, pois_and_parcels_grid.geometry.centroid.y),
  crs=pois_and_parcels_grid.crs
  )

  sites_gdf["lat"] = sites_gdf.geometry.y
  sites_gdf["lon"] = sites_gdf.geometry.x

else:
  sites_gdf = usa_pois_gdf

#  RUN THE POIs+PARCELS and GRID JOIN. GETS ALL PIXELS THAT CONTAIN POI PARCEL CENTROIDS.
pois_grid = gpd.sjoin(
    region_grid_gdf,
    sites_gdf,
    how="inner",
    predicate="intersects",
)

print("see what POIS GRID LOOKSL LIKE NOW")
print(pois_grid.head())

#  CHECK THE OUTPUT
#print(f"--- Join Complete! ---")
##print(f"Total grid cells with points: {len(pois_grid)}")
#print(pois_and_parcels_grid.head())

# GET STATS ON AND CHECK VALIDITY OF PARCEL TO POI FIX
if parcel_check==True:
 
  print("summary statistics")
  minnesota_summary = create_distance_summary(pois_and_parcels_grid, 26915)
  print(minnesota_summary.head())

  # save_location = output_path + "/Intermediate/summary_statistics_test.csv"

  # CHECK TO SEE IF ANY POIS DO NOT INTERSECT WITH PARCELS
  rogue_pois = usa_pois_gdf[~usa_pois_gdf.index.isin(pois_and_parcels_grid.index)]
  print(f"Number of POIs not captured by parcels: {len(rogue_pois)}")

  # CHECKING PARCELS FOR WEIRD BEHAVIOR
  print("PARCEL EVALUATION")
  parcel_evaluation_summary = parcel_evaluation(parcel_gdf, 26915)
  print(parcel_evaluation_summary.head())

  parcel_save_location = output_path + "/Intermediate/parcel_statistics_test.csv"

  parcel_evaluation_summary.to_csv(parcel_save_location)


    
    
    
### ----- CREATE LABEL SUMMARY ----- ###
# From MOSAIKS: "We then group the labels by the grid cell and count the number of labels in each grid cell. This will be our label summary."
# Group by grid cell (using lat/lon) and fclass, then count
pois_grid_count = pois_grid.groupby(
    ["lat_left", "lon_left", "unique_id"],
    as_index=False,
).unique_id.count()

# Rename the fclass column
pois_grid_count = pois_grid_count.rename(columns={
    "unique_id": "superfund",
    "lat_left": "lat",
    "lon_left": "lon"
    })
pois_grid_count["superfund"] = 1

pois_grid_count = gpd.GeoDataFrame(
    pois_grid_count,
    geometry=gpd.points_from_xy(pois_grid_count.lon, pois_grid_count.lat),
    crs="EPSG:4326",
)
pois_grid_count.geometry = pois_grid_count.geometry.buffer(buff, cap_style=3)
pois_grid_count





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
percent_negatives = 0.1 #(in decimal format; so if you want 50% additional 0s you would input 0.5 here. You can also put 0.)

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
combined_lables_filename = base_directory + "/output/" + project_file + "_combinedlabels" + file_suffix + ".csv"
labels_df.to_csv(combined_lables_filename, index=False)

print("Label creation complete!")

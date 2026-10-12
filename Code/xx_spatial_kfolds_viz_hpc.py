import pandas as pd
import glob
import os
import datetime
import numpy as np
import seaborn as sns
import geopandas as gpd
from sklearn import preprocessing
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.model_selection import cross_validate
import matplotlib.pyplot as plt
#from matplotlib import cm
import matplotlib as mpl
import matplotlib.colors as colors
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from sklearn.metrics import roc_curve, roc_auc_score
import sys
from decimal import Decimal



from spatialkfold.blocks import spatial_blocks
from spatialkfold.datasets import load_ames
from spatialkfold.clusters import spatial_kfold_clusters
from spatialkfold.plotting import spatial_kfold_plot
from spatialkfold.stats import spatial_kfold_stats

from sklearn.metrics import auc, RocCurveDisplay
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

from sklearn.model_selection import FixedThresholdClassifier

from sklearn.metrics import accuracy_score, precision_score, log_loss

from matplotlib.ticker import ScalarFormatter

from config import config


###### --- START BOILERPLATE --- ######
debug: bool = True

### ACCEPTING ARGUMENTS FROM SHELL SCRIPT ###

###### --- START BOILERPLATE --- ######
res = config.res
location = config.location
parcel_check = config.parcel_check
zeroes = config.zeroes
suffix = config.suffix

buff = config.buff
round_value = config.round_value

project_file = config.project_file

scratch_directory = "/scratch.local"

poi_path = config.raw_data 

print("Resolution value is " + str(res) + " and the type is " + str(type(res)))
print("Location value is " + str(location) + " and the type is " + str(type(location)))
print("Parcel check value is " + str(parcel_check) + " and the type is " + str(type(parcel_check)))
print("Zeroes value is " + str(zeroes) + " and the type is " + str(type(zeroes)))
print("Suffix value is " + str(suffix) + " and the type is " + str(type(suffix)))

###### --- END BOILERPLATE --- ######

testing_suffix = "rf_mainmodel"

###### --- GENERATE SPATIAL KFOLD RESULTS FILENAMES --- ######

zeroes_list = [0, 1, 5, 10, 25, 50, 100, 200, 300, 400]

results_frames = {}

for zero in zeroes_list:
    results_filename = results_stem + "_z" + str(zero) + suffix + "_rfmainmodel_results.csv"
    print(results_filename)
    results_full_path = os.path.join(input_path, results_filename)
    results_df_name = f"df_{zero}"
    results_frames[results_df_name] = pd.read_csv(results_full_path)
    print(f"head at {zero}% zeroes is:")
    print(results_frames[results_df_name].head())
    print(f"tail at {zero}% zeroes is:")
    print(results_frames[results_df_name].tail())
    


df_long = pd.concat(results_frames.values(), ignore_index=True)

print(df_long.head())
print(df_long.tail())



###### ===== FIGURE CREATION ===== #####

#Each block of code below features a different type of figure. The first block is the one we prefer.


#Primary figure!


# --- Plotting Logic (from user's prompt) ---
metrics = ['auc', 'precision', 'accuracy']
titles = ['Median AUC Score', 'Median Precision', 'Median Accuracy']
colors = {'Random': '#1f77b4', 'K fold': '#ff7f0e'}
percentages = [0, 1, 5, 10, 25, 50, 100, 200, 400]

fig, axes = plt.subplots(1, 3, figsize=(22, 7))

for i, metric in enumerate(metrics):
    ax = axes[i]
    for cv_type in ['Random', 'K fold']:
        subset = df_long[(df_long['Metric'] == metric) & (df_long['Type'] == cv_type)].sort_values('Pct')

        # Main Median Line
        ax.plot(subset['Pct'], subset['Median'], label=f'{cv_type} CV', marker='o', color=colors[cv_type], linewidth=2.5)
        #Primary thick lines representing median data from results

        # Shaded IQR (Q1 to Q3)
        ax.fill_between(subset['Pct'], subset['Q1'], subset['Q3'], color=colors[cv_type], alpha=0.15)
        #shaded area on graph representing standard deviation

        # Dotted Min/Max
        ax.plot(subset['Pct'], subset['Min'], linestyle=':', alpha=0.3, color=colors[cv_type])
        ax.plot(subset['Pct'], subset['Max'], linestyle=':', alpha=0.3, color=colors[cv_type])
        #Dotted lines represent minimum and maximum

    # Axis Formatting
    ax.set_title(titles[i], fontsize=15, fontweight='bold', pad=15)
    ax.set_xlabel('Randomness Percentage (%)', fontsize=12)
    ax.set_xlim(-10, 410)
    ax.set_xticks(percentages)
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.grid(True, linestyle='--', alpha=0.5)
    if i == 0: ax.set_ylabel('Score', fontsize=12)

axes[0].legend(loc='lower right')
plt.suptitle('Performance Distribution by Data Imbalance (Median Focus)', fontsize=18, y=1.02)
plt.tight_layout()

#-----USER INPUT-----#
# Save plot
output_filename = f'{results_stem}_{testing_suffix}_Performance_Distribution_by_Data_Imbalance_MedianFocus.pdf' #name of pdf
full_path = os.path.join(output_directory, output_filename)
plt.savefig(full_path, dpi=300, bbox_inches='tight')

plt.show()

#Same as above except Mean instead of Median
# --- Plotting Logic (from user's prompt) ---
metrics = ['auc', 'precision', 'accuracy']
titles = ['Mean AUC Score', 'Mean Precision', 'Mean Accuracy']
colors = {'Random': '#1f77b4', 'K fold': '#ff7f0e'}
percentages = [0, 1, 5, 10, 25, 50, 100, 200, 400]

fig, axes = plt.subplots(1, 3, figsize=(22, 7))

for i, metric in enumerate(metrics):
    ax = axes[i]
    for cv_type in ['Random', 'K fold']:
        subset = df_long[(df_long['Metric'] == metric) & (df_long['Type'] == cv_type)].sort_values('Pct')

        # Main Mean Line
        ax.plot(subset['Pct'], subset['Mean'], label=f'{cv_type} CV', marker='o', color=colors[cv_type], linewidth=2.5)

        # Shaded IQR (Q1 to Q3)
        ax.fill_between(subset['Pct'], subset['Q1'], subset['Q3'], color=colors[cv_type], alpha=0.15)

        # Dotted Min/Max
        ax.plot(subset['Pct'], subset['Min'], linestyle=':', alpha=0.3, color=colors[cv_type])
        ax.plot(subset['Pct'], subset['Max'], linestyle=':', alpha=0.3, color=colors[cv_type])

    # Axis Formatting
    ax.set_title(titles[i], fontsize=15, fontweight='bold', pad=15)
    ax.set_xlabel('Randomness Percentage (%)', fontsize=12)
    ax.set_xlim(-10, 410)
    ax.set_xticks(percentages)
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.grid(True, linestyle='--', alpha=0.5)
    if i == 0: ax.set_ylabel('Score', fontsize=12)

axes[0].legend(loc='lower right')
plt.suptitle('Performance Distribution by Data Imbalance (Mean Focus)', fontsize=18, y=1.02)
plt.tight_layout()

#-----USER INPUT-----#
# Save plot
output_filename = f'{results_stem}_{testing_suffix}_Performance_Distribution_by_Data_Imbalance_MeanFocus.pdf'
full_path = os.path.join(output_directory, output_filename)
plt.savefig(full_path, dpi=300, bbox_inches='tight')

plt.show()

#Mean model performance results, logged

import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

# --- Graphing Portion ---
metrics = ['auc', 'precision', 'accuracy']
titles = ['Mean AUC Score', 'Mean Precision', 'Mean Accuracy']
colors = {'Random': '#1f77b4', 'K fold': '#ff7f0e'}
percentages = [0, 1, 5, 10, 25, 50, 100, 200, 400]

fig, axes = plt.subplots(1, 3, figsize=(22, 7))

for i, metric in enumerate(metrics):
    ax = axes[i]
    for cv_type in ['Random', 'K fold']:
        subset = df_long[(df_long['Metric'] == metric) & (df_long['Type'] == cv_type)].sort_values('Pct')

        # Plot Mean, Shaded IQR, and Min/Max range
        ax.plot(subset['Pct'], subset['Mean'], label=f'{cv_type}', marker='o', color=colors[cv_type], linewidth=2.5)
        ax.fill_between(subset['Pct'], subset['Q1'], subset['Q3'], color=colors[cv_type], alpha=0.15)
        ax.plot(subset['Pct'], subset['Min'], linestyle=':', alpha=0.3, color=colors[cv_type])
        ax.plot(subset['Pct'], subset['Max'], linestyle=':', alpha=0.3, color=colors[cv_type])

    # --- Axis Formatting ---
    ax.set_title(titles[i], fontsize=15, fontweight='bold', pad=15)
    ax.set_xlabel('Randomness Percentage (%)', fontsize=12)

    # Scale and Limits - logs the x axis
    ax.set_xscale('symlog', linthresh=5)
    ax.set_xlim(0, 400)

    # FORCE LABELS TO BE NUMBERS:
    ax.set_xticks(percentages)
    ax.xaxis.set_major_formatter(ScalarFormatter())

    ax.grid(True, which="both", linestyle='--', alpha=0.5)
    if i == 0: ax.set_ylabel('Score', fontsize=12)

axes[0].legend(loc='lower right')
plt.suptitle('Mean Model Performance Results, Logged', fontsize=18, y=1.02)
plt.tight_layout()

#-----USER INPUT-----#
# Save plot
output_filename = f'{results_stem}_{testing_suffix}_Mean_Model_Performance_Logged.pdf'
full_path = os.path.join(output_directory, output_filename)
plt.savefig(full_path, dpi=300, bbox_inches='tight')

plt.show()



# Dynamically generate results_data from df_long for 'Random' CV type
df_random = df_long[df_long['Type'] == 'Random'].sort_values('Pct')

results_data = {
    'Randomness_%': df_random[df_random['Metric'] == 'auc']['Pct'].tolist(),
    'AUC': df_random[df_random['Metric'] == 'auc']['Mean'].tolist(),
    'Precision': df_random[df_random['Metric'] == 'precision']['Mean'].tolist(),
    'Accuracy': df_random[df_random['Metric'] == 'accuracy']['Mean'].tolist()
}

df_results = pd.DataFrame(results_data)


plt.figure(figsize=(14, 6))

# Figure 1: AUC and Accuracy (The "Steepening" Check)
plt.subplot(1, 2, 1)
plt.plot(df_results['Randomness_%'], df_results['Accuracy'], marker='o', label='Accuracy', color='blue', linewidth=2)
plt.plot(df_results['Randomness_%'], df_results['AUC'], marker='s', label='ROC-AUC', color='green', linewidth=2)
plt.title('Performance vs. Dataset Randomness', fontsize=14) # \n(Tuned Cut-off Threshold)
plt.xlabel('Randomness Percentage (%)', fontsize=12)
plt.ylabel('Score', fontsize=12)
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)

# Figure 2: Precision (The "Trade-off" Check)
plt.subplot(1, 2, 2)
plt.plot(df_results['Randomness_%'], df_results['Precision'], marker='^', label='Precision', color='red', linewidth=2)
plt.title('Precision vs. Dataset Randomness', fontsize=14)
plt.xlabel('Randomness Percentage (%)', fontsize=12)
plt.ylabel('Precision Score', fontsize=12)
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()

#-----USER INPUT-----#
# Save plot
output_filename = f'{results_stem}_{testing_suffix}_Research_Curve.pdf'
full_path = os.path.join(output_directory, output_filename)
plt.savefig(full_path, dpi=300, bbox_inches='tight')

plt.show()
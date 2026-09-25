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
output_filename = f'{project_file}_Performance_Distribution_by_Data_Imbalance_MedianFocus.pdf' #name of pdf
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
output_filename = f'{project_file}_Performance_Distribution_by_Data_Imbalance_MeanFocus.pdf'
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
output_filename = f'{project_file}_Mean_Model_Performance_Logged_.01_Federal.pdf'
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
plt.title('Performance vs. Dataset Randomness\n(Tuned Cut-off Threshold)', fontsize=14)
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
output_filename = f'{project_file}_Research_Curve.pdf'
full_path = os.path.join(output_directory, output_filename)
plt.savefig(full_path, dpi=300, bbox_inches='tight')

plt.show()

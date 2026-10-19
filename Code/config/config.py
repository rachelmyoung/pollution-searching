import os
from decimal import Decimal
import sys



### ACCEPTING ARGUMENTS FROM SHELL SCRIPT ###

debug = True

if debug == True:
    res = 0.01
    location = "Minnesota"
    parcel_check = False
    zeroes = 2.0
    suffix = ""

else:
    res = float(sys.argv[1])
    location = str(sys.argv[2])
    parcel_check = str(sys.argv[3]).lower() == "true"
    zeroes = float((sys.argv[4]).replace(",", ""))
    suffix = ""

res_string = str(int(res*100))
zeroes_pct = int(zeroes*100)
zeroes_string = str(zeroes_pct)

buff = (res*5)/10
round_value = abs((Decimal(res_string).as_tuple().exponent) - 1)

project_file = location + "_r" + res_string + "_z" + zeroes_string + suffix

###### --- END BOILERPLATE --- ######

combined_labels_filename = project_file + "_combinedlabels.csv"
featurized_labels_filename = "GEE_featurization_" + project_file + "_*.csv"
performance_filename = project_file + "_performance.csv"

# probably should do this more elegantly
base_directory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

#raw
# doesn't have a name for each region, but I will probably add those once I figure out how to name them programmatically


if location == "US":
    raw_data = os.path.join(base_directory, "data", "raw", "federal_superfund_spreadsheet.csv")
elif location == "Minnesota":
    raw_data = os.path.join(base_directory, "data", "raw", "mn_superfund_spreadsheet.csv")
elif location == "California":
    raw_data = ""


features_directory = os.path.join(base_directory, "data", "intermediate", "featurized_labels")
performance_directory = os.path.join(base_directory, "data", "intermediate", "performance_results")

# intermediate
combined_labels_path = os.path.join(base_directory, "data", "intermediate", "combined_labels", combined_labels_filename)
featurized_labels_path = os.path.join(base_directory, "data", "intermediate", "featurized_labels", featurized_labels_filename)
performance_results_path = os.path.join(base_directory, "data", "intermediate", "performance_results", performance_filename)


# results
# doesn't have name a file for visualizations, because there are many different figures and they aren't taken in by other scripts
figures_directory = os.path.join(base_directory, "data", "results", "figures")


# create output folders if they don't exist yet
for _path in [combined_labels_path, featurized_labels_path, performance_results_path]:
    os.makedirs(os.path.dirname(_path), exist_ok=True)
os.makedirs(figures_directory, exist_ok=True)
import os
from decimal import Decimal
import sys



###### --- START BOILERPLATE --- ######
debug: bool = False

### ACCEPTING ARGUMENTS FROM SHELL SCRIPT ###

res = float(sys.argv[1])
print("Arg 1 is " + str(sys.argv[1]))
    
location = str(sys.argv[2])
print("Arg 2 is " + str(sys.argv[2]))
    
parcel_check = str(sys.argv[3]).lower() == "true"
print("Arg 3 is " + str(sys.argv[3]))
   
zeroes = float((sys.argv[4]).replace(",", ""))
print("Arg 4 is " + str(sys.argv[4]))

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

base_directory = os.path.dirname(os.path.dirname(__file__))

#raw
# doesn't have a name for each region, but I will probably add those once I figure out how to name them programmatically
raw_data = os.path.join(base_directory, "data", "raw")

# intermediate
combined_labels_directory = os.path.join(base_directory, "data", "intermediate", "combined_labels", combined_labels_filename)
featurized_labels_directory = os.path.join(base_directory, "data", "intermediate", "featurized_labels", featurized_labels_filename)
performance_results_directory = os.path.join(base_directory, "data", "intermediate", "performance_results", performance_filename)

# results
# doesn't have name a file for visualizations, because there are many different figures and they aren't taken in by other scripts
figures_directory = os.path.join(base_directory, "data", "results", "figures")
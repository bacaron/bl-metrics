#!/bin/bash

# set variables
app_name=$1
repo_path=$2
stats_folder_name=$app_name/stats
output_dir=$3
output_name=$output_dir/${app_name}_lines_of_code.csv

# clone repo
[ ! -d $app_name ] && git clone https://github.com/${repo_path}.git ./$app_name

# run GitStats on dir
gitstats ./$app_name $stats_folder_name

# make config.json
echo '{"data_path": "'$stats_folder_name'/lines_of_code.dat", "out_path": "'$output_name'"}' > config.json

# make lines of code data into csv with datetime
python3 /home/brad/Desktop/bl-metrics/convert-git-stats-lines-of-code.py

[ -f $output_name ] && rm -rf config.json ./$app_name

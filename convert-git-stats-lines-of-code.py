#!/usr/bin/env python3
# reformat lines of code data from GitStats
import pandas as pd
from datetime import datetime
import json

# functions
def convert_to_datetime(x):
    return datetime.fromtimestamp(x).strftime("%Y-%m-%d-%H:%M:%S")

# def main
def main():

    # load config.json
    with open('config.json','r') as config_f:
        config = json.load(config_f)

    # set important paths
    data_path = config['data_path']
    out_path = config['out_path']

    # load data_path
    data = pd.read_table(data_path, sep=" ", header=None, names=['timestamp','lines'])

    # convert timestamp to datetime
    data['datetime'] = data['timestamp'].apply(lambda x: convert_to_datetime(x))

    # output to out_path
    data.to_csv(out_path,index=False)

if __name__ == '__main__':
    main()

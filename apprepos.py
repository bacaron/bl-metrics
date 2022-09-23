#!/usr/bin/env python3

import os,sys
import pandas as pd
import numpy as np

# use this to update rows of dataframe in dumb lazy way
def a_df(df,app,owner,branch,container):
    df.loc[len(df.index)] = [app,owner,branch,container] 
    df = df.reset_index(drop=True)
    
    return df

# use this if previous branches call same containers as new branch
def b_df(df,app_name,branch_to_copy,branch_to_copy_to):
    tmp = df.loc[(df['app'] == app_name) & (df['branch'] == branch_to_copy)]
    tmp.branch = [ branch_to_copy_to for f in tmp['branch'] ]
    df = df.append(tmp)
    df = df.reset_index(drop=True)    
    
    return df

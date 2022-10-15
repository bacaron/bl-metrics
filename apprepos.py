#!/usr/bin/env python3

import os,sys
import pandas as pd
import numpy as np
import subprocess

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

# this function will check for common neuroimaging packages that have install locations not identified by syft. will probably need to continually update this with 
# new software and versions
def check_neuroimage_package(df,package,container,check_command,check_file):

    tmp = subprocess.run(["docker","run","--rm",container.split('docker://')[1],check_command,check_file],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    found_by = 'brad-code'

    if package == 'freesurfer-stats':
        if tmp.stdout.decode('utf-8'):
            filepath = check_file+'/Pipfile'
            tmp_vs = subprocess.run(["docker","run","--rm",container.split('docker://')[1],"cat",filepath],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.decode('utf-8').split('\n')
            package_version = [ tmp_vs[f+1] for f in range(len(tmp_vs)) if 'freesurfer-stats' in tmp_vs[f] ][0].split(' ')[1]
            df = df.append({'package': package, 'version': package_version, 'found_by': found_by},ignore_index=True)
    else:    
        if not tmp.stdout.decode('utf-8').split(':')[1] == '\n' and not tmp.stdout.decode('utf-8').split(':')[1] == '':
            if package == 'freesurfer':
                filepath = tmp.stdout.decode('utf-8').split(' ')[-1].replace('\n','')
                if 'bin' in filepath:
                    filepath = filepath.split('/bin')[0]
                filepath = filepath+'/VERSION'
                package_version = subprocess.run(["docker","run","--rm",container.split('docker://')[1],"cat",filepath],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.decode('utf-8').split('\n')[0]
                if not package_version:
                    package_version = subprocess.run(["docker","run","--rm",container.split('docker://')[1],"mri_vol2vol","--version"],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.decode('utf-8').split('\n')[0].split(' ')[-1]

            elif package == 'connectome_workbench':
                tmp_vs = subprocess.run(["docker","run","--rm",container.split('docker://')[1],check_file,"-version"],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.decode('utf-8').split('\n')
                package_version = [ f for f in tmp_vs if 'Version:' in f ][0].split('Version:')[1].strip(' ')

            elif package == 'mrtrix':
                tmp_vs = subprocess.run(["docker","run","--rm",container.split('docker://')[1],check_file,"--version"],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.decode('utf-8').split('\n')
                package_version = [ f for f in tmp_vs if check_file in f ][0].replace('==','').strip(' ').split(' ')[1]

            elif package == 'dsistudio':
                package_version = subprocess.run(["docker","run","--rm",container.split('docker://')[1],check_file,"--version"],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.decode('utf-8').split('\n')[0].split(': ')[1]

            elif package == 'pynets':
                package_version = subprocess.run(["docker","run","--rm",container.split('docker://')[1],check_file,"--version"],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.decode('utf-8').split('\n')[0].split(' ')[1]   
                        
            df = df.append({'package': package, 'version': package_version, 'found_by': found_by},ignore_index=True)

    return df

# use this function to create tables of installed binaries using syft
def identify_binaries(container):

    print('identifying installed binaries for container %s' %container)
    # runs syft in shell and returns the output, which is a comma-separated table stored as a list
    tmp = subprocess.run(["syft", container.split('docker://')[1], "--scope", "all-layers", "-o", "template", "-t", "csv.tmpl"],stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')[:-1]

    # builds the dataframe
    df = pd.DataFrame([ f.replace('"','').split(',') for f in tmp[1:] ],columns=["package","version","found_by"])
    
    # check for common neuroimaging softwares with odd install locations not identifyed by syft
    print('checking for neuroimaging packages syft missed')
    packages_to_check = ['freesurfer','connectome_workbench','mrtrix3','dsistudio','pynets','freesurfer-stats']
    
    for i in packages_to_check:
        check_command = 'whereis'
        print('checking for %s install' %i)
        if i == 'freesurfer':
            check_file = 'mri_vol2vol'
        elif i == 'connectome_workbench':
            check_file = 'wb_command'
        elif i == 'mrtrix':
            check_file = 'mrconvert'
        elif i == 'dsistudio':
            check_file = 'dsi_studio'
        elif i == 'pynets':
            check_file = 'pynets'
        elif i == 'freesurfer-stats':
            check_file = '/freesurfer-stats'
            check_command = 'ls'

        df = check_neuroimage_package(df,i,container,check_command,check_file)

    # adds the container name as a new column to allow for merging with other containers
    df['container'] = [ container for f in range(len(df)) ]

    # removes the singularity image to avoid memory issues
    subprocess.run(["docker","rmi", container.split('docker://')[1]])
    
    return df

    # # check for freesurfer install
    # df = check_neuroimage_package(df,'freesurfer',container,"whereis","mri_vol2vol")

    # # check for connectome workbench install
    # df = check_neuroimage_package(df,'connectome_workbench',container,"whereis","wb_command")

    # # check for mrtrix install
    # df = check_neuroimage_package(df,'mrtrix',container,"whereis","mrconvert")

    # # check for dsistudio install
    # df = check_neuroimage_package(df,'dsistudio',container,"whereis","dsi_studio")

    # # check for pynets install
    # df = check_neuroimage_package(df,'pynets',container,"whereis","pynets")






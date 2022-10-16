#!/usr/bin/env python3

import os,sys
import pandas as pd
import numpy as np
import subprocess
import shutil

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


# identify docker containers for github repository information for brainlife apps.
def identify_docker_containers(owner,repo,branch,main_file):

    print('identifying docker containers used in %s/%s:%s' %(owner,repo,branch))

    current_dir = os.getcwd()

    # clone the github repo
    print('cloning repository')
    subprocess.run(["git","clone","https://github.com/"+owner+"/"+repo,"-b",branch],stdout=subprocess.PIPE,stderr=subprocess.PIPE)

    # cd into the directory
    os.chdir(repo)

    # grab the singularity calls
    print('grabbing containers')
    tmp_line = subprocess.run(["awk","/docker:/",main_file],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.decode('utf-8').split('\n')[:-1]

    # clean up container names
    containers = [ "docker://"+f.split('docker://')[1].split(' ')[0] for f in tmp_line ]

    # remove duplicates
    containers = [ containers[i] for i in range(len(containers)) if i == containers.index(containers[i]) ]

    # change dir to previous pwd and remove cloned directory
    os.chdir(current_dir)
    shutil.rmtree(repo)

    return containers

def identify_app_branches(owner,repo):

    print('identifying branches for repository %s/%s' %(owner,repo))

    # use git ls-remote to identify all the branches for a repo
    tmp_branches = subprocess.run(["git","ls-remote","--heads","https://github.com/"+owner+"/"+repo],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.decode('utf-8').split('\n')[:-1]

    # clean up
    branches = [ f.split('/heads/')[1] for f in tmp_branches ]

    return branches

def build_app_branches_df(owner,repo,main_file):

    print('identifying app branches and docker containers for app %s/%s' %(owner,repo))

    df = pd.DataFrame(columns=['app','owner','branch','containers'])

    # grab app repo branches from git
    branches = identify_app_branches(owner,repo)

    # grab app containers for each branch
    for i in branches:
        tmp = pd.DataFrame()
        containers = identify_docker_containers(owner,repo,i,main_file)
        tmp['app'] = [ repo for f in range(len(containers)) ]
        tmp['owner'] = [ owner for f in range(len(containers)) ]
        tmp['branch'] = [ i for f in range(len(containers)) ]
        tmp['containers'] = containers

        df = pd.concat([df,tmp])
        df = df.reset_index(drop=True)

    return df

def check_if_python(tmp):

    if 'Run a python command' in tmp.stdout.decode('utf-8'):
        tmp.stdout = tmp.stdout.decode('utf-8').replace('\nUsage: docker run <imagename> COMMAND\n\nCommands\n\npython     : Run a python command\nbash       : Start a bash shell\nvtk_ccmake : Prepare VTK to build with ccmake. This happens in the container (not during image build)\nvtk_make   : Build the VTK library\nhelp       : Show this message\n\n','').encode()

    return tmp

def check_fsl_citation(tmp):

    if 'Some packages in this Docker container are non-free' in tmp.stdout.decode('utf-8'):
        tmp.stdout = tmp.stdout.decode('utf-8').replace('Some packages in this Docker container are non-free\nIf you are considering commercial use of this container, please consult the relevant license:\nhttps://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Licence\n','').encode()

    return tmp

def check_fsl_python(tmp):

    tmp = check_fsl_citation(tmp)

    tmp = check_if_python(tmp)

    return tmp

def find_filename(container,check_filename):

    tmp = subprocess.run(["docker","run","--rm",container.split('docker://')[1],"find","/","-type","f","-name",check_filename],stdout=subprocess.PIPE,stderr=subprocess.PIPE)

    return tmp

# this function will check for common neuroimaging packages that have install locations not identified by syft. will probably need to continually update this with 
# new software and versions
# NEED TO SOLVE REMAINING FREESURFER CONTAINERS (containers[20:28]) and FSL VERSIONS. HAVE FINISHED THROUGH FREESURFER 6. CONTAINERS

def check_neuroimage_package(df,package,container,check_command,check_file):

    if check_command == 'find':
        tmp = subprocess.run(["docker","run","--rm",container.split('docker://')[1],"find","/","-type","f","-name",check_file],stdout=subprocess.PIPE,stderr=subprocess.PIPE)        
    else:
        tmp = subprocess.run(["docker","run","--rm",container.split('docker://')[1],check_command,check_file],stdout=subprocess.PIPE,stderr=subprocess.PIPE)

    tmp = check_fsl_python(tmp)

    found_by = 'manual-inspection'

    if package == 'qsiprep' or package == 'fmriprep' or package == 'mriqc':
        package_version = subprocess.run(["docker","run","--rm",container.split('docker://')[1],package,check_command],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        package_version = check_fsl_python(package_version).stdout.decode('utf-8').strip('\n').split(' ')
        package_version = [ f for f in package_version if f != package ][-1]
        if package_version:
            df = df.append({'package': package, 'version': package_version, 'found_by': found_by},ignore_index=True)
    elif package == 'freesurfer-stats':
        if tmp.stdout.decode('utf-8'):
            filepath = check_file+'/Pipfile'
            tmp_vs = subprocess.run(["docker","run","--rm",container.split('docker://')[1],"cat",filepath],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            tmp_vs = check_fsl_python(tmp_vs).stdout.decode('utf-8').split('\n')
            package_version = [ tmp_vs[f+1] for f in range(len(tmp_vs)) if 'freesurfer-stats' in tmp_vs[f] ][0].split(' ')[1]
            df = df.append({'package': package, 'version': package_version, 'found_by': found_by},ignore_index=True)
    else:    
        if not tmp.stdout.decode('utf-8').split(':')[-1] == '\n' and not tmp.stdout.decode('utf-8').split(':')[-1] == '':
            if package == 'freesurfer':
                filepath = tmp.stdout.decode('utf-8').split(' ')[-1].replace('\n','')
                if '/bin' in filepath:
                    filepath = filepath.split('/bin')[0]
                filepath = filepath+'/VERSION'
                tmp_vs = subprocess.run(["docker","run","--rm",container.split('docker://')[1],"cat",filepath],stdout=subprocess.PIPE,stderr=subprocess.PIPE)

                package_version = check_fsl_python(tmp_vs).stdout.decode('utf-8').split('\n')[-1]
                if not package_version:
                    tmp_vs = subprocess.run(["docker","run","--rm",container.split('docker://')[1],"mri_vol2vol","--version"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)

                    package_version = check_fsl_python(tmp_vs).stdout.decode('utf-8').split('\n')[0].split(' ')[-1]
                    if package_version == 'info)':
                        package_version = 'dev'
            
            elif package == 'connectome_workbench':
                tmp_vs = subprocess.run(["docker","run","--rm",container.split('docker://')[1],check_file,"-version"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                tmp_vs = check_fsl_python(tmp_vs).stdout.decode('utf-8').split('\n')

                package_version = [ f for f in tmp_vs if 'Version:' in f ][0].split('Version:')[1].strip(' ')
            
            elif package == 'mrtrix':
                tmp_vs = subprocess.run(["docker","run","--rm",container.split('docker://')[1],check_file,"--version"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)

                tmp_vs = check_fsl_python(tmp_vs).stdout.decode('utf-8').split('\n')

                package_version = [ f for f in tmp_vs if check_file in f ][0].replace('==','').strip(' ').split(' ')[1]
            
            elif package == 'dsistudio':
                tmp_vs = subprocess.run(["docker","run","--rm",container.split('docker://')[1],check_file,"--version"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                package_version = check_fsl_python(tmp_vs).stdout.decode('utf-8').split('\n')[0].split(': ')[-1]

            elif package == 'pynets':
                tmp_vs = subprocess.run(["docker","run","--rm",container.split('docker://')[1],check_file,"--version"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)

                package_version = check_fsl_python(tmp_vs).stdout.decode('utf-8').split('\n')[0].split(' ')[1]
            
            elif package == 'fsl':
                tmp_vs = find_filename(container,'fslversion')
                tmp_vs = check_fsl_python(tmp_vs).stdout.decode('utf-8').split('\n')[:-1]

                package_version = subprocess.run(["docker","run","--rm",container.split('docker://')[1],"cat",tmp_vs[-1]],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                package_version = check_fsl_python(package_version).stdout.decode('utf-8').split('\n')[0]
                
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
    packages_to_check = ['freesurfer','connectome_workbench','mrtrix','dsistudio','pynets','freesurfer-stats','fsl']
    # current_packages = df.package.unique().tolist()

    if 'qsiprep' in container:
        i = 'qsiprep'
        check_command = '--version'
        check_file = ''      
        df = check_neuroimage_package(df,i,container,check_command,check_file)
    elif 'fmriprep' in container:
        i = 'fmriprep'
        check_command = '--version'
        check_file = ''
        df = check_neuroimage_package(df,i,container,check_command,check_file)
    elif 'mriqc' in container:
        i = 'mriqc'
        check_command = '--version'
        check_file = ''
        df = check_neuroimage_package(df,i,container,check_command,check_file)
    else:
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
            elif i == 'fsl':
                check_file = 'fslversion'
                check_command = 'find'
            
            # if i not in current_packages:
            df = check_neuroimage_package(df,i,container,check_command,check_file)

    # adds the container name as a new column to allow for merging with other containers
    df['containers'] = [ container for f in range(len(df)) ]

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






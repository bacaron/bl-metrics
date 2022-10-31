#!/usr/bin/env python3

import os,sys
import argparse
import pandas as pd
import numpy as np
import json

def check_for_command_usage(returns):

	if "Usage: bl-datatype [options] [command]\n\nOptions:\n  -h, --help      display help for command\n\nCommands:\n  query           run a query against all datatypes\n  help [command]  display help for command" in returns:
		
		return returns.replace("Usage: bl-datatype [options] [command]\n\nOptions:\n  -h, --help      display help for command\n\nCommands:\n  query           run a query against all datatypes\n  help [command]  display help for command",'')
	else:
		return returns

def pull_brainlife(bl_command,identifyer_key=''):

	bl_pull = json.loads(check_for_command_usage(subprocess.run(bl_command+" '"+identifyer_key+"' -j --limit 1000000",stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True).stdout.decode('utf-8')))

	if len(bl_pull) == 1:
		bl_pull = bl_pull[0]

	return bl_pull


def build_dictionary(dictionary,subset_list=''):

	dictionary = dict(zip([ f['name'] for f in dictionary ],[ f['_id'] for f in dictionary ]))

	if not subset_list:
		return dictionary
	else:
		return {k: v for k,v in dictionary.items() if k in subset_list}


def identify_number_datatypes(projects,datatypes):

	df = pd.DataFrame()

	# generate list of names and ids
	project_names = list(projects.keys())
	project_ids = list(projects.values())
	datatypes_names = list(datatypes.keys())
	datatypes_ids = list(datatypes.values())

	for i in range(len(projects)):
		tmp = pd.DataFrame()
		tmp_dictionary = pull_brainlife("bl project query -i",project_ids[i])
		ids, counts, size = map(list,zip(*[ [f['type'],f['count'],f['size']] for f in tmp_dictionary['stats']['datasets']['datatypes_detail'] if f['type'] in datatypes_ids ]))
		missing_ids = list(set(datatypes_ids).difference(ids))
		ids = ids + missing_ids
		counts = counts + [ 0 for f in range(len(missing_ids)) ]
		size = size + [ 0 for f in range(len(missing_ids)) ]
		tmp['project'] = [ project_names[i] for f in range(len(datatypes_ids)) ]
		tmp['project_id'] = [ project_ids[i] for f in range(len(datatypes_ids)) ]
		#tmp['datatype'] = datatypes_names
		tmp['datatype'] = [ datatypes_names[datatypes_ids.index(f)] for f in ids ]
		tmp['datatype_id'] = ids
		tmp['datatype_count'] = counts
		tmp['datatype_memory'] = size
		
		df = pd.concat([df,tmp])

	return df

def main(config_path):

	# load config
	with open(config_path,'r') as config_f:
		config = json.load(config_f)

	# extract important variables
	important_dataypes = config['important_datatypes']
	important_projects = config['important_projects']
	outpath = config['outpath']

	# build dictionary of important datatypes and projects. first, pull brainlife for datatypes and projects information. then build dictionary of important datatypes and important projects
	projects_dictionary = build_dictionary(pull_brainlife("bl project query -q"),important_projects)
	datatypes_dictionary = build_dictionary(pull_brainlife("bl datatype query -q"),important_datatypes)

	# loop through projects, identify counts of all datatypes within project, return table
	projects_datatypes_counts_df = identify_number_datatypes(projects_dictionary,datatypes_dictionary)

	# save dataframe
	projects_datatypes_counts_df.to_csv(outpath+'/projects_datatypes_counts.csv',index=False)


if __name__ == '__main__':
	
    parser = argparse.ArgumentParser(description='Generate the number and size of data objects within each project and datatypes of interest')
    parser.add_argument('--config_path', metavar='path', required=True,
                        help='the path to config.json containing the appropriate information')
    args = parser.parse_args()
    main(config_path=args.config_path)



# important_datatypes = ['neuro/freesurfer','neuro/parc-stats','neuro/parcellation/volume','neuro/parcellation/surface','neuro/cortexmap',
# 'neuro/wmc','neuro/conmat','generic/network','neuro/mask','neuro/csd','neuro/tensor','neuro/noddi','neuro/track/tck','neuro/tractmeasures',
# 'neuro/meeg/mne/epochs','neuro/meeg/psd','neuro/surface/gradient']

# important_projects = ['Human Connectome Young Adult - Test-Retest Dataset','Cambridge Centre for Ageing and Neuroscience - Full Dataset',
# 'Human Connectome Young adult – Full Dataset','Pediatric Imaging, Neurocognition, and Genetics (PING) Dataset - SIEMENS only',
# 'Human Connectome Young Adult 3T Resting State fMRI - Retest dataset',
# 'Human Connectome Young Adults Test-Retest Data set - fMRI Gradients Experiments','MEG [fif] CamCan','MEG [fif] Run1 vs Run2',
# 'MEG [fif] CamCan - maxfilt','ASHS Segmentation of Hippocampal Subfields - Replication derivatives','IU Concussion Biobank',
# 'Inherited Retinal Disease','Glaucoma white matter microstructure','PVP-development','ABCD BL Replication Paper','Replicability of NN and LAP']
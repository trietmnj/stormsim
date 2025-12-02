import h5py
import re
import numpy as np

def summarize_attrs(obj):
    return {key: obj.attrs[key] for key in obj.attrs}

def inspect_group_members(group, indent="  "):
    for member_key in group.keys():
        member = group[member_key]
        print(f"{indent}Member: {member_key}")
        if isinstance(member, h5py.Dataset):
            print(f"{indent}  Dataset: {member.name}")
            print(f"{indent}    Shape: {member.shape}")
            print(f"{indent}    Dtype: {member.dtype}")
            print(f"{indent}    Attributes: {summarize_attrs(member)}")
        elif isinstance(member, h5py.Group):
            print(f"{indent}  Subgroup: {member.name}")
            inspect_group_members(member, indent + "    ")

def inspect_top_level_groups(file_path):
    with h5py.File(file_path, 'r') as f:
        keys = list(f.keys())

        # Filter: keep only one group, remove other groups
        group_keys = [k for k in keys if isinstance(f[k], h5py.Group)]
        dataset_keys = [k for k in keys if not isinstance(f[k], h5py.Group)]

        reduced_keys = dataset_keys + group_keys[:1]  # keep only first group

        for key in reduced_keys:
            obj = f[key]
            if isinstance(obj, h5py.Dataset):
                print(f"Top-level Dataset: {key}")
                print(f"  Shape: {obj.shape}")
                print(f"  Dtype: {obj.dtype}")
                print(f"  Attributes: {summarize_attrs(obj)}")
            elif isinstance(obj, h5py.Group):
                print(f"Top-level Group: {key}")
                inspect_group_members(obj)

def extract_ids(strings):
    return [
        int(re.search(r'Synthetic_(\d{4})', s).group(1))
        for s in strings
        if re.search(r'Synthetic_(\d{4})', s)
    ]

def build_dic(h5_file):
    # Create H5 Object
    fObj = h5py.File(h5_file, 'r')
    # Get HDF5 Groups
    Groups = list(fObj.keys())
    # Initialize Dictionary
    storm_data = {}
    # Append Data (Keys -> Storm IDs)
    for g in Groups:
        # Trim Storm ID Name 
        stm_id = extract_ids([g])
        # Initialize Dictionary entry
        storm_data[stm_id[0]] = {}  # Initialize sub-dictionary for each group
        for ds in fObj[g].keys():  # Get datasets per group dynamically
            ds_data = np.array(fObj[g][ds])
            storm_data[stm_id[0]][ds] = ds_data
    return storm_data

# Example Ways To interact With H5 
# What File To Read
Filein = "Andrew_River_Jetties\CHS-NA_TS_SimB1RT_Post0_SP0064_STWAVE04_Timeseries.h5"
# Create H5 Object
fObj = h5py.File(Filein, 'r')
# Get HDF5 Groups
Groups = list(fObj.keys()) # keys will list Datasets/Groups at Base Level
# Get HDF5 Datasets 
Datasets = list(fObj[Groups[0]].keys()) # This will list the keys inside each group
# Import CHS Data To Dicitonary
outDic = build_dic(Filein)
# Parse Out ID From Group Names
ids = extract_ids(Groups)
# Get Preview Of HDF5 Heirarchy
inspect_top_level_groups(Filein)

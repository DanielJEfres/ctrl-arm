

import tkinter as tk
from tkinter import filedialog
import os.path
from os.path import basename
import pandas as pd
import os
import shutil
root = tk.Tk()
root.withdraw()


def get_files(title='Select files.'):
    
    root = tk.Tk()
    files = list(filedialog.askopenfilenames(title=title))
    root.destroy()
    return files


def get_dir(title='Select directory.'):
    
    root = tk.Tk()
    found_dir = filedialog.askdirectory(title=title)
    found_dir = f"{found_dir}/"
    root.destroy()
    return found_dir


def copy_files(files_to_copy, dst=None):
    
    if not os.path.isdir(dst):
        dst = filedialog.askdirectory(
            title='Select directory to store copied files.')

    newnames = []
    for n, file in enumerate(files_to_copy):
        dst_file = f"{dst}/{basename(file)}"
        dst_file = dst_file.replace('//', '/')
        if not os.path.isfile(dst_file):
            try:
                shutil.copyfile(file, dst_file)
                newnames.append(dst_file)
                print(f"Copied {n+1} of {len(files_to_copy)}.")
            except:
                pass

    return newnames


def rename_file(full_filename, new_filename):
    os.rename(full_filename, new_filename)
    return print(new_filename)


def get_gesture_metadata(file, datatype='gesture'):
    
    metadata_dict = {}
    bn_split = basename(file).split('_')
    ext = file.split('.')[-1]

    if datatype == 'gesture':
        if ext == 'csv':
            metadata_dict['gesture_type'] = bn_split[0]
            metadata_dict['date'] = bn_split[1]
            metadata_dict['time'] = bn_split[2]
            metadata_dict['timestamp'] = f"{bn_split[1]}_{bn_split[2]}"
            metadata_dict['filename'] = basename(file)
            metadata_dict['filepath'] = file
    elif datatype == 'emg':
        metadata_dict['gesture_type'] = bn_split[0]
        metadata_dict['date'] = bn_split[1]
        metadata_dict['time'] = bn_split[2]
        metadata_dict['sensor_type'] = 'emg'
        metadata_dict['timestamp'] = f"{bn_split[1]}_{bn_split[2]}"
    elif datatype == 'imu':
        metadata_dict['gesture_type'] = bn_split[0]
        metadata_dict['date'] = bn_split[1]
        metadata_dict['time'] = bn_split[2]
        metadata_dict['sensor_type'] = 'imu'
        metadata_dict['timestamp'] = f"{bn_split[1]}_{bn_split[2]}"

    return metadata_dict


def search_folders(date_threshold=20000000, parent_folder_path=''):
    

    if not os.path.isdir(parent_folder_path):
        parent_folder_path = filedialog.askdirectory(
            title='Select source of data files to search through.')

    folders = []
    for dirpath, dirnames, filenames in os.walk(parent_folder_path):
        for dirname in dirnames:
            dirname = dirname.replace('-', '')
            try:
                if int(dirname) >= int(date_threshold):
                    new_folder = os.path.join(dirpath, dirname)
                    folders.append(new_folder)
                    print(f'{new_folder} added for processing.')
            except ValueError:
                print(f'{dirname} skipped.')
                pass
    return folders


def get_directory_names(source):
    
    directory_names = []
    for dirpath, dirnames, filenames in os.walk(source):
        for name in dirnames:
            directory_names.append(name)
            print(name)
    return directory_names


def search_gesture_files(gesture_types=None, data_path=''):
    

    if not gesture_types:
        gesture_types = ['rest', 'left_single', 'right_single', 'left_double', 'right_double',
                        'left_hold', 'right_hold', 'left_hard', 'right_hard', 'both_flex',
                        'left_then_right', 'right_then_left']

    if not os.path.isdir(data_path):
        data_path = filedialog.askdirectory(
            title='Select source of gesture data files to search through.')

    gesture_data_dict = {}
    
    for gesture_type in gesture_types:
        all_files = []
        print(f"Searching for {gesture_type} files.")

        for (dirpath, dirnames, filenames) in os.walk(data_path):
            [all_files.append(f"{dirpath}/{f}")
             for f in filenames if f.startswith(gesture_type) and f.endswith('.csv')]
            all_files = [a.replace('//', '/') for a in all_files]
            gesture_data_dict[gesture_type] = all_files

    return gesture_data_dict


def retrieve_gesture_data(gesture_type, data_path):
    
    files = []
    print(f"Searching for {gesture_type} files.")

    for (dirpath, dirnames, filenames) in os.walk(data_path):
        [files.append(f"{dirpath}/{f}")
         for f in filenames if f.startswith(gesture_type) and f.endswith('.csv')]
        files = [a.replace('//', '/') for a in files]
    
    return files


def copy_gesture_data_to_folder(gesture_data_dict=None, dst=None):
    
    if not dst:
        dst = filedialog.askdirectory(
            title='Select folder where files will be copied to.')

    for gesture_type in gesture_data_dict:
        dst_gesture_dir = f"{dst}/{gesture_type.upper()}/"
        dst_gesture_dir = dst_gesture_dir.replace('//', '/')
        if not os.path.isdir(dst_gesture_dir):
            os.mkdir(dst_gesture_dir)
        print(
            f"Begin copying {gesture_type} files: {len(gesture_data_dict[gesture_type])} found.")
        copy_files(gesture_data_dict[gesture_type], dst=dst_gesture_dir)
        print(
            f"Finished copying {len(gesture_data_dict[gesture_type])} {gesture_type.upper()} files.")


def search_and_copy_gesture_files(gesture_types=None, data_path='', dst=None):
    
    gesture_data_dict = search_gesture_files(gesture_types, data_path)
    copy_gesture_data_to_folder(gesture_data_dict, dst)


def get_files_in_directory(source_dir=None):
    
    if not source_dir:
        source_dir = get_dir(
            'Select source directory from which you want to load all files.')

    all_files = []
    for (dirpath, dirnames, filenames) in os.walk(source_dir):
        [all_files.append(f"{dirpath}/{f}") for f in filenames]
        all_files = [a.replace('//', '/') for a in all_files]

    return all_files


def get_latest_gesture_files(gesture_files):
    
    latest_files = []

    times = []
    gesture_types = []
    for f in gesture_files:
        bn_split = basename(f).split('_')
        gesture_type = bn_split[0]
        time_str = bn_split[2]
        times.append(time_str)
        gesture_types.append(gesture_type)

    gesture_info = pd.DataFrame({"files": gesture_files,
                                "gesture_type": gesture_types,
                                "times": times})

    for g in gesture_info.groupby('gesture_type'):
        latest_files.append(
            list(g[1].sort_values('times').reset_index().files)[-1])

    return latest_files


def label_gesture_file(filename_string, datatype='gesture',
                       order=['gesture_type', 'date', 'time']):
    
    metadata = get_gesture_metadata(filename_string, datatype=datatype)

    gesture_type = metadata['gesture_type']
    date = metadata['date']
    time = metadata['time']
    timestamp = metadata['timestamp']

    options = {'gesture_type': gesture_type, 'date': date, 'time': time,
               'timestamp': timestamp}

    label = "_".join([options[i] for i in order])
    return label, options

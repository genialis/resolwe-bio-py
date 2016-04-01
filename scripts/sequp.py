#!/usr/bin/env python
"""
Auto-upload NGS reads from directory to the Resolwe server.

Usage: ``python sequp.py [OPTIONS]``

Options:
*  -a, --address
    URL of the server where the reads should be uploaded. Default
    value is http://cloud.genialis.com
* -e, --email
    User e-mail to gain upload permission. Default is anonymous@genialis.com
* -p', '--password
    User password to gain upload permission. Default is 'anonymous'
* -d, --directory
    Observed directory with reads. Default is the user's home directory


The aim of the script is to run repeatedly (for example every hour).
Script checks if there are any new read or annotation files in the
specified directory or any of its subdirectories. If both: reads and
corresponding annotation files are present, upload the reads and set
the initial annotation based on the annotation file.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import appdirs
import argparse
import csv
import fnmatch
import os
import sys
import time

from os.path import expanduser

import resolwe_api


# The name of the confid direcotry, file and author where the
# modification timestamp of last uploaded file is stored.
# Also the TIMEOUT param is specified - this is used when checking
# if a file is already fully uploaded.
CONFIG_DIR = "resolwe-bio-py"
CONFIG_FILE = "resolwe_bio_py.config"
AUTHOR = "genialis"
TIMEOUT = 5
"""
TODO:
* Does this kind of naming makes sense?
* Should timeout be exposed as argument? What is the appropriate value for it?
"""

###########################################################

# Setting of the GENIALIS_* parameters. If provided, they are taken
# from the command line (argparse). If not, they are loaded from
# envoronment variables. If appropriate environment variables are not
# set, use the default values.

GENIALIS_URL = os.getenv('GENIALIS_URL') if 'GENIALIS_URL' in os.environ else 'http://cloud.genialis.com'
GENIALIS_EMAIL = os.getenv('GENIALIS_EMAIL') if 'GENIALIS_EMAIL' in os.environ else 'anonymous@genialis.com'
GENIALIS_PASS = os.getenv('GENIALIS_PASS') if 'GENIALIS_PASS' in os.environ else 'anonymous'
GENIALIS_SEQ_DIR = os.getenv('GENIALIS_SEQ_DIR') if 'GENIALIS_SEQ_DIR' in os.environ else expanduser("~")

parser = argparse.ArgumentParser(description='Auto-upload NGS reads from directory to the Resolwe server.')

parser.add_argument('-a', '--address', default=GENIALIS_URL, help='Resolwe server address')
parser.add_argument('-e', '--email', default=GENIALIS_EMAIL, help='User e-mail')
parser.add_argument('-p', '--password', default=GENIALIS_PASS, help='User password')
parser.add_argument('-d', '--directory', default=GENIALIS_SEQ_DIR, help='Observed directory with reads')
parser.add_argument('-f', '--force', action='store_true', help='Force upload of all files')

args = parser.parse_args()

GENIALIS_URL = args.address
GENIALIS_EMAIL = args.email
GENIALIS_PASS = args.password
GENIALIS_SEQ_DIR = os.path.normpath(os.path.join(os.getcwd(), args.directory))

print("Address:", GENIALIS_URL)
print("User:", GENIALIS_EMAIL)
print("Pass:", GENIALIS_PASS)
print("Directory:", GENIALIS_SEQ_DIR)

###########################################################

# We only want to upload files which have not been uploaded yet. So
# we need to know the most recent modification date of all uploaded
# files. Only files modiffied later will be candidates for upload.
# The timestamp of last modification time is stored in CONFIG_FILE
# in CONFIG_DIR in ``user_data_dir`` as specified by appdirs package.
# Multiple GENIALIS_SEQ_DIRs can be specified in the CONFIG_FILE.

TS_FILE = os.path.join(appdirs.user_data_dir(CONFIG_DIR, AUTHOR), CONFIG_FILE)

if args.force:
    if os.path.isfile(TS_FILE):
        os.remove(TS_FILE)
        

def get_timestamp():
    """Get the timestamp for GENIALIS_SEQ_DIR"""
    data = {}
    # if the file is present:
    if os.path.isfile(TS_FILE):
        with open(TS_FILE, "r") as f:
            for line in f:
                parts = line.strip().split("\t")
                data[parts[0]] = float(parts[1])
        if GENIALIS_SEQ_DIR in data:
            return data[GENIALIS_SEQ_DIR]
        else:
            # file is created but no entry fo this directory. Upload
            # all files: timestamp = 0
            return 0

    # File is not present, this must be the first iteration for the
    # script, upload all files: timestamp = 0
    else:
        return 0


def set_timestamp(timestamp):
    """Set timestamp for GENIALIS_SEQ_DIR"""
    
    def write_timestamp(pairs):
        """Write the timestamp into appropriate file"""
        with open(TS_FILE, "w") as f:
            for a, b in pairs.items():
                f.write(str(a) + "\t" + str(b) + "\n")

    # If file exists, rewrite the contents of GENIALIS_SEQ_DIR
    if os.path.isfile(TS_FILE):
        pairs = get_timestamp()
        pairs[GENIALIS_SEQ_DIR] = timestamp
        write_timestamp(pairs)

    # If file does not exist, create file and put in the data
    else:
        try:
            os.makedirs(os.path.dirname(TS_FILE))
            write_timestamp({GENIALIS_SEQ_DIR: timestamp})
        except OSError:
            # Folder already exists, just make the file:
            write_timestamp({GENIALIS_SEQ_DIR: timestamp})


# Get the timestamp:
timestamp = get_timestamp()
"""
TODO:
* Saving the CONFIG_FILE in ``user_data_dir`` is probably not the right
decision, right? We want multiple users should be able to upload data
to the same directory - therefore the CONFIG_FILE should be systemic and
not user-dependant as is the directory defined by ``user_data_dir`` ?

Maybe Tadej can provide some more wisdom into this...
"""

###########################################################

# Now we have GENIALIS_SEQ_DIR and timestampariable and we know the timestamp for this directory

all_new_read_files = []
read_file_extensions = ['*.fastq', '*.fq']

for root, dirnames, filenames in os.walk(GENIALIS_SEQ_DIR):
    for extension in read_file_extensions:
        for filename in fnmatch.filter(filenames, extension):
            f = os.path.join(root, filename)
            if os.path.getmtime(f) > timestamp:
                all_new_read_files.append(f)


# We end up with all read files to condier, saved into
# ``ll_new_read_files`` list

###########################################################

# Determnine if the candidate files are fully uploaded. The idea is to
# get the file sizes and wait for TIMEOUT secosnds. If file size stays
# the same, then it is fully uplodaed:

sizes1 = {f: os.path.getsize(f) for f in all_new_read_files}
time.sleep(TIMEOUT)
sizes2 = {f: os.path.getsize(f) for f in all_new_read_files}


all_new_read_files_uploaded = [f for f in all_new_read_files if sizes1[f] == sizes2[f]]

###########################################################

# Find all annotaten files:

all_annotation_files = []
annotation_file_extensions = ['*.csv', '*.txt', '*.tsv']
for root, dirnames, filenames in os.walk(GENIALIS_SEQ_DIR):
    for extension in annotation_file_extensions:
        for filename in fnmatch.filter(filenames, extension):
            all_annotation_files.append(os.path.join(root, filename))


def parse_annotation_file(annotation_file):
    """Parse data from annotation file into list od annotation objects

    Annotations for multiple files can be found in one annotation file.
    """
    anns = {}
    # We use "rU" mode to be able to read also files with "\r" chars.
    with open(annotation_file, "rU") as f:
        try:
            reader = csv.DictReader(f, delimiter=str('\t'))
            fieldnames = reader.fieldnames
            
            # One line corresponds to one annotation (one reads file)
            for row in reader:
                if 'FASTQ_PATH' in row:
                    seqfile = os.path.normpath(os.path.join(GENIALIS_SEQ_DIR, row['FASTQ_PATH']))
                    
                    if os.path.isfile(seqfile):
                        row['FASTQ_PATH'] = seqfile
                        anns[seqfile] = row
                 
        # If the file is binary, everything crashes... This can be optimized. :-)
        except csv.Error:
            print("Binary files not supported", file=sys.stderr)
            exit(1)
    return anns


# Write all annotations in a single dictionary with reads filenames as the keys:
annotations = {}
for ann_file in all_annotation_files:
    annotations.update(parse_annotation_file(ann_file))

###########################################################

# Upload the data

# Get the connection with the server:
re = resolwe_api.Resolwe(GENIALIS_EMAIL, GENIALIS_PASS, GENIALIS_URL)

# process_name = 'import:upload:reads-fastq'
process_name = 'Upload NGS reads'

# Upload all files in ``all_new_read_files_uploaded`` that have annotations.
uploaded_files = []
for fn in set(set(annotations.keys()) & set(all_new_read_files_uploaded)):
    kwargs = {
        'process_name': process_name,
        'name': annotations[fn]['SAMPLE_NAME'],  
        'src': fn,
    }
    
    # Single and reads:
    if annotations[fn]["PAIRED_END"] != "Y":
        kwargs['src'] = fn
    # Paired and reads:
    else:
        kwargs['src1'] = fn 
        kwargs['src2'] = annotations[fn]["FASTQ_PATH_PAIR"]
       
    response = re.upload(**kwargs)
    
    if response.ok:
        uploaded_files.append(fn)
    else:
        print("Error uploading {}".format(fn), file=sys.stderr)
        print(response.text, file=sys.stderr)


###########################################################
# Finally set the modification timestamp:

modif_times = [os.path.getmtime(f) for f in uploaded_files]
if len(modif_times) > 0:
    set_timestamp(sorted(modif_times)[-1])

#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals
import sys
import argparse
import json

import resolwe_api

email = 'admin'
passw = 'admin'
url = 'http://127.0.0.1:8000/'

re = resolwe_api.Resolwe(email, passw, url)

# cid = 1
# cid = "slug1"
# r = re.collection_data(cid)
# print(len(r))
# print(r[-1].print_annotation())
# print(r[-1].print_downloads())

# TODO:
# collection_data(self, collection)
# data(self, **query)
# rundata(self, strjson)
# create(self, data, resource='data') - for all types of resource not just "data"
# download(self, data_objects, field)



# WORKS, yay!:
##############
# c = re.collections()
# print(c)
#
# p1 = re.processes()
# print(len(p1))
#
# p2 = re.processes('Upload genome')
# print(len(p2))
#
# re.print_upload_processes()
#
# re.print_process_inputs('Upload genome')
#
# r = re._upload_file('/home/jure/genialis/resolwe_bio_py/fastqs/20151231-shep21-0hr-twist-RZ2638_S4_R1_001.fastq')
# print(r)
#
cid = 6
process_name = 'Upload NGS reads'
fname = '/home/jure/genialis/resolwe_bio_py/fastqs/20151231-shep21-0hr-twist-RZ2638_S4_R1_001.fastq'
response = re.upload(process_name, collections=[cid], src=fname)
print("-" * 30)
print(response.content)
print("-" * 30)
print(response.raw)
print("-" * 30)
print(response.reason)

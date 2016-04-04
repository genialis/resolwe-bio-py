#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals
import argparse
import resolwe_bio

parser = argparse.ArgumentParser(description='Upload NGS reads to the Resolwe server.')

parser.add_argument('collection', help='Collection ID')
parser.add_argument('-a', '--address', default='http://cloud.genialis.com', help='Resolwe server address')
parser.add_argument('-e', '--email', default='anonymous@genialis.com', help='User e-mail')
parser.add_argument('-p', '--password', default='anonymous', help='User password')
parser.add_argument('-r', metavar='READS', help='NGS fastq file')
parser.add_argument('-r1', metavar='READS-1', help='NGS fastq file (mate 1)')
parser.add_argument('-r2', metavar='READS-2', help='NGS fastq file (mate 2)')

args = parser.parse_args()

if not (args.r or (args.r1 and args.r2)) or \
    (args.r and (args.r1 or args.r2)):
    parser.print_help()
    print
    print "ERROR: define either -r or -r1 and -r2."
    print
    exit(1)

re = resolwe_bio.Resolwe(args.email, args.password, args.address)

if args.r:
    r = re.upload(process_name='import:upload:reads-fastq', collections=[args.collection], src=args.r)
else:
    r = re.upload(process_name='import:upload:reads-fastq-paired-end', collections=[args.collection], src1=args.r1, src2=args.r2)

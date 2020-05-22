#!/bin/env python
# -*- mode: python; coding: utf-8 -*
# Copyright (c) 2020 Radio Astronomy Software Group
# Licensed under the 3-clause BSD License

import requests
import os
import argparse

# The google drive ID for the folder containing these files:
# 14hH-zBhHGddVacc0ncqRWq7ofhGLWfND


parser = argparse.ArgumentParser(
    description="A script to download the latest archived reference simulation data."
)
parser.add_argument('generation', type=int, help="Generation of reference "
                                                 "sims to download (1 or 2).", default=1)

args = parser.parse_args()

if args.generation not in [1, 2]:
    raise ValueError(f"Invalid generation: {args.generation}")

version = f"v{args.generation}"

target_dir = os.path.join('latest_ref_data', version)

if not os.path.exists(target_dir):
    os.makedirs(target_dir)

urlbase = 'https://drive.google.com/uc?export=download'

fileids = 'gdrive_file_ids.dat'

dat = []

with open(fileids, 'r') as dfile:
    for line in dfile:
        line = line.strip()
        # fileid name type size size_unit date time
        dat.append(line.split())
        d = line.split()
        fname = d[1]
        if args.generation == 1:
            if 'ref_2.' in fname:
                continue
        elif args.generation == 2:
            if 'ref_1.' in fname:
                continue
        fid = d[0]
        r = requests.get(urlbase, params={'id': fid})
        print(fname)
        fname = os.path.join(target_dir, fname)
        with open(fname, 'wb') as ofile:
            ofile.write(r.content)

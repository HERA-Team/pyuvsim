#!/usr/bin/env python
# -*- mode: python; coding: utf-8 -*
# Copyright (c) 2018 Radio Astronomy Software Group
# Licensed under the 3-clause BSD License

from __future__ import absolute_import, division, print_function

import pyuvsim
import argparse
import numpy as np
import yaml
import os
from pyuvdata import UVBeam, UVData
from pyuvdata.data import DATA_PATH
from pyuvsim.data import DATA_PATH as SIM_DATA_PATH
from pyuvsim import simsetup
from astropy.coordinates import EarthLocation
from pyuvsim import mpi

parser = argparse.ArgumentParser(description=("A command-line script "
                                              "to execute a pyuvsim simulation for profiling purposes."))

paramsfile = os.path.join(SIM_DATA_PATH, 'profiling_params.yaml')
cst_files = ['HERA_NicCST_150MHz.txt', 'HERA_NicCST_123MHz.txt']
beam_files = [os.path.join(DATA_PATH, f) for f in cst_files]

parser.add_argument('--Nsrcs', dest='Nsrcs', type=int, default=1)
parser.add_argument('--Ntimes', dest='Ntimes', type=int, default=1)
parser.add_argument('--Nfreqs', dest='Nfreqs', type=int, default=1)
parser.add_argument('--Nbls', dest='Nbls', type=int, default=1)
parser.add_argument('--beam', dest='beam', type=str, default='uniform')

args = parser.parse_args()

with open(paramsfile, 'r') as pfile:
    params = yaml.safe_load(pfile)

params['config_path'] = os.path.dirname(paramsfile)

min_alt = 70  # Degrees

mpi.start_mpi()
rank = mpi.get_rank()

beam_list = None
beam_dict = None
input_uv = UVData()
mock_keywords = None
catalog = 'mock'
if rank == 0:

    params['freq']['Nfreqs'] = args.Nfreqs
    params['time']['Ntimes'] = args.Ntimes

    input_uv, beam_list, beam_dict, beam_ids = simsetup.initialize_uvdata_from_params(params)

    # Baseline selection:
    input_uv.baseline_array = np.repeat(input_uv.baseline_array[:args.Nbls], args.Ntimes)
    input_uv.ant_1_array, input_uv.ant_2_array = input_uv.baseline_to_antnums(input_uv.baseline_array)
    ants_new = np.unique(input_uv.ant_1_array.tolist() + input_uv.ant_2_array.tolist())
    input_uv.antenna_numbers = ants_new
    input_uv.antenna_names = ants_new.astype(str)  # Antnames/numbers are going to be messed up by the baseline selection. Unimportant.
    Nants = ants_new.size
    beam_dict = dict(zip(input_uv.antenna_names, np.zeros(Nants, dtype=int)))  # For now, all use the same beam model
    input_uv.antenna_positions = input_uv.antenna_positions[:Nants, :]
    input_uv.Nants_data = Nants
    input_uv.Nants_telescope = Nants

    # Time selection:
    inds = np.array([np.arange(args.Nbls) + i * input_uv.Nbls for i in range(args.Ntimes)]).flatten()
    input_uv.time_array = input_uv.time_array[inds]
    input_uv.Nbls = args.Nbls
    input_uv.Nblts = args.Nbls * args.Ntimes

    # Beam selection:
    # Default is uniform
    if args.beam == 'hera':
        beam = UVBeam()
        beam.read_cst_beam(beam_files, beam_type='efield', frequency=[150e6, 123e6],
                           telescope_name='HERA',
                           feed_name='PAPER', feed_version='0.1', feed_pol=['x'],
                           model_name='E-field pattern - Rigging height 4.9m',
                           model_version='1.0')
        beamfile = 'temp_hera_beam.uvbeam'
        if not os.path.exists(beamfile):
            beam.write_beamfits(beamfile)
        beam_list = [beamfile]

    mock_keywords = {'arrangement': 'random', 'Nsrcs': args.Nsrcs, 'min_alt': min_alt}

uvdata_out = pyuvsim.uvsim.run_uvsim(input_uv, beam_list=beam_list, beam_dict=beam_dict, catalog_file=catalog, mock_keywords=mock_keywords)

# -*- mode: python; coding: utf-8 -*
# Copyright (c) 2019 Radio Astronomy Software Group
# Licensed under the 3-clause BSD License

"""Testing environment setup and teardown for pytest."""
import os
import shutil
import warnings

import pytest
from astropy.time import Time
from astropy.utils import iers
from astropy.coordinates import EarthLocation
from pyuvdata import UVBeam
from pyuvdata.data import DATA_PATH

from pyuvsim.data import DATA_PATH as SIM_DATA_PATH


@pytest.fixture(autouse=True, scope="session")
def setup_and_teardown_package():
    """Make data/test directory to put test output files in."""
    testdir = os.path.join(SIM_DATA_PATH, 'temporary_test_data/')
    if not os.path.exists(testdir):
        os.mkdir(testdir)

    # Do a calculation that requires a current IERS table. This will trigger
    # automatic downloading of the IERS table if needed, including trying the
    # mirror site in python 3 (but won't redownload if a current one exists).
    # If there's not a current IERS table and it can't be downloaded, turn off
    # auto downloading for the tests and turn it back on once all tests are
    # completed (done by extending auto_max_age).
    try:
        t1 = Time.now()
        t1.ut1
    except (Exception):
        iers.conf.auto_max_age = None

    # yield to allow tests to run
    yield

    iers.conf.auto_max_age = 30

    # clean up the test directory after
    if os.path.exists(testdir):
        shutil.rmtree(testdir)


@pytest.fixture(autouse=True)
def ignore_deprecation():
    warnings.filterwarnings('ignore', message='Achromatic gaussian beams will not be supported',
                            category=PendingDeprecationWarning)
    warnings.filterwarnings('ignore', message='"initialize_catalog_from_params will not return'
                                              ' recarray by default in the future.',
                            category=PendingDeprecationWarning)


@pytest.fixture(scope='session')
def cst_beam():
    beam = UVBeam()
    beam.freq_interp_kind = 'linear'

    freqs = [150e6, 123e6]

    cst_files = ['HERA_NicCST_150MHz.txt', 'HERA_NicCST_123MHz.txt']
    beam_files = [os.path.join(DATA_PATH, 'NicCSTbeams', f) for f in cst_files]
    beam.read_cst_beam(
        beam_files, beam_type='efield', frequency=freqs,
        telescope_name='HERA', feed_name='PAPER', feed_version='0.1', feed_pol=['x'],
        model_name='E-field pattern - Rigging height 4.9m', model_version='1.0'
    )
    beam.peak_normalize()
    return beam


@pytest.fixture(scope='session')
def hera_loc():
    return EarthLocation(lat='-30d43m17.5s', lon='21d25m41.9s', height=1073.)

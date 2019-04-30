# -*- mode: python; coding: utf-8 -*
# Copyright (c) 2018 Radio Astronomy Software Group
# Licensed under the 3-clause BSD License

from __future__ import absolute_import, division, print_function

import numpy as np
import os
import yaml
import shutil
import copy
from six.moves import map, range, zip
import six
import nose.tools as nt
import astropy
from astropy.time import Time
from astropy.coordinates import Angle, SkyCoord, EarthLocation
from astropy import units

from pyuvdata import UVBeam, UVData
import pyuvdata.tests as uvtest

import pyuvsim
import pyuvsim.tests as simtest
from pyuvsim.data import DATA_PATH as SIM_DATA_PATH
import pyuvsim.tests as simtest

herabeam_default = os.path.join(SIM_DATA_PATH, 'HERA_NicCST.uvbeam')

# Five different test configs
param_filenames = [os.path.join(SIM_DATA_PATH, 'test_config', 'param_10time_10chan_{}.yaml'.format(x)) for x in range(6)]

longbl_uvfits_file = os.path.join(SIM_DATA_PATH, '5km_triangle_1time_1chan.uvfits')
triangle_uvfits_file = os.path.join(SIM_DATA_PATH, '28m_triangle_10time_10chan.uvfits')
GLEAM_vot = os.path.join(SIM_DATA_PATH, 'gleam_50srcs.vot')
manytimes_config = os.path.join(SIM_DATA_PATH, 'test_config', 'param_100times_1.5days_triangle.yaml')
gleam_param_file = os.path.join(SIM_DATA_PATH, 'test_config', 'param_1time_1src_testgleam.yaml')


def test_mock_catalog_zenith_source():

    time = Time(2457458.65410, scale='utc', format='jd')

    array_location = EarthLocation(lat='-30d43m17.5s', lon='21d25m41.9s',
                                   height=1073.)
    freq = (150e6 * units.Hz)

    source_coord = SkyCoord(alt=Angle(90 * units.deg), az=Angle(0 * units.deg),
                            obstime=time, frame='altaz', location=array_location)
    icrs_coord = source_coord.transform_to('icrs')

    ra = icrs_coord.ra
    dec = icrs_coord.dec

    test_source = pyuvsim.SkyModel('src0', ra, dec, freq, [1, 0, 0, 0])

    cat, mock_keywords = pyuvsim.create_mock_catalog(time, arrangement='zenith')
    cat_source = cat[0]

    nt.assert_equal(cat_source, test_source)


def test_mock_catalog_off_zenith_source():

    src_az = Angle('90.0d')
    src_alt = Angle('85.0d')

    time = Time(2457458.65410, scale='utc', format='jd')

    array_location = EarthLocation(lat='-30d43m17.5s', lon='21d25m41.9s',
                                   height=1073.)
    freq = (150e6 * units.Hz)

    source_coord = SkyCoord(alt=src_alt, az=src_az,
                            obstime=time, frame='altaz', location=array_location)
    icrs_coord = source_coord.transform_to('icrs')

    ra = icrs_coord.ra
    dec = icrs_coord.dec
    test_source = pyuvsim.SkyModel('src0', ra, dec, freq, [1.0, 0, 0, 0])

    cat, mock_keywords = pyuvsim.create_mock_catalog(time, arrangement='off-zenith', alt=src_alt.deg)
    cat_source = cat[0]

    nt.assert_equal(cat_source, test_source)


def test_catalog_from_params():
    # Pass in parameter dictionary as dict
    hera_uv = UVData()
    uvtest.checkWarnings(hera_uv.read_uvfits, [triangle_uvfits_file],
                         message='Telescope 28m_triangle_10time_10chan.yaml is not in known_telescopes.')

    source_dict = {}

    simtest.assert_raises_message(KeyError, 'No catalog defined.', pyuvsim.simsetup.initialize_catalog_from_params, {'sources': source_dict})
    arrloc = '{:.5f},{:.5f},{:.5f}'.format(*hera_uv.telescope_location_lat_lon_alt_degrees)
    source_dict = {'catalog': 'mock', 'mock_arrangement': 'zenith', 'Nsrcs': 5, 'time': hera_uv.time_array[0]}
    uvtest.checkWarnings(pyuvsim.simsetup.initialize_catalog_from_params, [{'sources': source_dict}],
                         message="No array_location specified. Defaulting to the HERA site.")
    catalog_uv, srclistname = pyuvsim.simsetup.initialize_catalog_from_params({'sources': source_dict}, hera_uv)
    catalog_uv = pyuvsim.simsetup.array_to_skymodel(catalog_uv)
    source_dict['array_location'] = arrloc
    del source_dict['time']

    simtest.assert_raises_message(TypeError, 'input_uv must be UVData object', pyuvsim.simsetup.initialize_catalog_from_params, {'sources': source_dict}, input_uv='not_uvdata')
    simtest.assert_raises_message(ValueError, 'input_uv must be supplied if using mock catalog without specified julian date',
                                  pyuvsim.simsetup.initialize_catalog_from_params, {'sources': source_dict})
    catalog_str, srclistname2 = uvtest.checkWarnings(pyuvsim.simsetup.initialize_catalog_from_params, [{'sources': source_dict}, hera_uv],
                                                     message="Warning: No julian date given for mock catalog. Defaulting to first time step.")

    nt.assert_true(np.all(catalog_str == catalog_uv))


def test_flux_cuts():
    # Check that min/max flux limits in test params work.

    gleam_path = os.path.join(SIM_DATA_PATH, 'test_config', '..', 'gleam_50srcs.vot')
    catalog, srclistname = uvtest.checkWarnings(pyuvsim.simsetup.initialize_catalog_from_params, [gleam_param_file],
                                                message=gleam_path, nwarnings=11,
                                                category=[astropy.io.votable.exceptions.W27]
                                                + [astropy.io.votable.exceptions.W50] * 10)
    catalog = pyuvsim.simsetup.array_to_skymodel(catalog)
    for sI in catalog.stokes[0,:]:
        nt.assert_true(np.all(0.2 < sI < 1.5))


def check_param_reader(config_num):
    """
        Part of test_param_reader
    """

    param_filename = param_filenames[config_num]
    hera_uv = UVData()
    uvtest.checkWarnings(hera_uv.read_uvfits, [triangle_uvfits_file],
                         message='Telescope 28m_triangle_10time_10chan.yaml is not in known_telescopes.')
    hera_uv.telescope_name = 'HERA'
    if config_num == 5:
        hera_uv.select(bls=[(0, 1), (1, 2)])

    time = Time(hera_uv.time_array[0], scale='utc', format='jd')
    sources, _ = pyuvsim.create_mock_catalog(time, arrangement='zenith')

    beam0 = UVBeam()
    beam0.read_beamfits(herabeam_default)
    beam1 = pyuvsim.AnalyticBeam('uniform')
    beam2 = pyuvsim.AnalyticBeam('gaussian', sigma=0.02)
    beam3 = pyuvsim.AnalyticBeam('airy', diameter=14.6)
    beam_list = [beam0, beam1, beam2, beam3]

    beam_dict = {'ANT1': 0, 'ANT2': 1, 'ANT3': 2, 'ANT4': 3}
    Ntasks = hera_uv.Nblts * hera_uv.Nfreqs * len(sources)
    taskiter = pyuvsim.uvdata_to_task_iter(range(Ntasks), hera_uv, sources,
                                           beam_list, beam_dict=beam_dict)
    expected_uvtask_list = uvtest.checkWarnings(list, [taskiter],
                                                message='The default for the `center` keyword has changed',
                                                category=DeprecationWarning)

    # Check error conditions:
    if config_num == 0:
        params_bad = pyuvsim.simsetup._config_str_to_dict(param_filename)
        bak_params_bad = copy.deepcopy(params_bad)

        # Missing config file info
        params_bad['config_path'] = os.path.join(SIM_DATA_PATH, 'nonexistent_directory', 'nonexistent_file')
        simtest.assert_raises_message(ValueError, 'nonexistent_directory is not a directory', pyuvsim.initialize_uvdata_from_params, params_bad)

        params_bad['config_path'] = os.path.join(SIM_DATA_PATH, "test_config")
        params_bad['telescope']['array_layout'] = 'nonexistent_file'
        simtest.assert_raises_message(ValueError, 'nonexistent_file from yaml does not exist', pyuvsim.initialize_uvdata_from_params, params_bad)

        params_bad['telescope']['telescope_config_name'] = 'nonexistent_file'
        simtest.assert_raises_message(ValueError, 'telescope_config_name file from yaml does not exist', pyuvsim.initialize_uvdata_from_params, params_bad)

        # Missing beam keywords
        params_bad = copy.deepcopy(bak_params_bad)

        params_bad['config_path'] = os.path.join(SIM_DATA_PATH, "test_config")

        params_bad = copy.deepcopy(bak_params_bad)
        params_bad['telescope']['telescope_config_name'] = os.path.join(SIM_DATA_PATH, 'test_config', '28m_triangle_10time_10chan_gaussnoshape.yaml')
        simtest.assert_raises_message(KeyError, 'Missing shape parameter for gaussian beam (diameter or sigma).',
                                      pyuvsim.initialize_uvdata_from_params, params_bad)
        params_bad['telescope']['telescope_config_name'] = os.path.join(SIM_DATA_PATH, 'test_config', '28m_triangle_10time_10chan_nodiameter.yaml')
        simtest.assert_raises_message(KeyError, 'Missing diameter for airy beam.',
                                      pyuvsim.initialize_uvdata_from_params, params_bad)
        params_bad['telescope']['telescope_config_name'] = os.path.join(SIM_DATA_PATH, 'test_config', '28m_triangle_10time_10chan_nofile.yaml')
        simtest.assert_raises_message(OSError, 'Could not find file',
                                      pyuvsim.initialize_uvdata_from_params, params_bad)

    # Check default configuration
    uv_obj, new_beam_list, new_beam_dict = pyuvsim.initialize_uvdata_from_params(param_filename)
    for i, bm in enumerate(new_beam_list):
        new_beam_list[i] = pyuvsim.simsetup.beam_string_to_object(bm)
    # write_uvdata tests with different configs:
    with open(param_filename, 'r') as fhandle:
        param_dict = yaml.safe_load(fhandle)
    expected_ofilepath = pyuvsim.utils.write_uvdata(uv_obj, param_dict, return_filename=True, dryrun=True)
    ofilename = 'sim_results.uvfits'
    if config_num == 1:
        if os.path.isdir('tempdir'):
            os.rmdir('tempdir')
        ofilename = os.path.join('.', 'tempdir', ofilename)
    else:
        ofilename = os.path.join('.', ofilename)
    print(ofilename, expected_ofilepath)
    nt.assert_equal(ofilename, expected_ofilepath)

    Ntasks = uv_obj.Nblts * uv_obj.Nfreqs * len(sources)
    taskiter = pyuvsim.uvdata_to_task_iter(range(Ntasks), uv_obj, sources,
                                           beam_list, beam_dict=beam_dict)
    uvtask_list = uvtest.checkWarnings(list, [taskiter],
                                       message='The default for the `center` keyword has changed',
                                       category=DeprecationWarning)

    # Tasks are not ordered in UVTask lists, so need to sort them.
    uvtask_list = sorted(uvtask_list)
    expected_uvtask_list = sorted(expected_uvtask_list)
    nt.assert_true(uvtask_list == expected_uvtask_list)

# This loops through different config files and tests all of them the same way
# note that each config tested shows up as a separate '.' in the nosetests output

def test_param_reader():
    """
    Tests initialize_uvdata_from_params for six different parameter files.
        Each file has a different arrangement of parameters that should yield the same uvdata object, so this
        checks that the various configurations all work consistently, and that if insufficient information is
        provided that the function errors appropriately.
    """
    for n in [0]:
        yield (check_param_reader, n)


def test_tele_parser():
    """
    Check a variety of cases not already tested by param reader
    """
    # check no tele config passed
    tdict = dict(array_layout=os.path.join(SIM_DATA_PATH, 'test_layout_6ant.csv'))
    tel_error = 'If telescope_config_name not provided in `telescope` obsparam section, you must provide telescope_location'
    simtest.assert_raises_message(KeyError, tel_error, pyuvsim.simsetup.parse_telescope_params, tdict)
    tdict['telescope_location'] = '(-30.72152777777791, 21.428305555555557, 1073.0000000093132)'
    tel_error = 'If telescope_config_name not provided in `telescope` obsparam section, you must provide telescope_name'
    simtest.assert_raises_message(KeyError, tel_error, pyuvsim.simsetup.parse_telescope_params, tdict)

    tdict['telescope_name'] = 'tele'
    tpars, blist, bdict = pyuvsim.simsetup.parse_telescope_params(tdict)
    nt.assert_equal(tpars['Nants_data'], 6)
    nt.assert_equal(blist, [])
    nt.assert_equal(bdict, {})

    tdict.pop('array_layout')
    simtest.assert_raises_message(KeyError, 'array_layout must be provided.', pyuvsim.simsetup.parse_telescope_params, tdict)


def test_freq_parser():
    """
    Check a variety of cases for the frequency parser.
    """

    fdict_base = dict(
        Nfreqs=10,
        channel_width=0.5,
        start_freq=0.0,
        end_freq=4.5,
        bandwidth=5.0)

    freq_array = np.linspace(fdict_base['start_freq'],
                             fdict_base['start_freq'] + fdict_base['bandwidth'] - fdict_base['channel_width'],
                             fdict_base['Nfreqs'], endpoint=True)

    fdict_base['freq_array'] = freq_array

    # As long as one tuple from each set is represented,
    # the param parser should work.

    bpass_kwd_combos = [('start_freq', 'end_freq'),
                        ('channel_width', 'Nfreqs'),
                        ('bandwidth',)]
    chwid_kwd_combos = [('bandwidth', 'Nfreqs'),
                        ('channel_width',)]
    ref_freq_combos = [('start_freq',),
                       ('end_freq',)]

    for bpass in bpass_kwd_combos:
        for chwid in chwid_kwd_combos:
            for ref in ref_freq_combos:
                keys = tuple(set(bpass + chwid + (ref)))  # Get unique keys
                subdict = {key: fdict_base[key] for key in keys}
                test = pyuvsim.parse_frequency_params(subdict)
                nt.assert_true(np.allclose(test['freq_array'][0], freq_array))

    # Now check error cases
    err_cases = [('bandwidth',),
                 ('start_freq', 'Nfreqs'),
                 ('start_freq', 'channel_width'),
                 ('start_freq', 'end_freq')]
    err_mess = ['Either start or end frequency must be specified: bandwidth',
                'Either bandwidth or channel width must be specified: Nfreqs, start_freq',
                'Either bandwidth or band edges must be specified: channel_width, start_freq',
                'Either channel_width or Nfreqs  must be included in parameters:end_freq, start_freq']
    for ei, er in enumerate(err_cases):
        subdict = {key: fdict_base[key] for key in er}
        simtest.assert_raises_message(ValueError, err_mess[ei], pyuvsim.parse_frequency_params, subdict)

    subdict = {'freq_array': freq_array[0]}
    simtest.assert_raises_message(ValueError, 'Channel width must be specified if freq_arr has length 1', pyuvsim.parse_frequency_params, subdict)

    subdict = {'freq_array': np.random.choice(freq_array, 4, replace=False)}
    simtest.assert_raises_message(ValueError, 'Spacing in frequency array is uneven.', pyuvsim.parse_frequency_params, subdict)

    subdict = {'channel_width': 3.14, 'start_freq': 1.0, 'end_freq': 8.3}
    simtest.assert_raises_message(ValueError, 'end_freq - start_freq must be evenly divisible by channel_width', pyuvsim.parse_frequency_params, subdict)

    subdict = fdict_base.copy()
    subdict['Nfreqs'] = 7
    del subdict['freq_array']
    simtest.assert_raises_message(ValueError, 'Frequency array spacings are not equal to channel width.',
                                  pyuvsim.parse_frequency_params, subdict)


def test_time_parser():
    """
    Check a variety of cases for the time parser.
    """

    daysperhour = 1 / 24.
    dayspersec = 1 / (24 * 3600.)

    tdict_base = {'Ntimes': 24,
                  'duration_hours': 0.9999999962747097 / daysperhour,
                  'end_time': 2457458.9583333298,
                  'integration_time': 3599.999986588955,
                  'start_time': 2457458.0}

    inttime_days = tdict_base['integration_time'] * dayspersec
    time_array = np.linspace(tdict_base['start_time'] + inttime_days / 2.,
                             tdict_base['start_time'] + tdict_base['duration_hours'] * daysperhour - inttime_days / 2.,
                             tdict_base['Ntimes'], endpoint=True)

    tdict_base['time_array'] = time_array

    # As long as one tuple from each set is represented,
    # the param parser should work.

    bpass_kwd_combos = [('start_time', 'end_time'),
                        ('integration_time', 'Ntimes'),
                        ('duration_hours',)]
    chwid_kwd_combos = [('duration_hours', 'Ntimes'),
                        ('integration_time',)]
    ref_freq_combos = [('start_time',),
                       ('end_time',)]

    for bpass in bpass_kwd_combos:
        for chwid in chwid_kwd_combos:
            for ref in ref_freq_combos:
                keys = tuple(set(bpass + chwid + (ref)))  # Get unique keys
                subdict = {key: tdict_base[key] for key in keys}
                test = pyuvsim.parse_time_params(subdict)
                nt.assert_true(np.allclose(test['time_array'], time_array, atol=dayspersec))

    subdict = {'time_array': time_array}
    test = pyuvsim.parse_time_params(subdict)
    nt.assert_true(np.allclose(test['time_array'], time_array, atol=dayspersec))

    # Now check error cases
    err_cases = [('duration_hours',),
                 ('start_time', 'Ntimes'),
                 ('start_time', 'integration_time'),
                 ('start_time', 'end_time')]
    err_mess = ['Start or end time must be specified: duration_hours',
                'Either duration or integration time must be specified: Ntimes, start_time',
                'Either duration or time bounds must be specified: integration_time, start_time',
                'Either integration_time or Ntimes must be included in parameters: end_time, start_time']

    for ei, er in enumerate(err_cases):
        subdict = {key: tdict_base[key] for key in er}
        simtest.assert_raises_message(ValueError, err_mess[ei], pyuvsim.parse_time_params, subdict)

    subdict = {'integration_time': 3.14, 'start_time': 10000.0, 'end_time': 80000.3, 'Ntimes': 30}
    simtest.assert_raises_message(ValueError, 'Calculated time array is not consistent with set integration_time',
                                  pyuvsim.parse_time_params, subdict)

    subdict = tdict_base.copy()
    subdict['Ntimes'] = 7
    del subdict['time_array']
    simtest.assert_raises_message(ValueError, 'Calculated time array is not consistent with set integration_time.',
                                  pyuvsim.parse_time_params, subdict)


def test_freq_time_params():
    freqs = np.linspace(100, 200, 1024)
    times = np.linspace(2458570, 2458570 + 0.5, 239)
    time_dict = pyuvsim.simsetup.time_array_to_params(times)
    freq_dict = pyuvsim.simsetup.freq_array_to_params(freqs)
    ftest = pyuvsim.simsetup.parse_frequency_params(freq_dict)
    ttest = pyuvsim.simsetup.parse_time_params(time_dict)
    nt.assert_true(np.allclose(ftest['freq_array'], freqs))
    nt.assert_true(np.allclose(ttest['time_array'], times))

    # Check that this works for unevenly-spaced times

    times = np.random.choice(times, 150, replace=False)
    times.sort()
    time_dict = pyuvsim.simsetup.time_array_to_params(times)
    ttest = pyuvsim.simsetup.parse_time_params(time_dict)
    nt.assert_true(np.allclose(ttest['time_array'], times))

    # check Ntimes = 1 and Nfreqs = 1 case
    times = np.linspace(2458570, 2458570.5, 1)
    tdict = pyuvsim.simsetup.time_array_to_params(times)
    nt.assert_equal(tdict['Ntimes'], 1)

    freqs = np.linspace(100, 200, 1)
    fdict = pyuvsim.simsetup.freq_array_to_params(freqs)
    nt.assert_equal(fdict['Nfreqs'], 1)


def test_param_select_cross():
    param_filename = os.path.join(SIM_DATA_PATH, 'test_config', 'obsparam_mwa_nocore.yaml')

    param_dict = pyuvsim.simsetup._config_str_to_dict(param_filename)

    uv_obj_full, new_beam_list, new_beam_dict = pyuvsim.initialize_uvdata_from_params(param_dict)

    # test only keeping cross pols
    param_dict['select'] = {'ant_str': 'cross'}

    uv_obj_cross, new_beam_list, new_beam_dict = \
        pyuvsim.initialize_uvdata_from_params(param_dict)

    uv_obj_cross2 = uv_obj_full.select(ant_str='cross', inplace=False, metadata_only=True)

    nt.assert_equal(uv_obj_cross, uv_obj_cross2)


def test_param_select_bls():
    param_filename = os.path.join(SIM_DATA_PATH, 'test_config', 'obsparam_mwa_nocore.yaml')

    param_dict = pyuvsim.simsetup._config_str_to_dict(param_filename)

    uv_obj_full, new_beam_list, new_beam_dict = pyuvsim.initialize_uvdata_from_params(param_dict)

    # test only keeping certain baselines
    param_dict['select'] = {'bls': '[(40, 41), (42, 43), (44, 45)]'}    # Test as string

    uv_obj_bls, new_beam_list, new_beam_dict = \
        pyuvsim.initialize_uvdata_from_params(param_dict)

    uv_obj_bls2 = uv_obj_full.select(bls=[(40, 41), (42, 43), (44, 45)], inplace=False, metadata_only=True)

    uv_obj_bls.history, uv_obj_bls2.history = '', ''

    nt.assert_equal(uv_obj_bls, uv_obj_bls2)

    # check kwargs passed
    param_dict['object_name'] = 'foo'
    uv_obj_full, new_beam_list, new_beam_dict = pyuvsim.initialize_uvdata_from_params(param_dict)
    nt.assert_equal(uv_obj_full.object_name, 'foo')


def test_param_select_redundant():
    param_filename = os.path.join(SIM_DATA_PATH, 'test_config', 'obsparam_mwa_nocore.yaml')

    param_dict = pyuvsim.simsetup._config_str_to_dict(param_filename)

    uv_obj_full, new_beam_list, new_beam_dict = pyuvsim.initialize_uvdata_from_params(param_dict)

    # test only keeping one baseline per redundant group
    param_dict['select'] = {'redundant_threshold': 0.1}

    uv_obj_red, new_beam_list, new_beam_dict = \
        pyuvsim.initialize_uvdata_from_params(param_dict)

    uv_obj_red2 = uv_obj_full.compress_by_redundancy(tol=0.1, inplace=False, metadata_only=True)

    uv_obj_red.history, uv_obj_red2.history = '', ''

    nt.assert_equal(uv_obj_red, uv_obj_red2)


def check_uvdata_keyword_init(case):
    base_kwargs = dict(array_layout=os.path.join(SIM_DATA_PATH, "test_config/triangle_bl_layout.csv"),
                       telescope_location=(-30.72152777777791, 21.428305555555557, 1073.0000000093132),
                       telescope_name="HERA", Nfreqs=10, start_freq=1e8, bandwidth=1e8, Ntimes=60,
                       integration_time=100.0, start_time=2458101.0, polarizations=['xx'], no_autos=True, write_files=False, run_check=True)

    if case == 0:
        # check it runs through
        uvd, _, _ = pyuvsim.simsetup.initialize_uvdata_from_keywords(**base_kwargs)
        nt.assert_true(np.allclose(base_kwargs['telescope_location'], uvd.telescope_location_lat_lon_alt_degrees))
        nt.assert_true(np.allclose(base_kwargs['integration_time'], uvd.integration_time))
        nt.assert_equal(base_kwargs['telescope_name'], uvd.telescope_name)
        nt.assert_equal(base_kwargs['start_freq'], uvd.freq_array[0, 0])
        nt.assert_equal(base_kwargs['start_time'], uvd.time_array[0])
        nt.assert_equal(base_kwargs['Ntimes'], uvd.Ntimes)
        nt.assert_equal(base_kwargs['Nfreqs'], uvd.Nfreqs)
        nt.assert_equal(base_kwargs['polarizations'], uvd.get_pols())
        nt.assert_false(np.any(uvd.ant_1_array == uvd.ant_2_array))

    elif case == 1:
        # check bls and antenna_nums selections work
        bls = [(1, 0), (2, 0), (3, 0)]
        new_kwargs = copy.deepcopy(base_kwargs)
        new_kwargs['bls'] = bls
        uvd, _, _ = pyuvsim.simsetup.initialize_uvdata_from_keywords(**new_kwargs)
        antpairs = uvd.get_antpairs()
        nt.assert_equal(antpairs, bls)

    elif case == 2:
        # also check that '1' gets converted to [1]
        # Note -- Currently, pyuvdata's selection does not intersect antenna_nums with bls, but joins them.
        # If/when that is changed, this test should also include the bls selection keyword above.
        new_kwargs = copy.deepcopy(base_kwargs)
        new_kwargs['polarizations'] = ['xx', 'yy']
        new_kwargs['no_autos'] = False
        new_kwargs['antenna_nums'] = '1'
        uvd, _, _ = pyuvsim.simsetup.initialize_uvdata_from_keywords(**new_kwargs)

        nt.assert_equal(uvd.Nbls, 1)
        nt.assert_equal(uvd.get_pols(), new_kwargs['polarizations'])
    elif case == 3:
        # check time and freq array definitions supersede other parameters
        fa = np.linspace(100, 200, 11) * 1e6
        ta = np.linspace(2458101, 2458102, 21)
        new_kwargs = copy.deepcopy(base_kwargs)
        new_kwargs['freq_array'] = fa
        new_kwargs['time_array'] = ta
        uvd, _, _ = pyuvsim.simsetup.initialize_uvdata_from_keywords(**new_kwargs)

        nt.assert_true(np.allclose(uvd.time_array[::uvd.Nbls], ta))
        nt.assert_true(np.allclose(uvd.freq_array[0], fa))
    elif case == 4:
        # test feeding array layout as dictionary
        uvd, _, _ = pyuvsim.simsetup.initialize_uvdata_from_keywords(**base_kwargs)
        antpos, ants = uvd.get_ENU_antpos()
        antpos_d = dict(zip(ants, antpos))
        layout_fname = 'temp_layout.csv'
        obsparam_fname = 'temp_obsparam.yaml'

        new_kwargs = copy.deepcopy(base_kwargs)
        new_kwargs['antenna_layout_filename'] = layout_fname
        new_kwargs['yaml_filename'] = obsparam_fname
        new_kwargs['array_layout'] = antpos_d
        new_kwargs['path_out'] = '.'
        new_kwargs['write_files'] = True
        uvd, _, _ = pyuvsim.simsetup.initialize_uvdata_from_keywords(**new_kwargs)

        nt.assert_true(os.path.exists(layout_fname))
        nt.assert_true(os.path.exists(obsparam_fname))
        os.remove(layout_fname)
        os.remove(obsparam_fname)

        nt.assert_equal(uvd.Nbls, 6)
        nt.assert_equal(uvd.Nants_data, 4)
        ap, a = uvd.get_ENU_antpos()
        apd = dict(zip(a, ap))
        nt.assert_true(np.all([np.isclose(antpos_d[a], apd[a]) for a in ants]))


def test_kwarg_uv_init():
    """
    Tests different forms of UVData setup from keyword arguments.
    """
    for i in range(5):
        yield (check_uvdata_keyword_init, i)


def test_uvfits_to_config():
    """
        Loopback test of reading parameters from uvfits file, generating uvfits file, and reading in again.
    """
    opath = 'uvfits_yaml_temp'
    param_filename = 'obsparam.yaml'
    second_param_filename = 'test2_config.yaml'
    telescope_config = 'test_telescope_config.yaml'
    if not os.path.exists(opath):
        os.makedirs(opath)        # Directory will be deleted when test completed.

    # Read uvfits file to params.
    uv0 = UVData()
    uv0.read_uvfits(longbl_uvfits_file)

    warningmessages = ['The default for the `center` keyword has changed. Previously it defaulted to True, using the median antennna location; now it defaults to False, using the telescope_location.',
                       'The xyz array in ENU_from_ECEF is being interpreted as (Npts, 3). Historically this function has supported (3, Npts) arrays, please verify that array ordering is as expected.']
    path, telescope_config, layout_fname = \
        uvtest.checkWarnings(pyuvsim.simsetup.uvdata_to_telescope_config,
                             [uv0, herabeam_default], dict(path_out=opath, return_names=True),
                             nwarnings=2,
                             category=DeprecationWarning,
                             message=warningmessages)
    uv0.integration_time[-1] += 2  # Test case of non-uniform integration times
    uvtest.checkWarnings(pyuvsim.simsetup.uvdata_to_config_file, [uv0], dict(
        telescope_config_name=os.path.join(path, telescope_config),
        layout_csv_name=os.path.join(path, layout_fname),
        path_out=opath),
        message='The integration time is not constant. Using the shortest integration time')

    # From parameters, generate a uvdata object.
    param_dict = pyuvsim.simsetup._config_str_to_dict(os.path.join(opath, param_filename))

    orig_param_dict = copy.deepcopy(param_dict)   # The parameter dictionary gets modified in the function below.
    uv1, new_beam_list, new_beam_dict = \
        uvtest.checkWarnings(pyuvsim.initialize_uvdata_from_params, [param_dict],
                             category=[DeprecationWarning] * 2,
                             nwarnings=2, message=['The enu array in ECEF_from_ENU is being interpreted', 'The xyz array in ENU_from_ECEF is being interpreted as (Npts, 3)'])
    # Generate parameters from new uvfits and compare with old.
    path, telescope_config, layout_fname = \
        uvtest.checkWarnings(pyuvsim.simsetup.uvdata_to_telescope_config, [uv1, herabeam_default],
                             dict(telescope_config_name=telescope_config,
                                  layout_csv_name=layout_fname,
                                  path_out=opath, return_names=True),
                             category=DeprecationWarning,
                             nwarnings=2,
                             message=warningmessages)
    pyuvsim.simsetup.uvdata_to_config_file(uv1, param_filename=second_param_filename,
                                           telescope_config_name=os.path.join(path, telescope_config),
                                           layout_csv_name=os.path.join(path, layout_fname),
                                           path_out=opath)

    del param_dict

    param_dict = pyuvsim.simsetup._config_str_to_dict(os.path.join(opath, second_param_filename))
    shutil.rmtree(opath)
    nt.assert_true(param_dict['param_file'] == second_param_filename)
    nt.assert_true(orig_param_dict['param_file'] == param_filename)
    orig_param_dict['param_file'] = second_param_filename
    nt.assert_true(simtest.compare_dictionaries(param_dict, orig_param_dict))


def test_point_catalog_reader():
    catfile = os.path.join(SIM_DATA_PATH, 'test_config', 'pointsource_catalog.txt')
    catalog = pyuvsim.simsetup.read_text_catalog(catfile)

    with open(catfile, 'r') as fhandle:
        header = fhandle.readline()
    header = [h.strip() for h in header.split()]
    dt = np.format_parser(['U10', 'f8', 'f8', 'f8', 'f8'],
                          ['source_id', 'ra_j2000', 'dec_j2000', 'flux_density_I', 'frequency'], header)

    catalog_table = np.genfromtxt(catfile, autostrip=True, skip_header=1,
                                  dtype=dt.dtype)

    for src in catalog:
        nt.assert_true(src.name in catalog_table['source_id'])
        nt.assert_true(src.ra.deg in catalog_table['ra_j2000'])
        nt.assert_true(src.dec.deg in catalog_table['dec_j2000'])
        nt.assert_true(src.stokes[0] in catalog_table['flux_density_I'])
        nt.assert_true(src.freq.to("Hz").value in catalog_table['frequency'])


def test_horizon_cut():
    # Check that the coarse horizon cut doesn't remove sources that are actually up.
    uv_in, beam_list, beam_dict = pyuvsim.simsetup.initialize_uvdata_from_params(manytimes_config)
    Nsrcs = 20
    uv_in.select(times=np.unique(uv_in.time_array)[:50], bls=[(0, 1)], metadata_only=True)
    hera_loc = EarthLocation.from_geocentric(*uv_in.telescope_location, unit='m')

    dt = np.format_parser(['U10', 'f8', 'f8', 'f8', 'f8'],
                          ['source_id', 'ra_j2000', 'dec_j2000', 'flux_density_I', 'frequency'], [])

    catalog_table = np.recarray(Nsrcs, dtype=dt.dtype)
    catalog_table['source_id'] = ["src{}".format(i) for i in range(Nsrcs)]
    catalog_table['ra_j2000'] = np.random.uniform(0, 360., Nsrcs)
    catalog_table['dec_j2000'] = np.random.uniform(-90, 90, Nsrcs)
    catalog_table['flux_density_I'] = np.ones(Nsrcs)
    catalog_table['frequency'] = np.ones(Nsrcs) * 200e6

    uvtest.checkWarnings(pyuvsim.simsetup.source_cuts, [catalog_table],
                         {'lst_array': uv_in.lst_array},
                         message="It looks like you want to do a coarse horizon cut, but you're missing keywords", nwarnings=1)

    cut_sourcelist = pyuvsim.simsetup.array_to_skymodel(catalog_table)
    cut_sourcelist = pyuvsim.simsetup.source_cuts(catalog_table, input_uv=uv_in) #lst_array=uv_in.lst_array, latitude_deg=uv_in.telescope_location_lat_lon_alt_degrees[0])

    selected_source_names = cut_sourcelist['source_id'] #[s.name for s in cut_sourcelist]

    full_sourcelist = pyuvsim.simsetup.array_to_skymodel(catalog_table)  # No cuts

    # For each source in the full sourcelist, calculate the AltAz for all times.
    # If Alt > 0 at any time, confirm that the source is in the selection.

    time_arr = Time(uv_in.time_array, scale='utc', format='jd')
    for t in time_arr:
        full_sourcelist.update_positions(t, hera_loc)
        above_horizon = full_sourcelist.alt_az[0] > 0
        if sum(above_horizon) > 0:
            nt.assert_true(np.all(np.in1d(full_sourcelist.name[above_horizon], selected_source_names)))

    full_sourcelist = pyuvsim.simsetup.skymodel_to_array(full_sourcelist)
    # Now check that I get the same visibilities simulating with and without the horizon cut.
    beam_list = ['analytic_uniform']  # Simplify with a single uniform beam model
    kwds = dict(source_list_name='random', obs_param_file='', telescope_config_file='', antenna_location_file='')
    kwds['catalog'] = cut_sourcelist
    uv_select = uvtest.checkWarnings(pyuvsim.run_uvdata_uvsim, [uv_in, beam_list],
                                     kwds, category=DeprecationWarning,
                                     message='The default for the `center` keyword has changed')
    kwds['catalog'] = full_sourcelist
    uv_full = uvtest.checkWarnings(pyuvsim.run_uvdata_uvsim, [uv_in, beam_list],
                                   kwds, category=DeprecationWarning,
                                   message='The default for the `center` keyword has changed')
    nt.assert_equal(uv_full, uv_select)


def test_read_gleam():

    # sourcelist = pyuvsim.simsetup.read_votable_catalog(GLEAM_vot)
    sourcelist = uvtest.checkWarnings(pyuvsim.simsetup.read_votable_catalog, [GLEAM_vot],
                                      message=GLEAM_vot, nwarnings=11,
                                      category=[astropy.io.votable.exceptions.W27]
                                      + [astropy.io.votable.exceptions.W50] * 10)

    nt.assert_equal(len(sourcelist), 50)


def test_mock_catalogs():
    time = Time(2458098.27471265, scale='utc', format='jd')

    arrangements = ['off-zenith', 'zenith', 'cross', 'triangle', 'long-line', 'random', 'hera_text']

    cats = {}
    for arr in arrangements:
        # rseed is only used by the "random" mock catalog
        cat, mock_kwds = pyuvsim.simsetup.create_mock_catalog(time, arr, rseed=2458098)
        cats[arr] = cat

    # For each mock catalog, verify the Ra/Dec source positions against a text catalog.

    text_catalogs = {'cross': 'mock_cross_2458098.27471.txt',
                     'hera_text': 'mock_hera_text_2458098.27471.txt',
                     'long-line': 'mock_long-line_2458098.27471.txt',
                     'off-zenith': 'mock_off-zenith_2458098.27471.txt',
                     'triangle': 'mock_triangle_2458098.27471.txt',
                     'random': 'mock_random_2458098.27471.txt',
                     'zenith': 'mock_zenith_2458098.27471.txt'}
    simtest.assert_raises_message(KeyError, "Invalid mock catalog arrangement: invalid_catalog_name",
                                  pyuvsim.simsetup.create_mock_catalog, time, 'invalid_catalog_name')

    for arr in arrangements:
        radec_catalog = pyuvsim.simsetup.read_text_catalog(os.path.join(SIM_DATA_PATH,
                                                                        'test_catalogs', text_catalogs[arr]))
        nt.assert_true(np.all(radec_catalog == cats[arr]))

    cat, mock_kwds = pyuvsim.simsetup.create_mock_catalog(time, 'random', save=True)
    loc = eval(mock_kwds['array_location'])
    loc = EarthLocation.from_geodetic(loc[1], loc[0], loc[2])    # Lon, Lat, alt
    fname = 'mock_catalog_random.npz'
    alts_reload = np.load(fname)['alts']
    cat.update_positions(time, loc)
    alt, az = cat.alt_az
    nt.assert_true(np.all(alt > np.radians(30.)))
    nt.assert_true(np.allclose(alts_reload, np.degrees(alt)))
    os.remove(fname)


def test_catalog_file_writer():
    time = Time(2458098.27471265, scale='utc', format='jd')
    mock_zenith, mock_kwds = pyuvsim.simsetup.create_mock_catalog(time, 'zenith')
    fname = os.path.join(simtest.TESTDATA_PATH, 'temp_cat.txt')
    pyuvsim.simsetup.write_catalog_to_file(fname, mock_zenith)
    mock_zenith_loop = pyuvsim.simsetup.read_text_catalog(fname)
    nt.assert_true(np.all(mock_zenith_loop == mock_zenith))
    os.remove(fname)


def test_keyword_param_loop():
    # Check that yaml/csv files made by intialize_uvdata_from_keywords will work
    # on their own.

    layout_fname = 'temp_layout.csv'
    obsparam_fname = 'temp_obsparam.yaml'
    path_out = simtest.TESTDATA_PATH
    antpos_enu = np.ones(30).reshape((10, 3))
    antnums = np.arange(10)
    antpos_d = dict(zip(antnums, antpos_enu))
    uvd, _, _ = pyuvsim.simsetup.initialize_uvdata_from_keywords(array_layout=antpos_d,
                                                                 telescope_location=(-30.72152777777791, 21.428305555555557, 1073.0000000093132),
                                                                 telescope_name="HERA", Nfreqs=10, start_freq=1e8, bandwidth=1e8, Ntimes=60,
                                                                 integration_time=100.0, start_time=2458101.0, polarizations=[-5], no_autos=True,
                                                                 path_out=path_out, antenna_layout_filename=layout_fname, yaml_filename=obsparam_fname)

    uv2, _, _ = pyuvsim.simsetup.initialize_uvdata_from_params(os.path.join(path_out, obsparam_fname))

    uv2.extra_keywords = {}
    uvd.extra_keywords = {}  # These will not match

    nt.assert_equal(uv2, uvd)

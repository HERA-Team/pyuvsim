# -*- mode: python; coding: utf-8 -*
# Copyright (c) 2018 Radio Astronomy Software Group
# Licensed under the 3-clause BSD License

from __future__ import absolute_import, division, print_function

import numpy as np
import nose.tools as nt
from astropy.time import Time
from astropy.coordinates import Angle, SkyCoord, EarthLocation
from astropy import units

import pyuvsim
import pyuvsim.tests as simtest
from pyuvsim.source import Source


def test_calc_basis_rotation_matrix():
    time = Time('2018-01-01 00:00')
    telescope_location = EarthLocation(lat='-30d43m17.5s', lon='21d25m41.9s',height=1073.)

    source = Source('Test',Angle(12.*units.hr),Angle(-30.*units.deg),150*units.MHz,[1.,0.,0.,0.])

    basis_rot_matrix = source._calc_basis_rotation_matrix(time, telescope_location)

    # This is not a very strenous test :)
    assert(np.allclose(np.matmul(basis_rot_matrix, basis_rot_matrix.T),np.eye(3),atol=1.e-5))


def test_source_zenith_from_icrs():
    """Test single source position at zenith constructed using icrs."""
    array_location = EarthLocation(lat='-30d43m17.5s', lon='21d25m41.9s',
                                   height=1073.)
    time = Time('2018-03-01 00:00:00', scale='utc', location=array_location)

    freq = (150e6 * units.Hz)

    lst = time.sidereal_time('apparent')

    tee_ra = lst
    cirs_ra = pyuvsim.tee_to_cirs_ra(tee_ra, time)

    cirs_source_coord = SkyCoord(ra=cirs_ra, dec=array_location.lat,
                                 obstime=time, frame='cirs', location=array_location)

    icrs_coord = cirs_source_coord.transform_to('icrs')

    ra = icrs_coord.ra
    dec = icrs_coord.dec
    # Check error cases
    nt.assert_raises(ValueError, pyuvsim.Source, 'icrs_zen', ra.rad, dec.rad, freq.value, [1, 0, 0, 0])
    nt.assert_raises(ValueError, pyuvsim.Source, 'icrs_zen', ra, dec.rad, freq.value, [1, 0, 0, 0])
    nt.assert_raises(ValueError, pyuvsim.Source, 'icrs_zen', ra, dec, freq.value, [1, 0, 0, 0])
    zenith_source = pyuvsim.Source('icrs_zen', ra, dec, freq, [1, 0, 0, 0])

    zenith_source_lmn = zenith_source.pos_lmn(time, array_location)

    nt.assert_true(np.allclose(zenith_source_lmn, np.array([0, 0, 1]), atol=1e-5))


def test_source_zenith():
    """Test single source position at zenith."""
    time = Time('2018-03-01 00:00:00', scale='utc')

    array_location = EarthLocation(lat='-30d43m17.5s', lon='21d25m41.9s',
                                   height=1073.)
    source_arr, _ = pyuvsim.create_mock_catalog(time, arrangement='zenith',
                                                array_location=array_location)
    zenith_source = source_arr[0]
    zenith_source_lmn = zenith_source.pos_lmn(time, array_location)

    nt.assert_true(np.allclose(zenith_source_lmn, np.array([0, 0, 1])))


def test_sources_equal():
    time = Time('2018-03-01 00:00:00', scale='utc')
    src1, _ = pyuvsim.create_mock_catalog(time, arrangement='zenith')
    src2, _ = pyuvsim.create_mock_catalog(time, arrangement='zenith')
    nt.assert_equal(src1, src2)

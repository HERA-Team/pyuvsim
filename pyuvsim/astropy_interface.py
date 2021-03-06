# -*- mode: python; coding: utf-8 -*
# Copyright (c) 2020 Radio Astronomy Software Group
# Licensed under the 3-clause BSD License

"""
Special import interface for astropy.

The lunarsky module wraps several classes in astropy. This module
provides the classes from lunarsky if it's installed, or from astropy if
it isn't.

Provides:
    * MoonLocation -- Equivalent to EarthLocation.
    * LunarTopo    -- An AltAz frame on the Moon.
    * Time         -- astropy Time class that works with MoonLocation.
    * SkyCoord     -- source coordinate position compatible with MoonLocation.

The lunarsky classes are entirely compatible with normal astropy behavior, even
if observing locations on the Moon are not used.
"""

try:
    from lunarsky import SkyCoord, MoonLocation, LunarTopo, Time
    hasmoon = True
except ImportError:
    from astropy.coordinates import SkyCoord
    from astropy.time import Time
    hasmoon = False

    class MoonLocation:
        pass

    class LunarTopo:
        pass

for obj in [SkyCoord, MoonLocation, LunarTopo, Time]:
    assert obj

# -*- mode: python; coding: utf-8 -*
# Copyright (c) 2018 Radio Astronomy Software Group
# Licensed under the 3-clause BSD License

"""
Use the line profiler when requested.

If the set_profiler method is called, the profile decorators
throughout the code will do line profiling on all instance methods.
"""

from __future__ import absolute_import, division, print_function

from .mpi import start_mpi, get_rank
import inspect
import sys
import atexit

try:
    from line_profiler import LineProfiler
except ImportError:   # pragma: no cover
    def LineProfiler():
        return None

PY3 = sys.version_info[0] == 3

if PY3:
    import builtins
else:
    import __builtin__ as builtins

prof = LineProfiler()


def set_profiler():
    """ If profiling is requested, then assign it to the builtins """
    start_mpi()
    if prof is not None:
        builtins.__dict__['profile'] = prof
        if get_rank() == 0:
            atexit.register(prof.print_stats)


# By default, the profile decorator has no effect.
if 'profile' not in builtins.__dict__:
    builtins.__dict__['profile'] = lambda f: f
else:
    set_profiler()  # Will activate if run with kernprof

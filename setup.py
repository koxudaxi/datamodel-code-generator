#! /usr/bin/env python

from pathlib import Path

from setuptools import __version__, setup
from setuptools.config import read_configuration

if int(__version__.split(".")[0]) < 41:
    raise RuntimeError("setuptools >= 41 required to build")

config = read_configuration(Path(__file__).parent.joinpath('setup.cfg'))

extras_require = {
    'test': config['options']['tests_require'],
    **config['options']['extras_require'],
}
extras_require['all'] = [*extras_require.values()]
use_scm_version = {'write_to': Path(config['metadata']['name'].replace('-', '_'), 'version.py')}

setup(setup_requires=["setuptools_scm >= 2"], extras_require=extras_require, use_scm_version=use_scm_version)

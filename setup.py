#! /usr/bin/env python

from pathlib import Path

from setuptools import setup
from setuptools.config import read_configuration

config = read_configuration(Path(__file__).parent.joinpath('setup.cfg'))

extras_require = {
    'setup': config['options']['setup_requires'],
    'test': config['options']['tests_require'],
    **config['options']['extras_require'],
}
extras_require['all'] = [*extras_require.values()]
use_scm_version = {'write_to': Path(config['metadata']['name'].replace('-', '_'), 'version.py')}

setup(extras_require=extras_require, use_scm_version=use_scm_version)

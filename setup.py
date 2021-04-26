#! /usr/bin/env python

from pathlib import Path

from setuptools import setup
from setuptools.config import read_configuration

# This Version number is formatted such that the latest version of the Upstream that is integrated precedes the
# underscore, and Pie's version succeeds the underscore.
VERSION = '0.9.2_1.1.0'

config = read_configuration(Path(__file__).parent.joinpath('setup.cfg'))

extras_require = {
    'setup': config['options']['setup_requires'],
    'test': config['options']['tests_require'],
    **config['options']['extras_require'],
}
extras_require['all'] = [*extras_require.values()]
use_scm_version = {'write_to': Path(config['metadata']['name'].replace('-', '_'), 'version.py')}

setup(version=VERSION,
      extras_require=extras_require,
      use_scm_version=use_scm_version
)

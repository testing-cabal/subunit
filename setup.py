#!/usr/bin/env python
import os.path
try:
    # If the user has setuptools / distribute installed, use it
    from setuptools import setup
except ImportError:
    # Otherwise, fall back to distutils.
    from distutils.core import setup
    extra = {}
else:
    extra = {
        'install_requires': [
            'extras',
            'testtools>=0.9.34',
        ],
        'tests_require': [
            'fixtures',
            'hypothesis',
            'testscenarios',
        ],
        'extras_require': {
            'docs': ['docutils'],
            'test': ['fixtures', 'testscenarios'],
            'test:python_version!="3.2"': ['hypothesis'],
        },
    }


def _get_version_from_file(filename, start_of_line, split_marker):
    """Extract version from file, giving last matching value or None"""
    try:
        return [x for x in open(filename)
            if x.startswith(start_of_line)][-1].split(split_marker)[1].strip()
    except (IOError, IndexError):
        return None


VERSION = (
    # Assume we are in a distribution, which has PKG-INFO
    _get_version_from_file('PKG-INFO', 'Version:', ':')
    # Must be a development checkout, so use the Makefile
    or _get_version_from_file('Makefile', 'VERSION', '=')
    or "0.0")


relpath = os.path.dirname(__file__)
if relpath:
    os.chdir(relpath)
setup(
    name='python-subunit',
    version=VERSION,
    description=('Python implementation of subunit test streaming protocol'),
    long_description=open('README.rst').read(),
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Testing',
    ],
    keywords='python test streaming',
    author='Robert Collins',
    author_email='subunit-dev@lists.launchpad.net',
    url='http://launchpad.net/subunit',
    license='Apache-2.0 or BSD',
    project_urls={
        "Bug Tracker": "https://bugs.launchpad.net/subunit",
        "Source Code": "https://github.com/testing-cabal/subunit/",
    },
    packages=['subunit', 'subunit.tests'],
    package_dir={'subunit': 'python/subunit'},
    scripts = [
        'filters/subunit-1to2',
        'filters/subunit-2to1',
        'filters/subunit-filter',
        'filters/subunit-ls',
        'filters/subunit-notify',
        'filters/subunit-output',
        'filters/subunit-stats',
        'filters/subunit-tags',
        'filters/subunit2csv',
        'filters/subunit2disk',
        'filters/subunit2gtk',
        'filters/subunit2junitxml',
        'filters/subunit2pyunit',
        'filters/tap2subunit',
    ],
    **extra
)

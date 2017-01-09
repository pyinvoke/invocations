#!/usr/bin/env python

import sys

from setuptools import setup, find_packages

# Version info -- read without importing
_locals = {}
with open('invocations/_version.py') as fp:
    exec(fp.read(), None, _locals)
version = _locals['__version__']

requirements = [
    # Core dependency, obviously
    'invoke>=0.13,<2.0',

    # Dependencies for various subpackages.
    # NOTE: these used to be all optional (only complained about at import
    # time if missing), but that got hairy fast, and these are all
    # pure-Python packages, so it shouldn't be a huge burden for users to
    # obtain them.
    'blessings>=1.6,<2',
    # TODO: this pulls down Sphinx and its whole tree too, and eventually the
    # release module will want Releases-specific changelogs to be optional. At
    # that time, make this optional again.
    'releases>=1.2,<2',
    'semantic_version>=2.4,<3',
    'tabulate>=0.7,<0.8',
    'tqdm>=4.8.1',
]
if sys.version_info < (3, 4): # which is when stdlib.enum arrived
    requirements.append('enum34>=1.1,<2')

setup(
    name='invocations',
    version=version,
    description='Reusable Invoke tasks',
    license='BSD',
    author='Jeff Forcier',
    author_email='jeff@bitprophet.org',
    url='http://pyinvoke.org',

    # Release requirements. See dev-requirements.txt for dev version reqs.
    install_requires=requirements,

    packages=find_packages(),

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
    ],
)

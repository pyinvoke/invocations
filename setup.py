#!/usr/bin/env python

# Support setuptools or distutils
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

# Version info -- read without importing
_locals = {}
with open('invocations/_version.py') as fp:
    exec(fp.read(), None, _locals)
version = _locals['__version__']

setup(
    name='invocations',
    version=version,
    description='Reusable Invoke tasks',
    license='BSD',
    author='Jeff Forcier',
    author_email='jeff@bitprophet.org',
    url='http://pyinvoke.org',

    # Release requirements. See dev-requirements.txt for dev version reqs.
    requirements=['invoke>=0.6.0,<=0.9.0'],

    packages=['invocations'],

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

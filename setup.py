#!/usr/bin/env python

from setuptools import setup, find_packages

# Version info -- read without importing
_locals = {}
with open("invocations/_version.py") as fp:
    exec(fp.read(), None, _locals)
version = _locals["__version__"]

requirements = [
    # Core dependency
    "invoke>=1.7.2",
    # Dependencies for various subpackages.
    # NOTE: these used to be all optional (only complained about at import
    # time if missing), but that got hairy fast, and these are all
    # pure-Python packages, so it shouldn't be a huge burden for users to
    # obtain them.
    "blessings>=1.6",
    "releases>=1.6",
    "semantic_version>=2.4,<2.7",
    "tabulate>=0.7.5",
    "tqdm>=4.8.1",
    "twine>=1.15",
    "wheel>=0.24.0",
]

setup(
    name="invocations",
    version=version,
    description="Common/best-practice Invoke tasks and collections",
    long_description=open("README.rst").read(),
    license="BSD",
    author="Jeff Forcier",
    author_email="jeff@bitprophet.org",
    url="https://invocations.readthedocs.io",
    project_urls={
        "Source": "https://github.com/pyinvoke/invocations",
        "Changelog": "https://invocations.readthedocs.io/en/latest/changelog.html",  # noqa
        "CI": "https://app.circleci.com/pipelines/github/pyinvoke/invocations",
        "Issues": "https://github.com/pyinvoke/invocations/issues",
    },
    # Release requirements. See dev-requirements.txt for dev version reqs.
    python_requires=">=3.6",
    install_requires=requirements,
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Software Distribution",
        "Topic :: System :: Systems Administration",
    ],
)

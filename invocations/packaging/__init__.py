# Make the inner modules' tasks/collections readily available.
from .vendorize import vendorize
from . import release

# Most of the time, importers of this module want the 'release' sub-collection.
# TODO: update other libs & then remove this so it's a bit cleaner.
ns = release

# flake8: noqa

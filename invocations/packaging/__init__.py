# Just make the inner modules' tasks/collections readily available.
# TODO: maaaaybe add our own sub-collection at this level so folks who want to
# call stuff as 'packaging.vendorize' or 'packaging.release.upload' (vs binding
# closer to project's root) have an easy import?
from .vendorize import vendorize
from .release import release

# flake8: noqa

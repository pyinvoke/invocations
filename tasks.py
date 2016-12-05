from invoke import Collection, task

from invocations.packaging import release
from invocations.testing import test, watch_tests, coverage as coverage_


# TODO: add coverage at the Travis level as well sometime. For now this is just
# to help me as I overhaul the release modules

@task
def coverage(c, html=True):
    # TODO: can we realistically make use of functools.partial for this sort of
    # thing?
    # TODO: is it best left to config option overrides (currently the usual
    # approach)? Is there stuff we can do to make that even easier?
    return coverage_(c, html=html, integration_=False)


ns = Collection(release, test, watch_tests, coverage)
ns.configure({
    'tests': {
        'package': 'invocations',
    },
    'packaging': {
        'sign': True,
        'wheel': True,
    },
})

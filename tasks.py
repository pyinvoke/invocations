from invoke import Collection

from invocations.packaging import release
from invocations.testing import test, watch_tests


ns = Collection(release, test, watch_tests)
ns.configure({
    'tests': {
        'package': 'invocations',
    },
    'packaging': {
        'sign': True,
        'wheel': True,
    },
})

from invoke import Collection

from invocations.packaging import release
from invocations.pytest import test, coverage


ns = Collection(release, test, coverage)
ns.configure({
    'packaging': {
        'sign': True,
        'wheel': True,
    },
    'run': {
        'env': {
            # Our ANSI color tests test against hardcoded codes appropriate for
            # this terminal, for now.
            'TERM': 'xterm-256color',
        },
    },
})

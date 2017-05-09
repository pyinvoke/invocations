from invoke import Collection, task

from invocations.packaging import release
from invocations import pytest as pytests


ns = Collection(release, pytests.test, pytests.coverage)
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

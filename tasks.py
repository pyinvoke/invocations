from invoke import Collection

from invocations import packaging


ns = Collection(release=packaging)
ns.configure({
    'packaging': {
        'sign': True,
        'wheel': True,
    },
})

from importlib import metadata

import invocations


def package_has_dunder_version():
    assert invocations.__version__ == metadata.version("invocations")

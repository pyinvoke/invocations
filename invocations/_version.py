from importlib_metadata import version  # type: ignore

__version__ = version(__package__)
__version_info__ = tuple(map(int, __version__.split(".")))

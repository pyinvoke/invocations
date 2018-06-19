"""
Monkey patches for ``semantic_version.Version``.

We never like monkey-patching, but for now this is easier than either vendoring
or distributing our own fork.
"""

from invoke.vendor.six import text_type

from semantic_version import Version


def clone(self):
    """
    Return a new copy of this Version object.

    Useful when you need to generate a new object that can be mutated
    separately from the original.
    """
    return Version(text_type(self))


Version.clone = clone


def next_minor(self):
    """
    Return a Version whose minor number is one greater than self's.

    .. note::
        The new Version will always have a zeroed-out bugfix/tertiary version
        number, because the "next minor release" of e.g. 1.2.1 is 1.3.0, not
        1.3.1.
    """
    clone = self.clone()
    clone.minor += 1
    clone.patch = 0
    return clone


Version.next_minor = next_minor


def next_patch(self):
    """
    Return a Version whose patch/bugfix number is one greater than self's.
    """
    clone = self.clone()
    clone.patch += 1
    return clone


Version.next_patch = next_patch

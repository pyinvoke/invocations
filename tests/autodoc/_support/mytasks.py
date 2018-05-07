"""
Some fake tasks to test task autodoc.
"""

from invoke import task


@task
def undocumented(c):
    # I have no docstring so I may not show up. Or...may I?!
    pass


@task
def base_case(c):
    """
    Literally the smallest possible task.
    """
    pass


@task
def simple_case(c, arg):
    """
    Parameterization!
    """
    pass

from importlib import metadata

__version__ = metadata.version("invocations")


# Ignore SyntaxWarnings that come out of old semantic_version versions under
# newer Pythons (re: comparing ints with 'is')
# TODO: finish the WIP re: upgrading to modern semantic_version (it's
# nontrivial unfortunately) then nuke this.
from warnings import filterwarnings

filterwarnings(action="ignore", category=SyntaxWarning, module=".*")

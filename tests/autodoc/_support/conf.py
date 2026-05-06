import sys
from os.path import dirname, abspath, join

# Basic path setup
support = abspath(dirname(__file__))
repo_root = abspath(join(support, "..", "..", ".."))

if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if support not in sys.path:
    sys.path.insert(0, support)

master_doc = "index"
extensions = ["invocations.autodoc"]
autodoc_default_options = {"members": True}
project = "Invocations"

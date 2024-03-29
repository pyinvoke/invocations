from os.path import dirname
import sys


# Add local support dir to path so tasks modules may be imported by autodoc
sys.path.insert(0, dirname(__file__))

master_doc = "index"
extensions = ["invocations.autodoc"]
autodoc_default_options = dict(members=True)

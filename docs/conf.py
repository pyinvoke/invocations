from datetime import datetime
from os import environ, getcwd
from os.path import abspath, join, dirname
import sys


# Core settings
extensions = [
    "releases",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "invocations.autodoc",
]
templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"
exclude_patterns = ["_build"]
default_role = "obj"

project = u"Invocations"
year = datetime.now().year
copyright = u"%d Jeff Forcier" % year

# Ensure project directory is on PYTHONPATH for version, autodoc access
sys.path.insert(0, abspath(join(getcwd(), "..")))

# Enforce use of Alabaster (even on RTD) and configure it
html_theme = "alabaster"
html_theme_options = {
    "description": "Common/best-practice Invoke tasks and collections",
    "github_user": "pyinvoke",
    "github_repo": "invocations",
    # TODO: make new UA property? only good for full domains and not RTD.io?
    # 'analytics_id': 'UA-18486793-X',
    "travis_button": True,
    # 'codecov_button': True, # TODO: get better coverage sometime, heh
    "tidelift_url": "https://tidelift.com/subscription/pkg/pypi-invocations?utm_source=pypi-invocations&utm_medium=referral&utm_campaign=docs",  # noqa
}
html_sidebars = {
    "**": ["about.html", "navigation.html", "searchbox.html", "donate.html"]
}

# Other extension configs
autodoc_default_flags = ["members", "special-members"]
releases_github_path = "pyinvoke/invocations"

# Intersphinx
# TODO: this could probably get wrapped up into us or some other shared lib?
on_rtd = environ.get("READTHEDOCS") == "True"
on_travis = environ.get("TRAVIS", False)
on_dev = not (on_rtd or on_travis)

# Invoke
inv_target = join(
    dirname(__file__), "..", "..", "invoke", "sites", "docs", "_build"
)
if not on_dev:
    inv_target = "http://docs.pyinvoke.org/en/latest/"
# Put them all together, + Python core
intersphinx_mapping = {
    "python": ("http://docs.python.org/", None),
    "invoke": (inv_target, None),
}

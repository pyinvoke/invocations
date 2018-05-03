from datetime import datetime
import os
import sys


# Core settings
extensions = ['releases', 'sphinx.ext.intersphinx', 'sphinx.ext.autodoc']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
exclude_patterns = ['_build']

project = u'Invocations'
year = datetime.now().year
copyright = u'%d Jeff Forcier' % year

# Ensure project directory is on PYTHONPATH for version, autodoc access
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '..')))

# Alabaster is the default theme; configure it here.
html_theme_options = {
    'description': "Common/best-practice Invoke tasks and collections",
    'github_user': 'pyinvoke',
    'github_repo': 'invocations',
    # TODO: make new UA property? only good for full domains and not RTD.io?
    # 'analytics_id': 'UA-18486793-X', 
    'travis_button': True,
    # 'codecov_button': True, # TODO: get better coverage sometime, heh
}
html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'searchbox.html',
        'donate.html',
    ]
}

# Other extension configs
autodoc_default_flags = ['members', 'special-members']
releases_github_path = 'pyinvoke/invocations'

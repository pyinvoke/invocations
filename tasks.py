from invoke import Collection

from invocations import docs, checks
from invocations.packaging import release
from invocations.pytest import test, coverage


ns = Collection(release, test, coverage, docs, checks.blacken, checks)
ns.configure(
    {
        "packaging": {"wheel": True, "changelog_file": "docs/changelog.rst"},
        "run": {
            "env": {
                # Our ANSI color tests test against hardcoded codes appropriate
                # for this terminal, for now.
                "TERM": "xterm-256color"
            },
        },
    }
)

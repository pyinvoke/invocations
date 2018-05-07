from os.path import join, dirname
import shutil

from mock import Mock
from pytest import skip

from invoke import Context
from invocations.autodoc import setup, TaskDocumenter


def _build():
    """
    Build local support docs tree and return the build target dir for cleanup.
    """
    c = Context()
    support = join(dirname(__file__), '_support')
    docs = join(support, 'docs')
    build = join(support, '_build')
    with c.cd(support):
        c.run("sphinx-build -c {} -W {} {}".format(support, docs, build))
    return build


class autodoc_:
    @classmethod
    def setup_class(self):
        # Build once, introspect many...for now
        self.build_dir = _build()

    @classmethod
    def teardown_class(self):
        shutil.rmtree(self.build_dir)

    def setup_adds_TaskDocumenter_as_documenter(self):
        app = Mock()
        setup(app)
        app.add_autodocumenter.assert_called_once_with(TaskDocumenter)

    def undocumented_members_do_not_appear_by_default(self):
        # This really just tests basic Sphinx/autodoc stuff for now...meh
        skip()

    def base_case_of_no_argument_docstringed_task(self):
        skip()

    def simple_case_of_single_argument_task(self):
        skip()

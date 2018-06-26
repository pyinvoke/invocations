from os.path import join, dirname
import re
import shutil

from mock import Mock, patch

from invoke import Context
from invocations.autodoc import setup, TaskDocumenter


def _build():
    """
    Build local support docs tree and return the build target dir for cleanup.
    """
    c = Context()
    support = join(dirname(__file__), "_support")
    docs = join(support, "docs")
    build = join(support, "_build")
    command = "sphinx-build -c {} -W {} {}".format(support, docs, build)
    with c.cd(support):
        # Turn off stdin mirroring to avoid irritating pytest.
        c.run(command, in_stream=False)
    return build


class autodoc_:
    @classmethod
    def setup_class(self):
        # Build once, introspect many...for now
        self.build_dir = _build()
        with open(join(self.build_dir, "api.html")) as fd:
            self.api_docs = fd.read()

    @classmethod
    def teardown_class(self):
        shutil.rmtree(self.build_dir, ignore_errors=True)

    @patch("sphinx.ext.autodoc.add_documenter")
    def setup_adds_TaskDocumenter_as_documenter(self, add_documenter):
        setup(Mock())
        add_documenter.assert_called_once_with(TaskDocumenter)

    def module_docstring_unmodified(self):
        # Just a sanity test, really.
        assert "Some fake tasks to test task autodoc." in self.api_docs

    def regular_functions_only_appear_once(self):
        # Paranoid sanity check re: our
        # very-much-like-FunctionDocumenter-documenter not accidentally loading
        # up non-task objects. SHRUG.
        # TODO: incredibly stupid "is HTML string literal" test because too
        # lazy to whip up something with BeautifulSoup et al.
        for sentinel in (">not_a_task", ">I am a regular function"):
            assert len(re.findall(sentinel, self.api_docs)) == 1

    def undocumented_members_do_not_appear_by_default(self):
        # This really just tests basic Sphinx/autodoc stuff for now...meh
        assert "undocumented" not in self.api_docs

    def base_case_of_no_argument_docstringed_task(self):
        for sentinel in ("base_case", "smallest possible task"):
            assert sentinel in self.api_docs

    def simple_case_of_single_argument_task(self):
        # TODO: OK we really need something that scales better soon re:
        # viewing the output as a non-HTML string / something that is not
        # super tied to sphinx/theme output...heh
        for sentinel in ("simple_case", "simple_arg", "Parameterization!"):
            assert sentinel in self.api_docs

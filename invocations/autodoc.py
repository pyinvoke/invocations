"""
Sphinx autodoc hooks for documenting Invoke-level objects such as tasks.

Unlike most of the rest of Invocations, this module isn't for reuse in the
"import and call functions" sense, but instead acts as a Sphinx extension which
allows Sphinx's `autodoc`_ functionality to see and document
Invoke tasks and similar Invoke objects.

.. note::
    This functionality is mostly useful for redistributable/reusable tasks
    which have been defined as importable members of some Python package or
    module, as opposed to "local-only" tasks that live in a single project's
    ``tasks.py``.

    However, it will work for any tasks that Sphinx autodoc can import, so in a
    pinch you could for example tweak ``sys.path`` in your Sphinx ``conf.py``
    to get it loading up a "local" tasks file for import.

To use:

- Add ``"sphinx.ext.autodoc"`` and ``"invocations.autodoc"`` to your Sphinx
  ``conf.py``'s ``extensions`` list.
- Use Sphinx autodoc's ``automodule`` directive normally, aiming it at your
  tasks module(s), e.g. ``.. automodule:: myproject.tasks`` in some ``.rst``
  document of your choosing.

    - As noted above, this only works for modules that are importable, like any
      other Sphinx autodoc use case.
    - Unless you want to opt-in which module members get documented, use
      ``:members:`` or add ``"members"`` to your ``conf.py``'s
      ``autodoc_default_flags``.
    - By default, only tasks with docstrings will be picked up, unless you also
      give the ``:undoc-members:`` flag or add ``:undoc-members:`` / add
      ``"undoc-members"`` to ``autodoc_default_flags``.
    - Please see the `autodoc`_ docs for details on these settings and more!

- Build your docs, and you should see your tasks showing up as documented
  functions in the result.


.. _autodoc: http://www.sphinx-doc.org/en/master/ext/autodoc.html
"""

from invoke import Task
from sphinx.util.inspect import getargspec  # Improved over raw stdlib

# For sane mock patching. Meh.
from sphinx.ext import autodoc


class TaskDocumenter(
    autodoc.DocstringSignatureMixin, autodoc.ModuleLevelDocumenter
):
    objtype = "task"
    directivetype = "function"

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, Task)

    def format_args(self):
        function = self.object.body
        # TODO: consider extending (or adding a sibling to) Task.argspec so it
        # preserves more of the full argspec tuple.
        # TODO: whether to preserve the initial context argument is an open
        # question. For now, it will appear, but only pending invoke#170 -
        # after which point "call tasks as raw functions" may be less common.
        # TODO: also, it may become moot-ish if we turn this all into emission
        # of custom domain objects and/or make the CLI arguments the focus
        return autodoc.formatargspec(function, *getargspec(function))

    def document_members(self, all_members=False):
        # Neuter this so superclass bits don't introspect & spit out autodoc
        # directives for task attributes. Most of that's not useful.
        pass


def setup(app):
    # NOTE: the "correct", forward compatible call to make here is
    # app.add_autodocumenter() - because as of Sphinx 1.7, the inner API we are
    # manipulating here got changed around a bunch (but the outer
    # API of add_autodocumenter() remained the same, on purpose).
    # Unfortunately, in both cases add_autodocumenter() both registers the
    # documenter AND adds an `auto<type>` directive - meaning it's not possible
    # to register a "acts kinda like another" Documenter or you double-define
    # e.g. autofunction, which Sphinx warns about and also presumably kills
    # real function documenting.
    # NOTE: sooo for now, since a bunch of our other shit breaks on Sphinx 1.7,
    # we are just explicitly calling autodoc's add_documenter. Sadface.
    autodoc.add_documenter(TaskDocumenter)

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

- Add ``"invocations.autodoc"`` to your Sphinx ``conf.py``'s ``extensions``
  list.
- Use Sphinx autodoc's ``automodule`` directive normally, aiming it at your
  tasks module(s), e.g. ``.. automodule:: myproject.tasks`` in some ``.rst``
  document of your choosing.

    - As noted above, this only works for modules that are importable, like any
      other Sphinx autodoc use case.
    - Unless you want to opt-in which module members get documented, use
      ``:members:`` or add ``"members": True`` to your ``conf.py``'s
      ``autodoc_default_options``.
    - By default, only tasks with docstrings will be picked up, unless you also
      give the ``:undoc-members:`` flag or add ``:undoc-members:`` / add
      ``"undoc-members": True`` to ``autodoc_default_options``.
    - Please see the `autodoc`_ docs for details on these settings and more!

- Build your docs, and you should see your tasks showing up as documented
  functions in the result.


.. _autodoc: http://www.sphinx-doc.org/en/master/ext/autodoc.html
"""

import inspect

from invoke import Task

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
        return autodoc.stringify_signature(inspect.signature(function))

    def document_members(self, all_members=False):
        # Neuter this so superclass bits don't introspect & spit out autodoc
        # directives for task attributes. Most of that's not useful.
        pass


def setup(app):
    app.setup_extension("sphinx.ext.autodoc")
    app.add_autodocumenter(TaskDocumenter)

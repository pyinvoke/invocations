"""
Sphinx autodoc hooks for documenting Invoke-level objects such as tasks.

Unlike most of the rest of Invocations, this module isn't for reuse in the
"import and call functions" sense, but instead acts as a Sphinx extension which
allows Sphinx's `autodoc`_ functionality to see and document
Invoke tasks and similar Invoke objects.

To use:
- Add ``"invocations.autodoc"`` to your Sphinx ``conf.py``'s ``extensions``.
- Use ``.. automodule:: myproject.tasks`` with ``:members:``.
"""

import inspect
from sphinx.ext import autodoc

# Compatibility layer for signature stringification
try:
    from sphinx.util import inspect as sphinx_inspect

    stringify = sphinx_inspect.stringify_signature
except (ImportError, AttributeError):
    try:
        stringify = autodoc.stringify_signature
    except AttributeError:

        def stringify(x):
            return str(x)


class TaskDocumenter(autodoc.ModuleLevelDocumenter):
    """
    Custom autodoc documenter for Invoke Task objects.

    Inherits from ModuleLevelDocumenter to ensure tasks are discovered in
    modules without triggering DataDocumenter's ':value:' header logic,
    which causes errors in standard function directives.
    """

    objtype = "task"
    directivetype = "function"
    priority = 50

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        from invoke import Task

        # Identify Invoke tasks by their characteristic attributes or class type
        return (
            isinstance(member, Task)
            or hasattr(member, "body")
            and hasattr(member, "argspec")
        )

    def import_object(self, **kwargs):
        # Import the Task instance, then store the wrapped function for inspection
        success = super().import_object(**kwargs)
        if success and hasattr(self.object, "body"):
            self.wrapped_function = self.object.body
        return success

    def get_object_members(self, want_all):
        # Tasks are atomic; they have no child members to document
        return False, []

    def format_args(self, **kwargs):
        try:
            sig = inspect.signature(self.object.body)
            return stringify(sig)
        except Exception:
            return None

    def format_signature(self, **kwargs):
        # Extract signature from the wrapped function body
        try:
            sig = inspect.signature(self.wrapped_function)
            return stringify(sig)
        except Exception:
            return ""

    def add_directive_header(self, sig):
        # Write the standard header (.. py:function:: name(args))
        # Note: 3.10+ adds :value: which is incompatible with py:function
        super().add_directive_header(sig)

    def add_content(self, more_content, no_docstring=False):
        # Manually inject the docstring from the wrapped function
        sourcename = self.get_sourcename()
        docstring = inspect.getdoc(self.wrapped_function)

        if docstring:
            for line in docstring.splitlines():
                self.add_line(line, sourcename)

        # Call parent with no_docstring=True to avoid redundant lookup attempts
        try:
            super().add_content(more_content, no_docstring=True)
        except TypeError:
            super().add_content(more_content)


def setup(app):
    app.setup_extension("sphinx.ext.autodoc")
    app.add_autodocumenter(TaskDocumenter)
    return {"version": "1.0", "parallel_read_safe": True}

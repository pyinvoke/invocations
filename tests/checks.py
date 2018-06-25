from pytest import skip

from invocations.checks import blacken


class checks:

    class blacken_:

        def base_case_is_all_files_and_79_characters(self, ctx):
            blacken(ctx)
            ctx.run.assert_called_once_with(
                "find . -name '*.py' | xargs black -l 79", pty=True
            )

        def check_flag_passed_through(self):
            skip()

        def diff_flag_passed_through(self):
            skip()

        def line_length_configurable(self):
            skip()

        def target_folders_configurable(self):
            skip()

        def subfolders_can_be_ignored(self):
            # TODO: how best to do this? there's no way at all to ignore
            # vendor/ currently, even if you "opt in" you can't give the top
            # level to get tasks.py, setup.py etc as it's recursive by default
            # TODO: probably best to just make it a catchall opts passthru to
            # find???
            skip()

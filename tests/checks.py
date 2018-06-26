from pytest import skip

from invocations.checks import blacken


class checks:

    class blacken_:

        def base_case_is_all_files_and_79_characters(self, ctx):
            blacken(ctx)
            ctx.run.assert_called_once_with(
                "find . -name '*.py' | xargs black -l 79", pty=True
            )

        def line_length_configurable(self, ctx):
            blacken(ctx, line_length=80)
            ctx.run.assert_called_once_with(
                "find . -name '*.py' | xargs black -l 80", pty=True
            )

        def target_folders_configurable(self, ctx):
            blacken(ctx, folder=["foo", "bar"])
            ctx.run.assert_called_once_with(
                "find foo bar -name '*.py' | xargs black -l 79", pty=True
            )

        def check_flag_passed_through(self, ctx):
            blacken(ctx, check=True)
            ctx.run.assert_called_once_with(
                "find . -name '*.py' | xargs black -l 79 --check", pty=True
            )

        def diff_flag_passed_through(self, ctx):
            blacken(ctx, diff=True)
            ctx.run.assert_called_once_with(
                "find . -name '*.py' | xargs black -l 79 --diff", pty=True
            )

        def multiple_options_given_simultaneously(self, ctx):
            blacken(
                ctx,
                diff=True,
                check=True,
                line_length=80,
                folder=["foo", "bar"],
            )
            ctx.run.assert_called_once_with(
                "find foo bar -name '*.py' | xargs black -l 80 --check --diff",
                pty=True,
            )

        def subfolders_can_be_ignored(self):
            # TODO: how best to do this? there's no way at all to ignore
            # vendor/ currently, even if you "opt in" you can't give the top
            # level to get tasks.py, setup.py etc as it's recursive by default
            # TODO: probably best to just make it a catchall opts passthru to
            # find???
            skip()

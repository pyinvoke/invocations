import pytest

from invocations.checks import blacken


class checks:
    class blacken_:
        @pytest.mark.parametrize(
            "kwargs,command",
            [
                (dict(), "find . -name '*.py' | xargs black -l 79"),
                (
                    dict(line_length=80),
                    "find . -name '*.py' | xargs black -l 80",
                ),
                (
                    dict(folders=["foo", "bar"]),
                    "find foo bar -name '*.py' | xargs black -l 79",
                ),
                (
                    # Explicit invocation that matches a default CLI
                    # invocation, since 'folders' is an iterable and thus shows
                    # up as an empty list in real life. Ehhh.
                    dict(folders=[]),
                    "find . -name '*.py' | xargs black -l 79",
                ),
                (
                    dict(check=True),
                    "find . -name '*.py' | xargs black -l 79 --check",
                ),
                (
                    dict(diff=True),
                    "find . -name '*.py' | xargs black -l 79 --diff",
                ),
                (
                    dict(
                        diff=True,
                        check=True,
                        line_length=80,
                        folders=["foo", "bar"],
                    ),
                    "find foo bar -name '*.py' | xargs black -l 80 --check --diff",  # noqa
                ),
                (
                    dict(find_opts="-and -not -name foo"),
                    "find . -name '*.py' -and -not -name foo | xargs black -l 79",  # noqa
                ),
            ],
            ids=[
                "base case is all files and 79 characters",
                "line length controllable",
                "folders controllable",
                "folders real default value",
                "check flag passed through",
                "diff flag passed through",
                "most args combined",
                "find opts controllable",
            ],
        )
        def runs_black(self, ctx, kwargs, command):
            blacken(ctx, **kwargs)
            ctx.run.assert_called_once_with(command, pty=True)

        def folders_configurable(self, ctx):
            # Just config -> works fine
            ctx.blacken = dict(folders=["elsewhere"])
            blacken(ctx)
            assert "elsewhere" in ctx.run_command

        def folders_config_loses_to_runtime(self, ctx):
            # Config + CLI opt -> CLI opt wins
            ctx.blacken = dict(folders=["nowhere"])
            blacken(ctx, folders=["nowhere"])
            assert "nowhere" in ctx.run_command

        def find_opts_configurable(self, ctx):
            ctx.blacken = dict(find_opts="-and -not -name foo.py")
            blacken(ctx)
            assert (
                "find . -name '*.py' -and -not -name foo.py" in ctx.run_command
            )

        def find_opts_config_loses_to_runtime(self, ctx):
            ctx.blacken = dict(find_opts="-and -not -name foo.py")
            blacken(ctx, find_opts="-or -name '*.js'")
            assert "find . -name '*.py' -or -name '*.js'" in ctx.run_command

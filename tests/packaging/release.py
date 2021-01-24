from __future__ import unicode_literals, print_function

from contextlib import contextmanager
from os import path
import re
import sys

from invoke.vendor.six import PY2
from invoke.vendor.lexicon import Lexicon
from invoke import MockContext, Result, Config, Exit
from mock import Mock, patch
from pytest import skip
from pytest_relaxed import trap, raises

from invocations.packaging.semantic_version_monkey import Version
from invocations.packaging.release import (
    Changelog,
    Release,
    Tag,
    UndefinedReleaseType,
    VersionFile,
    _latest_and_next_version,
    _latest_feature_bucket,
    _release_and_issues,
    _release_line,
    all_,
    build,
    load_version,
    status,
)


class release_line_:
    def assumes_bugfix_if_release_branch(self):
        c = MockContext(run=Result("2.7"))
        assert _release_line(c)[1] == Release.BUGFIX

    def assumes_feature_if_main(self):
        c = MockContext(run=Result("main"))
        assert _release_line(c)[1] == Release.FEATURE

    def assumes_feature_if_master(self):
        c = MockContext(run=Result("master"))
        assert _release_line(c)[1] == Release.FEATURE

    def is_undefined_if_arbitrary_branch_name(self):
        c = MockContext(run=Result("yea-whatever"))
        assert _release_line(c)[1] == Release.UNDEFINED

    def is_undefined_if_specific_commit_checkout(self):
        # Just a sanity check; current logic doesn't differentiate between e.g.
        # 'gobbledygook' and 'HEAD'.
        c = MockContext(run=Result("HEAD"))
        assert _release_line(c)[1] == Release.UNDEFINED


class latest_feature_bucket_:
    def base_case_of_single_release_family(self):
        bucket = _latest_feature_bucket(
            dict.fromkeys(["unreleased_1_feature"])
        )
        assert bucket == "unreleased_1_feature"

    def simple_ordering_by_bucket_number(self):
        bucket = _latest_feature_bucket(
            dict.fromkeys(["unreleased_1_feature", "unreleased_2_feature"])
        )
        assert bucket == "unreleased_2_feature"

    def ordering_goes_by_numeric_not_lexical_order(self):
        bucket = _latest_feature_bucket(
            dict.fromkeys(
                [
                    "unreleased_1_feature",
                    # Yes, releases like 10.x or 17.x are unlikely, but
                    # definitely plausible - think modern Firefox for example.
                    "unreleased_10_feature",
                    "unreleased_23_feature",
                    "unreleased_202_feature",
                    "unreleased_17_feature",
                    "unreleased_2_feature",
                ]
            )
        )
        assert bucket == "unreleased_202_feature"


class release_and_issues_:
    class bugfix:
        # TODO: factor out into setup() so each test has some excluded/ignored
        # data in it - helps avoid naive implementation returning x[0] etc.

        def no_unreleased(self):
            release, issues = _release_and_issues(
                changelog={"1.1": [], "1.1.0": [1, 2]},
                branch="1.1",
                release_type=Release.BUGFIX,
            )
            assert release == "1.1.0"
            assert issues == []

        def has_unreleased(self):
            skip()

    class feature:
        def no_unreleased(self):
            # release is None, issues is empty list
            release, issues = _release_and_issues(
                changelog={"1.0.1": [1], "unreleased_1_feature": []},
                branch="main",
                release_type=Release.FEATURE,
            )
            assert release is None
            assert issues == []

        def has_unreleased(self):
            # release is still None, issues is nonempty list
            release, issues = _release_and_issues(
                changelog={"1.0.1": [1], "unreleased_1_feature": [2, 3]},
                branch="main",
                release_type=Release.FEATURE,
            )
            assert release is None
            assert issues == [2, 3]

    def undefined_always_returns_None_and_empty_list(self):
        skip()


class find_package_:
    def can_be_short_circuited_with_config_value(self):
        # TODO: should we just bundle this + the version part into one
        # function and setting? do we ever peep into the package for anything
        # else besides version module?
        skip()

    def seeks_directories_with_init_py_in_em(self):
        skip()

    def blacklists_common_non_public_modules(self):
        skip()

    def errors_if_cannot_find_anything(self):
        skip()

    def errors_if_ambiguous_results(self):
        # I.e. >1 possible result
        skip()


class load_version_:
    def setup(self):
        sys.path.insert(0, support_dir)

    def teardown(self):
        sys.path.remove(support_dir)

    def _expect_version(self, expected, config_val=None):
        config = {"package": "fakepackage"}
        if config_val is not None:
            config["version_module"] = config_val
        c = MockContext(Config(overrides={"packaging": config}))
        assert load_version(c) == expected

    # NOTE: these all also happen to test the Python bug re: a unicode value
    # given to `__import__(xxx, fromlist=[u'onoz'])`. No real point making
    # another one.

    def defaults_to_underscore_version(self):
        self._expect_version("1.0.0")

    def can_configure_which_module_holds_version_data(self):
        self._expect_version("1.0.1", config_val="otherversion")

    def errors_usefully_if_version_module_not_found(self):
        skip()


class latest_and_next_version_:
    def next_patch_of_bugfix_release(self):
        versions = _latest_and_next_version(
            Lexicon(
                {
                    "release_type": Release.BUGFIX,
                    "latest_line_release": Version("1.2.2"),
                    "latest_overall_release": Version("1.4.1"),  # realism!
                }
            )
        )
        assert versions == (Version("1.2.2"), Version("1.2.3"))

    def next_minor_of_feature_release(self):
        versions = _latest_and_next_version(
            Lexicon(
                {
                    "release_type": Release.FEATURE,
                    "latest_line_release": None,  # realism!
                    "latest_overall_release": Version("1.2.2"),
                }
            )
        )
        assert versions == (Version("1.2.2"), Version("1.3.0"))


# Multi-dimensional scenarios, in relatively arbitrary nesting order:
# - what type of release we're talking about (based on branch name)
# - whether there appear to be unreleased issues in the changelog
# - comparison of version file contents w/ latest release in changelog
# TODO: ... (pypi release, etc)

support_dir = path.join(path.dirname(__file__), "_support")

# Sentinel for targeted __import__ mocking. Is a string so that it can be
# expected in tests about the version file, etc.
# NOTE: needs to not shadow any real imported module name!
FAKE_PACKAGE = "fakey_mcfakerson_not_real_in_any_way"

# NOTE: can't easily slap this on the test class itself due to using inner
# classes. If we can get the inner classes to not only copy attributes but also
# decorators (seems unlikely?), we could organize more "naturally".
# NOTE: OTOH, it's actually nice to use this in >1 top level class, so...meh?
@contextmanager
def _mock_context(self):
    """
    Context manager for a mocked Invoke context + other external patches.

    Specifically:

    - Examine test class attributes for configuration; this allows easy
      multidimensional test setup.
    - Where possible, the code under test relies on calling shell commands via
      the Context object, so we pass in a MockContext for that.
    - Where not possible (eg things which must be Python-level and not
      shell-level, such as version imports), mock with the 'mock' lib as usual.

    The MockContext's `run` method has been further mocked by wrapping it in a
    pass-through `mock.Mock`. It will act like regular `MockContext.run`
    (returning the result value it's been configured to return) but will be a
    `mock.Mock` object and thus exhibit all the usual call-tracking attributes
    and methods such as ``.called``, ``.call_args_list``, etc.

    :yields:
        an `invoke.context.MockContext` created & modified as described above.
    """
    #
    # Generate config & context from attrs
    #

    changelog_file = "{}.rst".format(self._changelog)
    config = Config(
        overrides={
            "packaging": {
                "changelog_file": path.join(support_dir, changelog_file),
                "package": FAKE_PACKAGE,
            }
        }
    )
    tag_output = ""
    if hasattr(self, "_tags"):
        tag_output = "\n".join(self._tags) + "\n"
    # NOTE: Result first posarg is stdout string data.
    run_results = {
        # Branch detection
        "git rev-parse --abbrev-ref HEAD": self._branch,
        # Changelog update action - just here so it can be called
        re.compile(r"\$EDITOR.*"): True,
        # Git tags
        "git tag": tag_output,
        # Git status/commit/tagging
        re.compile("git tag .*"): True,
        re.compile("git commit.*"): True,
        # NOTE: some tests will need to override this, for now default to a
        # result that implies a commit is needed
        'git status --porcelain | egrep -v "^\\?"': Result(
            "M somefile", exited=0
        ),
    }
    context = MockContext(config=config, run=run_results, repeat=True)

    #
    # Execute converge() inside a mock environment
    #

    # Allow targeted import mocking, leaving regular imports alone.
    real_import = __import__

    def fake_import(*args, **kwargs):
        if args[0] is not FAKE_PACKAGE:
            return real_import(*args, **kwargs)
        return Mock(_version=Mock(__version__=self._version))

    # Because I can't very well patch six.moves.builtins itself, can I? =/
    builtins = "__builtin__" if PY2 else "builtins"
    import_patcher = patch(
        "{}.__import__".format(builtins), side_effect=fake_import
    )

    with import_patcher:
        yield context


def _mock_status(self):
    with _mock_context(self) as c:
        return status(c)


@trap
def _expect_actions(self, *actions):
    _mock_status(self)
    stdout = sys.stdout.getvalue()
    for action in actions:
        # Check for action's text value in the table which gets printed.
        # (Actual table formatting is tested in an individual test.)
        err = "Didn't find {} in stdout:\n\n{}".format(action, stdout)
        assert action.value in stdout, err


class status_:
    class overall_behavior:
        _branch = "1.1"
        _changelog = "unreleased_1.1_bugs"
        _version = "1.1.1"
        _tags = ("1.1.0", "1.1.1")

        @trap
        def displays_expectations_and_component_statuses(self):
            _mock_status(self)

            # TODO: make things more organic/specific/less tabular:
            #
            # current git branch: xxx (implies type yyy)
            # changelog: xxx
            # so the next release would be: a.b.c (or: 'so the release we're
            # cutting/expecting is a.b.c')
            # version file: <status output including current value>
            # git tag: <status output saying found/not found> (maybe including
            # latest that is found? that's extra logic...)
            # etc...

            parts = dict(
                changelog=Changelog.NEEDS_RELEASE.value,
                version=VersionFile.NEEDS_BUMP.value,
                tag=Tag.NEEDS_CUTTING.value,
            )
            for part in parts:
                parts[part] = re.escape(parts[part])
            parts["header_footer"] = r"-+ +-+"
            # NOTE: forces impl to follow specific order, which is good
            regex = r"""
{header_footer}
Changelog +{changelog}
Version +{version}
Tag +{tag}
{header_footer}
""".format(
                **parts
            ).strip()
            output = sys.stdout.getvalue()
            err = "Expected:\n\n{}\n\nGot:\n\n{}".format(regex, output)
            err += "\n\nRepr edition...\n\n"
            err += "Expected:\n\n{!r}\n\nGot:\n\n{!r}".format(regex, output)
            assert re.match(regex, output), err

        @trap  # just for cleaner test output
        def returns_lexica_for_reuse(self):
            actions = Lexicon(
                changelog=Changelog.NEEDS_RELEASE,
                version=VersionFile.NEEDS_BUMP,
                tag=Tag.NEEDS_CUTTING,
            )
            found_actions, found_state = _mock_status(self)
            assert found_actions == actions
            # Spot check state, don't need to check whole thing...
            assert found_state.branch == self._branch
            assert found_state.latest_version == Version("1.1.1")
            assert found_state.tags == [Version(x) for x in self._tags]

    # TODO: I got this attribute jazz working in pytest but see if there is a
    # 'native' pytest feature that works better (while still in conjunction
    # with nested tasks, ideally)
    class release_line_branch:
        _branch = "1.1"

        class unreleased_issues:
            _changelog = "unreleased_1.1_bugs"

            class file_version_equals_latest_in_changelog:
                _version = "1.1.1"

                class tags_only_exist_for_past_releases:
                    _tags = ("1.1.0", "1.1.1")

                    def changelog_release_version_update_tag_update(self):
                        _expect_actions(
                            self,
                            Changelog.NEEDS_RELEASE,
                            VersionFile.NEEDS_BUMP,
                            Tag.NEEDS_CUTTING,
                        )

            class version_file_is_newer:
                _version = "1.1.2"

                class tags_only_exist_for_past_releases:
                    _tags = ("1.1.0", "1.1.1")

                    def changelog_release_version_okay_tag_update(self):
                        _expect_actions(
                            self,
                            Changelog.NEEDS_RELEASE,
                            VersionFile.OKAY,
                            Tag.NEEDS_CUTTING,
                        )

            class changelog_version_is_newer:
                _version = "1.1.0"
                # Undefined situation - unsure how/whether to test

        class no_unreleased_issues:
            _changelog = "no_unreleased_1.1_bugs"

            class file_version_equals_latest_in_changelog:
                _version = "1.1.2"

                class tag_for_new_version_present:
                    _tags = ("1.1.0", "1.1.1", "1.1.2")

                    def no_updates_necessary(self):
                        _expect_actions(
                            self, Changelog.OKAY, VersionFile.OKAY, Tag.OKAY
                        )

                class tag_for_new_version_missing:
                    _tags = ("1.1.0", "1.1.1")

                    def tag_needs_cutting_still(self):
                        _expect_actions(
                            self,
                            Changelog.OKAY,
                            VersionFile.OKAY,
                            Tag.NEEDS_CUTTING,
                        )

            class version_file_out_of_date:
                _version = "1.1.1"

                class tag_missing:
                    _tags = ("1.1.0", "1.1.1")  # no 1.1.2

                    def changelog_okay_version_needs_bump_tag_needs_cut(self):
                        _expect_actions(
                            self,
                            Changelog.OKAY,
                            VersionFile.NEEDS_BUMP,
                            Tag.NEEDS_CUTTING,
                        )

                # TODO: as in other TODOs, tag can't be expected to exist/be up
                # to date if any other files are also not up to date. so tag
                # present but version file out of date, makes no sense, would
                # be an error.

            class version_file_is_newer:
                _version = "1.1.3"

                def both_technically_okay(self):
                    skip()  # see TODO below
                    _expect_actions(
                        self,
                        # TODO: display a 'warning' state noting that your
                        # version outpaces your changelog despite your
                        # changelog having no unreleased stuff in it. Still
                        # "Okay" (no action needed), not an error per se, but
                        # still "strange".
                        Changelog.OKAY,
                        VersionFile.OKAY,
                    )

    class main_branch:
        _branch = "main"

        class unreleased_issues:
            _changelog = "unreleased_1.x_features"

            class file_version_equals_latest_in_changelog:
                _version = "1.0.1"

                class latest_tag_same_as_file_version:
                    _tags = ("1.0.0", "1.0.1")

                    def changelog_release_version_update_tag_cut(self):
                        # TODO: do we want some sort of "and here's _what_ you
                        # ought to be adding as the new release and/or version
                        # value" aspect to the actions? can leave up to user
                        # for now, but, more automation is better.
                        _expect_actions(
                            self,
                            Changelog.NEEDS_RELEASE,
                            VersionFile.NEEDS_BUMP,
                            Tag.NEEDS_CUTTING,
                        )

                # TODO: if there's somehow a tag present for a release as yet
                # uncut...which makes no sense as changelog still has no
                # release. Would represent error state!

            # TODO: what if the version file is newer _but not what it needs to
            # be for the branch_? e.g. if it was 1.0.2 here (where latest
            # release is 1.0.1 but branch (main) implies desire is 1.1.0)?

            class version_file_is_newer:
                _version = "1.1.0"

                class new_tag_not_present:
                    _tags = ("1.0.1",)

                    def changelog_release_version_okay(self):
                        _expect_actions(
                            self,
                            # TODO: same as above re: suggesting the release
                            # value to the edit step
                            Changelog.NEEDS_RELEASE,
                            VersionFile.OKAY,
                            Tag.NEEDS_CUTTING,
                        )

            class changelog_version_is_newer:
                _version = "1.2.0"
                # TODO: as with bugfix branches, this is undefined, except here
                # it's even moreso because...well it's even more wacky. why
                # would we have anything >1.1.0 when the changelog itself only
                # even goes up to 1.0.x??

        class no_unreleased_issues:
            _changelog = "no_unreleased_1.x_features"

            class file_version_equals_latest_in_changelog:
                _version = "1.1.0"

                class tag_present:
                    _tags = ("1.0.2", "1.1.0")

                    def all_okay(self):
                        _expect_actions(
                            self, Changelog.OKAY, VersionFile.OKAY, Tag.OKAY
                        )

                class tag_missing:
                    _tags = "1.0.2"

                    def changelog_and_version_okay_tag_needs_cut(self):
                        _expect_actions(
                            self,
                            Changelog.OKAY,
                            VersionFile.OKAY,
                            Tag.NEEDS_CUTTING,
                        )

    class undefined_branch:
        _branch = "whatever"
        _changelog = "nah"
        _tags = ("nope",)

        @raises(UndefinedReleaseType)
        def raises_exception(self):
            _mock_status(self)


def _confirm(which):
    path = "invocations.packaging.release.confirm"

    def _wrapper(f):
        return trap(patch(path, return_value=which)(f))

    return _wrapper


_confirm_true = _confirm(True)
_confirm_false = _confirm(False)


# This is shit but I'm too tired and angry right now to give a fuck.
def _run_all(c, mute=True):
    try:
        return all_(c)
    except Exit:
        if not mute:
            raise


class All:
    "all_"  # mehhh

    # NOTE: just testing the base case of 'everything needs updating',
    # all the permutations are tested elsewhere.
    _branch = "1.1"
    _changelog = "unreleased_1.1_bugs"
    _version = "1.1.1"
    _tags = ("1.1.0",)

    @_confirm_false
    def displays_status_output(self, _):
        with _mock_context(self) as c:
            _run_all(c)
        output = sys.stdout.getvalue()
        for action in (
            Changelog.NEEDS_RELEASE,
            VersionFile.NEEDS_BUMP,
            Tag.NEEDS_CUTTING,
        ):
            err = "Didn't see '{}' text in status output!".format(action.name)
            assert action.value in output, err

    @trap
    @patch("invocations.console.input", return_value="no")
    def prompts_before_taking_action(self, mock_input):
        with _mock_context(self) as c:
            _run_all(c)
        assert mock_input.call_args[0][0] == "Take the above actions? [Y/n] "

    @_confirm_false
    def if_prompt_response_negative_no_action_taken(self, _):
        with _mock_context(self) as c:
            _run_all(c)
        # TODO: move all action-y code into subroutines, then mock them and
        # assert they were never called?
        # Expect that only the status-y run() calls were made.
        assert c.run.call_count == 2
        commands = [x[0][0] for x in c.run.call_args_list]
        assert commands[0].startswith("git rev-parse")
        assert commands[1].startswith("git tag")

    @_confirm_true
    def opens_EDITOR_with_changelog_when_it_needs_update(self, _):
        with _mock_context(self) as c:
            _run_all(c)
            # Grab changelog path from the context config, why not
            path = c.config.packaging.changelog_file
            # TODO: real code should probs expand EDITOR explicitly so it can
            # run w/o a shell wrap / require a full env?
            cmd = "$EDITOR {}".format(path)
            c.run.assert_any_call(cmd, pty=True, hide=False)

    @_confirm_true
    def opens_EDITOR_with_version_file_when_it_needs_update(self, _):
        with _mock_context(self) as c:
            _run_all(c)
            path = "{}/_version.py".format(FAKE_PACKAGE)
            # TODO: real code should probs expand EDITOR explicitly so it can
            # run w/o a shell wrap / require a full env?
            cmd = "$EDITOR {}".format(path)
            c.run.assert_any_call(cmd, pty=True, hide=False)

    @_confirm_true
    def commits_and_adds_git_tag_when_needs_cutting(self, _):
        with _mock_context(self) as c:
            _run_all(c)
            version = "1.1.2"  # as changelog has issues & prev was 1.1.1
            # Ensure the commit necessity test happened. (Default mock_context
            # sets it up to result in a commit being necessary.)
            check = 'git status --porcelain | egrep -v "^\\?"'
            c.run.assert_any_call(check, hide=True, warn=True)
            commit = 'git commit -am "Cut {}"'.format(version)
            # TODO: annotated, signed, etc?
            tag = "git tag {}".format(version)
            for cmd in (commit, tag):
                c.run.assert_any_call(cmd, hide=False)

    @_confirm_true
    def does_not_commit_if_no_commit_necessary(self, _):
        with _mock_context(self) as c:
            # Set up for a no-commit-necessary result to check command
            check = 'git status --porcelain | egrep -v "^\\?"'
            c.set_result_for("run", check, Result("", exited=1))
            _run_all(c)
            # Expect NO git commit
            commands = [x[0][0] for x in c.run.call_args_list]
            assert not any(x.startswith("git commit") for x in commands)
            # Expect git tag
            c.run.assert_any_call("git tag 1.1.2", hide=False)

    def reruns_status_at_end_as_sanity_check(self):
        # I.e. you might have screwed up editing one of the files...
        skip()

    # Don't want a full re-enactment of status_ test tree, but do want to spot
    # check that actions not needing to be taken, aren't...
    class lack_of_action:
        _changelog = "no_unreleased_1.1_bugs"

        @_confirm_true
        def no_changelog_update_needed_means_no_changelog_edit(self, _):
            with _mock_context(self) as c:
                _run_all(c)
                # TODO: as with the 'took no actions at all' test above,
                # proving a negative sucks - eventually make this subroutine
                # assert based. Meh.
                path = c.config.packaging.changelog_file
                cmd = "$EDITOR {}".format(path)
                err = "Saw {!r} despite changelog not needing update!".format(
                    cmd
                )
                assert cmd not in [x[0][0] for x in c.run.call_args_list], err

    # TODO: rest...


# NOTE: yea...this kinda pushes the limits of sane TDD...meh
# NOTE: possible that the actual codes blessings emits differ based on
# termcap/etc; consider sucking it up and just calling blessings directly in
# that case, even though it makes the tests kinda tautological.
# TODO: yes, when I personally went from TERM=xterm-256color to
# TERM=screen-256color, that made these tests break! Updating test machinery to
# account for now, but...not ideal!
class component_state_enums_contain_human_readable_values:
    class changelog:
        def okay(self):
            expected = "\x1b[32m\u2714 no unreleased issues\x1b(B\x1b[m"
            assert Changelog.OKAY.value == expected

        def needs_release(self):
            expected = "\x1b[31m\u2718 needs :release: entry\x1b(B\x1b[m"
            assert Changelog.NEEDS_RELEASE.value == expected

    class version_file:
        def okay(self):
            expected = "\x1b[32m\u2714 version up to date\x1b(B\x1b[m"
            assert VersionFile.OKAY.value == expected

        def needs_bump(self):
            expected = "\x1b[31m\u2718 needs version bump\x1b(B\x1b[m"
            assert VersionFile.NEEDS_BUMP.value == expected

    class tag:
        def okay(self):
            assert Tag.OKAY.value == "\x1b[32m\u2714 all set\x1b(B\x1b[m"

        def needs_cutting(self):
            expected = "\x1b[31m\u2718 needs cutting\x1b(B\x1b[m"
            assert Tag.NEEDS_CUTTING.value == expected


@contextmanager
def _expect_setuppy(
    flags, python="python", config=None, yield_rmtree=False
):
    kwargs = dict(run=True)
    if config is not None:
        kwargs["config"] = config
    c = MockContext(**kwargs)
    # Make sure we don't actually run rmtree regardless
    with patch("invocations.packaging.release.rmtree") as rmtree:
        if yield_rmtree:
            yield c, rmtree
        else:
            yield c
    c.run.assert_called_once_with("{} setup.py {}".format(python, flags))


class build_:
    sdist_flags = "sdist -d dist"
    wheel_flags = "build -b build bdist_wheel -d dist"
    both_flags = "sdist -d dist build -b build bdist_wheel -d dist"
    oh_dir = "sdist -d {0} build -b {1} bdist_wheel -d {0}".format(
        path.join("dir", "dist"), path.join("dir", "build")
    )

    class sdist:
        def indicates_sdist_builds(self):
            with _expect_setuppy(self.both_flags) as c:
                build(c, sdist=True)

        def on_by_default(self):
            with _expect_setuppy(self.both_flags) as c:
                build(c)

        def can_be_disabled_via_config(self):
            config = Config(dict(packaging=dict(sdist=False)))
            with _expect_setuppy(self.wheel_flags, config=config) as c:
                build(c)

        def kwarg_wins_over_config(self):
            config = Config(dict(packaging=dict(sdist=True)))
            with _expect_setuppy(self.wheel_flags, config=config) as c:
                build(c, sdist=False)

    class wheel:
        def indicates_explicit_build_and_wheel(self):
            with _expect_setuppy(self.wheel_flags) as c:
                build(c, sdist=False, wheel=True)

        def on_by_default(self):
            with _expect_setuppy(self.wheel_flags) as c:
                build(c, sdist=False)

        def can_be_disabled_via_config(self):
            config = Config(dict(packaging=dict(wheel=False)))
            with _expect_setuppy(self.sdist_flags, config=config) as c:
                build(c)

        def kwarg_wins_over_config(self):
            config = Config(dict(packaging=dict(wheel=True)))
            with _expect_setuppy(self.sdist_flags, config=config) as c:
                build(c, wheel=False)

    @raises(Exit)
    def kabooms_if_sdist_and_wheel_both_False(self):
        build(MockContext(), sdist=False, wheel=False)

    class directory:
        def defaults_to_blank_or_cwd(self):
            with _expect_setuppy(self.both_flags) as c:
                build(c)

        def if_given_affects_build_and_dist_dirs(self):
            with _expect_setuppy(self.oh_dir) as c:
                build(c, directory="dir")

        def may_be_given_via_config(self):
            config = Config(dict(packaging=dict(directory="dir")))
            with _expect_setuppy(self.oh_dir, config=config) as c:
                build(c)

        def kwarg_wins_over_config(self):
            config = Config(dict(packaging=dict(directory="NOTdir")))
            with _expect_setuppy(self.oh_dir, config=config) as c:
                build(c, directory="dir")

    class python:
        def defaults_to_python(self):
            with _expect_setuppy(self.both_flags, python="python") as c:
                build(c, python="python")

        def may_be_overridden(self):
            with _expect_setuppy(self.both_flags, python="fython") as c:
                build(c, python="fython")

        def can_be_given_via_config(self):
            config = Config(dict(packaging=dict(python="python17")))
            with _expect_setuppy(
                self.both_flags, config=config, python="python17"
            ) as c:
                build(c)

        def kwarg_wins_over_config(self):
            config = Config(dict(packaging=dict(python="python17")))
            with _expect_setuppy(
                self.both_flags, config=config, python="python99"
            ) as c:
                build(c, python="python99")

    class clean:
        def _expect_with_rmtree(self):
            return _expect_setuppy(self.both_flags, yield_rmtree=True)

        def defaults_to_False_meaning_no_clean(self):
            with self._expect_with_rmtree() as (c, rmtree):
                build(c)
            assert not rmtree.called

        def True_means_clean_both_dirs(self):
            with self._expect_with_rmtree() as (c, rmtree):
                build(c, clean=True)
            rmtree.assert_any_call("dist", ignore_errors=True)
            rmtree.assert_any_call("build", ignore_errors=True)

        def understands_directory_option(self):
            with _expect_setuppy(self.oh_dir, yield_rmtree=True) as (
                c,
                rmtree,
            ):
                build(c, directory="dir", clean=True)
            rmtree.assert_any_call(
                path.join("dir", "build"), ignore_errors=True
            )
            rmtree.assert_any_call(
                path.join("dir", "dist"), ignore_errors=True
            )

        def may_be_configured(self):
            config = Config(dict(packaging=dict(clean=True)))
            with _expect_setuppy(
                self.both_flags, yield_rmtree=True, config=config
            ) as (c, rmtree):
                build(c)
            rmtree.assert_any_call("dist", ignore_errors=True)
            rmtree.assert_any_call("build", ignore_errors=True)

        def kwarg_wins_over_config(self):
            config = Config(dict(packaging=dict(clean=True)))
            with _expect_setuppy(
                self.both_flags, yield_rmtree=True, config=config
            ) as (c, rmtree):
                build(c, clean=False)
            rmtree.assert_any_call("dist", ignore_errors=True)
            rmtree.assert_any_call("build", ignore_errors=True)

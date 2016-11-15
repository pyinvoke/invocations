from __future__ import unicode_literals, print_function

from contextlib import contextmanager
from os import path
import re
import sys

from invoke.vendor.six import PY2

from mock import Mock, patch
from spec import Spec, trap, skip, eq_, ok_, raises

from invoke import MockContext, Result, Config

from invocations.packaging.release import (
    release_line, latest_feature_bucket, release_and_issues, all_, status,
    Changelog, Release, VersionFile, UndefinedReleaseType, load_version
)


class release_line_(Spec):
    def assumes_bugfix_if_release_branch(self):
        c = MockContext(run=Result("2.7"))
        eq_(release_line(c)[1], Release.BUGFIX)

    def assumes_feature_if_master(self):
        c = MockContext(run=Result("master"))
        eq_(release_line(c)[1], Release.FEATURE)

    def is_undefined_if_arbitrary_branch_name(self):
        c = MockContext(run=Result("yea-whatever"))
        eq_(release_line(c)[1], Release.UNDEFINED)

    def is_undefined_if_specific_commit_checkout(self):
        # Just a sanity check; current logic doesn't differentiate between e.g.
        # 'gobbledygook' and 'HEAD'.
        c = MockContext(run=Result("HEAD"))
        eq_(release_line(c)[1], Release.UNDEFINED)


class latest_feature_bucket_(Spec):
    def base_case_of_single_release_family(self):
        eq_(
            latest_feature_bucket(dict.fromkeys(['unreleased_1_feature'])),
            'unreleased_1_feature'
        )

    def simple_ordering_by_bucket_number(self):
        eq_(
            latest_feature_bucket(dict.fromkeys([
                'unreleased_1_feature',
                'unreleased_2_feature',
            ])),
            'unreleased_2_feature'
        )

    def ordering_goes_by_numeric_not_lexical_order(self):
        eq_(
            latest_feature_bucket(dict.fromkeys([
                'unreleased_1_feature',
                # Yes, releases like 10.x or 17.x are unlikely, but definitely
                # plausible - think modern Firefox for example.
                'unreleased_10_feature',
                'unreleased_23_feature',
                'unreleased_202_feature',
                'unreleased_17_feature',
                'unreleased_2_feature',
            ])),
            'unreleased_202_feature'
        )


class release_and_issues_(Spec):
    class bugfix:
        # TODO: factor out into setup() so each test has some excluded/ignored
        # data in it - helps avoid naive implementation returning x[0] etc.

        def no_unreleased(self):
            release, issues = release_and_issues(
                changelog={'1.1': [], '1.1.0': [1, 2]},
                branch='1.1',
                release_type=Release.BUGFIX,
            )
            eq_(release, '1.1.0')
            eq_(issues, [])

        def has_unreleased(self):
            skip()

    class feature:
        def no_unreleased(self):
            # release is None, issues is empty list
            release, issues = release_and_issues(
                changelog={'1.0.1': [1], 'unreleased_1_feature': []},
                branch='master',
                release_type=Release.FEATURE,
            )
            eq_(release, None)
            eq_(issues, [])

        def has_unreleased(self):
            # release is still None, issues is nonempty list
            release, issues = release_and_issues(
                changelog={'1.0.1': [1], 'unreleased_1_feature': [2, 3]},
                branch='master',
                release_type=Release.FEATURE,
            )
            eq_(release, None)
            eq_(issues, [2, 3])

    def undefined_always_returns_None_and_empty_list(self):
        skip()


class find_package_(Spec):
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


class load_version_(Spec):
    def setup(self):
        sys.path.insert(0, support_dir)

    def teardown(self):
        sys.path.remove(support_dir)

    def _expect_version(self, expected, config_val=None):
        config = {
            'package': 'fakepackage',
        }
        if config_val is not None:
            config['version_module'] = config_val
        c = MockContext(Config(overrides={'packaging': config}))
        eq_(load_version(c), expected)

    # NOTE: these all also happen to test the Python bug re: a unicode value
    # given to `__import__(xxx, fromlist=[u'onoz'])`. No real point making
    # another one.

    def defaults_to_underscore_version(self):
        self._expect_version('1.0.0')

    def can_configure_which_module_holds_version_data(self):
        self._expect_version('1.0.1', config_val='otherversion')

    def errors_usefully_if_version_module_not_found(self):
        skip()


# Multi-dimensional scenarios, in relatively arbitrary nesting order:
# - what type of release we're talking about (based on branch name)
# - whether there appear to be unreleased issues in the changelog
# - comparison of version file contents w/ latest release in changelog
# TODO: ... (git tag, pypi release, etc)

support_dir = path.join(path.dirname(__file__), '_support')

# Sentinel for targeted __import__ mocking. Is a string so that it can be
# expected in tests about the version file, etc.
# NOTE: needs to not shadow any real imported module name!
FAKE_PACKAGE = 'fakey_mcfakerson_not_real_in_any_way'

# NOTE: can't slap this on the test class itself due to how Spec has to handle
# inner classes (basically via getattr chain). If that can be converted to true
# inheritance (seems unlikely), we could organize more "naturally".
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

    changelog_file = '{0}.rst'.format(self._changelog)
    config = Config(overrides={
        'packaging': {
            'changelog_file': path.join(support_dir, changelog_file),
            'package': FAKE_PACKAGE,
        },
    })
    # TODO: if/when regex implemented for MockContext, make these keys less
    # strictly tied to the real implementation.
    run_results = {
        # Branch detection
        "git rev-parse --abbrev-ref HEAD": Result(self._branch),
        # Changelog update action - just here so it can be called
        "$EDITOR {0.packaging.changelog_file}".format(config): Result(),
        # Version file update - ditto
        "$EDITOR {0}/_version.py".format(FAKE_PACKAGE): Result(),
    }
    context = MockContext(config=config, run=run_results)
    # Wrap run() in a Mock too.
    # NOTE: we don't do this inside MockContext itself because that would add a
    # test lib as a runtime dependency =/
    # NOTE: end-running around Context/DataProxy setattr because doing
    # context.run.echo = True (or similar) is too common a use case to be worth
    # breaking just for stupid test monkeypatch purposes
    object.__setattr__(context, 'run', Mock(wraps=context.run))

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
    builtins = '__builtin__' if PY2 else 'builtins'
    import_patcher = patch(
        '{0}.__import__'.format(builtins),
        side_effect=fake_import,
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
        ok_(
            action.value in stdout,
            "Didn't find {0} in stdout:\n\n{1}".format(action, stdout),
        )


class status_(Spec):
    class overall_behavior:
        _branch = '1.1'
        _changelog = 'unreleased_1.1_bugs'
        _version = '1.1.1'

        @trap
        def displays_statuses_in_a_table(self):
            _mock_status(self)
            parts = dict(
                changelog=Changelog.NEEDS_RELEASE.value,
                version=VersionFile.NEEDS_BUMP.value,
            )
            for part in parts:
                parts[part] = re.escape(parts[part])
            parts['header_footer'] = r'-+ +-+'
            regex = r"""
{header_footer}
Changelog +{changelog}
Version +{version}
{header_footer}
""".format(**parts).strip()
            output = sys.stdout.getvalue()
            err = "Expected:\n\n{0}\n\nGot:\n\n{1}".format(regex, output)
            err += "\n\nRepr edition...\n\nExpected:\n\n{0!r}\n\nGot:\n\n{1!r}".format(regex, output) # noqa
            ok_(re.match(regex, output), err)

        @trap # just for cleaner test output
        def returns_actions_dict_for_reuse(self):
            expected = dict(
                changelog=Changelog.NEEDS_RELEASE,
                version=VersionFile.NEEDS_BUMP,
            )
            eq_(_mock_status(self), expected)

    class release_line_branch:
        _branch = '1.1'

        class unreleased_issues:
            _changelog = 'unreleased_1.1_bugs'

            class file_version_equals_latest_in_changelog:
                _version = '1.1.1'

                def changelog_release_version_update(self):
                    _expect_actions(self,
                        Changelog.NEEDS_RELEASE,
                        VersionFile.NEEDS_BUMP,
                    )

            class version_file_is_newer:
                _version = '1.1.2'

                def changelog_release_version_okay(self):
                    _expect_actions(self,
                        Changelog.NEEDS_RELEASE,
                        VersionFile.OKAY,
                    )

            class changelog_version_is_newer:
                _version = '1.1.0'
                # Undefined situation - unsure how/whether to test

        class no_unreleased_issues:
            _changelog = 'no_unreleased_1.1_bugs'

            class file_version_equals_latest_in_changelog:
                _version = '1.1.2'

                def no_updates_necessary(self):
                    _expect_actions(self,
                        Changelog.OKAY,
                        VersionFile.OKAY,
                    )

            class changelog_is_newer:
                _version = '1.1.1'

                def changelog_okay_version_needs_bump(self):
                    _expect_actions(self,
                        Changelog.OKAY,
                        VersionFile.NEEDS_BUMP,
                    )

            class version_file_is_newer:
                _version = '1.1.3'

                def both_technically_okay(self):
                    _expect_actions(self,
                        # TODO: display a 'warning' state noting that your
                        # version outpaces your changelog despite your
                        # changelog having no unreleased stuff in it. Still
                        # "Okay" (no action needed), not an error per se, but
                        # still "strange".
                        Changelog.OKAY,
                        VersionFile.OKAY,
                    )

    class master_branch:
        _branch = 'master'

        class unreleased_issues:
            _changelog = 'unreleased_1.x_features'

            class file_version_equals_latest_in_changelog:
                _version = '1.0.1'

                def changelog_release_version_update(self):
                    # TODO: do we want some sort of "and here's _what_ you
                    # ought to be adding as the new release and/or version
                    # value" aspect to the actions? can leave up to user for
                    # now, but, more automation is better.
                    _expect_actions(self,
                        Changelog.NEEDS_RELEASE,
                        VersionFile.NEEDS_BUMP,
                    )

            # TODO: what if the version file is newer _but not what it needs to
            # be for the branch_? e.g. if it was 1.0.2 here (where latest
            # release is 1.0.1 but branch (master) implies desire is 1.1.0)?

            class version_file_is_newer:
                _version = '1.1.0'

                def changelog_release_version_okay(self):
                    _expect_actions(self,
                        # TODO: same as above re: suggesting the release value
                        # to the edit step
                        Changelog.NEEDS_RELEASE,
                        VersionFile.OKAY,
                    )

            class changelog_version_is_newer:
                _version = '1.2.0'
                # TODO: as with bugfix branches, this is undefined, except here
                # it's even moreso because...well it's even more wacky. why
                # would we have anything >1.1.0 when the changelog itself only
                # even goes up to 1.0.x??

        class no_unreleased_issues:
            _changelog = 'no_unreleased_1.x_features'

    class undefined_branch:
        _branch = "whatever"
        _changelog = "nah"

        @raises(UndefinedReleaseType)
        def raises_exception(self):
            _mock_status(self)


def _confirm(which):
    path = 'invocations.packaging.release.confirm'
    def _wrapper(f):
        return trap(patch(path, return_value=which)(f))
    return _wrapper
_confirm_true = _confirm(True)
_confirm_false = _confirm(False)


class All(Spec):
    "all_" # mehhh

    _branch = '1.1'
    _changelog = 'unreleased_1.1_bugs'
    _version = '1.1.1'

    @_confirm_false
    def displays_status_output(self, _):
        with _mock_context(self) as c:
            all_(c)
        output = sys.stdout.getvalue()
        # Basic spot checks suffice; we test status() explicitly elsewhere.
        for action in (Changelog.NEEDS_RELEASE, VersionFile.NEEDS_BUMP):
            err = "Didn't see '{0}' text in status output!".format(action.name)
            ok_(action.value in output, err)

    @trap
    @patch('invocations.console.input', return_value='no')
    def prompts_before_taking_action(self, mock_input):
        with _mock_context(self) as c:
            all_(c)
        eq_(mock_input.call_args[0][0], "Take the above actions? [Y/n] ")

    @_confirm_false
    def if_prompt_response_negative_no_action_taken(self, _):
        with _mock_context(self) as c:
            all_(c)
        # TODO: move all action-y code into subroutines, then mock them and
        # assert they were never called?
        # Expect that only the status-y run() calls were made.
        eq_(c.run.call_count, 1)
        ok_(c.run.call_args[0][0].startswith('git rev-parse'))

    @_confirm_true
    def opens_EDITOR_with_changelog_when_it_needs_update(self, _):
        with _mock_context(self) as c:
            all_(c)
            # Grab changelog path from the context config, why not
            path = c.config.packaging.changelog_file
            # TODO: real code should probs expand EDITOR explicitly so it can
            # run w/o a shell wrap / require a full env?
            cmd = "$EDITOR {0}".format(path)
            c.run.assert_any_call(cmd, pty=True, hide=False)

    @_confirm_true
    def opens_EDITOR_with_version_file_when_it_needs_update(self, _):
        with _mock_context(self) as c:
            all_(c)
            path = "{0}/_version.py".format(FAKE_PACKAGE)
            # TODO: real code should probs expand EDITOR explicitly so it can
            # run w/o a shell wrap / require a full env?
            cmd = "$EDITOR {0}".format(path)
            c.run.assert_any_call(cmd, pty=True, hide=False)

    def reruns_status_at_end_as_sanity_check(self):
        # I.e. you might have screwed up editing one of the files...
        skip()

    # Don't want a full re-enactment of status_ test tree, but do want to spot
    # check that actions not needing to be taken, aren't...
    class lack_of_action:
        _changelog = 'no_unreleased_1.1_bugs'

        @_confirm_true
        def no_changelog_update_needed_means_no_changelog_edit(self, _):
            with _mock_context(self) as c:
                all_(c)
                # TODO: as with the 'took no actions at all' test above,
                # proving a negative sucks - eventually make this subroutine
                # assert based. Meh.
                path = c.config.packaging.changelog_file
                cmd = "$EDITOR {0}".format(path)
                err = "Saw {0!r} despite changelog not needing update!".format(
                    cmd
                )
                ok_(cmd not in [x[0][0] for x in c.run.call_args_list], err)

    # TODO: rest...


# NOTE: yea...this kinda pushes the limits of sane TDD...meh
# NOTE: possible that the actual codes blessings emits differ based on
# termcap/etc; consider sucking it up and just calling blessings directly in
# that case, even though it makes the tests kinda tautological.
class component_state_enums_contain_human_readable_values(Spec):
    class changelog:
        def okay(self):
            eq_(
                Changelog.OKAY.value,
                "\x1b[32m\u2714 no unreleased issues\x1b(B\x1b[m",
            )

        def needs_release(self):
            eq_(
                Changelog.NEEDS_RELEASE.value,
                "\x1b[31m\u2718 needs :release: entry\x1b(B\x1b[m",
            )

    class version_file:
        def okay(self):
            eq_(
                VersionFile.OKAY.value,
                "\x1b[32m\u2714 version up to date\x1b(B\x1b[m",
            )

        def needs_bump(self):
            eq_(
                VersionFile.NEEDS_BUMP.value,
                "\x1b[31m\u2718 needs version bump\x1b(B\x1b[m",
            )

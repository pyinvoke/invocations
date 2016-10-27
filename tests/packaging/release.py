from __future__ import unicode_literals

from contextlib import nested

from invoke.vendor.six import iteritems

from invoke.vendor.six import text_type
from mock import Mock, patch
from spec import Spec, trap, skip, eq_, raises

from invoke import MockContext, Result, Config

from invocations.packaging.release import (
    converge, release_line, latest_feature_bucket, release_and_issues,
    Changelog, Release, VersionFile, UndefinedReleaseType,
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
            skip()

        def has_unreleased(self):
            # release is still None, issues is nonempty list
            skip()

    def undefined_always_returns_None_and_empty_list(self):
        skip()


# TODO: chop up into more converge() tests
class changelog_needs_release_(Spec):
    class true:
        def master_branch_and_issues_in_unreleased_feature_bucket(self):
            skip()
            c = self._context("master", 'unreleased_1.x_features')
            eq_(changelog_up_to_date(c), True)

    class false:
        def master_branch_and_empty_unreleased_feature_bucket(self):
            skip()
            c = self._context("master", 'no_unreleased_1.x_features')
            eq_(changelog_up_to_date(c), False)


# Multi-dimensional scenarios, in relatively arbitrary nesting order:
# - what type of release we're talking about (based on branch name)
# - whether there appear to be unreleased issues in the changelog
# - comparison of version file contents w/ latest release in changelog
# TODO: ... (git tag, pypi release, etc)


# NOTE: can't slap this on the converge_ class itself due to how Spec has to
# handle inner classes (basically via getattr chain). If that can be converted
# to true inheritance (seems unlikely), we can organize more "naturally".
def _mock_converge(self):
    """
    Run `converge` with a mocked Context & some external mocks where needed.

    Specifically:

    - Examine test class attributes for configuration; this allows easy
      multidimensional test setup.
    - Where possible, the code under test relies on calling shell commands via
      the Context object, so we pass in a MockContext for that.
    - Where not possible (eg things which must be Python-level and not
      shell-level, such as version imports), mock with the 'mock' lib as usual.

    Returns the value of the `converge` call unaltered.
    """
    # Sentinel for targeted __import__ mocking
    PACKAGE = object()

    #
    # Generate config & context from attrs
    #

    config = Config(overrides={
        'packaging': {
            'changelog_file': 'packaging/_support/{0}.rst'.format(
                self._changelog
            ),
            'package': PACKAGE,
        },
    })
    # TODO: if/when regex implemented for MockContext, make these keys less
    # strictly tied to the real implementation.
    run_results = {
        "git rev-parse --abbrev-ref HEAD": Result(self._branch),
    }
    context = MockContext(config=config, run=run_results)
    
    #
    # Execute converge() inside a mock environment
    #

    patches = []

    # Allow targeted import mocking, leaving regular imports alone.
    real_import = __import__
    def fake_import(*args, **kwargs):
        if args[0] is not PACKAGE:
            return real_import(*args, **kwargs)
        return Mock(_version=Mock(__version__=self._version))
    patches.append(patch('__builtin__.__import__', side_effect=fake_import))

    with nested(*patches):
        return converge(context)

# TODO: ditto re: integration with outermost Spec classes
def _expect_actions(self, **kwargs):
    actions, state = _mock_converge(self)
    for component, action in iteritems(kwargs):
        eq_(actions[component], action)


class converge_(Spec):
    class release_line_branch:
        _branch = "1.1"

        class unreleased_issues:
            _changelog = 'unreleased_1.1_bugs'

            class file_version_equals_latest_in_changelog:
                _version = '1.1.1'
                
                def changelog_release_version_update(self):
                    _expect_actions(self,
                        changelog=Changelog.NEEDS_RELEASE,
                        version=VersionFile.NEEDS_BUMP,
                    )

            class version_file_is_newer:
                _version = '1.1.2'

                def changelog_release_version_okay(self):
                    _expect_actions(self,
                        changelog=Changelog.NEEDS_RELEASE,
                        version=VersionFile.OKAY,
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
                        changelog=Changelog.OKAY,
                        version=VersionFile.OKAY,
                    )

            class changelog_is_newer:
                _version = '1.1.1'

                def changelog_okay_version_needs_bump(self):
                    _expect_actions(self,
                        changelog=Changelog.OKAY,
                        version=VersionFile.NEEDS_BUMP,
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
                        changelog=Changelog.OKAY,
                        version=VersionFile.OKAY,
                    )

    class master_branch:
        pass

    class undefined_branch:
        _branch = "whatever"
        _changelog = "nah"

        @raises(UndefinedReleaseType)
        def raises_exception(self):
            _mock_converge(self)



class All(Spec):
    "all_" # mehhh

    def displays_all_component_actions_in_a_table(self):
        skip()

    def display_only_when_dry_run_set(self):
        skip()

    def prompts_to_take_necessary_actions_by_default(self):
        # I.e. --dry-run is nondefault behavior
        # TODO: how to test interactive stuff exactly? how are we doing that in
        # invoke again? maybe we DO need to expose the quirky low level test
        # helpers too...and expect-like stuff...ugh
        skip()

    def prompt_disabled_with_flag(self):
        # TODO: or should it be the default?? feels like no?
        # TODO: what flag exactly? -y? --headless?
        skip()

    def opens_EDITOR_with_changelog_when_it_needs_update(self):
        skip()

    def opens_EDITOR_with_version_file_when_it_needs_update(self):
        skip()

    # TODO: rest...


# Blurgh, nose 1.x isn't super unicode friendly, uses str() etc
def _safe_eq(val1, val2, msg=None):
    if msg is None:
        msg = "{0!r} != {1!r}".format(val1, val2)
    eq_(val1, val2, msg)

# NOTE: yea...this kinda pushes the limits of sane TDD...meh
# NOTE: possible that the actual codes blessings emits differ based on
# termcap/etc; consider sucking it up and just calling blessings directly in
# that case, tautology or no.
class component_state_enums_contain_human_readable_values(Spec):
    class changelog:
        def okay(self):
            _safe_eq(
                Changelog.OKAY.value,
                "\x1b[32m\u2714 up to date\x1b(B\x1b[m",
            )

        def needs_release(self):
            skip()

    class version_file:
        def okay(self):
            skip()

        def needs_bump(self):
            skip()

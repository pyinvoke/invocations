from spec import Spec, trap, skip, eq_

from invoke import MockContext, Result, Config

from invocations.packaging.release import (
    converge, release_line, Release, Changelog, latest_feature_bucket
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


class changelog_needs_release_(Spec):
    # TODO: find way to reuse sphinx conf option instead of duplicating
    # it/requiring use of the invoke-specific conf option. Looks like one can
    # safely chdir to sphinx.source (invoke conf setting) then 'import conf'
    # and examine 'conf.releases_changelog_name' or w/e it is
    def _context(self, branch, file_):
        # Fake git rev-parse output & path to mock changelog
        config = Config(overrides={
            'packaging': {
                'changelog_file': 'packaging/_support/{0}.rst'.format(file_),
            },
        })
        return MockContext(config=config, run=Result(branch))

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


class should_version_(Spec):
    class true:
        def no_pending_changelog_and_changelog_version_newer(self):
            skip()

        def pending_changelog_and_versions_match(self):
            skip()

    class false:
        def no_pending_changelog_and_versions_match(self):
            skip()

        def pending_changelog_and_version_file_newer(self):
            skip()

    class error:
        def no_pending_changelog_and_version_file_newer(self):
            skip()

        def pending_changelog_and_changelog_newer(self):
            skip()



# Multi-dimensional scenarios, in relatively arbitrary nesting order:
# - what type of release we're talking about (based on branch name)
# - whether there appear to be unreleased issues in the changelog
# - comparison of version file contents w/ latest release in changelog
# TODO: ... (git tag, pypi release, etc)


# NOTE: can't slap this on the converge_ class itself due to how Spec has to
# handle inner classes (basically via getattr chain). If that can be converted
# to true inheritance (seems unlikely), we can organize more "naturally".
def _context(self):
    config = Config(overrides={
        'packaging': {
            'changelog_file': 'packaging/_support/{0}.rst'.format(
                self._changelog
            ),
        },
    })
    # TODO: if/when regex implemented for MockContext, make these keys less
    # strictly tied to the real implementation.
    run_results = {
        "git rev-parse --abbrev-ref HEAD": Result(self._branch),
    }
    return MockContext(config=config, run=run_results)


class converge_(Spec):
    class release_line_branch:
        _branch = "1.1"

        class unreleased_issues:
            _changelog = 'unreleased_1.1_bugs'

            def versions_match(self):
                # TODO: actually test version stuff
                actions, state = converge(_context(self))
                eq_(actions['changelog'], Changelog.NEEDS_RELEASE)

            def changelog_newer(self):
                skip()

            def version_newer(self):
                skip()

        class no_unreleased_issues:
            _changelog = 'no_unreleased_1.1_bugs'

            def versions_match(self):
                # TODO: actually test version stuff
                #eq_(changelog_up_to_date(_context(self)), False)
                skip()

            def changelog_newer(self):
                pass

            def version_newer(self):
                pass

    class master_branch:
        pass

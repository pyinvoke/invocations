from spec import Spec, trap, skip, eq_
from mock import Mock

from invoke import MockContext, Result, Config

from invocations.packaging.release import (
    should_changelog, release_line, BUGFIX, FEATURE, UNDEFINED,
    latest_feature_bucket,
)


class dry_run_(Spec):
    @trap
    def changelog_shows_update_if_needs_it(self):
        skip()

    def changelog_ok_if_ok(self):
        skip()


class release_line_(Spec):
    def assumes_bugfix_if_release_branch(self):
        c = MockContext(run=Result("2.7"))
        eq_(release_line(c)[1], BUGFIX)

    def assumes_feature_if_master(self):
        c = MockContext(run=Result("master"))
        eq_(release_line(c)[1], FEATURE)

    def is_undefined_if_arbitrary_branch_name(self):
        c = MockContext(run=Result("yea-whatever"))
        eq_(release_line(c)[1], UNDEFINED)

    def is_undefined_if_specific_commit_checkout(self):
        # Just a sanity check; current logic doesn't differentiate between e.g.
        # 'gobbledygook' and 'HEAD'.
        c = MockContext(run=Result("HEAD"))
        eq_(release_line(c)[1], UNDEFINED)


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


class should_changelog_(Spec):
    # TODO: find way to reuse sphinx conf option instead of duplicating
    # it/requiring use of the invoke-specific conf option.
    def _context(self, branch, file_):
        # Fake git rev-parse output & path to mock changelog
        config = Config(overrides={
            'packaging': {
                'changelog_file': 'packaging/_support/{0}.rst'.format(file_),
            },
        })
        return MockContext(config=config, run=Result(branch))

    class true:
        def release_line_branch_and_issues_in_line_bucket(self):
            c = self._context("1.1", 'outstanding_1.1_issues')
            eq_(should_changelog(c), True)

        def master_branch_and_issues_in_unreleased_feature_bucket(self):
            c = self._context("master", 'unreleased_1.x_features')
            eq_(should_changelog(c), True)

    class false:
        def release_line_branch_and_empty_line_bucket(self):
            skip()

        def master_branch_and_empty_unreleased_feature_bucket(self):
            c = self._context("master", 'no_unreleased_1.x_features')
            eq_(should_changelog(c), False)

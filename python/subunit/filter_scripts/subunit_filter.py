#!/usr/bin/env python3
#  subunit: extensions to python unittest to get test results from subprocesses.
#  Copyright (C) 200-2013  Robert Collins <robertc@robertcollins.net>
#            (C) 2009  Martin Pool
#
#  Licensed under either the Apache License, Version 2.0 or the BSD 3-clause
#  license at the users choice. A copy of both licenses are available in the
#  project source as Apache-2.0 and BSD. You may not use this file except in
#  compliance with one of these two licences.
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under these licenses is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
#  license you chose for the specific language governing permissions and
#  limitations under that license.
#

"""Filter a subunit stream to include/exclude tests.

The default is to strip successful tests.

Tests can be filtered by Python regular expressions with --with and --without,
which match both the test name and the error text (if any).  The result
contains tests which match any of the --with expressions and none of the
--without expressions.  For case-insensitive matching prepend '(?i)'.
Remember to quote shell metacharacters.
"""

import re
import sys
from optparse import OptionParser

# Removed testtools dependency - using subunit implementations instead

from subunit import StreamResultToBytes, read_test_list
from subunit.filters import filter_by_result, find_stream
from subunit.test_results import and_predicates, make_tag_filter


class StreamFilter:
    """Filter stream events based on predicates."""

    def __init__(
        self,
        target,
        filter_success=True,
        filter_skip=False,
        filter_error=False,
        filter_failure=False,
        filter_xfail=False,
        filter_predicate=None,
        fixup_expected_failures=None,
        rename=None,
    ):
        self.target = target
        self.filter_success = filter_success
        self.filter_skip = filter_skip
        self.filter_error = filter_error
        self.filter_failure = filter_failure
        self.filter_xfail = filter_xfail
        self.filter_predicate = filter_predicate
        self.fixup_expected_failures = fixup_expected_failures or frozenset()
        self.rename = rename
        # Track test states
        self._test_started = {}
        self._test_tags = {}

    def startTestRun(self):
        if hasattr(self.target, "startTestRun"):
            self.target.startTestRun()

    def stopTestRun(self):
        if hasattr(self.target, "stopTestRun"):
            self.target.stopTestRun()

    def status(self, test_id=None, test_status=None, test_tags=None, **kwargs):
        """Filter and forward status events."""
        # Handle non-test events
        if test_id is None:
            self.target.status(test_id=test_id, test_status=test_status, test_tags=test_tags, **kwargs)
            return

        # Apply rename if configured
        original_test_id = test_id
        if self.rename:
            test_id = self.rename(test_id)
            kwargs = kwargs.copy() if kwargs else {}

        # Track test state
        if test_status == "inprogress":
            self._test_started[test_id] = True
            self._test_tags[test_id] = test_tags

        # Check if this test was already filtered at start
        if test_id in self._test_started and not self._test_started[test_id]:
            return  # Already decided to filter this test

        # Check if we should filter this test
        should_filter = False

        # Filter by status
        if test_status == "success" and self.filter_success:
            should_filter = True
        elif test_status == "skip" and self.filter_skip:
            should_filter = True
        elif test_status == "error" and self.filter_error:
            should_filter = True
        elif test_status == "failure" and self.filter_failure:
            should_filter = True
        elif test_status == "expectedfailure" and self.filter_xfail:
            should_filter = True

        # Apply custom predicate
        if not should_filter and self.filter_predicate:
            # Create a dummy test object
            class DummyTest:
                def __init__(self, test_id):
                    self._id = test_id

                def id(self):
                    return self._id

            test = DummyTest(original_test_id)
            # Get tags for this test (use stored tags from inprogress or current tags)
            tags = test_tags
            if tags is None and test_id in self._test_tags:
                tags = self._test_tags[test_id]

            # Map status to outcome
            outcome_map = {
                "success": "success",
                "failure": "failure",
                "error": "error",
                "skip": "skip",
                "expectedfailure": "expectedfailure",
                "unexpectedsuccess": "unexpectedsuccess",
                "inprogress": "exists",  # For tag filtering on start
            }
            outcome = outcome_map.get(test_status, test_status)

            if not self.filter_predicate(test, outcome, None, None, tags):
                should_filter = True
                # If filtering at inprogress, mark to filter all events for this test
                if test_status == "inprogress":
                    self._test_started[test_id] = False  # Mark as filtered

        # If filtering, skip all events for this test
        if should_filter:
            # Clean up tracking
            if test_status != "inprogress":
                self._test_started.pop(test_id, None)
                self._test_tags.pop(test_id, None)
            return

        # Forward the event
        self.target.status(test_id=test_id, test_status=test_status, test_tags=test_tags, **kwargs)


def make_options(description):
    parser = OptionParser(description=__doc__)
    parser.add_option("--error", action="store_false", help="include errors", default=False, dest="error")
    parser.add_option("-e", "--no-error", action="store_true", help="exclude errors", dest="error")
    parser.add_option("--failure", action="store_false", help="include failures", default=False, dest="failure")
    parser.add_option("-f", "--no-failure", action="store_true", help="exclude failures", dest="failure")
    parser.add_option(
        "--passthrough",
        action="store_false",
        help="Forward non-subunit input as 'stdout'.",
        default=False,
        dest="no_passthrough",
    )
    parser.add_option(
        "--no-passthrough",
        action="store_true",
        help="Discard all non subunit input.",
        default=False,
        dest="no_passthrough",
    )
    parser.add_option("-s", "--success", action="store_false", help="include successes", dest="success")
    parser.add_option("--no-success", action="store_true", help="exclude successes", default=True, dest="success")
    parser.add_option("--no-skip", action="store_true", help="exclude skips", dest="skip")
    parser.add_option("--xfail", action="store_false", help="include expected failures", default=True, dest="xfail")
    parser.add_option("--no-xfail", action="store_true", help="exclude expected failures", default=True, dest="xfail")
    parser.add_option("--with-tag", type=str, help="include tests with these tags", action="append", dest="with_tags")
    parser.add_option(
        "--without-tag", type=str, help="exclude tests with these tags", action="append", dest="without_tags"
    )
    parser.add_option(
        "-m",
        "--with",
        type=str,
        help="regexp to include (case-sensitive by default)",
        action="append",
        dest="with_regexps",
    )
    parser.add_option(
        "--fixup-expected-failures",
        type=str,
        help="File with list of test ids that are expected to fail; on failure "
        "their result will be changed to xfail; on success they will be "
        "changed to error.",
        dest="fixup_expected_failures",
        action="append",
    )
    parser.add_option(
        "--without",
        type=str,
        help="regexp to exclude (case-sensitive by default)",
        action="append",
        dest="without_regexps",
    )
    parser.add_option(
        "-F",
        "--only-genuine-failures",
        action="callback",
        callback=only_genuine_failures_callback,
        help="Only pass through failures and exceptions.",
    )
    parser.add_option(
        "--rename",
        action="append",
        nargs=2,
        help="Apply specified regex substitutions to test names.",
        dest="renames",
        default=[],
    )
    return parser


def only_genuine_failures_callback(option, opt, value, parser):
    parser.rargs.insert(0, "--no-passthrough")
    parser.rargs.insert(0, "--no-xfail")
    parser.rargs.insert(0, "--no-skip")
    parser.rargs.insert(0, "--no-success")


def _compile_re_from_list(list):
    return re.compile("|".join(list), re.MULTILINE)


def _make_regexp_filter(with_regexps, without_regexps):
    """Make a callback that checks tests against regexps.

    with_regexps and without_regexps are each either a list of regexp strings,
    or None.
    """
    with_re = with_regexps and _compile_re_from_list(with_regexps)
    without_re = without_regexps and _compile_re_from_list(without_regexps)

    def check_regexps(test, outcome, err, details, tags):
        """Check if this test and error match the regexp filters."""
        test_str = str(test) + outcome + str(err) + str(details)
        if with_re and not with_re.search(test_str):
            return False
        if without_re and without_re.search(test_str):
            return False
        return True

    return check_regexps


def _compile_rename(patterns):
    def rename(name):
        for from_pattern, to_pattern in patterns:
            name = re.sub(from_pattern, to_pattern, name)
        return name

    return rename


def _make_result(output, options, predicate):
    """Make the result that we'll send the test outcomes to."""
    # Create base result
    result = StreamResultToBytes(output)

    # Apply filters if needed
    if options.success or options.skip or options.error or options.failure or options.xfail or predicate is not None:
        # Get fixup expected failures if provided
        fixup_expected_failures = frozenset()
        if options.fixup_expected_failures:
            for fixture in options.fixup_expected_failures:
                fixup_expected_failures = fixup_expected_failures.union(read_test_list(fixture))

        # Create rename function
        rename_func = None
        if options.renames:
            rename_func = _compile_rename(options.renames)

        # Apply stream filter
        result = StreamFilter(
            result,
            filter_success=options.success,
            filter_skip=options.skip,
            filter_error=options.error,
            filter_failure=options.failure,
            filter_xfail=options.xfail,
            filter_predicate=predicate,
            fixup_expected_failures=fixup_expected_failures,
            rename=rename_func,
        )

    return result


def main():
    parser = make_options(__doc__)
    (options, args) = parser.parse_args()

    regexp_filter = _make_regexp_filter(options.with_regexps, options.without_regexps)
    tag_filter = make_tag_filter(options.with_tags, options.without_tags)
    filter_predicate = and_predicates([regexp_filter, tag_filter])

    filter_by_result(
        lambda output_to: _make_result(output_to, options, filter_predicate),
        output_path=None,
        passthrough=(not options.no_passthrough),
        forward=False,
        protocol_version=2,
        input_stream=find_stream(sys.stdin, args),
    )
    sys.exit(0)


if __name__ == "__main__":
    main()

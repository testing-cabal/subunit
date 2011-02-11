#
#  subunit: extensions to python unittest to get test results from subprocesses.
#  Copyright (C) 2005  Robert Collins <robertc@robertcollins.net>
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

"""Tests for subunit.TestResultFilter."""

import unittest
from StringIO import StringIO

import subunit
from subunit.test_results import TestResultFilter


class TestTestResultFilter(unittest.TestCase):
    """Test for TestResultFilter, a TestResult object which filters tests."""

    def test_default(self):
        """The default is to exclude success and include everything else."""
        filtered_result = unittest.TestResult()
        result_filter = TestResultFilter(filtered_result)
        self.run_tests(result_filter)
        # skips are seen as success by default python TestResult.
        self.assertEqual(['error'],
            [error[0].id() for error in filtered_result.errors])
        self.assertEqual(['failed'],
            [failure[0].id() for failure in
            filtered_result.failures])
        self.assertEqual(4, filtered_result.testsRun)

    def test_exclude_errors(self):
        filtered_result = unittest.TestResult()
        result_filter = TestResultFilter(filtered_result, filter_error=True)
        self.run_tests(result_filter)
        # skips are seen as errors by default python TestResult.
        self.assertEqual([], filtered_result.errors)
        self.assertEqual(['failed'],
            [failure[0].id() for failure in
            filtered_result.failures])
        self.assertEqual(3, filtered_result.testsRun)

    def test_exclude_failure(self):
        filtered_result = unittest.TestResult()
        result_filter = TestResultFilter(filtered_result, filter_failure=True)
        self.run_tests(result_filter)
        self.assertEqual(['error'],
            [error[0].id() for error in filtered_result.errors])
        self.assertEqual([],
            [failure[0].id() for failure in
            filtered_result.failures])
        self.assertEqual(3, filtered_result.testsRun)

    def test_exclude_skips(self):
        filtered_result = subunit.TestResultStats(None)
        result_filter = TestResultFilter(filtered_result, filter_skip=True)
        self.run_tests(result_filter)
        self.assertEqual(0, filtered_result.skipped_tests)
        self.assertEqual(2, filtered_result.failed_tests)
        self.assertEqual(3, filtered_result.testsRun)

    def test_include_success(self):
        """Successes can be included if requested."""
        filtered_result = unittest.TestResult()
        result_filter = TestResultFilter(filtered_result,
            filter_success=False)
        self.run_tests(result_filter)
        self.assertEqual(['error'],
            [error[0].id() for error in filtered_result.errors])
        self.assertEqual(['failed'],
            [failure[0].id() for failure in
            filtered_result.failures])
        self.assertEqual(5, filtered_result.testsRun)

    def test_filter_predicate(self):
        """You can filter by predicate callbacks"""
        filtered_result = unittest.TestResult()
        def filter_cb(test, outcome, err, details):
            return outcome == 'success'
        result_filter = TestResultFilter(filtered_result,
            filter_predicate=filter_cb,
            filter_success=False)
        self.run_tests(result_filter)
        # Only success should pass
        self.assertEqual(1, filtered_result.testsRun)

    def run_tests(self, result_filter):
        input_stream = self.getTestStream()
        test = subunit.ProtocolTestCase(input_stream)
        test.run(result_filter)

    def getTestStream(self):
        # While TestResultFilter works on python objects, using a subunit
        # stream is an easy pithy way of getting a series of test objects to
        # call into the TestResult, and as TestResultFilter is intended for
        # use with subunit also has the benefit of detecting any interface
        # skew issues.
        input_stream = StringIO()
        input_stream.write("""tags: global
test passed
success passed
test failed
tags: local
failure failed
test error
error error [
error details
]
test skipped
skip skipped
test todo
xfail todo
""")
        input_stream.seek(0)
        return input_stream


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

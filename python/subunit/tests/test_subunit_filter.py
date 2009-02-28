#
#  subunit: extensions to python unittest to get test results from subprocesses.
#  Copyright (C) 2005  Robert Collins <robertc@robertcollins.net>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

"""Tests for subunit.TestResultFilter."""

import unittest
from StringIO import StringIO

import subunit


class TestTestResultFilter(unittest.TestCase):
    """Test for TestResultFilter, a TestResult object which filters tests."""

    def _setUp(self):
        self.output = StringIO()

    def test_default(self):
        """The default is to exclude success and include everything else."""
        self.filtered_result = unittest.TestResult()
        self.filter = subunit.TestResultFilter(self.filtered_result)
        self.run_tests()
        # skips are seen as errors by default python TestResult.
        self.assertEqual(['error', 'skipped'],
            [error[0].id() for error in self.filtered_result.errors])
        self.assertEqual(['failed'],
            [failure[0].id() for failure in
            self.filtered_result.failures])
        self.assertEqual(3, self.filtered_result.testsRun)

    def test_exclude_errors(self):
        self.filtered_result = unittest.TestResult()
        self.filter = subunit.TestResultFilter(self.filtered_result,
            filter_error=True)
        self.run_tests()
        # skips are seen as errors by default python TestResult.
        self.assertEqual(['skipped'],
            [error[0].id() for error in self.filtered_result.errors])
        self.assertEqual(['failed'],
            [failure[0].id() for failure in
            self.filtered_result.failures])
        self.assertEqual(2, self.filtered_result.testsRun)

    def test_exclude_failure(self):
        self.filtered_result = unittest.TestResult()
        self.filter = subunit.TestResultFilter(self.filtered_result,
            filter_failure=True)
        self.run_tests()
        self.assertEqual(['error', 'skipped'],
            [error[0].id() for error in self.filtered_result.errors])
        self.assertEqual([],
            [failure[0].id() for failure in
            self.filtered_result.failures])
        self.assertEqual(2, self.filtered_result.testsRun)

    def test_exclude_skips(self):
        self.filtered_result = subunit.TestResultStats(None)
        self.filter = subunit.TestResultFilter(self.filtered_result,
            filter_skip=True)
        self.run_tests()
        self.assertEqual(0, self.filtered_result.skipped_tests)
        self.assertEqual(2, self.filtered_result.failed_tests)
        self.assertEqual(2, self.filtered_result.testsRun)

    def test_include_success(self):
        """Success's can be included if requested."""
        self.filtered_result = unittest.TestResult()
        self.filter = subunit.TestResultFilter(self.filtered_result,
            filter_success=False)
        self.run_tests()
        self.assertEqual(['error', 'skipped'],
            [error[0].id() for error in self.filtered_result.errors])
        self.assertEqual(['failed'],
            [failure[0].id() for failure in
            self.filtered_result.failures])
        self.assertEqual(5, self.filtered_result.testsRun)

    def run_tests(self):
        self.setUpTestStream()
        self.test = subunit.ProtocolTestCase(self.input_stream)
        self.test.run(self.filter)

    def setUpTestStream(self):
        # While TestResultFilter works on python objects, using a subunit
        # stream is an easy pithy way of getting a series of test objects to
        # call into the TestResult, and as TestResultFilter is intended for use
        # with subunit also has the benefit of detecting any interface skew issues.
        self.input_stream = StringIO()
        self.input_stream.write("""tags: global
test passed
success passed
test failed
tags: local
failure failed
test error
error error
test skipped
skip skipped
test todo
xfail todo
""")
        self.input_stream.seek(0)
    


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

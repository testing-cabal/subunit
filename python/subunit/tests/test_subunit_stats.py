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

"""Tests for subunit.TestResultStats."""

import unittest
from StringIO import StringIO

import subunit


class TestTestResultStats(unittest.TestCase):
    """Test for TestResultStats, a TestResult object that generates stats."""

    def setUp(self):
        self.output = StringIO()
        self.result = subunit.TestResultStats(self.output)
        self.input_stream = StringIO()
        self.test = subunit.ProtocolTestCase(self.input_stream)

    def test_stats_empty(self):
        self.test.run(self.result)
        self.assertEqual(0, self.result.total_tests)
        self.assertEqual(0, self.result.passed_tests)
        self.assertEqual(0, self.result.failed_tests)
        self.assertEqual(set(), self.result.tags)

    def setUpUsedStream(self):
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
        self.test.run(self.result)
    
    def test_stats_smoke_everything(self):
        # Statistics are calculated usefully.
        self.setUpUsedStream()
        self.assertEqual(5, self.result.total_tests)
        self.assertEqual(3, self.result.passed_tests)
        self.assertEqual(2, self.result.failed_tests)
        self.assertEqual(set(["global", "local"]), self.result.tags)

    def test_stat_formatting(self):
        expected = ("""
Total tests:      5
Passed tests:     3
Failed tests:     2
Tags: global, local
""")[1:]
        self.setUpUsedStream()
        self.result.formatStats()
        self.assertEqual(expected, self.output.getvalue())


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

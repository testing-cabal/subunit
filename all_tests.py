#
#  subunit: extensions to Python unittest to get test results from subprocesses.
#  Copyright (C) 2013  Robert Collins <robertc@robertcollins.net>
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

import unittest

import subunit


class ShellTests(subunit.ExecTestCase):

    def test_sourcing(self):
        """./shell/tests/test_source_library.sh"""

    def test_functions(self):
        """./shell/tests/test_function_output.sh"""


def test_suite():
    result = unittest.TestSuite()
    result.addTest(subunit.test_suite())
    result.addTest(ShellTests('test_sourcing'))
    result.addTest(ShellTests('test_functions'))
    return result

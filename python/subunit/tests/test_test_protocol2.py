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

from io import BytesIO

from testtools import TestCase
from testtools.tests.test_testresult import TestStreamResultContract

import subunit

class TestStreamResultToBytesContract(TestCase, TestStreamResultContract):
    """Check that StreamResult behaves as testtools expects."""

    def _make_result(self):
        return subunit.StreamResultToBytes(BytesIO())


class TestStreamResultToBytes(TestCase):

    def _make_result(self):
        output = BytesIO()
        return subunit.StreamResultToBytes(output), output

    def test_trivial_enumeration(self):
        result, output = self._make_result()
        result.status("foo", 'exists')
        self.assertEqual(b'\xb3\x29\x01\0\0\x0f\0\x03foo\x99\x0c\x34\x3f',
            output.getvalue())


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

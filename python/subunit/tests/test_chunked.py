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

from cStringIO import StringIO
import unittest

import subunit.chunked


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result


class TestEncode(unittest.TestCase):

    def setUp(self):
        self.output = StringIO()
        self.encoder = subunit.chunked.Encoder(self.output)

    def test_encode_nothing(self):
        self.encoder.close()
        self.assertEqual('0\r\n', self.output.getvalue())

    def test_encode_empty(self):
        self.encoder.write('')
        self.encoder.close()
        self.assertEqual('0\r\n', self.output.getvalue())

    def test_encode_short(self):
        self.encoder.write('abc')
        self.encoder.close()
        self.assertEqual('3\r\nabc0\r\n', self.output.getvalue())

    def test_encode_combines_short(self):
        self.encoder.write('abc')
        self.encoder.write('def')
        self.encoder.close()
        self.assertEqual('6\r\nabcdef0\r\n', self.output.getvalue())

    def test_encode_over_9_is_in_hex(self):
        self.encoder.write('1234567890')
        self.encoder.close()
        self.assertEqual('A\r\n12345678900\r\n', self.output.getvalue())

    def test_encode_long_ranges_not_combined(self):
        self.encoder.write('1' * 65536)
        self.encoder.write('2' * 65536)
        self.encoder.close()
        self.assertEqual('10000\r\n' + '1' * 65536 + '10000\r\n' +
            '2' * 65536 + '0\r\n', self.output.getvalue())

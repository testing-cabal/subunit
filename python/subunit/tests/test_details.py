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

import subunit.tests
from subunit import details


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result


class TestSimpleDetails(unittest.TestCase):

    def test_lineReceived(self):
        parser = details.SimpleDetailsParser(None)
        parser.lineReceived("foo\n")
        parser.lineReceived("bar\n")
        self.assertEqual("foo\nbar\n", parser._message)

    def test_lineReceived_escaped_bracket(self):
        parser = details.SimpleDetailsParser(None)
        parser.lineReceived("foo\n")
        parser.lineReceived(" ]are\n")
        parser.lineReceived("bar\n")
        self.assertEqual("foo\n]are\nbar\n", parser._message)

    def test_get_message(self):
        parser = details.SimpleDetailsParser(None)
        self.assertEqual("", parser.get_message())

    def test_get_details_is_None(self):
        parser = details.SimpleDetailsParser(None)
        self.assertEqual(None, parser.get_details())


class TestMultipartDetails(unittest.TestCase):

    def test_get_message_is_None(self):
        parser = details.MultipartDetailsParser(None)
        self.assertEqual(None, parser.get_message())

    def test_get_details(self):
        parser = details.MultipartDetailsParser(None)
        self.assertEqual({}, parser.get_details())

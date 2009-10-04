#
#  subunit: extensions to Python unittest to get test results from subprocesses.
#  Copyright (C) 2009  Robert Collins <robertc@robertcollins.net>
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
from subunit.content import Content,  TracebackContent
from subunit.content_type import ContentType


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result


class TestContent(unittest.TestCase):

    def test___init___None_errors(self):
        self.assertRaises(ValueError, Content, None, None)
        self.assertRaises(ValueError, Content, None, lambda:["traceback"])
        self.assertRaises(ValueError, Content,
            ContentType("text", "traceback"), None)

    def test___init___sets_ivars(self):
        content_type = ContentType("foo", "bar")
        content = Content(content_type, lambda:["bytes"])
        self.assertEqual(content_type, content.content_type)
        self.assertEqual(["bytes"], list(content.iter_bytes()))


class TestTracebackContent(unittest.TestCase):

    def test___init___None_errors(self):
        self.assertRaises(ValueError, TracebackContent, None)

    def test___init___sets_ivars(self):
        content = TracebackContent(subunit.RemoteError("weird"))
        content_type = ContentType("text", "x-traceback",
            {"language":"python"})
        self.assertEqual(content_type, content.content_type)
        result = unittest.TestResult()
        expected = result._exc_info_to_string(subunit.RemoteError("weird"),
            subunit.RemotedTestCase(''))
        self.assertEqual(expected, ''.join(list(content.iter_bytes())))

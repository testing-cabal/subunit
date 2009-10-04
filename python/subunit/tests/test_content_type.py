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

import datetime
import unittest
from StringIO import StringIO
import os
import subunit
from subunit.content_type import ContentType
import sys

import subunit.iso8601 as iso8601


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result


class TestContentType(unittest.TestCase):

    def test___init___None_errors(self):
        self.assertRaises(ValueError, ContentType, None, None)
        self.assertRaises(ValueError, ContentType, None, "traceback")
        self.assertRaises(ValueError, ContentType, "text", None)

    def test___init___sets_ivars(self):
        content_type = ContentType("foo", "bar")
        self.assertEqual("foo", content_type.type)
        self.assertEqual("bar", content_type.subtype)
        self.assertEqual({}, content_type.parameters)

    def test___init___with_parameters(self):
        content_type = ContentType("foo", "bar", {"quux":"thing"})
        self.assertEqual({"quux":"thing"}, content_type.parameters)

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

"""Tests for subunit.tag_stream."""

from io import BytesIO
import unittest

import subunit
import subunit.test_results


class TestSubUnitTags(unittest.TestCase):

    def setUp(self):
        self.original = BytesIO()
        self.filtered = BytesIO()

    def test_add_tag(self):
        reference = BytesIO()
        stream = subunit.StreamResultToBytes(reference)
        stream.status(
            test_id='test', test_status='inprogress', test_tags=set(['quux', 'foo']))
        stream.status(
            test_id='test', test_status='success', test_tags=set(['bar', 'quux', 'foo']))
        stream = subunit.StreamResultToBytes(self.original)
        stream.status(
            test_id='test', test_status='inprogress', test_tags=set(['foo']))
        stream.status(
            test_id='test', test_status='success', test_tags=set(['foo', 'bar']))
        self.original.seek(0)
        self.assertEqual(
            0, subunit.tag_stream(self.original, self.filtered, ["quux"]))
        self.assertEqual(reference.getvalue(), self.filtered.getvalue())

    def test_remove_tag(self):
        reference = BytesIO()
        stream = subunit.StreamResultToBytes(reference)
        stream.status(
            test_id='test', test_status='inprogress', test_tags=set(['foo']))
        stream.status(
            test_id='test', test_status='success', test_tags=set(['foo']))
        stream = subunit.StreamResultToBytes(self.original)
        stream.status(
            test_id='test', test_status='inprogress', test_tags=set(['foo']))
        stream.status(
            test_id='test', test_status='success', test_tags=set(['foo', 'bar']))
        self.original.seek(0)
        self.assertEqual(
            0, subunit.tag_stream(self.original, self.filtered, ["-bar"]))
        self.assertEqual(reference.getvalue(), self.filtered.getvalue())

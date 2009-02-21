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

"""Tests for subunit.tag_stream."""

import unittest
from StringIO import StringIO

import subunit


class TestSubUnitTags(unittest.TestCase):

    def setUp(self):
        self.original = StringIO()
        self.filtered = StringIO()

    def test_add_tag(self):
        self.original.write("tags: foo\n")
        self.original.write("test: test\n")
        self.original.write("tags: bar -quux\n")
        self.original.write("success: test\n")
        self.original.seek(0)
        result = subunit.tag_stream(self.original, self.filtered, ["quux"])
        self.assertEqual([
            "tags: quux",
            "tags: foo",
            "test: test",
            "tags: bar",
            "success: test",
            ],
            self.filtered.getvalue().splitlines())

    def test_remove_tag(self):
        self.original.write("tags: foo\n")
        self.original.write("test: test\n")
        self.original.write("tags: bar -quux\n")
        self.original.write("success: test\n")
        self.original.seek(0)
        result = subunit.tag_stream(self.original, self.filtered, ["-bar"])
        self.assertEqual([
            "tags: -bar",
            "tags: foo",
            "test: test",
            "tags: -quux",
            "success: test",
            ],
            self.filtered.getvalue().splitlines())


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

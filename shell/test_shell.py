#!/usr/bin/env python
# -*- Mode: python -*-
#
# Copyright (C) 2004 Canonical.com 
#       Author:      Robert Collins <robert.collins@canonical.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import unittest
from subunit.tests.TestUtil import TestVisitor, TestSuite
import subunit
import sys
import os
import shutil
import logging


class ShellTests(subunit.ExecTestCase):

    def test_shell(self):
        """./tests/test_source_library.sh"""


def test_suite():
    result = TestSuite()
    result.addTest(ShellTests('test_shell'))
    return result



def main(argv):
    # TODO: We should find some standard way of giving tests-to-run to 
    # child processes.
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(test_suite()).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

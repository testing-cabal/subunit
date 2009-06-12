#!/usr/bin/python

# Simple subunit testrunner for python
# Copyright (C) Jelmer Vernooij <jelmer@samba.org> 2007
#   
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#   
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#   
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys

from subunit import TestProtocolClient


class SubunitTestRunner(object):
    def __init__(self, stream=sys.stdout):
        self.stream = stream

    def run(self, test):
        "Run the given test case or test suite."
        result = TestProtocolClient(self.stream)
        test(result)
        return result


if __name__ == '__main__':
    import optparse
    from unittest import TestProgram
    parser = optparse.OptionParser("subunitrun <tests>")

    args = parser.parse_args()[1]

    runner = SubunitTestRunner()
    program = TestProgram(module=None, argv=[sys.argv[0]] + args, 
                          testRunner=runner)

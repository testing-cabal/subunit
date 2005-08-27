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

import sys

def test_suite():
    import subunit.tests
    return subunit.tests.test_suite()

class TestProtocolServer(object):
    """A class for recieving results from a TestProtocol client."""

    OUTSIDE_TEST = 0
    TEST_STARTED = 1

    def __init__(self):
        self.state = TestProtocolServer.OUTSIDE_TEST
        
    def lineRecieved(self, line):
        """Call the appropriate local method for the recieved line."""
        if line.startswith("test:"):
            self._startTest(6, line)
        elif line.startswith("testing:"):
            self._startTest(9, line)
        elif line.startswith("testing"):
            self._startTest(8, line)
        elif line.startswith("test"):
            self._startTest(5, line)
        else:
            self.stdOutLineRecieved(line)

    def lostConnection(self):
        """The input connection has finished."""
        if self.state != TestProtocolServer.OUTSIDE_TEST:
            self.addError("lost connection during test '%s'" 
                          % self.current_test_description)

    def _startTest(self, offset, line):
        """Internal call to change state machine. Override startTest()."""
        if self.state == TestProtocolServer.OUTSIDE_TEST:
            self.state = TestProtocolServer.TEST_STARTED
            self.current_test_description = line[offset:-1]
            self.startTest(self.current_test_description)
        else:
            self.stdOutLineRecieved(line)
        
    def stdOutLineRecieved(self, line):
        sys.stdout.write(line)

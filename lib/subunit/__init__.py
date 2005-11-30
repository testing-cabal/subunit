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

import os
from StringIO import StringIO
import subprocess
import sys
import unittest

def test_suite():
    import subunit.tests
    return subunit.tests.test_suite()

class TestProtocolServer(object):
    """A class for recieving results from a TestProtocol client."""

    OUTSIDE_TEST = 0
    TEST_STARTED = 1
    READING_FAILURE = 2
    READING_ERROR = 3

    def __init__(self, client):
        """Create a TestProtocol server instance. 

        client should be an object that provides 
         - startTest
         - addSuccess
         - addFailure
         - addError
         - stopTest
        methods, i.e. a TestResult.
        """
        self.state = TestProtocolServer.OUTSIDE_TEST
        self.client = client
        
    def _addError(self, offset, line):
        if (self.state == TestProtocolServer.TEST_STARTED and
            self.current_test_description == line[offset:-1]):
            self.state = TestProtocolServer.OUTSIDE_TEST
            self.current_test_description = None
            self.client.addError(self._current_test, RemoteError(""))
            self.client.stopTest(self._current_test)
            self._current_test = None
        elif (self.state == TestProtocolServer.TEST_STARTED and
            self.current_test_description + " [" == line[offset:-1]):
            self.state = TestProtocolServer.READING_ERROR
            self._message = ""
        else:
            self.stdOutLineRecieved(line)

    def _addFailure(self, offset, line):
        if (self.state == TestProtocolServer.TEST_STARTED and
            self.current_test_description == line[offset:-1]):
            self.state = TestProtocolServer.OUTSIDE_TEST
            self.current_test_description = None
            self.client.addFailure(self._current_test, RemoteError())
            self.client.stopTest(self._current_test)
        elif (self.state == TestProtocolServer.TEST_STARTED and
            self.current_test_description + " [" == line[offset:-1]):
            self.state = TestProtocolServer.READING_FAILURE
            self._message = ""
        else:
            self.stdOutLineRecieved(line)

    def _addSuccess(self, offset, line):
        if (self.state == TestProtocolServer.TEST_STARTED and
            self.current_test_description == line[offset:-1]):
            self.client.addSuccess(self._current_test)
            self.client.stopTest(self._current_test)
            self.current_test_description = None
            self._current_test = None
            self.state = TestProtocolServer.OUTSIDE_TEST
        else:
            self.stdOutLineRecieved(line)
        
    def _appendMessage(self, line):
        if line[0:2] == " ]":
            # quoted ] start
            self._message += line[1:]
        else:
            self._message += line
        
    def endQuote(self, line):
        if self.state == TestProtocolServer.READING_FAILURE:
            self.state = TestProtocolServer.OUTSIDE_TEST
            self.current_test_description = None
            self.client.addFailure(self._current_test,
                                   RemoteError(self._message))
            self.client.stopTest(self._current_test)
        elif self.state == TestProtocolServer.READING_ERROR:
            self.state = TestProtocolServer.OUTSIDE_TEST
            self.current_test_description = None
            self.client.addError(self._current_test,
                                 RemoteError(self._message))
            self.client.stopTest(self._current_test)
        else:
            self.stdOutLineRecieved(line)
        
    def lineReceived(self, line):
        """Call the appropriate local method for the recieved line."""
        if line == "]\n":
            self.endQuote(line)
        elif (self.state == TestProtocolServer.READING_FAILURE or
              self.state == TestProtocolServer.READING_ERROR):
            self._appendMessage(line)
        elif line.startswith("test:"):
            self._startTest(6, line)
        elif line.startswith("testing:"):
            self._startTest(9, line)
        elif line.startswith("testing"):
            self._startTest(8, line)
        elif line.startswith("test"):
            self._startTest(5, line)
        elif line.startswith("error:"):
            self._addError(7, line)
        elif line.startswith("error"):
            self._addError(6, line)
        elif line.startswith("failure:"):
            self._addFailure(9, line)
        elif line.startswith("failure"):
            self._addFailure(8, line)
        elif line.startswith("successful:"):
            self._addSuccess(12, line)
        elif line.startswith("successful"):
            self._addSuccess(11, line)
        elif line.startswith("success:"):
            self._addSuccess(9, line)
        elif line.startswith("success"):
            self._addSuccess(8, line)
        else:
            self.stdOutLineRecieved(line)

    def lostConnection(self):
        """The input connection has finished."""
        if self.state == TestProtocolServer.TEST_STARTED:
            self.client.addError(self._current_test,
                                 RemoteError("lost connection during test '%s'"
                                             % self.current_test_description))
            self.client.stopTest(self._current_test)
        elif self.state == TestProtocolServer.READING_ERROR:
            self.client.addError(self._current_test,
                                 RemoteError("lost connection during "
                                             "error report of test "
                                             "'%s'" %
                                             self.current_test_description))
            self.client.stopTest(self._current_test)
        elif self.state == TestProtocolServer.READING_FAILURE:
            self.client.addError(self._current_test,
                                 RemoteError("lost connection during "
                                             "failure report of test "
                                             "'%s'" % 
                                             self.current_test_description))
            self.client.stopTest(self._current_test)

    def readFrom(self, pipe):
        for line in pipe.readlines():
            self.lineReceived(line)
        self.lostConnection()

    def _startTest(self, offset, line):
        """Internal call to change state machine. Override startTest()."""
        if self.state == TestProtocolServer.OUTSIDE_TEST:
            self.state = TestProtocolServer.TEST_STARTED
            self._current_test = RemotedTestCase(line[offset:-1])
            self.current_test_description = line[offset:-1]
            self.client.startTest(self._current_test)
        else:
            self.stdOutLineRecieved(line)
        
    def stdOutLineRecieved(self, line):
        sys.stdout.write(line)


class RemoteException(Exception):
    """An exception that occured remotely to python."""

    def __eq__(self, other):
        try:
            return self.args == other.args
        except AttributeError:
            return False
    

class TestProtocolClient(unittest.TestResult):
    """A class that looks like a TestResult and informs a TestProtocolServer."""
    
    def __init__(self, stream):
        unittest.TestResult.__init__(self)
        self._stream = stream
    
    def addError(self, test, error):
        """Report an error in test test."""
        self._stream.write("error: %s [\n" % test.shortDescription())
        for line in self._exc_info_to_string(error, test).split():
            self._stream.write("%s\n" % line)
        self._stream.write("]\n")
        
    def addFailure(self, test, error):
        """Report a failure in test test."""
        self._stream.write("failure: %s [\n" % test.shortDescription())
        for line in self._exc_info_to_string(error, test).split():
            self._stream.write("%s\n" % line)
        self._stream.write("]\n")

    def addSuccess(self, test):
        """Report a success in a test."""
        self._stream.write("successful: %s\n" % test.shortDescription())

    def startTest(self, test):
        """Mark a test as starting its test run."""
        self._stream.write("test: %s\n" % test.shortDescription())


def RemoteError(description=""):
    if description == "":
        description = "\n"
    return (RemoteException("RemoteError:\n%s" % description), None, None)


class RemotedTestCase(unittest.TestCase):
    """A class to represent test cases run in child processes."""

    def __eq__ (self, other):
        try:
            return self.__description == other.__description
        except AttributeError:
            return False
        
    def __init__(self, description):
        """Create a psuedo test case with description description."""
        self.__description = description

    def error(self, label):
        raise NotImplementedError("%s on RemotedTestCases is not permitted." %
            label)

    def setUp(self):
        self.error("setUp")

    def tearDown(self):
        self.error("tearDown")

    def shortDescription(self):
        return self.__description

    def id(self):
        return "%s.%s" % (self._strclass(), self.__description)

    def __str__(self):
        return "%s (%s)" % (self.__description, self._strclass())

    def __repr__(self):
        return "<%s description='%s'>" % \
               (self._strclass(), self.__description)

    def run(self, result=None):
        if result is None: result = self.defaultTestResult()
        result.startTest(self)
        result.addError(self, RemoteError("Cannot run RemotedTestCases.\n"))
        result.stopTest(self)
        
    def _strclass(self):
        cls = self.__class__
        return "%s.%s" % (cls.__module__, cls.__name__)

class ExecTestCase(unittest.TestCase):
    """A test case which runs external scripts for test fixtures."""

    def __init__(self, methodName='runTest'):
        """Create an instance of the class that will use the named test
           method when executed. Raises a ValueError if the instance does
           not have a method with the specified name.
        """
        unittest.TestCase.__init__(self, methodName)
        testMethod = getattr(self, methodName)
        self.script = testMethod.__doc__

    def countTestCases(self):
        return 1

    def run(self, result=None):
        if result is None: result = self.defaultTestResult()
        self._run(result)

    def debug(self):
        """Run the test without collecting errors in a TestResult"""
        self._run(unittest.TestResult())
    
    def _run(self, result):
        protocol = TestProtocolServer(result)
        output = subprocess.Popen([self.script],
                                  stdout=subprocess.PIPE).communicate()[0]
        protocol.readFrom(StringIO(output))


class IsolatedTestCase(unittest.TestCase):
    """A TestCase which runs its tests in a forked process."""

    def run(self, result=None):
        if result is None: result = self.defaultTestResult()
        c2pread, c2pwrite = os.pipe()
        # fixme - error -> result
        # now fork
        pid = os.fork()
        if pid == 0:
            # Child
            # Close parent's pipe ends
            os.close(c2pread)
            # Dup fds for child
            os.dup2(c2pwrite, 1)
            # Close pipe fds.
            os.close(c2pwrite)

            # at this point, sys.stdin is redirected, now we want
            # to filter it to escape ]'s.
            ### XXX: test and write that bit.

            result = TestProtocolClient(sys.stdout)
            unittest.TestCase.run(self, result)
            sys.stdout.flush()
            sys.stderr.flush()
            # exit HARD, exit NOW.
            os._exit(0)
        else:
            # Parent
            # Close child pipe ends
            os.close(c2pwrite)
            # hookup a protocol engine
            protocol = TestProtocolServer(result)
            protocol.readFrom(os.fdopen(c2pread, 'rU'))
            os.waitpid(pid, 0)
            # TODO return code evaluation.

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

import unittest
import subunit
import sys

try:
    class MockTestProtocolServer(subunit.TestProtocolServer):
        """A mock protocol server to test callbacks."""

        def __init__(self):
            self.error_calls = []
            self.failure_calls = []
            self.start_calls = []
            self.success_calls = []
            super(MockTestProtocolServer, self).__init__()

        def addError(self, error):
            self.error_calls.append(error)

        def addFailure(self, error):
            self.failure_calls.append(error)

        def addSuccess(self, test):
            self.success_calls.append(test)

        def startTest(self, test):
            self.start_calls.append(test)

except AttributeError:
    MockTestProtocolServer = None


class TestMockTestProtocolServer(unittest.TestCase):

    def test_start_test(self):
        protocol = MockTestProtocolServer()
        protocol.startTest(subunit.RemotedTestCase("test old mcdonald"))
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("test old mcdonald")])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])

    def test_add_error(self):
        protocol = MockTestProtocolServer()
        protocol.addError("omg it works")
        self.assertEqual(protocol.start_calls, [])
        self.assertEqual(protocol.error_calls, ["omg it works"])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])
        
    def test_add_failure(self):
        protocol = MockTestProtocolServer()
        protocol.addFailure("omg it works")
        self.assertEqual(protocol.start_calls, [])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, ["omg it works"])
        self.assertEqual(protocol.success_calls, [])

    def test_add_success(self):
        protocol = MockTestProtocolServer()
        protocol.addSuccess(subunit.RemotedTestCase("test old mcdonald"))
        self.assertEqual(protocol.start_calls, [])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, 
                         [subunit.RemotedTestCase("test old mcdonald")])
        

class TestTestImports(unittest.TestCase):
    
    def test_imports(self):
        from subunit import TestProtocolServer
        from subunit import RemotedTestCase


class TestTestProtocolServerStartTest(unittest.TestCase):
    
    def setUp(self):
        self.protocol = MockTestProtocolServer()
    
    def test_start_test(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.assertEqual(self.protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])

    def test_start_testing(self):
        self.protocol.lineReceived("testing old mcdonald\n")
        self.assertEqual(self.protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])

    def test_start_test_colon(self):
        self.protocol.lineReceived("test: old mcdonald\n")
        self.assertEqual(self.protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])

    def test_start_testing_colon(self):
        self.protocol.lineReceived("testing: old mcdonald\n")
        self.assertEqual(self.protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])


class TestTestProtocolServerPassThrough(unittest.TestCase):

    def setUp(self):
        from StringIO import StringIO
        self.real_stdout = sys.stdout
        self.stdout = StringIO()
        sys.stdout = self.stdout
        
    def tearDown(self):
        sys.stdout = self.real_stdout

    def keywords_before_test(self, protocol):
        protocol.lineReceived("failure a\n")
        protocol.lineReceived("failure: a\n")
        protocol.lineReceived("error a\n")
        protocol.lineReceived("error: a\n")
        protocol.lineReceived("success a\n")
        protocol.lineReceived("success: a\n")
        protocol.lineReceived("successful a\n")
        protocol.lineReceived("successful: a\n")
        protocol.lineReceived("]\n")
        self.assertEqual(self.stdout.getvalue(), "failure a\n"
                                                 "failure: a\n"
                                                 "error a\n"
                                                 "error: a\n"
                                                 "success a\n"
                                                 "success: a\n"
                                                 "successful a\n"
                                                 "successful: a\n"
                                                 "]\n")

    def test_keywords_before_test(self):
        protocol = MockTestProtocolServer()
        self.keywords_before_test(protocol)
        self.assertEqual(protocol.start_calls, [])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])

    def test_keywords_after_error(self):
        protocol = MockTestProtocolServer()
        protocol.lineReceived("test old mcdonald\n")
        protocol.lineReceived("error old mcdonald\n")
        self.keywords_before_test(protocol)
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])
        self.assertEqual(protocol.error_calls, [""])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])
        
    def test_keywords_after_failure(self):
        protocol = MockTestProtocolServer()
        protocol.lineReceived("test old mcdonald\n")
        protocol.lineReceived("failure old mcdonald\n")
        self.keywords_before_test(protocol)
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [""])
        self.assertEqual(protocol.success_calls, [])
        
    def test_keywords_after_success(self):
        protocol = MockTestProtocolServer()
        protocol.lineReceived("test old mcdonald\n")
        protocol.lineReceived("success old mcdonald\n")
        self.keywords_before_test(protocol)
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls,
                         [subunit.RemotedTestCase("old mcdonald")])

    def test_keywords_after_test(self):
        protocol = MockTestProtocolServer()
        protocol.lineReceived("test old mcdonald\n")
        protocol.lineReceived("test old mcdonald\n")
        protocol.lineReceived("failure a\n")
        protocol.lineReceived("failure: a\n")
        protocol.lineReceived("error a\n")
        protocol.lineReceived("error: a\n")
        protocol.lineReceived("success a\n")
        protocol.lineReceived("success: a\n")
        protocol.lineReceived("successful a\n")
        protocol.lineReceived("successful: a\n")
        protocol.lineReceived("]\n")
        protocol.lineReceived("failure old mcdonald\n")
        self.assertEqual(self.stdout.getvalue(), "test old mcdonald\n"
                                                 "failure a\n"
                                                 "failure: a\n"
                                                 "error a\n"
                                                 "error: a\n"
                                                 "success a\n"
                                                 "success: a\n"
                                                 "successful a\n"
                                                 "successful: a\n"
                                                 "]\n")
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])
        self.assertEqual(protocol.failure_calls, [""])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.success_calls, [])

    def test_keywords_during_failure(self):
        protocol = MockTestProtocolServer()
        protocol.lineReceived("test old mcdonald\n")
        protocol.lineReceived("failure: old mcdonald [\n")
        protocol.lineReceived("test old mcdonald\n")
        protocol.lineReceived("failure a\n")
        protocol.lineReceived("failure: a\n")
        protocol.lineReceived("error a\n")
        protocol.lineReceived("error: a\n")
        protocol.lineReceived("success a\n")
        protocol.lineReceived("success: a\n")
        protocol.lineReceived("successful a\n")
        protocol.lineReceived("successful: a\n")
        protocol.lineReceived(" ]\n")
        protocol.lineReceived("]\n")
        self.assertEqual(self.stdout.getvalue(), "")
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])
        self.assertEqual(protocol.failure_calls, ["test old mcdonald\n"
                                                 "failure a\n"
                                                 "failure: a\n"
                                                 "error a\n"
                                                 "error: a\n"
                                                 "success a\n"
                                                 "success: a\n"
                                                 "successful a\n"
                                                 "successful: a\n"
                                                 "]\n"])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.success_calls, [])


class TestTestProtocolServerLostConnection(unittest.TestCase):
    
    def test_lost_connection_no_input(self):
        protocol = MockTestProtocolServer()
        protocol.lostConnection()
        self.assertEqual(protocol.start_calls, [])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])

    def test_lost_connection_after_start(self):
        protocol = MockTestProtocolServer()
        protocol.lineReceived("test old mcdonald\n")
        protocol.lostConnection()
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])
        self.assertEqual(protocol.error_calls, ["lost connection during test 'old mcdonald'"])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])

    def test_lost_connected_after_error(self):
        protocol = MockTestProtocolServer()
        protocol.lineReceived("test old mcdonald\n")
        protocol.lineReceived("error old mcdonald\n")
        protocol.lostConnection()
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.error_calls, [""])
        self.assertEqual(protocol.success_calls, [])
        
    def test_lost_connection_during_error(self):
        protocol = MockTestProtocolServer()
        protocol.lineReceived("test old mcdonald\n")
        protocol.lineReceived("error old mcdonald [\n")
        protocol.lostConnection()
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])
        self.assertEqual(protocol.error_calls, ["lost connection during "
                                                "error report of test "
                                                "'old mcdonald'"])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])

    def test_lost_connected_after_failure(self):
        protocol = MockTestProtocolServer()
        protocol.lineReceived("test old mcdonald\n")
        protocol.lineReceived("failure old mcdonald\n")
        protocol.lostConnection()
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [""])
        self.assertEqual(protocol.success_calls, [])
        
    def test_lost_connection_during_failure(self):
        protocol = MockTestProtocolServer()
        protocol.lineReceived("test old mcdonald\n")
        protocol.lineReceived("failure old mcdonald [\n")
        protocol.lostConnection()
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])
        self.assertEqual(protocol.error_calls, ["lost connection during "
                                                "failure report of test "
                                                "'old mcdonald'"])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])

    def test_lost_connection_after_success(self):
        protocol = MockTestProtocolServer()
        protocol.lineReceived("test old mcdonald\n")
        protocol.lineReceived("success old mcdonald\n")
        protocol.lostConnection()
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls,
                         [subunit.RemotedTestCase("old mcdonald")])


class TestTestProtocolServerAddError(unittest.TestCase):
    
    def setUp(self):
        self.protocol = MockTestProtocolServer()
        self.protocol.lineReceived("test mcdonalds farm\n")

    def simple_error_keyword(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm\n" % keyword)
        self.assertEqual(self.protocol.start_calls,
                         [subunit.RemotedTestCase("mcdonalds farm")])
        self.assertEqual(self.protocol.error_calls, [""])
        self.assertEqual(self.protocol.failure_calls, [])

    def test_simple_error(self):
        self.simple_error_keyword("error")

    def test_simple_error_colon(self):
        self.simple_error_keyword("error:")

    def test_error_empty_message(self):
        self.protocol.lineReceived("error mcdonalds farm [\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.protocol.start_calls,
                         [subunit.RemotedTestCase("mcdonalds farm")])
        self.assertEqual(self.protocol.error_calls, [""])
        self.assertEqual(self.protocol.failure_calls, [])

    def error_quoted_bracket(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm [\n" % keyword)
        self.protocol.lineReceived(" ]\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.protocol.start_calls,
                         [subunit.RemotedTestCase("mcdonalds farm")])
        self.assertEqual(self.protocol.error_calls, ["]\n"])
        self.assertEqual(self.protocol.failure_calls, [])

    def test_error_quoted_bracket(self):
        self.error_quoted_bracket("error")

    def test_error_colon_quoted_bracket(self):
        self.error_quoted_bracket("error:")


class TestTestProtocolServerAddFailure(unittest.TestCase):
    
    def setUp(self):
        self.protocol = MockTestProtocolServer()
        self.protocol.lineReceived("test mcdonalds farm\n")

    def simple_failure_keyword(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm\n" % keyword)
        self.assertEqual(self.protocol.start_calls,
                         [subunit.RemotedTestCase("mcdonalds farm")])
        self.assertEqual(self.protocol.error_calls, [])
        self.assertEqual(self.protocol.failure_calls, [""])

    def test_simple_failure(self):
        self.simple_failure_keyword("failure")

    def test_simple_failure_colon(self):
        self.simple_failure_keyword("failure:")

    def test_failure_empty_message(self):
        self.protocol.lineReceived("failure mcdonalds farm [\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.protocol.start_calls,
                         [subunit.RemotedTestCase("mcdonalds farm")])
        self.assertEqual(self.protocol.error_calls, [])
        self.assertEqual(self.protocol.failure_calls, [""])

    def failure_quoted_bracket(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm [\n" % keyword)
        self.protocol.lineReceived(" ]\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.protocol.start_calls,
                         [subunit.RemotedTestCase("mcdonalds farm")])
        self.assertEqual(self.protocol.error_calls, [])
        self.assertEqual(self.protocol.failure_calls, ["]\n"])

    def test_failure_quoted_bracket(self):
        self.failure_quoted_bracket("failure")

    def test_failure_colon_quoted_bracket(self):
        self.failure_quoted_bracket("failure:")


class TestTestProtocolServerAddSuccess(unittest.TestCase):
    
    def setUp(self):
        self.protocol = MockTestProtocolServer()
        self.protocol.lineReceived("test mcdonalds farm\n")

    def simple_success_keyword(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm\n" % keyword)
        self.assertEqual(self.protocol.start_calls,
                         [subunit.RemotedTestCase("mcdonalds farm")])
        self.assertEqual(self.protocol.error_calls, [])
        self.assertEqual(self.protocol.success_calls,
                         [subunit.RemotedTestCase("mcdonalds farm")])

    def test_simple_success(self):
        self.simple_success_keyword("failure")

    def test_simple_success_colon(self):
        self.simple_success_keyword("failure:")

    def test_simple_success(self):
        self.simple_success_keyword("successful")

    def test_simple_success_colon(self):
        self.simple_success_keyword("successful:")


class TestRemotedTestCase(unittest.TestCase):

    def test_simple(self):
        test = subunit.RemotedTestCase("A test description")
        self.assertRaises(NotImplementedError, test.setUp)
        self.assertRaises(NotImplementedError, test.tearDown)
        self.assertEqual("A test description",
                         test.shortDescription())
        self.assertEqual("subunit.RemotedTestCase.A test description",
                         test.id())
        self.assertEqual("A test description (subunit.RemotedTestCase)", "%s" % test)
        self.assertEqual("<subunit.RemotedTestCase description="
                         "'A test description'>", "%r" % test)
        result = unittest.TestResult()
        test.run(result)
        self.assertEqual([(test, "Cannot run RemotedTestCases.\n\n")], result.errors)
        self.assertEqual(1, result.testsRun)
        another_test = subunit.RemotedTestCase("A test description")
        self.assertEqual(test, another_test)
        different_test = subunit.RemotedTestCase("ofo")
        self.assertNotEqual(test, different_test)
        self.assertNotEqual(another_test, different_test)


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

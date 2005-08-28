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
from StringIO import StringIO
import subunit
import sys

try:
    class MockTestProtocolServerClient(object):
        """A mock protocol server client to test callbacks."""

        def __init__(self):
            self.end_calls = []
            self.error_calls = []
            self.failure_calls = []
            self.start_calls = []
            self.success_calls = []
            super(MockTestProtocolServerClient, self).__init__()

        def addError(self, test, error):
            self.error_calls.append((test, error))

        def addFailure(self, test, error):
            self.failure_calls.append((test, error))

        def addSuccess(self, test):
            self.success_calls.append(test)

        def stopTest(self, test):
            self.end_calls.append(test)
            
        def startTest(self, test):
            self.start_calls.append(test)

except AttributeError:
    MockTestProtocolServer = None


class TestMockTestProtocolServer(unittest.TestCase):

    def test_start_test(self):
        protocol = MockTestProtocolServerClient()
        protocol.startTest(subunit.RemotedTestCase("test old mcdonald"))
        self.assertEqual(protocol.start_calls,
                         [subunit.RemotedTestCase("test old mcdonald")])
        self.assertEqual(protocol.end_calls, [])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])

    def test_add_error(self):
        protocol = MockTestProtocolServerClient()
        protocol.addError(subunit.RemotedTestCase("old mcdonald"), 
                          subunit.RemoteError("omg it works"))
        self.assertEqual(protocol.start_calls, [])
        self.assertEqual(protocol.end_calls, [])
        self.assertEqual(protocol.error_calls, [(
                            subunit.RemotedTestCase("old mcdonald"),
                            subunit.RemoteError("omg it works"))])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])
        
    def test_add_failure(self):
        protocol = MockTestProtocolServerClient()
        protocol.addFailure(subunit.RemotedTestCase("old mcdonald"),
                            subunit.RemoteError("omg it works"))
        self.assertEqual(protocol.start_calls, [])
        self.assertEqual(protocol.end_calls, [])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [
                            (subunit.RemotedTestCase("old mcdonald"),
                             subunit.RemoteError("omg it works"))])
        self.assertEqual(protocol.success_calls, [])

    def test_add_success(self):
        protocol = MockTestProtocolServerClient()
        protocol.addSuccess(subunit.RemotedTestCase("test old mcdonald"))
        self.assertEqual(protocol.start_calls, [])
        self.assertEqual(protocol.end_calls, [])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, 
                         [subunit.RemotedTestCase("test old mcdonald")])
        
    def test_end_test(self):
        protocol = MockTestProtocolServerClient()
        protocol.stopTest(subunit.RemotedTestCase("test old mcdonald"))
        self.assertEqual(protocol.end_calls,
                         [subunit.RemotedTestCase("test old mcdonald")])
        self.assertEqual(protocol.error_calls, [])
        self.assertEqual(protocol.failure_calls, [])
        self.assertEqual(protocol.success_calls, [])
        self.assertEqual(protocol.start_calls, [])

class TestTestImports(unittest.TestCase):
    
    def test_imports(self):
        from subunit import TestProtocolServer
        from subunit import RemotedTestCase
        from subunit import RemoteError


class TestTestProtocolServerPipe(unittest.TestCase):

    def test_story(self):
        client = unittest.TestResult()
        protocol = subunit.TestProtocolServer(client)
        pipe = StringIO("test old mcdonald\n"
                        "success old mcdonald\n"
                        "test bing crosby\n"
                        "failure bing crosby [\n"
                        "foo.c:53:ERROR invalid state\n"
                        "]\n"
                        "test an error\n"
                        "error an error\n")
        protocol.readFrom(pipe)
        mcdonald = subunit.RemotedTestCase("old mcdonald")
        bing = subunit.RemotedTestCase("bing crosby")
        an_error = subunit.RemotedTestCase("an error")
        self.assertEqual(client.errors, 
                         [(an_error, 'RemoteError:\n\n\n')])
        self.assertEqual(client.failures, 
                         [(bing,
                           "RemoteError:\nfoo.c:53:ERROR invalid state\n\n")])
        self.assertEqual(client.testsRun, 3)


class TestTestProtocolServerStartTest(unittest.TestCase):
    
    def setUp(self):
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)
    
    def test_start_test(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.assertEqual(self.client.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])

    def test_start_testing(self):
        self.protocol.lineReceived("testing old mcdonald\n")
        self.assertEqual(self.client.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])

    def test_start_test_colon(self):
        self.protocol.lineReceived("test: old mcdonald\n")
        self.assertEqual(self.client.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])

    def test_start_testing_colon(self):
        self.protocol.lineReceived("testing: old mcdonald\n")
        self.assertEqual(self.client.start_calls,
                         [subunit.RemotedTestCase("old mcdonald")])


class TestTestProtocolServerPassThrough(unittest.TestCase):

    def setUp(self):
        from StringIO import StringIO
        self.real_stdout = sys.stdout
        self.stdout = StringIO()
        sys.stdout = self.stdout
        self.test = subunit.RemotedTestCase("old mcdonald")
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)
        
    def tearDown(self):
        sys.stdout = self.real_stdout

    def keywords_before_test(self):
        self.protocol.lineReceived("failure a\n")
        self.protocol.lineReceived("failure: a\n")
        self.protocol.lineReceived("error a\n")
        self.protocol.lineReceived("error: a\n")
        self.protocol.lineReceived("success a\n")
        self.protocol.lineReceived("success: a\n")
        self.protocol.lineReceived("successful a\n")
        self.protocol.lineReceived("successful: a\n")
        self.protocol.lineReceived("]\n")
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
        self.keywords_before_test()
        self.assertEqual(self.client.start_calls, [])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_keywords_after_error(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("error old mcdonald\n")
        self.keywords_before_test()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, 
                         [(self.test, subunit.RemoteError(""))])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])
        
    def test_keywords_after_failure(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("failure old mcdonald\n")
        self.keywords_before_test()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, 
                         [(self.test, subunit.RemoteError())])
        self.assertEqual(self.client.success_calls, [])
        
    def test_keywords_after_success(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("success old mcdonald\n")
        self.keywords_before_test()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [self.test])

    def test_keywords_after_test(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("failure a\n")
        self.protocol.lineReceived("failure: a\n")
        self.protocol.lineReceived("error a\n")
        self.protocol.lineReceived("error: a\n")
        self.protocol.lineReceived("success a\n")
        self.protocol.lineReceived("success: a\n")
        self.protocol.lineReceived("successful a\n")
        self.protocol.lineReceived("successful: a\n")
        self.protocol.lineReceived("]\n")
        self.protocol.lineReceived("failure old mcdonald\n")
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
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.failure_calls, 
                         [(self.test, subunit.RemoteError())])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_keywords_during_failure(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("failure: old mcdonald [\n")
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("failure a\n")
        self.protocol.lineReceived("failure: a\n")
        self.protocol.lineReceived("error a\n")
        self.protocol.lineReceived("error: a\n")
        self.protocol.lineReceived("success a\n")
        self.protocol.lineReceived("success: a\n")
        self.protocol.lineReceived("successful a\n")
        self.protocol.lineReceived("successful: a\n")
        self.protocol.lineReceived(" ]\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.stdout.getvalue(), "")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.failure_calls, 
                         [(self.test, subunit.RemoteError("test old mcdonald\n"
                                                  "failure a\n"
                                                  "failure: a\n"
                                                  "error a\n"
                                                  "error: a\n"
                                                  "success a\n"
                                                  "success: a\n"
                                                  "successful a\n"
                                                  "successful: a\n"
                                                  "]\n"))])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.success_calls, [])


class TestTestProtocolServerLostConnection(unittest.TestCase):
    
    def setUp(self):
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)
        self.test = subunit.RemotedTestCase("old mcdonald")

    def test_lost_connection_no_input(self):
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_lost_connection_after_start(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError("lost connection during "
                                            "test 'old mcdonald'"))])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_lost_connected_after_error(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("error old mcdonald\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError(""))])
        self.assertEqual(self.client.success_calls, [])
        
    def test_lost_connection_during_error(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("error old mcdonald [\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError("lost connection during error "
                                            "report of test 'old mcdonald'"))])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_lost_connected_after_failure(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("failure old mcdonald\n")
        self.protocol.lostConnection()
        test = subunit.RemotedTestCase("old mcdonald")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, 
                         [(self.test, subunit.RemoteError())])
        self.assertEqual(self.client.success_calls, [])
        
    def test_lost_connection_during_failure(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("failure old mcdonald [\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, 
                         [(self.test,
                           subunit.RemoteError("lost connection during "
                                               "failure report"
                                               " of test 'old mcdonald'"))])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [])

    def test_lost_connection_after_success(self):
        self.protocol.lineReceived("test old mcdonald\n")
        self.protocol.lineReceived("success old mcdonald\n")
        self.protocol.lostConnection()
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, [])
        self.assertEqual(self.client.success_calls, [self.test])


class TestTestProtocolServerAddError(unittest.TestCase):
    
    def setUp(self):
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)
        self.protocol.lineReceived("test mcdonalds farm\n")
        self.test = subunit.RemotedTestCase("mcdonalds farm")

    def simple_error_keyword(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm\n" % keyword)
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError(""))])
        self.assertEqual(self.client.failure_calls, [])

    def test_simple_error(self):
        self.simple_error_keyword("error")

    def test_simple_error_colon(self):
        self.simple_error_keyword("error:")

    def test_error_empty_message(self):
        self.protocol.lineReceived("error mcdonalds farm [\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError(""))])
        self.assertEqual(self.client.failure_calls, [])

    def error_quoted_bracket(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm [\n" % keyword)
        self.protocol.lineReceived(" ]\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [
            (self.test, subunit.RemoteError("]\n"))])
        self.assertEqual(self.client.failure_calls, [])

    def test_error_quoted_bracket(self):
        self.error_quoted_bracket("error")

    def test_error_colon_quoted_bracket(self):
        self.error_quoted_bracket("error:")


class TestTestProtocolServerAddFailure(unittest.TestCase):
    
    def setUp(self):
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)
        self.protocol.lineReceived("test mcdonalds farm\n")
        self.test = subunit.RemotedTestCase("mcdonalds farm")

    def simple_failure_keyword(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm\n" % keyword)
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, 
                         [(self.test, subunit.RemoteError())])

    def test_simple_failure(self):
        self.simple_failure_keyword("failure")

    def test_simple_failure_colon(self):
        self.simple_failure_keyword("failure:")

    def test_failure_empty_message(self):
        self.protocol.lineReceived("failure mcdonalds farm [\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, 
                         [(self.test, subunit.RemoteError())])

    def failure_quoted_bracket(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm [\n" % keyword)
        self.protocol.lineReceived(" ]\n")
        self.protocol.lineReceived("]\n")
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.failure_calls, 
                         [(self.test, subunit.RemoteError("]\n"))])

    def test_failure_quoted_bracket(self):
        self.failure_quoted_bracket("failure")

    def test_failure_colon_quoted_bracket(self):
        self.failure_quoted_bracket("failure:")


class TestTestProtocolServerAddSuccess(unittest.TestCase):
    
    def setUp(self):
        self.client = MockTestProtocolServerClient()
        self.protocol = subunit.TestProtocolServer(self.client)
        self.protocol.lineReceived("test mcdonalds farm\n")
        self.test = subunit.RemotedTestCase("mcdonalds farm")

    def simple_success_keyword(self, keyword):
        self.protocol.lineReceived("%s mcdonalds farm\n" % keyword)
        self.assertEqual(self.client.start_calls, [self.test])
        self.assertEqual(self.client.end_calls, [self.test])
        self.assertEqual(self.client.error_calls, [])
        self.assertEqual(self.client.success_calls, [self.test])

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
        self.assertEqual([(test, "RemoteError:\n"
                                 "Cannot run RemotedTestCases.\n\n")],
                         result.errors)
        self.assertEqual(1, result.testsRun)
        another_test = subunit.RemotedTestCase("A test description")
        self.assertEqual(test, another_test)
        different_test = subunit.RemotedTestCase("ofo")
        self.assertNotEqual(test, different_test)
        self.assertNotEqual(another_test, different_test)


class TestRemoteError(unittest.TestCase):

    def test_eq(self):
        error = subunit.RemoteError("Something went wrong")
        another_error = subunit.RemoteError("Something went wrong")
        different_error = subunit.RemoteError("boo!")
        self.assertEqual(error, another_error)
        self.assertNotEqual(error, different_error)
        self.assertNotEqual(different_error, another_error)

    def test_empty_constructor(self):
        self.assertEqual(subunit.RemoteError(), subunit.RemoteError(""))

def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

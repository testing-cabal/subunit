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
import sys

import subunit
import subunit.iso8601 as iso8601
import subunit.test_results
from subunit.content_type import ContentType
from subunit.content import Content


class LoggingDecorator(subunit.test_results.HookedTestResultDecorator):

    def __init__(self, decorated):
        self._calls = 0
        super(LoggingDecorator, self).__init__(decorated)

    def _before_event(self):
        self._calls += 1


class AssertBeforeTestResult(LoggingDecorator):
    """A TestResult for checking preconditions."""

    def __init__(self, decorated, test):
        self.test = test
        super(AssertBeforeTestResult, self).__init__(decorated)

    def _before_event(self):
        self.test.assertEqual(1, self.earlier._calls)
        super(AssertBeforeTestResult, self)._before_event()


class TimeCapturingResult(unittest.TestResult):

    def __init__(self):
        super(TimeCapturingResult, self).__init__()
        self._calls = []

    def time(self, a_datetime):
        self._calls.append(a_datetime)


class LoggingResult(object):
    """Basic support for logging of results."""
    
    def __init__(self):
        self._calls = []


class Python26TestResult(LoggingResult):
    """A python 2.6 like test result, that logs."""

    def addError(self, test, err):
        self._calls.append(('addError', test, err))

    def addFailure(self, test, err):
        self._calls.append(('addFailure', test, err))

    def addSuccess(self, test):
        self._calls.append(('addSuccess', test))

    def startTest(self, test):
        self._calls.append(('startTest', test))

    def stopTest(self, test):
        self._calls.append(('stopTest', test))


class Python27TestResult(Python26TestResult):
    """A python 2.7 like test result, that logs."""

    def addExpectedFailure(self, test, err):
        self._calls.append(('addExpectedFailure', test, err))

    def addSkip(self, test, reason):
        self._calls.append(('addSkip', test, reason))

    def addUnexpectedSuccess(self, test):
        self._calls.append(('addUnexpectedSuccess', test))

    def startTestRun(self):
        self._calls.append(('startTestRun',))

    def stopTestRun(self):
        self._calls.append(('stopTestRun',))


class ExtendedTestResult(Python27TestResult):
    """A test result like the proposed extended unittest result API."""

    def addError(self, test, err=None, details=None):
        self._calls.append(('addError', test, err or details))

    def addFailure(self, test, err=None, details=None):
        self._calls.append(('addFailure', test, err or details))

    def addExpectedFailure(self, test, err=None, details=None):
        self._calls.append(('addExpectedFailure', test, err or details))

    def addSkip(self, test, reason=None, details=None):
        self._calls.append(('addSkip', test, reason or details))

    def addSuccess(self, test, details=None):
        if details:
            self._calls.append(('addSuccess', test, details))
        else:
            self._calls.append(('addSuccess', test))

    def addUnexpectedSuccess(self, test, details=None):
        if details:
            self._calls.append(('addUnexpectedSuccess', test, details))
        else:
            self._calls.append(('addUnexpectedSuccess', test))

    def progress(self, offset, whence):
        self._calls.append(('progress', offset, whence))

    def tags(self, new_tags, gone_tags):
        self._calls.append(('tags', new_tags, gone_tags))

    def time(self, time):
        self._calls.append(('time', time))


class TestExtendedToOriginalResultDecoratorBase(unittest.TestCase):

    def make_26_result(self):
        self.result = Python26TestResult()
        self.make_converter()

    def make_27_result(self):
        self.result = Python27TestResult()
        self.make_converter()

    def make_converter(self):
        self.converter = \
            subunit.test_results.ExtendedToOriginalDecorator(self.result)

    def make_extended_result(self):
        self.result = ExtendedTestResult()
        self.make_converter()

    def check_outcome_details(self, outcome):
        """Call an outcome with a details dict to be passed through."""
        # This dict is /not/ convertible - thats deliberate, as it should
        # not hit the conversion code path.
        details = {'foo': 'bar'}
        getattr(self.converter, outcome)(self, details=details)
        self.assertEqual([(outcome, self, details)], self.result._calls)

    def get_details_and_string(self):
        """Get a details dict and expected string."""
        text1 = lambda:["1\n2\n"]
        text2 = lambda:["3\n4\n"]
        bin1 = lambda:["5\n"]
        details = {'text 1': Content(ContentType('text', 'plain'), text1),
            'text 2': Content(ContentType('text', 'strange'), text2),
            'bin 1': Content(ContentType('application', 'binary'), bin1)}
        return (details, "Binary content: bin 1\n"
            "Text attachment: text 1\n------------\n1\n2\n"
            "------------\nText attachment: text 2\n------------\n"
            "3\n4\n------------\n")

    def check_outcome_details_to_exec_info(self, outcome, expected=None):
        """Call an outcome with a details dict to be made into exc_info."""
        # The conversion is a done using RemoteError and the string contents
        # of the text types in the details dict.
        if not expected:
            expected = outcome
        details, err_str = self.get_details_and_string()
        getattr(self.converter, outcome)(self, details=details)
        err = subunit.RemoteError(err_str)
        self.assertEqual([(expected, self, err)], self.result._calls)

    def check_outcome_details_to_nothing(self, outcome, expected=None):
        """Call an outcome with a details dict to be swallowed."""
        if not expected:
            expected = outcome
        details = {'foo': 'bar'}
        getattr(self.converter, outcome)(self, details=details)
        self.assertEqual([(expected, self)], self.result._calls)

    def check_outcome_details_to_string(self, outcome):
        """Call an outcome with a details dict to be stringified."""
        details, err_str = self.get_details_and_string()
        getattr(self.converter, outcome)(self, details=details)
        self.assertEqual([(outcome, self, err_str)], self.result._calls)

    def check_outcome_exc_info(self, outcome, expected=None):
        """Check that calling a legacy outcome still works."""
        # calling some outcome with the legacy exc_info style api (no keyword
        # parameters) gets passed through.
        if not expected:
            expected = outcome
        err = subunit.RemoteError("foo\nbar\n")
        getattr(self.converter, outcome)(self, err)
        self.assertEqual([(expected, self, err)], self.result._calls)

    def check_outcome_exc_info_to_nothing(self, outcome, expected=None):
        """Check that calling a legacy outcome on a fallback works."""
        # calling some outcome with the legacy exc_info style api (no keyword
        # parameters) gets passed through.
        if not expected:
            expected = outcome
        err = subunit.RemoteError("foo\nbar\n")
        getattr(self.converter, outcome)(self, err)
        self.assertEqual([(expected, self)], self.result._calls)

    def check_outcome_nothing(self, outcome, expected=None):
        """Check that calling a legacy outcome still works."""
        if not expected:
            expected = outcome
        getattr(self.converter, outcome)(self)
        self.assertEqual([(expected, self)], self.result._calls)

    def check_outcome_string_nothing(self, outcome, expected):
        """Check that calling outcome with a string calls expected."""
        getattr(self.converter, outcome)(self, "foo")
        self.assertEqual([(expected, self)], self.result._calls)

    def check_outcome_string(self, outcome):
        """Check that calling outcome with a string works."""
        getattr(self.converter, outcome)(self, "foo")
        self.assertEqual([(outcome, self, "foo")], self.result._calls)


class TestExtendedToOriginalResultDecorator(
    TestExtendedToOriginalResultDecoratorBase):

    def test_progress_py26(self):
        self.make_26_result()
        self.converter.progress(1, 2)

    def test_progress_py27(self):
        self.make_27_result()
        self.converter.progress(1, 2)

    def test_progress_pyextended(self):
        self.make_extended_result()
        self.converter.progress(1, 2)
        self.assertEqual([('progress', 1, 2)], self.result._calls)

    def test_startTest_py26(self):
        self.make_26_result()
        self.converter.startTest(self)
        self.assertEqual([('startTest', self)], self.result._calls)
    
    def test_startTest_py27(self):
        self.make_27_result()
        self.converter.startTest(self)
        self.assertEqual([('startTest', self)], self.result._calls)

    def test_startTest_pyextended(self):
        self.make_extended_result()
        self.converter.startTest(self)
        self.assertEqual([('startTest', self)], self.result._calls)

    def test_startTestRun_py26(self):
        self.make_26_result()
        self.converter.startTestRun()
        self.assertEqual([], self.result._calls)
    
    def test_startTestRun_py27(self):
        self.make_27_result()
        self.converter.startTestRun()
        self.assertEqual([('startTestRun',)], self.result._calls)

    def test_startTestRun_pyextended(self):
        self.make_extended_result()
        self.converter.startTestRun()
        self.assertEqual([('startTestRun',)], self.result._calls)

    def test_stopTest_py26(self):
        self.make_26_result()
        self.converter.stopTest(self)
        self.assertEqual([('stopTest', self)], self.result._calls)
    
    def test_stopTest_py27(self):
        self.make_27_result()
        self.converter.stopTest(self)
        self.assertEqual([('stopTest', self)], self.result._calls)

    def test_stopTest_pyextended(self):
        self.make_extended_result()
        self.converter.stopTest(self)
        self.assertEqual([('stopTest', self)], self.result._calls)

    def test_stopTestRun_py26(self):
        self.make_26_result()
        self.converter.stopTestRun()
        self.assertEqual([], self.result._calls)
    
    def test_stopTestRun_py27(self):
        self.make_27_result()
        self.converter.stopTestRun()
        self.assertEqual([('stopTestRun',)], self.result._calls)

    def test_stopTestRun_pyextended(self):
        self.make_extended_result()
        self.converter.stopTestRun()
        self.assertEqual([('stopTestRun',)], self.result._calls)

    def test_tags_py26(self):
        self.make_26_result()
        self.converter.tags(1, 2)

    def test_tags_py27(self):
        self.make_27_result()
        self.converter.tags(1, 2)

    def test_tags_pyextended(self):
        self.make_extended_result()
        self.converter.tags(1, 2)
        self.assertEqual([('tags', 1, 2)], self.result._calls)

    def test_time_py26(self):
        self.make_26_result()
        self.converter.time(1)

    def test_time_py27(self):
        self.make_27_result()
        self.converter.time(1)

    def test_time_pyextended(self):
        self.make_extended_result()
        self.converter.time(1)
        self.assertEqual([('time', 1)], self.result._calls)


class TestExtendedToOriginalAddError(TestExtendedToOriginalResultDecoratorBase):

    outcome = 'addError'

    def test_outcome_Original_py26(self):
        self.make_26_result()
        self.check_outcome_exc_info(self.outcome)
    
    def test_outcome_Original_py27(self):
        self.make_27_result()
        self.check_outcome_exc_info(self.outcome)

    def test_outcome_Original_pyextended(self):
        self.make_extended_result()
        self.check_outcome_exc_info(self.outcome)

    def test_outcome_Extended_py26(self):
        self.make_26_result()
        self.check_outcome_details_to_exec_info(self.outcome)
    
    def test_outcome_Extended_py27(self):
        self.make_27_result()
        self.check_outcome_details_to_exec_info(self.outcome)

    def test_outcome_Extended_pyextended(self):
        self.make_extended_result()
        self.check_outcome_details(self.outcome)

    def test_outcome__no_details(self):
        self.make_extended_result()
        self.assertRaises(ValueError,
            getattr(self.converter, self.outcome), self)


class TestExtendedToOriginalAddFailure(
    TestExtendedToOriginalAddError):

    outcome = 'addFailure'


class TestExtendedToOriginalAddExpectedFailure(
    TestExtendedToOriginalAddError):

    outcome = 'addExpectedFailure'

    def test_outcome_Original_py26(self):
        self.make_26_result()
        self.check_outcome_exc_info_to_nothing(self.outcome, 'addSuccess')
    
    def test_outcome_Extended_py26(self):
        self.make_26_result()
        self.check_outcome_details_to_nothing(self.outcome, 'addSuccess')
    


class TestExtendedToOriginalAddSkip(
    TestExtendedToOriginalResultDecoratorBase):

    outcome = 'addSkip'

    def test_outcome_Original_py26(self):
        self.make_26_result()
        self.check_outcome_string_nothing(self.outcome, 'addSuccess')
    
    def test_outcome_Original_py27(self):
        self.make_27_result()
        self.check_outcome_string(self.outcome)

    def test_outcome_Original_pyextended(self):
        self.make_extended_result()
        self.check_outcome_string(self.outcome)

    def test_outcome_Extended_py26(self):
        self.make_26_result()
        self.check_outcome_string_nothing(self.outcome, 'addSuccess')
    
    def test_outcome_Extended_py27(self):
        self.make_27_result()
        self.check_outcome_details_to_string(self.outcome)

    def test_outcome_Extended_pyextended(self):
        self.make_extended_result()
        self.check_outcome_details(self.outcome)

    def test_outcome__no_details(self):
        self.make_extended_result()
        self.assertRaises(ValueError,
            getattr(self.converter, self.outcome), self)


class TestExtendedToOriginalAddSuccess(
    TestExtendedToOriginalResultDecoratorBase):

    outcome = 'addSuccess'
    expected = 'addSuccess'

    def test_outcome_Original_py26(self):
        self.make_26_result()
        self.check_outcome_nothing(self.outcome, self.expected)
    
    def test_outcome_Original_py27(self):
        self.make_27_result()
        self.check_outcome_nothing(self.outcome)

    def test_outcome_Original_pyextended(self):
        self.make_extended_result()
        self.check_outcome_nothing(self.outcome)

    def test_outcome_Extended_py26(self):
        self.make_26_result()
        self.check_outcome_details_to_nothing(self.outcome, self.expected)
    
    def test_outcome_Extended_py27(self):
        self.make_27_result()
        self.check_outcome_details_to_nothing(self.outcome)

    def test_outcome_Extended_pyextended(self):
        self.make_extended_result()
        self.check_outcome_details(self.outcome)


class TestExtendedToOriginalAddUnexpectedSuccess(
    TestExtendedToOriginalAddSuccess):

    outcome = 'addUnexpectedSuccess'


class TestHookedTestResultDecorator(unittest.TestCase):

    def setUp(self):
        # And end to the chain
        terminal = unittest.TestResult()
        # Asserts that the call was made to self.result before asserter was
        # called.
        asserter = AssertBeforeTestResult(terminal, self)
        # The result object we call, which much increase its call count.
        self.result = LoggingDecorator(asserter)
        asserter.earlier = self.result

    def tearDown(self):
        # The hook in self.result must have been called
        self.assertEqual(1, self.result._calls)
        # The hook in asserter must have been called too, otherwise the
        # assertion about ordering won't have completed.
        self.assertEqual(1, self.result.decorated._calls)

    def test_startTest(self):
        self.result.startTest(self)
        
    def test_startTestRun(self):
        self.result.startTestRun()
        
    def test_stopTest(self):
        self.result.stopTest(self)
        
    def test_stopTestRun(self):
        self.result.stopTestRun()

    def test_addError(self):
        self.result.addError(self, subunit.RemoteError())
        
    def test_addFailure(self):
        self.result.addFailure(self, subunit.RemoteError())

    def test_addSuccess(self):
        self.result.addSuccess(self)

    def test_addSkip(self):
        self.result.addSkip(self, "foo")

    def test_addExpectedFailure(self):
        self.result.addExpectedFailure(self, subunit.RemoteError())

    def test_addUnexpectedSuccess(self):
        self.result.addUnexpectedSuccess(self)

    def test_progress(self):
        self.result.progress(1, subunit.PROGRESS_SET)

    def test_wasSuccessful(self):
        self.result.wasSuccessful()

    def test_shouldStop(self):
        self.result.shouldStop

    def test_stop(self):
        self.result.stop()

    def test_time(self):
        self.result.time(None)
 

class TestAutoTimingTestResultDecorator(unittest.TestCase):

    def setUp(self):
        # And end to the chain which captures time events.
        terminal = TimeCapturingResult()
        # The result object under test.
        self.result = subunit.test_results.AutoTimingTestResultDecorator(
            terminal)

    def test_without_time_calls_time_is_called_and_not_None(self):
        self.result.startTest(self)
        self.assertEqual(1, len(self.result.decorated._calls))
        self.assertNotEqual(None, self.result.decorated._calls[0])

    def test_no_time_from_progress(self):
        self.result.progress(1, subunit.PROGRESS_CUR)
        self.assertEqual(0, len(self.result.decorated._calls))

    def test_no_time_from_shouldStop(self):
        self.result.decorated.stop()
        self.result.shouldStop
        self.assertEqual(0, len(self.result.decorated._calls))

    def test_calling_time_inhibits_automatic_time(self):
        # Calling time() outputs a time signal immediately and prevents
        # automatically adding one when other methods are called.
        time = datetime.datetime(2009,10,11,12,13,14,15, iso8601.Utc())
        self.result.time(time)
        self.result.startTest(self)
        self.result.stopTest(self)
        self.assertEqual(1, len(self.result.decorated._calls))
        self.assertEqual(time, self.result.decorated._calls[0])

    def test_calling_time_None_enables_automatic_time(self):
        time = datetime.datetime(2009,10,11,12,13,14,15, iso8601.Utc())
        self.result.time(time)
        self.assertEqual(1, len(self.result.decorated._calls))
        self.assertEqual(time, self.result.decorated._calls[0])
        # Calling None passes the None through, in case other results care.
        self.result.time(None)
        self.assertEqual(2, len(self.result.decorated._calls))
        self.assertEqual(None, self.result.decorated._calls[1])
        # Calling other methods doesn't generate an automatic time event.
        self.result.startTest(self)
        self.assertEqual(3, len(self.result.decorated._calls))
        self.assertNotEqual(None, self.result.decorated._calls[2])


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

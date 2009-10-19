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

"""TestResult helper classes used to by subunit."""

import datetime

import iso8601

import subunit


# NOT a TestResult, because we are implementing the interface, not inheriting
# it.
class TestResultDecorator(object):
    """General pass-through decorator.

    This provides a base that other TestResults can inherit from to 
    gain basic forwarding functionality. It also takes care of 
    handling the case where the target doesn't support newer methods
    or features by degrading them.
    """

    def __init__(self, decorated):
        """Create a TestResultDecorator forwarding to decorated."""
        self.decorated = decorated

    def _call_maybe(self, method_name, fallback, *params):
        """Call method_name on self.decorated, if present.
        
        This is used to guard newer methods which older pythons do not
        support. While newer clients won't call these methods if they don't
        exist, they do exist on the decorator, and thus the decorator has to be
        the one to filter them out.

        :param method_name: The name of the method to call.
        :param fallback: If not None, the fallback to call to handle downgrading
            this method. Otherwise when method_name is not available, no
            exception is raised and None is returned.
        :param *params: Parameters to pass to method_name.
        :return: The result of self.decorated.method_name(*params), if it
            exists, and None otherwise.
        """
        method = getattr(self.decorated, method_name, None)
        if method is None:
            if fallback is not None:
                return fallback(*params)
            return
        return method(*params)

    def startTest(self, test):
        return self.decorated.startTest(test)

    def startTestRun(self):
        return self._call_maybe("startTestRun", None)

    def stopTest(self, test):
        return self.decorated.stopTest(test)

    def stopTestRun(self):
        return self._call_maybe("stopTestRun", None)

    def addError(self, test, err):
        return self.decorated.addError(test, err)

    def addFailure(self, test, err):
        return self.decorated.addFailure(test, err)

    def addSuccess(self, test):
        return self.decorated.addSuccess(test)

    def addSkip(self, test, reason):
        return self._call_maybe("addSkip", self._degrade_skip, test, reason)

    def _degrade_skip(self, test, reason):
        return self.decorated.addSuccess(test)

    def addExpectedFailure(self, test, err):
        return self._call_maybe("addExpectedFailure",
            self.decorated.addFailure, test, err)

    def addUnexpectedSuccess(self, test):
        return self._call_maybe("addUnexpectedSuccess",
            self.decorated.addSuccess, test)

    def progress(self, offset, whence):
        return self._call_maybe("progress", None, offset, whence)

    def wasSuccessful(self):
        return self.decorated.wasSuccessful()

    @property
    def shouldStop(self):
        return self.decorated.shouldStop

    def stop(self):
        return self.decorated.stop()

    def time(self, a_datetime):
        return self._call_maybe("time", None, a_datetime)


class HookedTestResultDecorator(TestResultDecorator):
    """A TestResult which calls a hook on every event."""

    def __init__(self, decorated):
        self.super = super(HookedTestResultDecorator, self)
        self.super.__init__(decorated)

    def startTest(self, test):
        self._before_event()
        return self.super.startTest(test)

    def startTestRun(self):
        self._before_event()
        return self.super.startTestRun()

    def stopTest(self, test):
        self._before_event()
        return self.super.stopTest(test)

    def stopTestRun(self):
        self._before_event()
        return self.super.stopTestRun()

    def addError(self, test, err):
        self._before_event()
        return self.super.addError(test, err)

    def addFailure(self, test, err):
        self._before_event()
        return self.super.addFailure(test, err)

    def addSuccess(self, test):
        self._before_event()
        return self.super.addSuccess(test)

    def addSkip(self, test, reason):
        self._before_event()
        return self.super.addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        self._before_event()
        return self.super.addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self._before_event()
        return self.super.addUnexpectedSuccess(test)

    def progress(self, offset, whence):
        self._before_event()
        return self.super.progress(offset, whence)

    def wasSuccessful(self):
        self._before_event()
        return self.super.wasSuccessful()

    @property
    def shouldStop(self):
        self._before_event()
        return self.super.shouldStop

    def stop(self):
        self._before_event()
        return self.super.stop()

    def time(self, a_datetime):
        self._before_event()
        return self.super.time(a_datetime)


class AutoTimingTestResultDecorator(HookedTestResultDecorator):
    """Decorate a TestResult to add time events to a test run.

    By default this will cause a time event before every test event,
    but if explicit time data is being provided by the test run, then
    this decorator will turn itself off to prevent causing confusion.
    """

    def __init__(self, decorated):
        self._time = None
        super(AutoTimingTestResultDecorator, self).__init__(decorated)

    def _before_event(self):
        time = self._time
        if time is not None:
            return
        time = datetime.datetime.utcnow().replace(tzinfo=iso8601.Utc())
        self._call_maybe("time", None, time)

    def progress(self, offset, whence):
        return self._call_maybe("progress", None, offset, whence)

    @property
    def shouldStop(self):
        return self.decorated.shouldStop

    def time(self, a_datetime):
        """Provide a timestamp for the current test activity.

        :param a_datetime: If None, automatically add timestamps before every
            event (this is the default behaviour if time() is not called at
            all).  If not None, pass the provided time onto the decorated
            result object and disable automatic timestamps.
        """
        self._time = a_datetime
        return self._call_maybe("time", None, a_datetime)


class ExtendedToOriginalDecorator(object):
    """Permit new TestResult API code to degrade gracefully with old results.

    This decorates an existing TestResult and converts missing outcomes
    such as addSkip to older outcomes such as addSuccess. It also supports
    the extended details protocol. In all cases the most recent protocol
    is attempted first, and fallbacks only occur when the decorated result
    does not support the newer style of calling.
    """

    def __init__(self, decorated):
        self.decorated = decorated

    def addError(self, test, err=None, details=None):
        self._check_args(err, details)
        if details is not None:
            try:
                return self.decorated.addError(test, details=details)
            except TypeError, e:
                # have to convert
                err = self._details_to_exc_info(details)
        return self.decorated.addError(test, err)

    def addExpectedFailure(self, test, err=None, details=None):
        self._check_args(err, details)
        addExpectedFailure = getattr(self.decorated, 'addExpectedFailure', None)
        if addExpectedFailure is None:
            return self.addSuccess(test)
        if details is not None:
            try:
                return addExpectedFailure(test, details=details)
            except TypeError, e:
                # have to convert
                err = self._details_to_exc_info(details)
        return addExpectedFailure(test, err)

    def addFailure(self, test, err=None, details=None):
        self._check_args(err, details)
        if details is not None:
            try:
                return self.decorated.addFailure(test, details=details)
            except TypeError, e:
                # have to convert
                err = self._details_to_exc_info(details)
        return self.decorated.addFailure(test, err)

    def addSkip(self, test, reason=None, details=None):
        self._check_args(reason, details)
        addSkip = getattr(self.decorated, 'addSkip', None)
        if addSkip is None:
            return self.decorated.addSuccess(test)
        if details is not None:
            try:
                return addSkip(test, details=details)
            except TypeError, e:
                # have to convert
                reason = self._details_to_str(details)
        return addSkip(test, reason)

    def addUnexpectedSuccess(self, test, details=None):
        outcome = getattr(self.decorated, 'addUnexpectedSuccess', None)
        if outcome is None:
            return self.decorated.addSuccess(test)
        if details is not None:
            try:
                return outcome(test, details=details)
            except TypeError, e:
                pass
        return outcome(test)

    def addSuccess(self, test, details=None):
        if details is not None:
            try:
                return self.decorated.addSuccess(test, details=details)
            except TypeError, e:
                pass
        return self.decorated.addSuccess(test)

    def _check_args(self, err, details):
        param_count = 0
        if err is not None:
            param_count += 1
        if details is not None:
            param_count += 1
        if param_count != 1:
            raise ValueError("Must pass only one of err '%s' and details '%s"
                % (err, details))

    def _details_to_exc_info(self, details):
        """Convert a details dict to an exc_info tuple."""
        return subunit.RemoteError(self._details_to_str(details))

    def _details_to_str(self, details):
        """Convert a details dict to a string."""
        lines = []
        # sorted is for testing, may want to remove that and use a dict
        # subclass with defined order for iteritems instead.
        for key, content in sorted(details.iteritems()):
            if content.content_type.type != 'text':
                lines.append('Binary content: %s\n' % key)
                continue
            lines.append('Text attachment: %s\n' % key)
            lines.append('------------\n')
            lines.extend(content.iter_bytes())
            if not lines[-1].endswith('\n'):
                lines.append('\n')
            lines.append('------------\n')
        return ''.join(lines)

    def startTest(self, test):
        return self.decorated.startTest(test)

    def startTestRun(self):
        try:
            return self.decorated.startTestRun()
        except AttributeError:
            return

    def stopTest(self, test):
        return self.decorated.stopTest(test)

    def stopTestRun(self):
        try:
            return self.decorated.stopTestRun()
        except AttributeError:
            return

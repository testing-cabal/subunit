#
#  subunit: extensions to Python unittest to get test results from subprocesses.
#  Copyright (C) 2009  Robert Collins <robertc@robertcollins.net>
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

"""TestResult helper classes used to by subunit."""

import datetime

import iso8601

class HookedTestResultDecorator(object):
    """A TestResult which calls a hook on every event."""

    def __init__(self, decorated):
        self.decorated = decorated

    def _call_maybe(self, method_name, *params):
        """Call method_name on self.decorated, if present.
        
        This is used to guard newer methods which older pythons do not
        support. While newer clients won't call these methods if they don't
        exist, they do exist on the decorator, and thus the decorator has to be
        the one to filter them out.

        :param method_name: The name of the method to call.
        :param *params: Parameters to pass to method_name.
        :return: The result of self.decorated.method_name(*params), if it
            exists, and None otherwise.
        """
        method = getattr(self.decorated, method_name, None)
        if method is None:
            return
        return method(*params)

    def startTest(self, test):
        self._before_event()
        return self.decorated.startTest(test)

    def startTestRun(self):
        self._before_event()
        return self._call_maybe("startTestRun")

    def stopTest(self, test):
        self._before_event()
        return self.decorated.stopTest(test)

    def stopTestRun(self):
        self._before_event()
        return self._call_maybe("stopTestRun")

    def addError(self, test, err):
        self._before_event()
        return self.decorated.addError(test, err)

    def addFailure(self, test, err):
        self._before_event()
        return self.decorated.addFailure(test, err)

    def addSuccess(self, test):
        self._before_event()
        return self.decorated.addSuccess(test)

    def addSkip(self, test, reason):
        self._before_event()
        return self._call_maybe("addSkip", test, reason)

    def addExpectedFailure(self, test, err):
        self._before_event()
        return self._call_maybe("addExpectedFailure", test, err)

    def addUnexpectedSuccess(self, test):
        self._before_event()
        return self._call_maybe("addUnexpectedSuccess", test)

    def wasSuccessful(self):
        self._before_event()
        return self.decorated.wasSuccessful()

    @property
    def shouldStop(self):
        self._before_event()
        return self.decorated.shouldStop

    def stop(self):
        self._before_event()
        return self.decorated.stop()

    def time(self, a_datetime):
        self._before_event()
        return self._call_maybe("time", a_datetime)


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
        self._call_maybe("time", time)

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
        return self._call_maybe("time", a_datetime)

    def done(self):
        """Transition function until stopTestRun is used."""

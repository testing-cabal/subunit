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

    def stop(self):
        self._before_event()
        return self.decorated.stop()

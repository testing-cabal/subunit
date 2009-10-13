#
#  subunit: extensions to Python unittest to get test results from subprocesses.
#  Copyright (C) 2005  Robert Collins <robertc@robertcollins.net>
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

"""Handlers for outcome details."""

class DetailsParser(object):
    """Base class/API reference for details parsing."""


class SimpleDetailsParser(DetailsParser):
    """Parser for single-part [] delimited details."""

    def __init__(self, state):
        self._message = ""
        self._state = state

    def lineReceived(self, line):
        if line == "]\n":
            self._state.endDetails()
            return
        if line[0:2] == " ]":
            # quoted ] start
            self._message += line[1:]
        else:
            self._message += line

    def get_details(self):
        return None

    def get_message(self):
        return self._message


class MultipartDetailsParser(DetailsParser):
    """Parser for multi-part [] surrounded MIME typed chunked details."""

    def __init__(self, state):
        self._state = state
        self._details = {}

    def get_details(self):
        return self._details

    def get_message(self):
        return None

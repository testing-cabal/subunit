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

"""ContentType - a MIME Content Type."""

class ContentType(object):
    """A content type from http://www.iana.org/assignments/media-types/
    
    :ivar type: The primary type, e.g. "text" or "application"
    :ivar subtype: The subtype, e.g. "plain" or "octet-stream"
    :ivar parameters: A dict of additional parameters specific to the
    content type.
    """

    def __init__(self, primary_type, sub_type, parameters=None):
        """Create a ContentType."""
        if None in (primary_type, sub_type):
            raise ValueError("None not permitted in %r, %r" % (
                primary_type, sub_type))
        self.type = primary_type
        self.subtype = sub_type
        self.parameters = parameters or {}

    def __eq__(self, other):
        if type(other) != ContentType:
            return False
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "%s/%s params=%s" % (self.type, self.subtype, self.parameters)

#
#  subunit: extensions to Python unittest to get test results from subprocesses.
#  Copyright (C) 2025  Robert Collins <robertc@robertcollins.net>
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

"""Content and content type classes for subunit."""

import traceback


class ContentType:
    """A MIME Content Type."""

    def __init__(self, type_name, subtype, parameters=None):
        """Create a ContentType."""
        self.type = type_name
        self.subtype = subtype
        self.parameters = parameters or {}

    def __eq__(self, other):
        """Check equality."""
        if not isinstance(other, ContentType):
            return False
        return self.type == other.type and self.subtype == other.subtype and self.parameters == other.parameters

    def __hash__(self):
        """Hash for use in sets/dicts."""
        return hash((self.type, self.subtype, tuple(sorted(self.parameters.items()))))

    def __repr__(self):
        """String representation matching testtools format."""
        result = f"{self.type}/{self.subtype}"
        if self.parameters:
            param_strs = []
            for k, v in sorted(self.parameters.items()):
                param_strs.append(f'{k}="{v}"')
            result += "; " + "; ".join(param_strs)
        return result


class Content:
    """Some content to be attached to a test outcome."""

    def __init__(self, content_type, content_bytes):
        """Create a Content object.

        :param content_type: A ContentType object.
        :param content_bytes: A callable that returns an iterable of bytes.
        """
        self.content_type = content_type
        self._content_bytes = content_bytes

    def iter_bytes(self):
        """Iterate over the content as bytes."""
        return self._content_bytes()

    def __eq__(self, other):
        """Check equality."""
        if not isinstance(other, Content):
            return False
        return self.content_type == other.content_type and list(self.iter_bytes()) == list(other.iter_bytes())

    def __repr__(self):
        """String representation for debugging."""
        # Match testtools Content repr format
        params = ""
        if self.content_type.parameters:
            param_strs = []
            for k, v in sorted(self.content_type.parameters.items()):
                param_strs.append('%s="%s"' % (k, v))
            params = "; " + ", ".join(param_strs)

        # Try to get the value for content
        try:
            value = b"".join(self.iter_bytes())
            return "<Content type=%s/%s%s, value=%r>" % (
                self.content_type.type,
                self.content_type.subtype,
                params,
                value,
            )
        except (TypeError, ValueError, AttributeError):
            # If we can't get the value, just show the type
            return "<Content type=%s/%s%s>" % (self.content_type.type, self.content_type.subtype, params)


def text_content(text):
    """Convenience function to create text content."""
    content_type = ContentType("text", "plain", {"charset": "utf8"})
    if isinstance(text, str):
        text = text.encode("utf-8")
    return Content(content_type, lambda: [text])


class TracebackContent(Content):
    """Content object for Python tracebacks."""

    def __init__(self, error_tuple, test_case):
        """Create a TracebackContent.

        :param error_tuple: An (exc_type, exc_value, exc_tb) tuple.
        :param test_case: The test case that had the error.
        """
        content_type = ContentType("text", "x-traceback", {"charset": "utf8", "language": "python"})
        exc_type, exc_value, exc_tb = error_tuple

        def get_traceback_bytes():
            if exc_tb is not None:
                # Real exception with traceback
                tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
                tb_text = "".join(tb_lines)
            else:
                # Remote exception without traceback - just use class name and message
                if exc_type and exc_value:
                    tb_text = f"{exc_type.__module__}.{exc_type.__name__}: {exc_value}\n"
                else:
                    tb_text = f"{exc_value}\n"
            return [tb_text.encode("utf-8")]

        super().__init__(content_type, get_traceback_bytes)

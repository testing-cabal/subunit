#
#  subunit: extensions to python unittest to get test results from subprocesses.
#  Copyright (C) 2013 Subunit Contributors
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
from functools import partial
from io import BytesIO, StringIO, TextIOWrapper
import optparse
import sys
from tempfile import NamedTemporaryFile

from contextlib import contextmanager
from testscenarios import WithScenarios
from testtools import TestCase
from testtools.compat import _u
from testtools.matchers import (
    Equals,
    Matcher,
    MatchesListwise,
    Mismatch,
    raises,
)
from testtools.testresult.doubles import StreamResult

from subunit.iso8601 import UTC
from subunit.v2 import StreamResultToBytes, ByteStreamToStreamResult
from subunit._output import (
    _ALL_ACTIONS,
    _FINAL_ACTIONS,
    generate_stream_results,
    parse_arguments,
)
import subunit._output as _o


class SafeOptionParser(optparse.OptionParser):
    """An ArgumentParser class that doesn't call sys.exit."""

    def exit(self, status=0, message=""):
        raise RuntimeError(message)


safe_parse_arguments = partial(parse_arguments, ParserClass=SafeOptionParser)


class TestCaseWithPatchedStderr(TestCase):

    def setUp(self):
        super(TestCaseWithPatchedStderr, self).setUp()
        # prevent OptionParser from printing to stderr:
        if sys.version[0] > '2':
            self._stderr = StringIO()
        else:
            self._stderr = BytesIO()
        self.patch(optparse.sys, 'stderr', self._stderr)


class TestStatusArgParserTests(WithScenarios, TestCaseWithPatchedStderr):

    scenarios = [
        (cmd, dict(command=cmd, option='--' + cmd)) for cmd in _ALL_ACTIONS
    ]

    def test_can_parse_all_commands_with_test_id(self):
        test_id = self.getUniqueString()
        args = safe_parse_arguments(args=[self.option, test_id])

        self.assertThat(args.action, Equals(self.command))
        self.assertThat(args.test_id, Equals(test_id))

    def test_all_commands_parse_file_attachment(self):
        with NamedTemporaryFile() as tmp_file:
            args = safe_parse_arguments(
                args=[self.option, 'foo', '--attach-file', tmp_file.name]
            )
            self.assertThat(args.attach_file.name, Equals(tmp_file.name))

    def test_all_commands_accept_mimetype_argument(self):
        with NamedTemporaryFile() as tmp_file:
            args = safe_parse_arguments(
                args=[self.option, 'foo', '--attach-file', tmp_file.name, '--mimetype', "text/plain"]
            )
            self.assertThat(args.mimetype, Equals("text/plain"))

    def test_all_commands_accept_file_name_argument(self):
        with NamedTemporaryFile() as tmp_file:
            args = safe_parse_arguments(
                args=[self.option, 'foo', '--attach-file', tmp_file.name, '--file-name', "foo"]
            )
            self.assertThat(args.file_name, Equals("foo"))

    def test_all_commands_accept_tags_argument(self):
        args = safe_parse_arguments(
            args=[self.option, 'foo', '--tags', "foo,bar,baz"]
        )
        self.assertThat(args.tags, Equals(["foo", "bar", "baz"]))

    def test_attach_file_with_hyphen_opens_stdin(self):
        self.patch(_o.sys, 'stdin', TextIOWrapper(BytesIO(b"Hello")))
        args = safe_parse_arguments(
            args=[self.option, "foo", "--attach-file", "-"]
        )

        self.assertThat(args.attach_file.read(), Equals(b"Hello"))

    def test_attach_file_with_hyphen_sets_filename_to_stdin(self):
        args = safe_parse_arguments(
            args=[self.option, "foo", "--attach-file", "-"]
        )

        self.assertThat(args.file_name, Equals("stdin"))

    def test_can_override_stdin_filename(self):
        args = safe_parse_arguments(
            args=[self.option, "foo", "--attach-file", "-", '--file-name', 'foo']
        )

        self.assertThat(args.file_name, Equals("foo"))

    def test_requires_test_id(self):
        fn = lambda: safe_parse_arguments(args=[self.option])
        self.assertThat(
            fn,
            raises(RuntimeError('subunit-output: error: argument %s: must '
                'specify a single TEST_ID.\n' % self.option))
        )


class ArgParserTests(TestCaseWithPatchedStderr):

    def test_can_parse_attach_file_without_test_id(self):
        with NamedTemporaryFile() as tmp_file:
            args = safe_parse_arguments(
                args=["--attach-file", tmp_file.name]
            )
            self.assertThat(args.attach_file.name, Equals(tmp_file.name))

    def test_must_specify_argument(self):
        fn = lambda: safe_parse_arguments([])
        self.assertThat(
            fn,
            raises(RuntimeError('subunit-output: error: Must specify either '
                '--attach-file or a status command\n'))
        )

    def test_cannot_specify_more_than_one_status_command(self):
        fn = lambda: safe_parse_arguments(['--fail', 'foo', '--skip', 'bar'])
        self.assertThat(
            fn,
            raises(RuntimeError('subunit-output: error: argument --skip: '
                'Only one status may be specified at once.\n'))
        )

    def test_cannot_specify_mimetype_without_attach_file(self):
        fn = lambda: safe_parse_arguments(['--mimetype', 'foo'])
        self.assertThat(
            fn,
            raises(RuntimeError('subunit-output: error: Cannot specify '
                '--mimetype without --attach-file\n'))
        )

    def test_cannot_specify_filename_without_attach_file(self):
        fn = lambda: safe_parse_arguments(['--file-name', 'foo'])
        self.assertThat(
            fn,
            raises(RuntimeError('subunit-output: error: Cannot specify '
                '--file-name without --attach-file\n'))
        )

    def test_cannot_specify_tags_without_status_command(self):
        fn = lambda: safe_parse_arguments(['--tags', 'foo'])
        self.assertThat(
            fn,
            raises(RuntimeError('subunit-output: error: Cannot specify '
                '--tags without a status command\n'))
        )

    def test_must_specify_tags_with_tags_options(self):
        fn = lambda: safe_parse_arguments(['--fail', 'foo', '--tags'])
        self.assertThat(
            fn,
            raises(RuntimeError('subunit-output: error: Must specify at least one tag with --tags\n'))
        )


def get_result_for(commands):
    """Get a result object from *commands.

    Runs the 'generate_stream_results' function from subunit._output after
    parsing *commands as if they were specified on the command line. The
    resulting bytestream is then converted back into a result object and
    returned.
    """
    stream = BytesIO()

    args = safe_parse_arguments(commands)
    output_writer = StreamResultToBytes(output_stream=stream)
    generate_stream_results(args, output_writer)

    stream.seek(0)

    case = ByteStreamToStreamResult(source=stream)
    result = StreamResult()
    case.run(result)
    return result


@contextmanager
def temp_file_contents(data):
    """Create a temporary file on disk containing 'data'."""
    with NamedTemporaryFile() as f:
        f.write(data)
        f.seek(0)
        yield f


class StatusStreamResultTests(WithScenarios, TestCase):

    scenarios = [
        (s, dict(status=s, option='--' + s)) for s in _ALL_ACTIONS
    ]

    _dummy_timestamp = datetime.datetime(2013, 1, 1, 0, 0, 0, 0, UTC)

    def setUp(self):
        super(StatusStreamResultTests, self).setUp()
        self.patch(_o, 'create_timestamp', lambda: self._dummy_timestamp)
        self.test_id = self.getUniqueString()

    def test_only_one_packet_is_generated(self):
        result = get_result_for([self.option, self.test_id])
        self.assertThat(
            len(result._events),
            Equals(1)
        )

    def test_correct_status_is_generated(self):
        result = get_result_for([self.option, self.test_id])

        self.assertThat(
            result._events[0],
            MatchesStatusCall(test_status=self.status)
        )

    def test_all_commands_generate_tags(self):
        result = get_result_for([self.option, self.test_id, '--tags', 'hello,world'])
        self.assertThat(
            result._events[0],
            MatchesStatusCall(test_tags=set(['hello', 'world']))
        )

    def test_all_commands_generate_timestamp(self):
        result = get_result_for([self.option, self.test_id])

        self.assertThat(
            result._events[0],
            MatchesStatusCall(timestamp=self._dummy_timestamp)
        )

    def test_all_commands_generate_correct_test_id(self):
        result = get_result_for([self.option, self.test_id])

        self.assertThat(
            result._events[0],
            MatchesStatusCall(test_id=self.test_id)
        )

    def test_file_is_sent_in_single_packet(self):
        with temp_file_contents(b"Hello") as f:
            result = get_result_for([self.option, self.test_id, '--attach-file', f.name])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(file_bytes=b'Hello', eof=True),
                ])
            )

    def test_can_read_binary_files(self):
        with temp_file_contents(b"\xDE\xAD\xBE\xEF") as f:
            result = get_result_for([self.option, self.test_id, '--attach-file', f.name])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(file_bytes=b"\xDE\xAD\xBE\xEF", eof=True),
                ])
            )

    def test_can_read_empty_files(self):
        with temp_file_contents(b"") as f:
            result = get_result_for([self.option, self.test_id, '--attach-file', f.name])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(file_bytes=b"", file_name=f.name, eof=True),
                ])
            )

    def test_can_read_stdin(self):
        self.patch(_o.sys, 'stdin', TextIOWrapper(BytesIO(b"\xFE\xED\xFA\xCE")))
        result = get_result_for([self.option, self.test_id, '--attach-file', '-'])

        self.assertThat(
            result._events,
            MatchesListwise([
                MatchesStatusCall(file_bytes=b"\xFE\xED\xFA\xCE", file_name='stdin', eof=True),
            ])
        )

    def test_file_is_sent_with_test_id(self):
        with temp_file_contents(b"Hello") as f:
            result = get_result_for([self.option, self.test_id, '--attach-file', f.name])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(test_id=self.test_id, file_bytes=b'Hello', eof=True),
                ])
            )

    def test_file_is_sent_with_test_status(self):
        with temp_file_contents(b"Hello") as f:
            result = get_result_for([self.option, self.test_id, '--attach-file', f.name])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(test_status=self.status, file_bytes=b'Hello', eof=True),
                ])
            )

    def test_file_chunk_size_is_honored(self):
        with temp_file_contents(b"Hello") as f:
            self.patch(_o, '_CHUNK_SIZE', 1)
            result = get_result_for([self.option, self.test_id, '--attach-file', f.name])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(test_id=self.test_id, file_bytes=b'H', eof=False),
                    MatchesStatusCall(test_id=self.test_id, file_bytes=b'e', eof=False),
                    MatchesStatusCall(test_id=self.test_id, file_bytes=b'l', eof=False),
                    MatchesStatusCall(test_id=self.test_id, file_bytes=b'l', eof=False),
                    MatchesStatusCall(test_id=self.test_id, file_bytes=b'o', eof=True),
                ])
            )

    def test_file_mimetype_specified_once_only(self):
        with temp_file_contents(b"Hi") as f:
            self.patch(_o, '_CHUNK_SIZE', 1)
            result = get_result_for([
                self.option,
                self.test_id,
                '--attach-file',
                f.name,
                '--mimetype',
                'text/plain',
            ])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(test_id=self.test_id, mime_type='text/plain', file_bytes=b'H', eof=False),
                    MatchesStatusCall(test_id=self.test_id, mime_type=None, file_bytes=b'i', eof=True),
                ])
            )

    def test_tags_specified_once_only(self):
        with temp_file_contents(b"Hi") as f:
            self.patch(_o, '_CHUNK_SIZE', 1)
            result = get_result_for([
                self.option,
                self.test_id,
                '--attach-file',
                f.name,
                '--tags',
                'foo,bar',
            ])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(test_id=self.test_id, test_tags=set(['foo', 'bar'])),
                    MatchesStatusCall(test_id=self.test_id, test_tags=None),
                ])
            )

    def test_timestamp_specified_once_only(self):
        with temp_file_contents(b"Hi") as f:
            self.patch(_o, '_CHUNK_SIZE', 1)
            result = get_result_for([
                self.option,
                self.test_id,
                '--attach-file',
                f.name,
            ])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(test_id=self.test_id, timestamp=self._dummy_timestamp),
                    MatchesStatusCall(test_id=self.test_id, timestamp=None),
                ])
            )

    def test_test_status_specified_once_only(self):
        with temp_file_contents(b"Hi") as f:
            self.patch(_o, '_CHUNK_SIZE', 1)
            result = get_result_for([
                self.option,
                self.test_id,
                '--attach-file',
                f.name,
            ])

            # 'inprogress' status should be on the first packet only, all other
            # statuses should be on the last packet.
            if self.status in _FINAL_ACTIONS:
                first_call = MatchesStatusCall(test_id=self.test_id, test_status=None)
                last_call = MatchesStatusCall(test_id=self.test_id, test_status=self.status)
            else:
                first_call = MatchesStatusCall(test_id=self.test_id, test_status=self.status)
                last_call = MatchesStatusCall(test_id=self.test_id, test_status=None)
            self.assertThat(
                result._events,
                MatchesListwise([first_call, last_call])
            )

    def test_filename_can_be_overridden(self):
        with temp_file_contents(b"Hello") as f:
            specified_file_name = self.getUniqueString()
            result = get_result_for([
                self.option,
                self.test_id,
                '--attach-file',
                f.name,
                '--file-name',
                specified_file_name])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(file_name=specified_file_name, file_bytes=b'Hello'),
                ])
            )

    def test_file_name_is_used_by_default(self):
        with temp_file_contents(b"Hello") as f:
            result = get_result_for([self.option, self.test_id, '--attach-file', f.name])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(file_name=f.name, file_bytes=b'Hello', eof=True),
                ])
            )


class FileDataTests(TestCase):

    def test_can_attach_file_without_test_id(self):
        with temp_file_contents(b"Hello") as f:
            result = get_result_for(['--attach-file', f.name])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(test_id=None, file_bytes=b'Hello', eof=True),
                ])
            )

    def test_file_name_is_used_by_default(self):
        with temp_file_contents(b"Hello") as f:
            result = get_result_for(['--attach-file', f.name])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(file_name=f.name, file_bytes=b'Hello', eof=True),
                ])
            )

    def test_filename_can_be_overridden(self):
        with temp_file_contents(b"Hello") as f:
            specified_file_name = self.getUniqueString()
            result = get_result_for([
                '--attach-file',
                f.name,
                '--file-name',
                specified_file_name
            ])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(file_name=specified_file_name, file_bytes=b'Hello'),
                ])
            )

    def test_files_have_timestamp(self):
        _dummy_timestamp = datetime.datetime(2013, 1, 1, 0, 0, 0, 0, UTC)
        self.patch(_o, 'create_timestamp', lambda: _dummy_timestamp)

        with temp_file_contents(b"Hello") as f:
            specified_file_name = self.getUniqueString()
            result = get_result_for([
                '--attach-file',
                f.name,
            ])

            self.assertThat(
                result._events,
                MatchesListwise([
                    MatchesStatusCall(file_bytes=b'Hello', timestamp=_dummy_timestamp),
                ])
            )


class MatchesStatusCall(Matcher):

    _position_lookup = {
        'call': 0,
        'test_id': 1,
        'test_status': 2,
        'test_tags': 3,
        'runnable': 4,
        'file_name': 5,
        'file_bytes': 6,
        'eof': 7,
        'mime_type': 8,
        'route_code': 9,
        'timestamp': 10,
    }

    def __init__(self, **kwargs):
        unknown_kwargs = list(filter(
            lambda k: k not in self._position_lookup,
            kwargs
        ))
        if unknown_kwargs:
            raise ValueError("Unknown keywords: %s" % ','.join(unknown_kwargs))
        self._filters = kwargs

    def match(self, call_tuple):
        for k, v in self._filters.items():
            try:
                pos = self._position_lookup[k]
                if call_tuple[pos] != v:
                    return Mismatch(
                        "Value for key is %r, not %r" % (call_tuple[pos], v)
                    )
            except IndexError:
                return Mismatch("Key %s is not present." % k)

    def __str__(self):
        return "<MatchesStatusCall %r>" % self._filters

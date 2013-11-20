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


import argparse
import datetime
from functools import partial
from io import BytesIO, StringIO
from tempfile import NamedTemporaryFile

from testscenarios import WithScenarios
from testtools import TestCase
from testtools.compat import _b, _u
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
    generate_bytestream,
    parse_arguments,
    write_chunked_file,
)
import subunit._output as _o


class SafeArgumentParser(argparse.ArgumentParser):
    """An ArgumentParser class that doesn't call sys.exit."""

    def exit(self, status=0, message=""):
        raise RuntimeError(message)


safe_parse_arguments = partial(parse_arguments, ParserClass=SafeArgumentParser)


class TestStatusArgParserTests(WithScenarios, TestCase):

    scenarios = [
        (cmd, dict(command=cmd, option='--' + cmd)) for cmd in (
            'exists',
            'fail',
            'inprogress',
            'skip',
            'success',
            'uxsuccess',
            'xfail',
        )
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
        self.patch(_o, 'stdin', StringIO(_u("Hello")))
        args = safe_parse_arguments(
            args=[self.option, "foo", "--attach-file", "-"]
        )

        self.assertThat(args.attach_file.read(), Equals("Hello"))

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


class ArgParserTests(TestCase):

    def setUp(self):
        super(ArgParserTests, self).setUp()
        # prevent ARgumentParser from printing to stderr:
        self._stderr = BytesIO()
        self.patch(argparse._sys, 'stderr', self._stderr)

    def test_can_parse_attach_file_without_test_id(self):
        with NamedTemporaryFile() as tmp_file:
            args = safe_parse_arguments(
                args=["--attach-file", tmp_file.name]
            )
            self.assertThat(args.attach_file.name, Equals(tmp_file.name))

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


def get_result_for(commands):
    """Get a result object from *commands.

    Runs the 'generate_bytestream' function from subunit._output after
    parsing *commands as if they were specified on the command line. The
    resulting bytestream is then converted back into a result object and
    returned.
    """
    stream = BytesIO()

    args = safe_parse_arguments(commands)
    output_writer = StreamResultToBytes(output_stream=stream)
    generate_bytestream(args, output_writer)

    stream.seek(0)

    case = ByteStreamToStreamResult(source=stream)
    result = StreamResult()
    case.run(result)
    return result


class ByteStreamCompatibilityTests(WithScenarios, TestCase):

    scenarios = [
        (s, dict(status=s, option='--' + s)) for s in (
            'exists',
            'fail',
            'inprogress',
            'skip',
            'success',
            'uxsuccess',
            'xfail',
        )
    ]

    _dummy_timestamp = datetime.datetime(2013, 1, 1, 0, 0, 0, 0, UTC)

    def setUp(self):
        super(ByteStreamCompatibilityTests, self).setUp()
        self.patch(_o, 'create_timestamp', lambda: self._dummy_timestamp)

    def test_correct_status_is_generated(self):
        result = get_result_for([self.option, 'foo'])

        self.assertThat(
            result._events[0],
            MatchesCall(
                call='status',
                test_id='foo',
                test_status=self.status,
                timestamp=self._dummy_timestamp,
            )
        )

    def test_all_commands_accept_tags(self):
        result = get_result_for([self.option, 'foo', '--tags', 'hello,world'])
        self.assertThat(
            result._events[0],
            MatchesCall(
                call='status',
                test_id='foo',
                test_tags=set(['hello', 'world']),
                timestamp=self._dummy_timestamp,
            )
        )


class FileChunkingTests(WithScenarios, TestCase):

    scenarios = [
        ("With test_id", dict(test_id="foo")),
        ("Without test_id", dict(test_id=None)),
    ]

    def _write_chunk_file(self, file_data, chunk_size=1024, mimetype=None, filename=None, test_id=None):
        """Write file data to a subunit stream, get a StreamResult object."""
        stream = BytesIO()
        output_writer = StreamResultToBytes(output_stream=stream)

        with NamedTemporaryFile() as f:
            self._tmp_filename = f.name
            f.write(file_data)
            f.seek(0)

            write_chunked_file(
                file_obj=f,
                output_writer=output_writer,
                chunk_size=chunk_size,
                mime_type=mimetype,
                test_id=test_id,
                file_name=filename,
            )

        stream.seek(0)

        case = ByteStreamToStreamResult(source=stream)
        result = StreamResult()
        case.run(result)
        return result

    def test_file_chunk_size_is_honored(self):
        result = self._write_chunk_file(
            file_data=_b("Hello"),
            chunk_size=1,
            test_id=self.test_id,
        )
        self.assertThat(
            result._events,
            MatchesListwise([
                MatchesCall(call='status', test_id=self.test_id, file_bytes=_b('H'), mime_type=None, eof=False),
                MatchesCall(call='status', test_id=self.test_id, file_bytes=_b('e'), mime_type=None, eof=False),
                MatchesCall(call='status', test_id=self.test_id, file_bytes=_b('l'), mime_type=None, eof=False),
                MatchesCall(call='status', test_id=self.test_id, file_bytes=_b('l'), mime_type=None, eof=False),
                MatchesCall(call='status', test_id=self.test_id, file_bytes=_b('o'), mime_type=None, eof=False),
                MatchesCall(call='status', test_id=self.test_id, file_bytes=_b(''), mime_type=None, eof=True),
            ])
        )

    def test_file_mimetype_is_honored(self):
        result = self._write_chunk_file(
            file_data=_b("SomeData"),
            mimetype="text/plain",
            test_id=self.test_id,
        )
        self.assertThat(
            result._events,
            MatchesListwise([
                MatchesCall(call='status', test_id=self.test_id, file_bytes=_b('SomeData'), mime_type="text/plain"),
                MatchesCall(call='status', test_id=self.test_id, file_bytes=_b(''), mime_type="text/plain"),
            ])
        )

    def test_file_name_is_honored(self):
        result = self._write_chunk_file(
            file_data=_b("data"),
            filename="/some/name",
            test_id=self.test_id
        )
        self.assertThat(
            result._events,
            MatchesListwise([
                MatchesCall(call='status', test_id=self.test_id, file_name='/some/name'),
                MatchesCall(call='status', test_id=self.test_id, file_name='/some/name'),
            ])
        )

    def test_default_filename_is_used(self):
        result = self._write_chunk_file(file_data=_b("data"))
        self.assertThat(
            result._events,
            MatchesListwise([
                MatchesCall(call='status', file_name=self._tmp_filename),
                MatchesCall(call='status', file_name=self._tmp_filename),
            ])
        )


class MatchesCall(Matcher):

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
        return "<MatchesCall %r>" % self._filters

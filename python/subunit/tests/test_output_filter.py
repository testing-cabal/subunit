#
#  subunit: extensions to python unittest to get test results from subprocesses.
#  Copyright (C) 2005  Thomi Richards <thomi.richards@canonical.com>
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
from collections import namedtuple
import datetime
from functools import partial
from io import BytesIO
from tempfile import NamedTemporaryFile
from testtools import TestCase
from testtools.matchers import (
    Equals,
    IsInstance,
    Matcher,
    MatchesListwise,
    Mismatch,
)
from testtools.testresult.doubles import StreamResult

from subunit.v2 import StreamResultToBytes, ByteStreamToStreamResult
from subunit._output import (
    generate_bytestream,
    parse_arguments,
    translate_command_name,
    utc,
    write_chunked_file,
)
import subunit._output as _o


class SafeArgumentParser(argparse.ArgumentParser):

    def exit(self, status=0, message=""):
        raise RuntimeError("ArgumentParser requested to exit with status "\
            " %d and message %r" % (status, message))


safe_parse_arguments = partial(parse_arguments, ParserClass=SafeArgumentParser)


class OutputFilterArgumentTests(TestCase):

    """Tests for the command line argument parser."""

    _all_supported_commands = ('start', 'pass', 'fail', 'skip', 'exists')

    def _test_command(self, command, test_id):
        args = safe_parse_arguments(args=[command, test_id])

        self.assertThat(args.action, Equals(command))
        self.assertThat(args.test_id, Equals(test_id))

    def test_can_parse_all_commands_with_test_id(self):
        for command in self._all_supported_commands:
            self._test_command(command, self.getUniqueString())

    def test_command_translation(self):
        self.assertThat(translate_command_name('start'), Equals('inprogress'))
        self.assertThat(translate_command_name('pass'), Equals('success'))
        for command in ('fail', 'skip', 'exists'):
            self.assertThat(translate_command_name(command), Equals(command))

    def test_all_commands_parse_file_attachment(self):
        with NamedTemporaryFile() as tmp_file:
            for command in self._all_supported_commands:
                args = safe_parse_arguments(
                    args=[command, 'foo', '--attach-file', tmp_file.name]
                )
                self.assertThat(args.attach_file, IsInstance(file))
                self.assertThat(args.attach_file.name, Equals(tmp_file.name))

    def test_all_commands_accept_mimetype_argument(self):
        for command in self._all_supported_commands:
            args = safe_parse_arguments(
                args=[command, 'foo', '--mimetype', "text/plain"]
            )
            self.assertThat(args.mimetype, Equals("text/plain"))


class ByteStreamCompatibilityTests(TestCase):

    _dummy_timestamp = datetime.datetime(2013, 1, 1, 0, 0, 0, 0, utc)

    def setUp(self):
        super(ByteStreamCompatibilityTests, self).setUp()
        self.patch(_o, 'create_timestamp', lambda: self._dummy_timestamp)

    def _get_result_for(self, *commands):
        """Get a result object from *commands.

        Runs the 'generate_bytestream' function from subunit._output after
        parsing *commands as if they were specified on the command line. The
        resulting bytestream is then converted back into a result object and
        returned.

        """
        stream = BytesIO()

        for command_list in commands:
            args = safe_parse_arguments(command_list)
            output_writer = StreamResultToBytes(output_stream=stream)
            generate_bytestream(args, output_writer)

        stream.seek(0)

        case = ByteStreamToStreamResult(source=stream)
        result = StreamResult()
        case.run(result)
        return result

    def test_start_generates_inprogress(self):
        result = self._get_result_for(
            ['start', 'foo'],
        )

        self.assertThat(
            result._events[0],
            MatchesCall(
                call='status',
                test_id='foo',
                test_status='inprogress',
                timestamp=self._dummy_timestamp,
            )
        )

    def test_pass_generates_success(self):
        result = self._get_result_for(
            ['pass', 'foo'],
        )

        self.assertThat(
            result._events[0],
            MatchesCall(
                call='status',
                test_id='foo',
                test_status='success',
                timestamp=self._dummy_timestamp,
            )
        )

    def test_fail_generates_fail(self):
        result = self._get_result_for(
            ['fail', 'foo'],
        )

        self.assertThat(
            result._events[0],
            MatchesCall(
                call='status',
                test_id='foo',
                test_status='fail',
                timestamp=self._dummy_timestamp,
            )
        )

    def test_skip_generates_skip(self):
        result = self._get_result_for(
            ['skip', 'foo'],
        )

        self.assertThat(
            result._events[0],
            MatchesCall(
                call='status',
                test_id='foo',
                test_status='skip',
                timestamp=self._dummy_timestamp,
            )
        )

    def test_exists_generates_exists(self):
        result = self._get_result_for(
            ['exists', 'foo'],
        )

        self.assertThat(
            result._events[0],
            MatchesCall(
                call='status',
                test_id='foo',
                test_status='exists',
                timestamp=self._dummy_timestamp,
            )
        )


class FileChunkingTests(TestCase):

    def _write_chunk_file(self, file_data, chunk_size, mimetype=None):
        """Write chunked data to a subunit stream, return a StreamResult object."""
        stream = BytesIO()
        output_writer = StreamResultToBytes(output_stream=stream)

        with NamedTemporaryFile() as f:
            f.write(file_data)
            f.seek(0)

            write_chunked_file(f, 'foo_test', output_writer, chunk_size, mimetype)

        stream.seek(0)

        case = ByteStreamToStreamResult(source=stream)
        result = StreamResult()
        case.run(result)
        return result

    def test_file_chunk_size_is_honored(self):
        result = self._write_chunk_file("Hello", 1)
        self.assertThat(
            result._events,
            MatchesListwise([
                MatchesCall(call='status', file_bytes='H', mime_type=None, eof=False),
                MatchesCall(call='status', file_bytes='e', mime_type=None, eof=False),
                MatchesCall(call='status', file_bytes='l', mime_type=None, eof=False),
                MatchesCall(call='status', file_bytes='l', mime_type=None, eof=False),
                MatchesCall(call='status', file_bytes='o', mime_type=None, eof=False),
                MatchesCall(call='status', file_bytes='', mime_type=None, eof=True),
            ])
        )

    def test_file_mimetype_is_honored(self):
        result = self._write_chunk_file("SomeData", 1024, "text/plain")
        self.assertThat(
            result._events,
            MatchesListwise([
                MatchesCall(call='status', file_bytes='SomeData', mime_type="text/plain"),
                MatchesCall(call='status', file_bytes='', mime_type="text/plain"),
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
        unknown_kwargs = filter(
            lambda k: k not in self._position_lookup,
            kwargs
        )
        if unknown_kwargs:
            raise ValueError("Unknown keywords: %s" % ','.join(unknown_kwargs))
        self._filters = kwargs

    def match(self, call_tuple):
        for k,v in self._filters.items():
            try:
                pos = self._position_lookup[k]
                if call_tuple[pos] != v:
                    return Mismatch("Value for key is %r, not %r" % (call_tuple[pos], v))
            except IndexError:
                return Mismatch("Key %s is not present." % k)

    def __str__(self):
        return "<MatchesCall %r>" % self._filters


#!/usr/bin/env python
#  subunit: extensions to python unittest to get test results from subprocesses.
#  Copyright (C) 2013  Thomi Richards <thomi.richards@canonical.com>
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

from argparse import ArgumentParser
import datetime
from functools import partial
from sys import stdout
from string import split

from subunit.v2 import StreamResultToBytes

def output_main():
    args = parse_arguments()
    output = get_output_stream_writer()
    generate_bytestream(args, output)

    return 0


def parse_arguments(args=None, ParserClass=ArgumentParser):
    """Parse arguments from the command line.

    If specified, args must be a list of strings, similar to sys.argv[1:].

    ParserClass can be specified to override the class we use to parse the
    command-line arguments. This is useful for testing.

    """
    parser = ParserClass(
        prog='subunit-output',
        description="A tool to generate a subunit result byte-stream",
    )

    common_args = ParserClass(add_help=False)
    common_args.add_argument(
        "test_id",
        help="A string that uniquely identifies this test."
    )
    common_args.add_argument(
        "--attach-file",
        type=file,
        help="Attach a file to the result stream for this test."
    )
    common_args.add_argument(
        "--mimetype",
        help="The mime type to send with this file. This is only used if the "\
        "--attach-file argument is used. This argument is optional. If it is "\
        "not specified, the file will be sent wihtout a mime type.",
        default=None
    )
    common_args.add_argument(
        "--tags",
        help="A comma-separated list of tags to associate with this test.",
        type=partial(split, sep=','),
        default=None
    )
    sub_parsers = parser.add_subparsers(dest="action")

    final_state = "This is a final action: No more actions may be generated " \
        "for this test id after this one."

    parser_start = sub_parsers.add_parser(
        "start",
        help="Start a test.",
        parents=[common_args]
    )

    parser_pass = sub_parsers.add_parser(
        "pass",
        help="Pass a test. " + final_state,
        parents=[common_args]
    )

    parser_fail = sub_parsers.add_parser(
        "fail",
        help="Fail a test. " + final_state,
        parents=[common_args]
    )

    parser_skip = sub_parsers.add_parser(
        "skip",
        help="Skip a test. " + final_state,
        parents=[common_args]
    )

    parser_exists = sub_parsers.add_parser(
        "exists",
        help="Marks a test as existing. " + final_state,
        parents=[common_args]
    )

    return parser.parse_args(args)


def translate_command_name(command_name):
    """Turn the friendly command names we show users on the command line into
    something subunit understands.

    """
    return {
        'start': 'inprogress',
        'pass': 'success',
    }.get(command_name, command_name)


def get_output_stream_writer():
    return StreamResultToBytes(stdout)


def generate_bytestream(args, output_writer):
    output_writer.startTestRun()
    if args.attach_file:
        write_chunked_file(
            args.attach_file,
            args.test_id,
            output_writer,
            args.mimetype,
        )
    output_writer.status(
        test_id=args.test_id,
        test_status=translate_command_name(args.action),
        timestamp=create_timestamp(),
        test_tags=args.tags,
        )
    output_writer.stopTestRun()


def write_chunked_file(file_obj, test_id, output_writer, chunk_size=1024,
    mime_type=None):
    reader = partial(file_obj.read, chunk_size)
    for chunk in iter(reader, ''):
        output_writer.status(
            test_id=test_id,
            file_name=file_obj.name,
            file_bytes=chunk,
            mime_type=mime_type,
            eof=False,
        )
    output_writer.status(
            test_id=test_id,
            file_name=file_obj.name,
            file_bytes='',
            mime_type=mime_type,
            eof=True,
        )


_ZERO = datetime.timedelta(0)


class UTC(datetime.tzinfo):
    """UTC"""
    def utcoffset(self, dt):
        return _ZERO
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return _ZERO


utc = UTC()


def create_timestamp():
    return datetime.datetime.now(utc)

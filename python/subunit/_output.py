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
from sys import stdout

from subunit.v2 import StreamResultToBytes

def output_main():
    args = parse_arguments()
    output = get_output_stream_writer()
    generate_bytestream(args, output)

    return 0


def parse_arguments(args=None):
    """Parse arguments from the command line.

    If specified, args must be a list of strings, similar to sys.argv[1:].

    """
    parser = ArgumentParser(
        prog='subunit-output',
        description="A tool to generate a subunit result byte-stream",
    )
    sub_parsers = parser.add_subparsers(dest="action")

    parser_start = sub_parsers.add_parser("start", help="Start a test.")
    parser_start.add_argument("test_id", help="The test id you want to start.")

    parser_pass = sub_parsers.add_parser("pass", help="Pass a test.")
    parser_pass.add_argument("test_id", help="The test id you want to pass.")

    parser_fail = sub_parsers.add_parser("fail", help="Fail a test.")
    parser_fail.add_argument("test_id", help="The test id you want to fail.")

    parser_skip = sub_parsers.add_parser("skip", help="Skip a test.")
    parser_skip.add_argument("test_id", help="The test id you want to skip.")

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
    output_writer.status(
        test_id=args.test_id,
        test_status=translate_command_name(args.action)
        )

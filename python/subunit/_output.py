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
from optparse import (
    OptionGroup,
    OptionParser,
    OptionValueError,
)
import sys

from subunit.iso8601 import UTC
from subunit.v2 import StreamResultToBytes


_FINAL_ACTIONS = frozenset([
    'exists',
    'fail',
    'skip',
    'success',
    'uxsuccess',
    'xfail',
])
_ALL_ACTIONS = _FINAL_ACTIONS.union(['inprogress'])
_CHUNK_SIZE=3670016 # 3.5 MiB


def output_main():
    args = parse_arguments()
    output = StreamResultToBytes(sys.stdout)
    generate_stream_results(args, output)
    return 0


def parse_arguments(args=None, ParserClass=OptionParser):
    """Parse arguments from the command line.

    If specified, args must be a list of strings, similar to sys.argv[1:].

    ParserClass may be specified to override the class we use to parse the
    command-line arguments. This is useful for testing.
    """
    parser = ParserClass(
        prog="subunit-output",
        description="A tool to generate a subunit v2 result byte-stream",
        usage="subunit-output [-h] [status TEST_ID] [options]",
    )
    parser.set_default('tags', None)
    parser.set_default('test_id', None)

    status_commands = OptionGroup(
        parser,
        "Status Commands",
        "These options report the status of a test. TEST_ID must be a string "
            "that uniquely identifies the test."
    )
    for action_name in _ALL_ACTIONS:
        status_commands.add_option(
            "--%s" % action_name,
            nargs=1,
            action="callback",
            callback=set_status_cb,
            callback_args=(action_name,),
            dest="action",
            metavar="TEST_ID",
            help="Report a test status."
        )
    parser.add_option_group(status_commands)

    file_commands = OptionGroup(
        parser,
        "File Options",
        "These options control attaching data to a result stream. They can "
            "either be specified with a status command, in which case the file "
            "is attached to the test status, or by themselves, in which case "
            "the file is attached to the stream (and not associated with any "
            "test id)."
    )
    file_commands.add_option(
        "--attach-file",
        help="Attach a file to the result stream for this test. If '-' is "
            "specified, stdin will be read instead. In this case, the file "
            "name will be set to 'stdin' (but can still be overridden with "
            "the --file-name option)."
    )
    file_commands.add_option(
        "--file-name",
        help="The name to give this file attachment. If not specified, the "
            "name of the file on disk will be used, or 'stdin' in the case "
            "where '-' was passed to the '--attach-file' argument. This option"
            " may only be specified when '--attach-file' is specified.",
        )
    file_commands.add_option(
        "--mimetype",
        help="The mime type to send with this file. This is only used if the "
            "--attach-file argument is used. This argument is optional. If it "
            "is not specified, the file will be sent wihtout a mime type. This "
            "option may only be specified when '--attach-file' is specified.",
        default=None
    )
    parser.add_option_group(file_commands)

    parser.add_option(
        "--tags",
        help="A comma-separated list of tags to associate with a test. This "
            "option may only be used with a status command.",
        action="callback",
        callback=set_tags_cb,
        default=[]
    )

    (options, args) = parser.parse_args(args)
    if options.mimetype and not options.attach_file:
        parser.error("Cannot specify --mimetype without --attach-file")
    if options.file_name and not options.attach_file:
        parser.error("Cannot specify --file-name without --attach-file")
    if options.attach_file:
        if options.attach_file == '-':
            if not options.file_name:
                options.file_name = 'stdin'
            if sys.version[0] >= '3':
                options.attach_file = sys.stdin.buffer
            else:
                options.attach_file = sys.stdin
        else:
            try:
                options.attach_file = open(options.attach_file, 'rb')
            except IOError as e:
                parser.error("Cannot open %s (%s)" % (options.attach_file, e.strerror))
    if options.tags and not options.action:
        parser.error("Cannot specify --tags without a status command")
    if not (options.attach_file or options.action):
        parser.error("Must specify either --attach-file or a status command")

    return options


def set_status_cb(option, opt_str, value, parser, status_name):
    if getattr(parser.values, "action", None) is not None:
        raise OptionValueError("argument %s: Only one status may be specified at once." % option)

    if len(parser.rargs) == 0:
        raise OptionValueError("argument %s: must specify a single TEST_ID." % option)
    parser.values.action = status_name
    parser.values.test_id = parser.rargs.pop(0)


def set_tags_cb(option, opt_str, value, parser):
    if not parser.rargs:
        raise OptionValueError("Must specify at least one tag with --tags")
    parser.values.tags = parser.rargs.pop(0).split(',')


def generate_stream_results(args, output_writer):
    output_writer.startTestRun()

    if args.attach_file:
        reader = partial(args.attach_file.read, _CHUNK_SIZE)
        this_file_hunk = reader()
        next_file_hunk = reader()

    is_first_packet = True
    is_last_packet = False
    while not is_last_packet:

        # XXX
        def logme(*args, **kwargs):
            print(args, kwargs)
            output_writer.status(*args, **kwargs)
        write_status = output_writer.status

        if is_first_packet:
            if args.attach_file:
                # mimetype is specified on the first chunk only:
                if args.mimetype:
                    write_status = partial(write_status, mime_type=args.mimetype)
            # tags are only written on the first packet:
            if args.tags:
                write_status = partial(write_status, test_tags=args.tags)
            # timestamp is specified on the first chunk as well:
            write_status = partial(write_status, timestamp=create_timestamp())
            if args.action not in _FINAL_ACTIONS:
                write_status = partial(write_status, test_status=args.action)
            is_first_packet = False

        if args.attach_file:
            # filename might be overridden by the user
            filename = args.file_name or args.attach_file.name
            write_status = partial(write_status, file_name=filename, file_bytes=this_file_hunk)
            if next_file_hunk == b'':
                write_status = partial(write_status, eof=True)
                is_last_packet = True
            else:
                this_file_hunk = next_file_hunk
                next_file_hunk = reader()
        else:
            is_last_packet = True

        if args.test_id:
            write_status = partial(write_status, test_id=args.test_id)

        if is_last_packet:
            write_status = partial(write_status, eof=True)
            if args.action in _FINAL_ACTIONS:
                write_status = partial(write_status, test_status=args.action)

        write_status()

    output_writer.stopTestRun()


def create_timestamp():
    return datetime.datetime.now(UTC)

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

from optparse import (
    OptionGroup,
    OptionParser,
    OptionValueError,
)
import datetime
from functools import partial
from sys import stdin, stdout

from testtools.compat import _b

from subunit.iso8601 import UTC
from subunit.v2 import StreamResultToBytes


def output_main():
    args = parse_arguments()
    output = get_output_stream_writer()
    generate_bytestream(args, output)
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
        usage="subunit-output [-h] [status test_id] [options]",
    )
    parser.set_default('tags', None)

    status_commands = OptionGroup(
        parser,
        "Status Commands",
        "These options report the status of a test. TEST_ID must be a string "
            "that uniquely identifies the test."
    )
    final_actions = 'exists fail skip success xfail uxsuccess'.split()
    all_actions = final_actions + ['inprogress']
    for action_name in all_actions:
        final_text =  " This is a final state: No more status reports may "\
            "be generated for this test id after this one."

        status_commands.add_option(
            "--%s" % action_name,
            nargs=1,
            action="callback",
            callback=status_action,
            callback_args=(action_name,),
            dest="action",
            metavar="TEST_ID",
            help="Report a test status." + final_text if action_name in final_actions else ""
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
        callback=tags_action,
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
            options.attach_file = stdin
        else:
            try:
                options.attach_file = open(options.attach_file)
            except IOError as e:
                parser.error("Cannot open %s (%s)" % (options.attach_file, e.strerror))
    if options.tags and not options.action:
        parser.error("Cannot specify --tags without a status command")
    if not (options.attach_file or options.action):
        parser.error("Must specify either --attach-file or a status command")

    return options


def status_action(option, opt_str, value, parser, status_name):
    if getattr(parser.values, "action", None) is not None:
        raise OptionValueError("argument %s: Only one status may be specified at once." % option)

    if len(parser.rargs) == 0:
        raise OptionValueError("argument %s: must specify a single TEST_ID.")
    parser.values.action = status_name
    parser.values.test_id = parser.rargs.pop(0)


def tags_action(option, opt_str, value, parser):
    parser.values.tags = parser.rargs.pop(0).split(',')


def get_output_stream_writer():
    return StreamResultToBytes(stdout)


def generate_bytestream(args, output_writer):
    output_writer.startTestRun()
    if args.attach_file:
        write_chunked_file(
            file_obj=args.attach_file,
            test_id=args.test_id,
            output_writer=output_writer,
            mime_type=args.mimetype,
        )
    output_writer.status(
        test_id=args.test_id,
        test_status=args.action,
        timestamp=create_timestamp(),
        test_tags=args.tags,
        )
    output_writer.stopTestRun()


def write_chunked_file(file_obj, output_writer, chunk_size=1024,
                       mime_type=None, test_id=None, file_name=None):
    reader = partial(file_obj.read, chunk_size)

    write_status = output_writer.status
    if mime_type is not None:
        write_status = partial(
            write_status,
            mime_type=mime_type
        )
    if test_id is not None:
        write_status = partial(
            write_status,
            test_id=test_id
        )
    filename = file_name if file_name else file_obj.name

    for chunk in iter(reader, _b('')):
        write_status(
            file_name=filename,
            file_bytes=chunk,
            eof=False,
        )
    write_status(
        file_name=filename,
        file_bytes=_b(''),
        eof=True,
    )


def create_timestamp():
    return datetime.datetime.now(UTC)

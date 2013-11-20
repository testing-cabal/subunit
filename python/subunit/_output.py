#  subunit: extensions to python unittest to get test results from subprocesses.
#  Copyright (C) 2013 'Subunit Contributors'
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

from argparse import ArgumentError, ArgumentParser, Action
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


def parse_arguments(args=None, ParserClass=ArgumentParser):
    """Parse arguments from the command line.

    If specified, args must be a list of strings, similar to sys.argv[1:].

    ParserClass can be specified to override the class we use to parse the
    command-line arguments. This is useful for testing.

    """

    class StatusAction(Action):
        """A custom action that stores option name and argument separately.

        This is part of a workaround for the fact that argparse does not
        support optional subcommands (http://bugs.python.org/issue9253).
        """

        def __init__(self, status_name, *args, **kwargs):
            super(StatusAction, self).__init__(*args, **kwargs)
            self._status_name = status_name

        def __call__(self, parser, namespace, values, option_string=None):
            if getattr(namespace, self.dest, None) is not None:
                raise ArgumentError(self, "Only one status may be specified at once.")
            setattr(namespace, self.dest, self._status_name)
            setattr(namespace, 'test_id', values[0])


    parser = ParserClass(
        prog='subunit-output',
        description="A tool to generate a subunit result byte-stream",
    )

    status_commands = parser.add_argument_group(
        "Status Commands",
        "These options report the status of a test. TEST_ID must be a string "
            "that uniquely identifies the test."
    )
    final_actions = 'success fail skip xfail uxsuccess'.split()
    for action in "inprogress success fail skip exists xfail uxsuccess".split():
        final_text =  "This is a final state: No more status reports may "\
            "be generated for this test id after this one."

        status_commands.add_argument(
            "--%s" % action,
            nargs=1,
            action=partial(StatusAction, action),
            dest="action",
            metavar="TEST_ID",
            help="Report a test status." + final_text if action in final_actions else ""
        )

    file_commands = parser.add_argument_group(
        "File Options",
        "These options control attaching data to a result stream. They can "
            "either be specified with a status command, in which case the file "
            "is attached to the test status, or by themselves, in which case "
            "the file is attached to the stream (and not associated with any "
            "test id)."
    )
    file_commands.add_argument(
        "--attach-file",
        help="Attach a file to the result stream for this test. If '-' is "
            "specified, stdin will be read instead. In this case, the file "
            "name will be set to 'stdin' (but can still be overridden with "
            "the --file-name option)."
    )
    file_commands.add_argument(
        "--file-name",
        help="The name to give this file attachment. If not specified, the "
            "name of the file on disk will be used, or 'stdin' in the case "
            "where '-' was passed to the '--attach-file' argument. This option"
            " may only be specified when '--attach-file' is specified.",
        )
    file_commands.add_argument(
        "--mimetype",
        help="The mime type to send with this file. This is only used if the "
            "--attach-file argument is used. This argument is optional. If it "
            "is not specified, the file will be sent wihtout a mime type. This "
            "option may only be specified when '--attach-file' is specified.",
        default=None
    )

    parser.add_argument(
        "--tags",
        help="A comma-separated list of tags to associate with a test. This "
            "option may only be used with a status command.",
        type=lambda s: s.split(','),
        default=None
    )

    args = parser.parse_args(args)
    if args.mimetype and not args.attach_file:
        parser.error("Cannot specify --mimetype without --attach-file")
    if args.file_name and not args.attach_file:
        parser.error("Cannot specify --file-name without --attach-file")
    if args.attach_file:
        if args.attach_file == '-':
            if not args.file_name:
                args.file_name = 'stdin'
            args.attach_file = stdin
        else:
            try:
                args.attach_file = open(args.attach_file)
            except IOError as e:
                parser.error("Cannot open %s (%s)" % (args.attach_file, e.strerror))
    if args.tags and not args.action:
        parser.error("Cannot specify --tags without a status command")

    return args


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

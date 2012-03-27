#  subunit: extensions to python unittest to get test results from subprocesses.
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


from optparse import OptionParser
import sys

from subunit import DiscardStream, ProtocolTestCase
from subunit.test_results import CsvResult


def make_options():
    parser = OptionParser(description=__doc__)
    parser.add_option(
        "--no-passthrough", action="store_true",
        help="Hide all non subunit input.", default=False, dest="no_passthrough")
    parser.add_option(
        "-o", "--output-to",
        help="Output the XML to this path rather than stdout.")
    parser.add_option(
        "-f", "--forward", action="store_true", default=False,
        help="Forward subunit stream on stdout.")
    return parser


def get_output_stream(output_to):
    if output_to is None:
        return sys.stdout
    else:
        return file(output_to, 'wb')


def filter_with_result(result_factory, input_stream, output_stream,
                       passthrough_stream, forward_stream):
    result = result_factory(output_stream)
    test = ProtocolTestCase(
        input_stream, passthrough=passthrough_stream,
        forward=forward_stream)
    result.startTestRun()
    test.run(result)
    result.stopTestRun()
    return result


def something(result_factory, output_path, no_passthrough, forward):
    if no_passthrough:
        passthrough_stream = DiscardStream()
    else:
        passthrough_stream = None

    if forward:
        forward_stream = sys.stdout
    else:
        forward_stream = None

    output_to = get_output_stream(output_path)
    try:
        result = filter_with_result(
            result_factory, sys.stdin, output_to, passthrough_stream,
            forward_stream)
    finally:
        if output_path:
            output_to.close()
    if result.wasSuccessful():
        return 0
    else:
        return 1


def main():
    parser = make_options()
    (options, args) = parser.parse_args()
    sys.exit(
        something(CsvResult, options.output_to, options.no_passthrough, options.forward))

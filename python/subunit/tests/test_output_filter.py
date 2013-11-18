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


from io import BytesIO

from testtools import TestCase, StreamToExtendedDecorator, TestResult
from testtools.matchers import Equals

from subunit.v2 import StreamResultToBytes, ByteStreamToStreamResult
from subunit._output import (
    generate_bytestream,
    parse_arguments,
    translate_command_name,
)

class OutputFilterArgumentTests(TestCase):

    """Tests for the command line argument parser."""

    def _test_command(self, command, test_id):
        args = parse_arguments(args=[command, test_id])

        self.assertThat(args.action, Equals(command))
        self.assertThat(args.test_id, Equals(test_id))

    def test_can_parse_start_test(self):
        self._test_command('start', self.getUniqueString())

    def test_can_parse_pass_test(self):
        self._test_command('pass', self.getUniqueString())

    def test_can_parse_fail_test(self):
        self._test_command('fail', self.getUniqueString())

    def test_can_parse_skip_test(self):
        self._test_command('skip', self.getUniqueString())

    def test_command_translation(self):
        self.assertThat(translate_command_name('start'), Equals('inprogress'))
        self.assertThat(translate_command_name('pass'), Equals('success'))
        for command in ('fail', 'skip'):
            self.assertThat(translate_command_name(command), Equals(command))


class ByteStreamCompatibilityTests(TestCase):

    """Tests that ensure that the subunit byetstream we generate contains what
    we expect it to.

    """

    def _get_result_for(self, *commands):
        """Get a result object from *args.

        Runs the 'generate_bytestream' function from subunit._output after
        parsing *args as if they were specified on the command line. The
        resulting bytestream is then converted back into a result object and
        returned.

        """
        stream = BytesIO()

        for command_list in commands:
            args = parse_arguments(command_list)
            output_writer = StreamResultToBytes(output_stream=stream)
            generate_bytestream(args, output_writer)

        stream.seek(0)

        case = ByteStreamToStreamResult(source=stream)
        result = TestResult()
        result = StreamToExtendedDecorator(result)
        result.startTestRun()
        case.run(result)
        result.stopTestRun()
        return result

    def test_start(self):
        result = self._get_result_for(
            ['start', 'foo'],
            ['pass', 'foo'],
        )

        self.assertThat(result.decorated.wasSuccessful(), Equals(True))
        # How do I get the id? or details?
        self.assertThat(result.decorated.id(), Equals('foo'))




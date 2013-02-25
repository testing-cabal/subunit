#
#  subunit: extensions to Python unittest to get test results from subprocesses.
#  Copyright (C) 2013  Robert Collins <robertc@robertcollins.net>
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
import datetime

from testtools import TestCase
from testtools.tests.test_testresult import TestStreamResultContract
from testtools.testresult.doubles import StreamResult

import subunit
import subunit.iso8601 as iso8601

class TestStreamResultToBytesContract(TestCase, TestStreamResultContract):
    """Check that StreamResult behaves as testtools expects."""

    def _make_result(self):
        return subunit.StreamResultToBytes(BytesIO())


class TestStreamResultToBytes(TestCase):

    def _make_result(self):
        output = BytesIO()
        return subunit.StreamResultToBytes(output), output

    def test_trivial_enumeration(self):
        result, output = self._make_result()
        result.status("foo", 'exists')
        self.assertEqual(b'\xb3\x29\x01\0\0\x0f\0\x03foo\x99\x0c\x34\x3f',
            output.getvalue())

    def test_inprogress(self):
        result, output = self._make_result()
        result.status("foo", 'inprogress')
        self.assertEqual(b'\xb3\x29\x02\0\0\x0f\0\x03foo\xa0\x81\x08\xfa',
            output.getvalue())

    def test_success(self):
        result, output = self._make_result()
        result.status("foo", 'success')
        self.assertEqual(b'\xb3\x29\x03\0\0\x0f\0\x03foo\xb7\xfa\x1c\xb9',
            output.getvalue())

    def test_uxsuccess(self):
        result, output = self._make_result()
        result.status("foo", 'uxsuccess')
        self.assertEqual(b'\xb3\x29\x04\0\0\x0f\0\x03foo\xd3\x9bqp',
            output.getvalue())

    def test_skip(self):
        result, output = self._make_result()
        result.status("foo", 'skip')
        self.assertEqual(b'\xb3\x29\x05\0\0\x0f\0\x03foo\xc4\xe0e3',
            output.getvalue())

    def test_fail(self):
        result, output = self._make_result()
        result.status("foo", 'fail')
        self.assertEqual(b'\xb3\x29\x06\0\0\x0f\0\x03foo\xfdmY\xf6',
            output.getvalue())

    def test_xfail(self):
        result, output = self._make_result()
        result.status("foo", 'xfail')
        self.assertEqual(b'\xb3\x29\x07\0\0\x0f\0\x03foo\xea\x16M\xb5',
            output.getvalue())

    def test_unknown_status(self):
        result, output = self._make_result()
        self.assertRaises(Exception, result.status, "foo", 'boo')
        self.assertEqual(b'', output.getvalue())

    def test_eof(self):
        result, output = self._make_result()
        result.status(eof=True)
        self.assertEqual(
            b'\xb3!\x10\x00\x00\na\xf1xM',
            output.getvalue())

    def test_file_content(self):
        result, output = self._make_result()
        result.status(file_name="barney", file_bytes=b"woo")
        self.assertEqual(
            b'\xb3!@\x00\x00\x15\x00\x06barneywoo\xfd\xecu\x1c',
            output.getvalue())

    def test_mime(self):
        result, output = self._make_result()
        result.status(mime_type="application/foo; charset=1")
        self.assertEqual(
            b'\xb3! \x00\x00&\x00\x1aapplication/foo; charset=1]#\xf9\xf9',
            output.getvalue())

    def test_route_code(self):
        result, output = self._make_result()
        result.status(test_id="bar", test_status='success',
            route_code="source")
        self.assertEqual(b'\xb3-\x03\x00\x00\x17\x00\x06source\x00\x03bar\xad\xbd\x8c$',
            output.getvalue())

    def test_runnable(self):
        result, output = self._make_result()
        result.status("foo", 'success', runnable=False)
        self.assertEqual(b'\xb3(\x03\x00\x00\x0f\x00\x03fooX8w\x87',
            output.getvalue())

    def test_tags(self):
        result, output = self._make_result()
        result.status(test_id="bar", test_tags=set(['foo', 'bar']))
        self.assertEqual(b'\xb3)\x80\x00\x00\x1b\x00\x03bar\x00\x02\x00\x03foo\x00\x03bar\xabMw\xe6',
            output.getvalue())

    def test_timestamp(self):
        timestamp = datetime.datetime(2001, 12, 12, 12, 59, 59, 45,
            iso8601.Utc())
        result, output = self._make_result()
        result.status(test_id="bar", test_status='success', timestamp=timestamp)
        self.assertEqual(b'\xb3+\x03\x00\x00\x17<\x17T\xcf\x00\x00\xaf\xc8\x00\x03barU>\xb2\xdb',
            output.getvalue())


class TestByteStreamToStreamResult(TestCase):

    def test_non_subunit_encapsulated(self):
        source = BytesIO(b"foo\nbar\n")
        result = StreamResult()
        subunit.ByteStreamToStreamResult(
            source, non_subunit_name="stdout").run(result)
        self.assertEqual([
            ('status', None, None, None, True, 'stdout', b'f', False, None, None, None),
            ('status', None, None, None, True, 'stdout', b'o', False, None, None, None),
            ('status', None, None, None, True, 'stdout', b'o', False, None, None, None),
            ('status', None, None, None, True, 'stdout', b'\n', False, None, None, None),
            ('status', None, None, None, True, 'stdout', b'b', False, None, None, None),
            ('status', None, None, None, True, 'stdout', b'a', False, None, None, None),
            ('status', None, None, None, True, 'stdout', b'r', False, None, None, None),
            ('status', None, None, None, True, 'stdout', b'\n', False, None, None, None),
            ], result._events)
        self.assertEqual(b'', source.read())

    def test_non_subunit_disabled_raises(self):
        source = BytesIO(b"foo\nbar\n")
        result = StreamResult()
        case = subunit.ByteStreamToStreamResult(source)
        e = self.assertRaises(Exception, case.run, result)
        self.assertEqual(b'f', e.args[1])
        self.assertEqual(b'oo\nbar\n', source.read())
        self.assertEqual([], result._events)

    def test_trivial_enumeration(self):
        source = BytesIO(b'\xb3\x29\x01\0\0\x0f\0\x03foo\x99\x0c\x34\x3f')
        result = StreamResult()
        subunit.ByteStreamToStreamResult(
            source, non_subunit_name="stdout").run(result)
        self.assertEqual(b'', source.read())
        self.assertEqual([
            ('status', 'foo', 'exists', None, True, None, None, False, None, None, None),
            ], result._events)

    def test_multiple_events(self):
        source = BytesIO(b'\xb3\x29\x01\0\0\x0f\0\x03foo\x99\x0c\x34\x3f'
                         b'\xb3\x29\x01\0\0\x0f\0\x03foo\x99\x0c\x34\x3f')
        result = StreamResult()
        subunit.ByteStreamToStreamResult(
            source, non_subunit_name="stdout").run(result)
        self.assertEqual(b'', source.read())
        self.assertEqual([
            ('status', 'foo', 'exists', None, True, None, None, False, None, None, None),
            ('status', 'foo', 'exists', None, True, None, None, False, None, None, None),
            ], result._events)

    def test_inprogress(self):
        self.check_event(
            b'\xb3\x29\x02\0\0\x0f\0\x03foo\xa0\x81\x08\xfa', 'inprogress')

    def test_success(self):
        self.check_event(
            b'\xb3\x29\x03\0\0\x0f\0\x03foo\xb7\xfa\x1c\xb9', 'success')

    def test_uxsuccess(self):
        self.check_event(
            b'\xb3\x29\x04\0\0\x0f\0\x03foo\xd3\x9bqp', 'uxsuccess')

    def test_skip(self):
        self.check_event(
            b'\xb3\x29\x05\0\0\x0f\0\x03foo\xc4\xe0e3', 'skip')

    def test_fail(self):
        self.check_event(
            b'\xb3\x29\x06\0\0\x0f\0\x03foo\xfdmY\xf6', 'fail')

    def test_xfail(self):
        self.check_event(
            b'\xb3\x29\x07\0\0\x0f\0\x03foo\xea\x16M\xb5', 'xfail')

    def check_events(self, source_bytes, events):
        source = BytesIO(source_bytes)
        result = StreamResult()
        subunit.ByteStreamToStreamResult(
            source, non_subunit_name="stdout").run(result)
        self.assertEqual(b'', source.read())
        self.assertEqual(events, result._events)

    def check_event(self, source_bytes, test_status=None, test_id="foo",
        route_code=None, timestamp=None, tags=None, mime_type=None,
        file_name=None, file_bytes=None, eof=False, runnable=True):
        event = self._event(test_id=test_id, test_status=test_status,
            tags=tags, runnable=runnable, file_name=file_name,
            file_bytes=file_bytes, eof=eof, mime_type=mime_type,
            route_code=route_code, timestamp=timestamp)
        self.check_events(source_bytes, [event])

    def _event(self, test_status=None, test_id=None, route_code=None,
        timestamp=None, tags=None, mime_type=None, file_name=None,
        file_bytes=None, eof=False, runnable=True):
        return ('status', test_id, test_status, tags, runnable, file_name,
            file_bytes, eof, mime_type, route_code, timestamp)

    def test_eof(self):
        self.check_event(
            b'\xb3!\x10\x00\x00\na\xf1xM',
            test_id=None, eof=True)

    def test_file_content(self):
        self.check_event(
            b'\xb3!@\x00\x00\x15\x00\x06barneywoo\xfd\xecu\x1c',
            test_id=None, file_name="barney", file_bytes=b"woo")

    def test_mime(self):
        self.check_event(
            b'\xb3! \x00\x00&\x00\x1aapplication/foo; charset=1]#\xf9\xf9',
            test_id=None, mime_type='application/foo; charset=1')

    def test_route_code(self):
        self.check_event(
            b'\xb3-\x03\x00\x00\x17\x00\x06source\x00\x03bar\xad\xbd\x8c$',
            'success', route_code="source", test_id="bar")

    def test_runnable(self):
        self.check_event(
            b'\xb3(\x03\x00\x00\x0f\x00\x03fooX8w\x87',
            test_status='success', runnable=False)

    def test_tags(self):
        self.check_event(
            b'\xb3)\x80\x00\x00\x1b\x00\x03bar\x00\x02\x00\x03foo\x00\x03bar\xabMw\xe6',
            None, tags=set(['foo', 'bar']), test_id="bar")

    def test_timestamp(self):
        timestamp = datetime.datetime(2001, 12, 12, 12, 59, 59, 45,
            iso8601.Utc())
        self.check_event(
            b'\xb3+\x03\x00\x00\x17<\x17T\xcf\x00\x00\xaf\xc8\x00\x03barU>\xb2\xdb',
            'success', test_id='bar', timestamp=timestamp)

    def test_bad_crc_errors_via_status(self):
        file_bytes = \
            b'\xb3! \x00\x00&\x00\x1aapplication/foo; charset=1]#\xf9\xee'
        self.check_events( file_bytes, [
            self._event(test_id="subunit.parser", eof=True,
                file_name="Packet data", file_bytes=file_bytes),
            self._event(test_id="subunit.parser", test_status="fail", eof=True,
                file_name="Parser Error",
                file_bytes=b'Bad checksum - calculated (0x5d23f9f9), '
                    b'stored (0x5d23f9ee)'),
            ])

    def test_not_utf8_in_string(self):
        file_bytes = \
            b'\xb3-\x03\x00\x00\x17\x00\x06\xb4ource\x00\x03bar\x25\x2f\xb5\xd7'
        self.check_events(file_bytes, [
            self._event(test_id="subunit.parser", eof=True,
                file_name="Packet data", file_bytes=file_bytes),
            self._event(test_id="subunit.parser", test_status="fail", eof=True,
                file_name="Parser Error",
                file_bytes=b'UTF8 string at offset 0 is not UTF8'),
            ])

    def test_NULL_in_string(self):
        file_bytes = \
            b'\xb3-\x03\x00\x00\x17\x00\x06so\x00rce\x00\x03bar\x17\x89\x0a\xbe'
        self.check_events(file_bytes, [
            self._event(test_id="subunit.parser", eof=True,
                file_name="Packet data", file_bytes=file_bytes),
            self._event(test_id="subunit.parser", test_status="fail", eof=True,
                file_name="Parser Error",
                file_bytes=b'UTF8 string at offset 0 contains NUL byte'),
            ])

    def test_bad_utf8_stringlength(self):
        file_bytes = \
            b'\xb3-\x03\x00\x00\x17\x00\x06source\x00\x08bar\x7a\xbc\x0b\x25'
        self.check_events(file_bytes, [
            self._event(test_id="subunit.parser", eof=True,
                file_name="Packet data", file_bytes=file_bytes),
            self._event(test_id="subunit.parser", test_status="fail", eof=True,
                file_name="Parser Error",
                file_bytes=b'UTF8 string at offset 8 extends past end of '
                    b'packet: claimed 8 bytes, 7 available'),
            ])


def test_suite():
    loader = subunit.tests.TestUtil.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

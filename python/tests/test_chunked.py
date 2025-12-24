#
#  subunit: extensions to python unittest to get test results from subprocesses.
#  Copyright (C) 2005  Robert Collins <robertc@robertcollins.net>
#  Copyright (C) 2011  Martin Pool <mbp@sourcefrog.net>
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

import unittest
from io import BytesIO


import subunit.chunked


class TestDecode(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.output = BytesIO()
        self.decoder = subunit.chunked.Decoder(self.output)

    def test_close_read_length_short_errors(self):
        self.assertRaises(ValueError, self.decoder.close)

    def test_close_body_short_errors(self):
        self.assertEqual(None, self.decoder.write(b"2\r\na"))
        self.assertRaises(ValueError, self.decoder.close)

    def test_close_body_buffered_data_errors(self):
        self.assertEqual(None, self.decoder.write(b"2\r"))
        self.assertRaises(ValueError, self.decoder.close)

    def test_close_after_finished_stream_safe(self):
        self.assertEqual(None, self.decoder.write(b"2\r\nab"))
        self.assertEqual(b"", self.decoder.write(b"0\r\n"))
        self.decoder.close()

    def test_decode_nothing(self):
        self.assertEqual(b"", self.decoder.write(b"0\r\n"))
        self.assertEqual(b"", self.output.getvalue())

    def test_decode_serialised_form(self):
        self.assertEqual(None, self.decoder.write(b"F\r\n"))
        self.assertEqual(None, self.decoder.write(b"serialised\n"))
        self.assertEqual(b"", self.decoder.write(b"form0\r\n"))

    def test_decode_short(self):
        self.assertEqual(b"", self.decoder.write(b"3\r\nabc0\r\n"))
        self.assertEqual(b"abc", self.output.getvalue())

    def test_decode_combines_short(self):
        self.assertEqual(b"", self.decoder.write(b"6\r\nabcdef0\r\n"))
        self.assertEqual(b"abcdef", self.output.getvalue())

    def test_decode_excess_bytes_from_write(self):
        self.assertEqual(b"1234", self.decoder.write(b"3\r\nabc0\r\n1234"))
        self.assertEqual(b"abc", self.output.getvalue())

    def test_decode_write_after_finished_errors(self):
        self.assertEqual(b"1234", self.decoder.write(b"3\r\nabc0\r\n1234"))
        self.assertRaises(ValueError, self.decoder.write, b"")

    def test_decode_hex(self):
        self.assertEqual(b"", self.decoder.write(b"A\r\n12345678900\r\n"))
        self.assertEqual(b"1234567890", self.output.getvalue())

    def test_decode_long_ranges(self):
        self.assertEqual(None, self.decoder.write(b"10000\r\n"))
        self.assertEqual(None, self.decoder.write(b"1" * 65536))
        self.assertEqual(None, self.decoder.write(b"10000\r\n"))
        self.assertEqual(None, self.decoder.write(b"2" * 65536))
        self.assertEqual(b"", self.decoder.write(b"0\r\n"))
        self.assertEqual(b"1" * 65536 + b"2" * 65536, self.output.getvalue())

    def test_decode_newline_nonstrict(self):
        """Tolerate chunk markers with no CR character."""
        # From <http://pad.lv/505078>
        self.decoder = subunit.chunked.Decoder(self.output, strict=False)
        self.assertEqual(None, self.decoder.write(b"a\n"))
        self.assertEqual(None, self.decoder.write(b"abcdeabcde"))
        self.assertEqual(b"", self.decoder.write(b"0\n"))
        self.assertEqual(b"abcdeabcde", self.output.getvalue())

    def test_decode_strict_newline_only(self):
        """Reject chunk markers with no CR character in strict mode."""
        # From <http://pad.lv/505078>
        self.assertRaises(ValueError, self.decoder.write, b"a\n")

    def test_decode_strict_multiple_crs(self):
        self.assertRaises(ValueError, self.decoder.write, b"a\r\r\n")

    def test_decode_short_header(self):
        self.assertRaises(ValueError, self.decoder.write, b"\n")


class TestEncode(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.output = BytesIO()
        self.encoder = subunit.chunked.Encoder(self.output)

    def test_encode_nothing(self):
        self.encoder.close()
        self.assertEqual(b"0\r\n", self.output.getvalue())

    def test_encode_empty(self):
        self.encoder.write(b"")
        self.encoder.close()
        self.assertEqual(b"0\r\n", self.output.getvalue())

    def test_encode_short(self):
        self.encoder.write(b"abc")
        self.encoder.close()
        self.assertEqual(b"3\r\nabc0\r\n", self.output.getvalue())

    def test_encode_combines_short(self):
        self.encoder.write(b"abc")
        self.encoder.write(b"def")
        self.encoder.close()
        self.assertEqual(b"6\r\nabcdef0\r\n", self.output.getvalue())

    def test_encode_over_9_is_in_hex(self):
        self.encoder.write(b"1234567890")
        self.encoder.close()
        self.assertEqual(b"A\r\n12345678900\r\n", self.output.getvalue())

    def test_encode_long_ranges_not_combined(self):
        self.encoder.write(b"1" * 65536)
        self.encoder.write(b"2" * 65536)
        self.encoder.close()
        self.assertEqual(b"10000\r\n" + b"1" * 65536 + b"10000\r\n" + b"2" * 65536 + b"0\r\n", self.output.getvalue())

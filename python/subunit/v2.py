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

import struct
import zlib

__all__ = [
    'StreamResultToBytes',
    ]


class StreamResultToBytes(object):
    """Convert StreamResult API calls to bytes.
    
    The StreamResult API is defined by testtools.StreamResult.
    """

    status_mask = {
        None: 0,
        'exists': 0x1,
        'inprogress': 0x2,
        'success': 0x3,
        'uxsuccess': 0x4,
        'skip': 0x5,
        'fail': 0x6,
        'xfail': 0x7,
        }

    fmt_16 = '>H'
    fmt_32 = '>I'
    zero_b = b'\0'[0]

    def __init__(self, output_stream):
        """Create a StreamResultToBytes with output written to output_stream.

        :param output_stream: A file-like object. Must support write(bytes)
            and flush() methods. Flush will be called after each write.
        """
        self.output_stream = output_stream

    def startTestRun(self):
        pass

    def stopTestRun(self):
        pass

    def file(stream, file_name, file_bytes, eof=False, mime_type=None,
        test_id=None, route_code=None, timestamp=None):
        pass

    def status(self, test_id, test_status, test_tags=None, runnable=True,
        route_code=None, timestamp=None):
        self._write_packet(test_id=test_id, test_status=test_status,
            test_tags=test_tags, runnable=runnable, route_code=route_code,
            timestamp=timestamp)

    def _write_utf8(self, a_string, packet):
        utf8 = a_string.encode('utf-8')
        assert len(utf8) < 65536
        packet.append(struct.pack(self.fmt_16, len(utf8)))
        packet.append(utf8)

    def _write_packet(self, test_id=None, test_status=None, test_tags=None,
        runnable=True, route_code=None, timestamp=None):
        packet = [b'\xb3']
        packet.append(b'FF') # placeholder for flags
        packet.append(b'FFF') # placeholder for length
        flags = 0x2000 # Version 0x2
        if test_id is not None:
            flags = flags | 0x0800
            self._write_utf8(test_id, packet)
        if route_code is not None:
            flags = flags | 0x0400
        if timestamp is not None:
            flags = flags | 0x0200
        if runnable:
            flags = flags | 0x0100
        if test_tags:
            flags = flags | 0x0080
        #if file_content:
        #    flags = flags | 0x0040
        #if mime_type:
        #    flags = flags | 0x0020
        # if eof: 
        #    flags = flags | 0x0010
        # 0x0008 - not used in v2.
        flags = flags | self.status_mask[test_status]
        packet[1] = struct.pack(self.fmt_16, flags)
        length = struct.pack(self.fmt_32, sum(map(len, packet)) + 4)
        assert length[0] == self.zero_b
        packet[2] = length[1:]
        # We could either do a partial application of crc32 over each chunk
        # or a single join to a temp variable then a final join 
        # or two writes (that python might then split).
        # For now, simplest code: join, crc32, join, output
        content = b''.join(packet)
        self.output_stream.write(content + struct.pack(
            self.fmt_32, zlib.crc32(content) & 0xffffffff))
        self.output_stream.flush()

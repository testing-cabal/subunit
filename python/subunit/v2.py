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

import datetime
import struct
import zlib

import subunit
import subunit.iso8601 as iso8601

__all__ = [
    'StreamResultToBytes',
    ]

SIGNATURE = b'\xb3'
FMT_16 = '>H'
FMT_32 = '>I'
FMT_TIMESTAMP = '>II'
FLAG_TEST_ID = 0x0800
FLAG_ROUTE_CODE = 0x0400
FLAG_TIMESTAMP = 0x0200
FLAG_RUNNABLE = 0x0100
FLAG_TAGS = 0x0080
FLAG_MIME_TYPE = 0x0020
FLAG_EOF = 0x0010
FLAG_FILE_CONTENT = 0x0040
EPOCH = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=iso8601.Utc())
NUL_ELEMENT = b'\0'[0]


class ParseError(Exception):
    """Used to pass error messages within the parser."""


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

    zero_b = b'\0'[0]

    def __init__(self, output_stream):
        """Create a StreamResultToBytes with output written to output_stream.

        :param output_stream: A file-like object. Must support write(bytes)
            and flush() methods. Flush will be called after each write.
            The stream will be passed through subunit.make_stream_binary,
            to handle regular cases such as stdout.
        """
        self.output_stream = subunit.make_stream_binary(output_stream)

    def startTestRun(self):
        pass

    def stopTestRun(self):
        pass

    def status(self, test_id=None, test_status=None, test_tags=None,
        runnable=True, file_name=None, file_bytes=None, eof=False,
        mime_type=None, route_code=None, timestamp=None):
        self._write_packet(test_id=test_id, test_status=test_status,
            test_tags=test_tags, runnable=runnable, file_name=file_name,
            file_bytes=file_bytes, eof=eof, mime_type=mime_type,
            route_code=route_code, timestamp=timestamp)

    def _write_utf8(self, a_string, packet):
        utf8 = a_string.encode('utf-8')
        self._write_len16(len(utf8), packet)
        packet.append(utf8)

    def _write_len16(self, length, packet):
        assert length < 65536
        packet.append(struct.pack(FMT_16, length))

    def _write_packet(self, test_id=None, test_status=None, test_tags=None,
        runnable=True, file_name=None, file_bytes=None, eof=False,
        mime_type=None, route_code=None, timestamp=None):
        packet = [SIGNATURE]
        packet.append(b'FF') # placeholder for flags
        packet.append(b'FFF') # placeholder for length
        flags = 0x2000 # Version 0x2
        if route_code is not None:
            flags = flags | FLAG_ROUTE_CODE
            self._write_utf8(route_code, packet)
        if timestamp is not None:
            flags = flags | FLAG_TIMESTAMP
            since_epoch = timestamp - EPOCH
            nanoseconds = since_epoch.microseconds * 1000
            seconds = (since_epoch.seconds + since_epoch.days * 24 * 3600)
            packet.append(struct.pack(FMT_TIMESTAMP, seconds, nanoseconds))
        if test_id is not None:
            flags = flags | FLAG_TEST_ID
            self._write_utf8(test_id, packet)
        if test_tags:
            flags = flags | FLAG_TAGS
            self._write_len16(len(test_tags), packet)
            for tag in test_tags:
                self._write_utf8(tag, packet)
        if runnable:
            flags = flags | FLAG_RUNNABLE
        if mime_type:
            flags = flags | FLAG_MIME_TYPE
            self._write_utf8(mime_type, packet)
        if file_name is not None:
            flags = flags | FLAG_FILE_CONTENT
            self._write_utf8(file_name, packet)
            packet.append(file_bytes)
        if eof: 
           flags = flags | FLAG_EOF
        # 0x0008 - not used in v2.
        flags = flags | self.status_mask[test_status]
        packet[1] = struct.pack(FMT_16, flags)
        length = struct.pack(FMT_32, sum(map(len, packet)) + 4)
        assert length[0] == self.zero_b
        packet[2] = length[1:]
        # We could either do a partial application of crc32 over each chunk
        # or a single join to a temp variable then a final join 
        # or two writes (that python might then split).
        # For now, simplest code: join, crc32, join, output
        content = b''.join(packet)
        self.output_stream.write(content + struct.pack(
            FMT_32, zlib.crc32(content) & 0xffffffff))
        self.output_stream.flush()


class ByteStreamToStreamResult(object):
    """Parse a subunit byte stream.

    Mixed streams that contain non-subunit content is supported when a
    non_subunit_name is passed to the contructor. The default is to raise an
    error containing the non-subunit byte after it has been read from the
    stream.

    Typical use:

       >>> case = ByteStreamToStreamResult(sys.stdin.buffer)
       >>> result = StreamResult()
       >>> result.startTestRun()
       >>> case.run(result)
       >>> result.stopTestRun()
    """

    status_lookup = {
        0x0: None,
        0x1: 'exists',
        0x2: 'inprogress',
        0x3: 'success',
        0x4: 'uxsuccess',
        0x5: 'skip',
        0x6: 'fail',
        0x7: 'xfail',
        }

    def __init__(self, source, non_subunit_name=None):
        """Create a ByteStreamToStreamResult.

        :param source: A file like object to read bytes from. Must support
            read(<count>) and return bytes. The file is not closed by
            ByteStreamToStreamResult. subunit.make_stream_binary() is
            called on the stream to get it into bytes mode.
        :param non_subunit_name: If set to non-None, non subunit content
            encountered in the stream will be converted into file packets
            labelled with this name.
        """
        self.non_subunit_name = non_subunit_name
        self.source = subunit.make_stream_binary(source)

    def run(self, result):
        """Parse source and emit events to result.
        
        This is a blocking call: it will run until EOF is detected on source.
        """
        while True:
            content = self.source.read(1)
            if not content:
                # EOF
                return
            if content[0] != SIGNATURE[0]:
                # Not subunit.
                # TODO: do nonblocking IO and wait 5ms or so to send more
                # efficient events than one per character.
                if self.non_subunit_name is not None:
                    result.status(
                        file_name=self.non_subunit_name, file_bytes=content)
                else:
                    raise Exception("Non subunit content", content)
                continue
            try:
                packet = [SIGNATURE]
                self._parse(packet, result)
            except ParseError as error:
                result.status(test_id="subunit.parser", eof=True,
                    file_name="Packet data", file_bytes=b''.join(packet))
                result.status(test_id="subunit.parser", test_status='fail',
                    eof=True, file_name="Parser Error",
                    file_bytes=(error.args[0]).encode('utf8'))

    def _parse(self, packet, result):
            packet.append(self.source.read(5)) # 2 bytes flags, 3 bytes length.
            flags = struct.unpack(FMT_16, packet[-1][:2])[0]
            length = struct.unpack(FMT_32, packet[-1][1:])[0] & 0x00ffffff
            packet.append(self.source.read(length - 6))
            if len(packet[-1]) != length - 6:
                raise ParseError(
                    'Short read - got %d bytes, wanted %d bytes' % (
                    len(packet[-1]), length - 6))
            crc = zlib.crc32(packet[0])
            crc = zlib.crc32(packet[1], crc)
            crc = zlib.crc32(packet[2][:-4], crc) & 0xffffffff
            packet_crc = struct.unpack(FMT_32, packet[2][-4:])[0]
            if crc != packet_crc:
                # Bad CRC, report it and stop parsing the packet.
                raise ParseError(
                    'Bad checksum - calculated (0x%x), stored (0x%x)'
                        % (crc, packet_crc))
            # One packet could have both file and status data; the Python API
            # presents these separately (perhaps it shouldn't?)
            pos = 0
            if flags & FLAG_ROUTE_CODE:
                route_code, pos = self._read_utf8(packet[2], pos)
            else:
                route_code = None
            if flags & FLAG_TIMESTAMP:
                seconds, nanoseconds = struct.unpack(FMT_TIMESTAMP, packet[2][pos:pos+8])
                pos += 8
                timestamp = EPOCH + datetime.timedelta(
                    seconds=seconds, microseconds=nanoseconds/1000)
            else:
                timestamp = None
            if flags & FLAG_TEST_ID:
                test_id, pos = self._read_utf8(packet[2], pos)
            else:
                test_id = None
            if flags & FLAG_TAGS:
                tag_count, pos = self._read_len16(packet[2], pos)
                test_tags = set()
                for _ in range(tag_count):
                    tag, pos = self._read_utf8(packet[2], pos)
                    test_tags.add(tag)
            else:
                test_tags = None
            if flags & FLAG_MIME_TYPE:
                mime_type, pos = self._read_utf8(packet[2], pos)
            else:
                mime_type = None
            if flags & FLAG_FILE_CONTENT:
                file_name, pos = self._read_utf8(packet[2], pos)
                file_bytes = packet[2][pos:-4]
            else:
                file_name = None
                file_bytes = None
            runnable = bool(flags & FLAG_RUNNABLE)
            eof = bool(flags & FLAG_EOF)
            test_status = self.status_lookup[flags & 0x0007]
            result.status(test_id=test_id, test_status=test_status,
                test_tags=test_tags, runnable=runnable, mime_type=mime_type,
                eof=eof, file_name=file_name, file_bytes=file_bytes,
                route_code=route_code, timestamp=timestamp)
    __call__ = run

    def _read_len16(self, buf, pos):
        length = struct.unpack(FMT_16, buf[pos:pos+2])[0]
        return length, pos + 2

    def _read_utf8(self, buf, pos):
        length, pos = self._read_len16(buf, pos)
        utf8_bytes = buf[pos:pos+length]
        if length != len(utf8_bytes):
            raise ParseError(
                'UTF8 string at offset %d extends past end of packet: '
                'claimed %d bytes, %d available' % (pos - 2, length,
                len(utf8_bytes)))
        if NUL_ELEMENT in utf8_bytes:
            raise ParseError('UTF8 string at offset %d contains NUL byte' % (
                pos-2,))
        try:
            return utf8_bytes.decode('utf-8'), length+pos
        except UnicodeDecodeError:
            raise ParseError('UTF8 string at offset %d is not UTF8' % (pos-2,))


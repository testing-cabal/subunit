#
#  subunit: extensions to python unittest to get test results from subprocesses.
#  Copyright (C) 2005  Robert Collins <robertc@robertcollins.net>
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

"""Encoder/decoder for http style chunked encoding."""

class Encoder(object):
    """Encode content to a stream using HTTP Chunked coding."""

    def __init__(self, output):
        """Create an encoder encoding to output.

        :param output: A file-like object. Bytes written  to the Encoder
            will be encoded using HTTP chunking. Small writes may be buffered
            and the ``close`` method must be called to finish the stream.
        """
        self.output = output
        self.buffered_bytes = []
        self.buffer_size = 0

    def flush(self, extra_len=0):
        """Flush the encoder to the output stream.
        
        :param extra_len: Increase the size of the chunk by this many bytes
            to allow for a subsequent write.
        """
        if not self.buffer_size and not extra_len:
            return
        buffered_bytes = self.buffered_bytes
        buffer_size = self.buffer_size
        self.buffered_bytes = []
        self.buffer_size = 0
        self.output.write("%X\r\n" % (buffer_size + extra_len))
        if buffer_size:
            self.output.write(''.join(buffered_bytes))
        return True

    def write(self, bytes):
        """Encode bytes to the output stream."""
        bytes_len = len(bytes)
        if self.buffer_size + bytes_len >= 65536:
            self.flush(bytes_len)
            self.output.write(bytes)
        else:
            self.buffered_bytes.append(bytes)
            self.buffer_size += bytes_len

    def close(self):
        """Finish the stream. This does not close the output stream."""
        self.flush()
        self.output.write("0\r\n")

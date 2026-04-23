#
#  subunit: extensions to Python unittest to get test results from subprocesses.
#  Copyright (C) 2026  Jelmer Vernooij <jelmer@jelmer.uk>
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

"""Tests for subunit.filter_scripts.subunit_combine."""

import os
import subprocess
import sys
import tempfile
from io import BytesIO

from testtools import TestCase
from testtools.testresult.doubles import StreamResult

from subunit import ByteStreamToStreamResult, StreamResultToBytes
from subunit.filter_scripts.subunit_combine import (
    _PrefixingStreamResult,
    combine,
    load_config,
)


def _stream_with_tests(test_ids):
    """Build a subunit v2 byte stream with an inprogress+success pair per id."""
    buf = BytesIO()
    out = StreamResultToBytes(buf)
    for tid in test_ids:
        out.status(test_id=tid, test_status="inprogress")
        out.status(test_id=tid, test_status="success")
    return buf.getvalue()


def _parse(data):
    """Parse a subunit v2 byte stream into a list of (test_id, test_status)."""
    events = StreamResult()
    ByteStreamToStreamResult(BytesIO(data)).run(events)
    return [(ev[1], ev[2]) for ev in events._events if ev[0] == "status"]


class TestPrefixingStreamResult(TestCase):
    def test_prefixes_test_id(self):
        target = StreamResult()
        result = _PrefixingStreamResult(target, "py/")
        result.status(test_id="foo", test_status="success")
        self.assertEqual([("status", "py/foo", "success")], [ev[:3] for ev in target._events])

    def test_passes_through_none_test_id(self):
        target = StreamResult()
        result = _PrefixingStreamResult(target, "py/")
        result.status(file_name="stdout", file_bytes=b"hi")
        self.assertEqual([("status", None, None)], [ev[:3] for ev in target._events])


class TestLoadConfig(TestCase):
    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".yaml")
        self.addCleanup(os.unlink, path)
        with os.fdopen(fd, "w") as f:
            f.write(text)
        return path

    def test_basic(self):
        path = self._write("commands:\n  - prefix: 'a/'\n    argv: ['echo', 'hi']\n  - argv: ['true']\n")
        self.assertEqual(
            [{"prefix": "a/", "argv": ["echo", "hi"]}, {"argv": ["true"]}],
            load_config(path),
        )

    def test_rejects_non_mapping(self):
        path = self._write("- 1\n- 2\n")
        self.assertRaises(ValueError, load_config, path)

    def test_rejects_empty_commands(self):
        path = self._write("commands: []\n")
        self.assertRaises(ValueError, load_config, path)

    def test_rejects_missing_argv(self):
        path = self._write("commands:\n  - prefix: 'a/'\n")
        self.assertRaises(ValueError, load_config, path)

    def test_rejects_non_string_prefix(self):
        path = self._write("commands:\n  - argv: ['x']\n    prefix: 42\n")
        self.assertRaises(ValueError, load_config, path)


class TestCombine(TestCase):
    def _cat_cmd(self, data):
        """A command that writes the given bytes to stdout and exits 0.

        We use python -c so this works on all platforms and without relying on
        shell quoting.
        """
        src = "import sys; sys.stdout.buffer.write({!r})".format(data)
        return [sys.executable, "-c", src]

    def test_merges_streams_with_prefixes(self):
        stream_a = _stream_with_tests(["one", "two"])
        stream_b = _stream_with_tests(["alpha"])
        commands = [
            {"prefix": "py/", "argv": self._cat_cmd(stream_a)},
            {"prefix": "rs/", "argv": self._cat_cmd(stream_b)},
        ]
        output = BytesIO()
        rc = combine(commands, output)
        self.assertEqual(0, rc)
        self.assertEqual(
            [
                ("py/one", "inprogress"),
                ("py/one", "success"),
                ("py/two", "inprogress"),
                ("py/two", "success"),
                ("rs/alpha", "inprogress"),
                ("rs/alpha", "success"),
            ],
            _parse(output.getvalue()),
        )

    def test_no_prefix(self):
        stream = _stream_with_tests(["solo"])
        commands = [{"argv": self._cat_cmd(stream)}]
        output = BytesIO()
        rc = combine(commands, output)
        self.assertEqual(0, rc)
        self.assertEqual(
            [("solo", "inprogress"), ("solo", "success")],
            _parse(output.getvalue()),
        )

    def test_nonzero_exit_propagates(self):
        stream = _stream_with_tests(["only"])
        src = "import sys; sys.stdout.buffer.write({!r}); sys.exit(3)".format(stream)
        commands = [{"argv": [sys.executable, "-c", src]}]
        output = BytesIO()
        rc = combine(commands, output)
        self.assertEqual(1, rc)


class TestCombineCommand(TestCase):
    def test_end_to_end(self):
        stream_a = _stream_with_tests(["a"])
        stream_b = _stream_with_tests(["b"])

        def cmd_for(data):
            src = "import sys; sys.stdout.buffer.write({!r})".format(data)
            return [sys.executable, "-c", src]

        import yaml

        config = {
            "commands": [
                {"prefix": "py/", "argv": cmd_for(stream_a)},
                {"prefix": "rs/", "argv": cmd_for(stream_b)},
            ]
        }
        fd, path = tempfile.mkstemp(suffix=".yaml")
        self.addCleanup(os.unlink, path)
        with os.fdopen(fd, "w") as f:
            yaml.safe_dump(config, f)

        ps = subprocess.Popen(
            [sys.executable, "-m", "subunit.filter_scripts.subunit_combine", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = ps.communicate()
        self.assertEqual(0, ps.returncode, err)
        self.assertEqual(
            [
                ("py/a", "inprogress"),
                ("py/a", "success"),
                ("rs/b", "inprogress"),
                ("rs/b", "success"),
            ],
            _parse(out),
        )

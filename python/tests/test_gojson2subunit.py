#
#  subunit: extensions to python unittest to get test results from subprocesses.
#  Copyright (C) 2026  Jelmer Vernooij <jelmer@samba.org>
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

"""Tests for GoJSON2SubUnit."""

import json
from io import BytesIO, StringIO

from testtools import TestCase
from testtools.testresult.doubles import StreamResult

import subunit

UTF8_TEXT = "text/plain; charset=UTF8"


def _ndjson(*events):
    """Render an iterable of dicts as one JSON object per line."""
    return "\n".join(json.dumps(e) for e in events) + "\n"


class TestGoJSON2SubUnit(TestCase):
    """Behavioural tests for `GoJSON2SubUnit`.

    Each test feeds a synthetic `go test -json` event stream in, decodes
    the resulting subunit bytes back into events via `StreamResult`, and
    asserts on the (status, test_id, test_status, ...) tuples.
    """

    def setUp(self):
        super().setUp()
        self.gojson = StringIO()
        self.subunit = BytesIO()

    def _events(self):
        self.subunit.seek(0)
        sink = StreamResult()
        subunit.ByteStreamToStreamResult(self.subunit).run(sink)
        return sink._events

    def _statuses(self, events):
        # Strip the verbose tuple down to (test_id, test_status) for clearer
        # assertions when timing/file content isn't what's being tested.
        return [(e[1], e[2]) for e in events if e[0] == "status"]

    def test_pass_emits_inprogress_then_success(self):
        self.gojson.write(
            _ndjson(
                {"Action": "run", "Package": "pkg/a", "Test": "TestFoo"},
                {"Action": "pass", "Package": "pkg/a", "Test": "TestFoo", "Elapsed": 0.01},
            )
        )
        self.gojson.seek(0)
        rc = subunit.GoJSON2SubUnit(self.gojson, self.subunit)
        self.assertEqual(0, rc)
        self.assertEqual(
            [("pkg/a::TestFoo", "inprogress"), ("pkg/a::TestFoo", "success")],
            self._statuses(self._events()),
        )

    def test_fail_returns_nonzero(self):
        self.gojson.write(
            _ndjson(
                {"Action": "run", "Package": "pkg/a", "Test": "TestBad"},
                {"Action": "run", "Package": "pkg/a", "Test": "TestGood"},
                {"Action": "pass", "Package": "pkg/a", "Test": "TestGood", "Elapsed": 0.01},
                {"Action": "fail", "Package": "pkg/a", "Test": "TestBad", "Elapsed": 0.02},
            )
        )
        self.gojson.seek(0)
        rc = subunit.GoJSON2SubUnit(self.gojson, self.subunit)
        self.assertEqual(1, rc)
        # Each test produces an inprogress packet and a terminal packet;
        # check the terminal status (last one wins in dict()).
        statuses = dict(self._statuses(self._events()))
        self.assertEqual("fail", statuses["pkg/a::TestBad"])
        self.assertEqual("success", statuses["pkg/a::TestGood"])

    def test_skip_status(self):
        self.gojson.write(
            _ndjson(
                {"Action": "run", "Package": "pkg/a", "Test": "TestSkipped"},
                {"Action": "skip", "Package": "pkg/a", "Test": "TestSkipped", "Elapsed": 0.0},
            )
        )
        self.gojson.seek(0)
        rc = subunit.GoJSON2SubUnit(self.gojson, self.subunit)
        self.assertEqual(0, rc)
        self.assertIn(("pkg/a::TestSkipped", "skip"), self._statuses(self._events()))

    def test_subtest_keeps_slash_separator(self):
        # Go subtests are reported as "Parent/Sub"; the resulting test ID
        # should be "<package>.Parent/Sub" so it round-trips through
        # `go test -run '^Parent$/^Sub$'`.
        self.gojson.write(
            _ndjson(
                {"Action": "run", "Package": "pkg/a", "Test": "TestParent/sub_one"},
                {"Action": "pass", "Package": "pkg/a", "Test": "TestParent/sub_one", "Elapsed": 0.01},
            )
        )
        self.gojson.seek(0)
        subunit.GoJSON2SubUnit(self.gojson, self.subunit)
        self.assertIn(
            ("pkg/a::TestParent/sub_one", "success"),
            self._statuses(self._events()),
        )

    def test_output_attached_to_terminal_packet(self):
        self.gojson.write(
            _ndjson(
                {"Action": "run", "Package": "pkg/a", "Test": "TestNoisy"},
                {"Action": "output", "Package": "pkg/a", "Test": "TestNoisy", "Output": "hello\n"},
                {"Action": "output", "Package": "pkg/a", "Test": "TestNoisy", "Output": "world\n"},
                {"Action": "fail", "Package": "pkg/a", "Test": "TestNoisy", "Elapsed": 0.01},
            )
        )
        self.gojson.seek(0)
        subunit.GoJSON2SubUnit(self.gojson, self.subunit)
        events = self._events()
        # Find the terminal packet for TestNoisy and confirm both lines
        # were folded into one attachment.
        terminal = [e for e in events if e[0] == "status" and e[1] == "pkg/a::TestNoisy" and e[2] == "fail"]
        self.assertEqual(1, len(terminal))
        # Tuple shape from StreamResult:
        # ("status", test_id, test_status, test_tags, runnable, file_name,
        #  file_bytes, eof, mime_type, route_code, timestamp)
        ev = terminal[0]
        self.assertEqual("go test output", ev[5])
        self.assertEqual(b"hello\nworld\n", ev[6])
        self.assertEqual(UTF8_TEXT, ev[8])

    def test_package_level_build_failure_synthesises_test(self):
        # When `go test` can't build a package it emits a `fail` event with
        # no `Test` field, preceded by `output` events scoped to the package.
        self.gojson.write(
            _ndjson(
                {"Action": "output", "Package": "pkg/broken", "Output": "./x.go:1:1: syntax error\n"},
                {"Action": "fail", "Package": "pkg/broken", "Elapsed": 0.0},
            )
        )
        self.gojson.seek(0)
        rc = subunit.GoJSON2SubUnit(self.gojson, self.subunit)
        self.assertEqual(1, rc)
        events = self._events()
        terminal = [e for e in events if e[0] == "status" and e[1] == "pkg/broken [build]" and e[2] == "fail"]
        self.assertEqual(1, len(terminal))
        self.assertEqual(b"./x.go:1:1: syntax error\n", terminal[0][6])

    def test_garbage_lines_are_skipped(self):
        # `go test -json` occasionally interleaves a non-JSON banner on
        # certain failure paths; a junk line shouldn't abort the stream.
        self.gojson.write("not json at all\n")
        self.gojson.write(
            _ndjson(
                {"Action": "run", "Package": "pkg/a", "Test": "TestFoo"},
                {"Action": "pass", "Package": "pkg/a", "Test": "TestFoo", "Elapsed": 0.0},
            )
        )
        self.gojson.seek(0)
        rc = subunit.GoJSON2SubUnit(self.gojson, self.subunit)
        self.assertEqual(0, rc)
        self.assertIn(("pkg/a::TestFoo", "success"), self._statuses(self._events()))

    def test_blank_lines_are_skipped(self):
        self.gojson.write("\n\n")
        self.gojson.write(_ndjson({"Action": "run", "Package": "pkg/a", "Test": "TestFoo"}))
        self.gojson.write("\n")
        self.gojson.write(_ndjson({"Action": "pass", "Package": "pkg/a", "Test": "TestFoo", "Elapsed": 0.0}))
        self.gojson.seek(0)
        rc = subunit.GoJSON2SubUnit(self.gojson, self.subunit)
        self.assertEqual(0, rc)
        self.assertIn(("pkg/a::TestFoo", "success"), self._statuses(self._events()))

    def test_unfinished_test_at_eof_is_failed(self):
        # A test that started but never reached a terminal action — the
        # runner died mid-test. Surface as a failure rather than dropping it.
        self.gojson.write(
            _ndjson(
                {"Action": "run", "Package": "pkg/a", "Test": "TestStuck"},
                {"Action": "output", "Package": "pkg/a", "Test": "TestStuck", "Output": "panic\n"},
            )
        )
        self.gojson.seek(0)
        rc = subunit.GoJSON2SubUnit(self.gojson, self.subunit)
        self.assertEqual(1, rc)
        events = self._events()
        terminal = [e for e in events if e[0] == "status" and e[1] == "pkg/a.TestStuck" and e[2] == "fail"]
        self.assertEqual(1, len(terminal))
        self.assertEqual(b"panic\n", terminal[0][6])

    def test_timestamp_is_propagated(self):
        # The `Time` on each event should land on the matching subunit packet.
        self.gojson.write(
            _ndjson(
                {
                    "Time": "2026-01-02T03:04:05.000000Z",
                    "Action": "run",
                    "Package": "pkg/a",
                    "Test": "TestTimed",
                },
                {
                    "Time": "2026-01-02T03:04:06.000000Z",
                    "Action": "pass",
                    "Package": "pkg/a",
                    "Test": "TestTimed",
                    "Elapsed": 1.0,
                },
            )
        )
        self.gojson.seek(0)
        subunit.GoJSON2SubUnit(self.gojson, self.subunit)
        # The terminal packet's timestamp (last tuple element) must be set,
        # which gives consumers a basis for computing duration.
        terminal = [e for e in self._events() if e[0] == "status" and e[1] == "pkg/a.TestTimed" and e[2] == "success"]
        self.assertEqual(1, len(terminal))
        self.assertIsNotNone(terminal[0][-1])

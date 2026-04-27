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

"""Tests for the `gotest-run` orchestrator script."""

import io
import json
import os
import tempfile
from unittest import mock

from testtools import TestCase
from testtools.testresult.doubles import StreamResult

import subunit
from subunit.filter_scripts import gotest_run


def _ndjson(*events):
    return ("\n".join(json.dumps(e) for e in events) + "\n").encode("utf-8")


class TestParseId(TestCase):
    def test_simple_id(self):
        self.assertEqual(("pkg/a", "TestFoo"), gotest_run.parse_id("pkg/a::TestFoo"))

    def test_subtest_keeps_slash(self):
        # Subtests carry through unchanged so the run-regex builder can
        # split on `/` and anchor each component.
        self.assertEqual(
            ("pkg/a", "TestFoo/sub_one"),
            gotest_run.parse_id("pkg/a::TestFoo/sub_one"),
        )

    def test_dotted_package(self):
        # Real Go package paths use dots; the rightmost `::` is the
        # boundary, not the rightmost dot.
        self.assertEqual(
            ("example.com/foo/bar", "TestX"),
            gotest_run.parse_id("example.com/foo/bar::TestX"),
        )

    def test_missing_separator_returns_none(self):
        self.assertIsNone(gotest_run.parse_id("just_a_test_name"))

    def test_empty_components_return_none(self):
        self.assertIsNone(gotest_run.parse_id("::TestX"))
        self.assertIsNone(gotest_run.parse_id("pkg/a::"))


class TestGroupIdsByPackage(TestCase):
    def test_groups_and_preserves_order_within_group(self):
        groups = gotest_run.group_ids_by_package(
            [
                "pkg/a::TestOne\n",
                "pkg/b::TestX\n",
                "pkg/a::TestTwo\n",
            ]
        )
        self.assertEqual({"pkg/a": ["TestOne", "TestTwo"], "pkg/b": ["TestX"]}, groups)

    def test_blank_lines_dropped(self):
        groups = gotest_run.group_ids_by_package(["", "pkg/a::TestOne", "  "])
        self.assertEqual({"pkg/a": ["TestOne"]}, groups)

    def test_malformed_ids_warned_and_skipped(self):
        # The malformed ID is skipped (otherwise we'd later build a bogus
        # `-run` regex), but the warning makes the misconfiguration visible.
        with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
            groups = gotest_run.group_ids_by_package(["TestNoPackage", "pkg/a::TestGood"])
        self.assertEqual({"pkg/a": ["TestGood"]}, groups)
        self.assertIn("malformed test ID", stderr.getvalue())


class TestBuildRunRegex(TestCase):
    def test_single_test(self):
        self.assertEqual("^TestFoo$", gotest_run.build_run_regex(["TestFoo"]))

    def test_subtest_is_anchored_per_component(self):
        # Go's `-run` flag anchors each `/`-separated component
        # independently, so the regex must too.
        self.assertEqual(
            "^TestFoo$/^sub_one$",
            gotest_run.build_run_regex(["TestFoo/sub_one"]),
        )

    def test_multiple_tests_unioned(self):
        self.assertEqual(
            "(?:^TestA$)|(?:^TestB$)",
            gotest_run.build_run_regex(["TestA", "TestB"]),
        )

    def test_special_characters_in_subtest_are_escaped(self):
        # Subtest names from `t.Run("[arg=42]", ...)` become regex-significant.
        regex = gotest_run.build_run_regex(["TestFoo/[arg=42]"])
        self.assertEqual("^TestFoo$/^\\[arg=42\\]$", regex)


class TestStripDoubleDash(TestCase):
    def test_strips_leading_double_dash(self):
        self.assertEqual(["-v", "-count=3"], gotest_run._strip_double_dash(["--", "-v", "-count=3"]))

    def test_no_double_dash_passthrough(self):
        self.assertEqual(["-v"], gotest_run._strip_double_dash(["-v"]))

    def test_empty(self):
        self.assertEqual([], gotest_run._strip_double_dash([]))


class TestListing(TestCase):
    """Verify `--list` mode emits a parseable subunit `exists` stream."""

    def _decode(self, output_stream):
        output_stream.seek(0)
        sink = StreamResult()
        subunit.ByteStreamToStreamResult(output_stream).run(sink)
        return sink._events

    def test_emits_exists_events_for_each_test_name(self):
        # `go test -json -list` emits Action=output events whose Output is
        # one test name per line, plus a trailing summary line that we
        # filter out via the identifier regex.
        fake_json = _ndjson(
            {"Action": "start", "Package": "pkg/a"},
            {"Action": "output", "Package": "pkg/a", "Output": "TestAlpha\n"},
            {"Action": "output", "Package": "pkg/a", "Output": "TestBeta\n"},
            {"Action": "output", "Package": "pkg/a", "Output": "ok  \tpkg/a\t0.001s\n"},
            {"Action": "pass", "Package": "pkg/a", "Elapsed": 0.001},
        )
        completed = mock.Mock(returncode=0, stdout=fake_json)
        out = io.BytesIO()
        with mock.patch("subprocess.run", return_value=completed) as sp:
            rc = gotest_run.list_tests(["./..."], out)
        self.assertEqual(0, rc)
        sp.assert_called_once()
        events = self._decode(out)
        statuses = [(e[1], e[2]) for e in events if e[0] == "status"]
        self.assertIn(("pkg/a::TestAlpha", "exists"), statuses)
        self.assertIn(("pkg/a::TestBeta", "exists"), statuses)
        # The summary line must not have produced a phantom test ID.
        self.assertFalse(any("0.001s" in s[0] for s in statuses))

    def test_examples_are_listed_alongside_tests(self):
        fake_json = _ndjson(
            {"Action": "output", "Package": "pkg/a", "Output": "TestAlpha\n"},
            {"Action": "output", "Package": "pkg/a", "Output": "ExampleFoo\n"},
        )
        completed = mock.Mock(returncode=0, stdout=fake_json)
        out = io.BytesIO()
        with mock.patch("subprocess.run", return_value=completed):
            gotest_run.list_tests(["./..."], out)
        statuses = [(e[1], e[2]) for e in self._decode(out) if e[0] == "status"]
        self.assertIn(("pkg/a::TestAlpha", "exists"), statuses)
        self.assertIn(("pkg/a::ExampleFoo", "exists"), statuses)

    def test_propagates_nonzero_exit_when_no_output(self):
        # A build failure with no usable output should propagate the
        # non-zero exit so inquest reports the listing failure rather than
        # claiming an empty test suite.
        completed = mock.Mock(returncode=2, stdout=b"")
        out = io.BytesIO()
        with mock.patch("subprocess.run", return_value=completed):
            with mock.patch("sys.stderr", new=io.StringIO()):
                rc = gotest_run.list_tests(["./..."], out)
        self.assertEqual(2, rc)


class TestSubsetExecution(TestCase):
    """Verify `--id-file` mode runs one `go test` per package."""

    def _stub_popen(self, per_call_json):
        """Build a Popen replacement that returns canned JSON streams.

        ``per_call_json`` is a list of bytes payloads, one per expected
        invocation; raises if the test invokes `Popen` more times than
        scripted, which catches accidental fan-out regressions.
        """
        calls = []
        bodies = list(per_call_json)

        def _factory(args, *_, **__):
            if not bodies:
                raise AssertionError("unexpected extra Popen call: {}".format(args))
            body = bodies.pop(0)
            calls.append(args)
            mock_proc = mock.Mock()
            mock_proc.stdout = io.BytesIO(body)
            mock_proc.wait.return_value = 0
            return mock_proc

        return _factory, calls

    def test_one_invocation_per_package_with_correct_run_regex(self):
        # Two tests in pkg/a, one in pkg/b → exactly two `go test` calls,
        # each scoped to its package and using a `-run` regex covering only
        # the requested tests.
        per_call = [
            _ndjson(
                {"Action": "run", "Package": "pkg/a", "Test": "TestOne"},
                {"Action": "pass", "Package": "pkg/a", "Test": "TestOne", "Elapsed": 0.0},
                {"Action": "run", "Package": "pkg/a", "Test": "TestTwo"},
                {"Action": "pass", "Package": "pkg/a", "Test": "TestTwo", "Elapsed": 0.0},
            ),
            _ndjson(
                {"Action": "run", "Package": "pkg/b", "Test": "TestX"},
                {"Action": "pass", "Package": "pkg/b", "Test": "TestX", "Elapsed": 0.0},
            ),
        ]
        factory, calls = self._stub_popen(per_call)
        out = io.BytesIO()
        groups = {"pkg/a": ["TestOne", "TestTwo"], "pkg/b": ["TestX"]}
        with mock.patch("subprocess.Popen", side_effect=factory):
            rc = gotest_run.run_subset(groups, ["./..."], [], out)
        self.assertEqual(0, rc)
        self.assertEqual(2, len(calls))
        # Calls are sorted by package name for determinism.
        self.assertEqual("pkg/a", calls[0][-1])
        self.assertEqual("pkg/b", calls[1][-1])
        # The combined `-run` regex appears just before the package arg.
        self.assertIn("-run", calls[0])
        run_idx = calls[0].index("-run")
        self.assertEqual("(?:^TestOne$)|(?:^TestTwo$)", calls[0][run_idx + 1])

    def test_failure_propagates_nonzero_exit(self):
        per_call = [
            _ndjson(
                {"Action": "run", "Package": "pkg/a", "Test": "TestBad"},
                {"Action": "fail", "Package": "pkg/a", "Test": "TestBad", "Elapsed": 0.0},
            )
        ]
        factory, _ = self._stub_popen(per_call)
        out = io.BytesIO()
        with mock.patch("subprocess.Popen", side_effect=factory):
            rc = gotest_run.run_subset({"pkg/a": ["TestBad"]}, ["./..."], [], out)
        self.assertEqual(1, rc)

    def test_extra_args_are_forwarded(self):
        per_call = [_ndjson()]
        factory, calls = self._stub_popen(per_call)
        out = io.BytesIO()
        with mock.patch("subprocess.Popen", side_effect=factory):
            gotest_run.run_subset({"pkg/a": ["TestX"]}, ["./..."], ["-count=3", "-v"], out)
        self.assertIn("-count=3", calls[0])
        self.assertIn("-v", calls[0])


class TestMain(TestCase):
    """End-to-end tests of `main()` dispatching the right mode."""

    def _run(self, argv, popen_bodies=None, list_body=None, list_rc=0):
        out = io.BytesIO()
        with mock.patch("sys.stdout") as stdout:
            stdout.buffer = out
            patches = []
            if list_body is not None:
                patches.append(
                    mock.patch(
                        "subprocess.run",
                        return_value=mock.Mock(returncode=list_rc, stdout=list_body),
                    )
                )
            if popen_bodies is not None:
                bodies = list(popen_bodies)

                def factory(args, *_, **__):
                    body = bodies.pop(0) if bodies else b""
                    proc = mock.Mock()
                    proc.stdout = io.BytesIO(body)
                    proc.wait.return_value = 0
                    return proc

                patches.append(mock.patch("subprocess.Popen", side_effect=factory))
            for p in patches:
                p.start()
            try:
                rc = gotest_run.main(argv)
            finally:
                for p in patches:
                    p.stop()
        return rc, out.getvalue()

    def test_no_args_runs_whole_suite(self):
        body = _ndjson(
            {"Action": "run", "Package": "pkg/a", "Test": "TestX"},
            {"Action": "pass", "Package": "pkg/a", "Test": "TestX", "Elapsed": 0.0},
        )
        rc, out_bytes = self._run([], popen_bodies=[body])
        self.assertEqual(0, rc)
        self.assertTrue(out_bytes)  # subunit bytes were written

    def test_list_dispatches_to_listing(self):
        list_body = _ndjson(
            {"Action": "output", "Package": "pkg/a", "Output": "TestX\n"},
        )
        rc, out_bytes = self._run(["--list"], list_body=list_body)
        self.assertEqual(0, rc)
        self.assertTrue(out_bytes)

    def test_id_file_dispatches_to_subset(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as fh:
            fh.write("pkg/a::TestX\n")
            fh.write("pkg/b::TestY\n")
            id_path = fh.name
        self.addCleanup(os.unlink, id_path)
        body_a = _ndjson(
            {"Action": "run", "Package": "pkg/a", "Test": "TestX"},
            {"Action": "pass", "Package": "pkg/a", "Test": "TestX", "Elapsed": 0.0},
        )
        body_b = _ndjson(
            {"Action": "run", "Package": "pkg/b", "Test": "TestY"},
            {"Action": "pass", "Package": "pkg/b", "Test": "TestY", "Elapsed": 0.0},
        )
        rc, _ = self._run(["--id-file", id_path], popen_bodies=[body_a, body_b])
        self.assertEqual(0, rc)

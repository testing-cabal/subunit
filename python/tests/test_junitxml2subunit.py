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

"""Tests for JUnitXML2SubUnit."""

import io
import os
import tempfile
from unittest import mock

from testtools import TestCase
from testtools.testresult.doubles import StreamResult

import subunit
from subunit.filter_scripts import junitxml2subunit


def _write(tmpdir, name, content):
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


class TestJUnitXML2SubUnit(TestCase):
    """Behavioural tests for `JUnitXML2SubUnit`.

    Each test writes a synthetic JUnit XML doc to disk, runs the converter,
    decodes the resulting subunit bytes back into events via
    `StreamResult`, and asserts on the (test_id, test_status) tuples.
    """

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp(prefix="junitxml2subunit-test-")
        self.addCleanup(self._rmtree, self.tmp)
        self.subunit = io.BytesIO()

    def _rmtree(self, path):
        import shutil

        shutil.rmtree(path, ignore_errors=True)

    def _events(self):
        self.subunit.seek(0)
        sink = StreamResult()
        subunit.ByteStreamToStreamResult(self.subunit).run(sink)
        return sink._events

    def _statuses(self, events):
        return [(e[1], e[2]) for e in events if e[0] == "status"]

    def test_passing_testcase(self):
        path = _write(
            self.tmp,
            "TEST-FooTest.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.FooTest" tests="1" failures="0" errors="0" skipped="0" time="0.123">
  <testcase classname="com.example.FooTest" name="testBar" time="0.05"/>
</testsuite>
""",
        )
        rc = subunit.JUnitXML2SubUnit([path], self.subunit)
        self.assertEqual(0, rc)
        self.assertEqual(
            [
                ("com.example.FooTest::testBar", "inprogress"),
                ("com.example.FooTest::testBar", "success"),
            ],
            self._statuses(self._events()),
        )

    def test_failure_marks_fail_and_returns_nonzero(self):
        path = _write(
            self.tmp,
            "TEST-FooTest.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="com.example.FooTest" tests="1" failures="1">
  <testcase classname="com.example.FooTest" name="testBar" time="0.01">
    <failure type="java.lang.AssertionError" message="expected x but was y">at line 42</failure>
  </testcase>
</testsuite>
""",
        )
        rc = subunit.JUnitXML2SubUnit([path], self.subunit)
        self.assertEqual(1, rc)
        events = self._events()
        terminal = [e for e in events if e[0] == "status" and e[1] == "com.example.FooTest::testBar" and e[2] == "fail"]
        self.assertEqual(1, len(terminal))
        # The failure detail (type + message + body) is folded into a
        # single attachment so consumers see everything in one place.
        ev = terminal[0]
        self.assertEqual("junit detail", ev[5])
        # The decoder returns the attachment as a memoryview; coerce to
        # bytes for substring searching.
        body = bytes(ev[6])
        self.assertIn(b"java.lang.AssertionError", body)
        self.assertIn(b"expected x but was y", body)
        self.assertIn(b"at line 42", body)

    def test_error_is_treated_as_fail(self):
        # An <error> in JUnit terms is "an unexpected exception". subunit
        # has no separate "error" status that maps cleanly, and from a
        # consumer's perspective both mean "did not pass" — so it lands
        # on `fail` like a failure does.
        path = _write(
            self.tmp,
            "TEST-FooTest.xml",
            """<?xml version="1.0"?>
<testsuite>
  <testcase classname="com.example.FooTest" name="testBar">
    <error type="java.lang.NullPointerException">stack trace</error>
  </testcase>
</testsuite>
""",
        )
        rc = subunit.JUnitXML2SubUnit([path], self.subunit)
        self.assertEqual(1, rc)
        statuses = self._statuses(self._events())
        self.assertIn(("com.example.FooTest::testBar", "fail"), statuses)

    def test_skipped(self):
        path = _write(
            self.tmp,
            "TEST-FooTest.xml",
            """<?xml version="1.0"?>
<testsuite>
  <testcase classname="com.example.FooTest" name="testBar">
    <skipped message="ignored for now"/>
  </testcase>
</testsuite>
""",
        )
        rc = subunit.JUnitXML2SubUnit([path], self.subunit)
        self.assertEqual(0, rc)
        statuses = self._statuses(self._events())
        self.assertIn(("com.example.FooTest::testBar", "skip"), statuses)

    def test_testsuites_wrapper_is_unwrapped(self):
        # Some emitters (Gradle, Ant) wrap multiple <testsuite> in a
        # <testsuites> root; both shapes need to work.
        path = _write(
            self.tmp,
            "report.xml",
            """<?xml version="1.0"?>
<testsuites>
  <testsuite name="A">
    <testcase classname="A" name="testOne"/>
  </testsuite>
  <testsuite name="B">
    <testcase classname="B" name="testTwo"/>
  </testsuite>
</testsuites>
""",
        )
        rc = subunit.JUnitXML2SubUnit([path], self.subunit)
        self.assertEqual(0, rc)
        statuses = self._statuses(self._events())
        self.assertIn(("A::testOne", "success"), statuses)
        self.assertIn(("B::testTwo", "success"), statuses)

    def test_multiple_files_concatenate(self):
        a = _write(
            self.tmp,
            "TEST-A.xml",
            """<?xml version="1.0"?>
<testsuite>
  <testcase classname="A" name="testOne"/>
</testsuite>
""",
        )
        b = _write(
            self.tmp,
            "TEST-B.xml",
            """<?xml version="1.0"?>
<testsuite>
  <testcase classname="B" name="testTwo"/>
</testsuite>
""",
        )
        rc = subunit.JUnitXML2SubUnit([a, b], self.subunit)
        self.assertEqual(0, rc)
        statuses = self._statuses(self._events())
        self.assertIn(("A::testOne", "success"), statuses)
        self.assertIn(("B::testTwo", "success"), statuses)

    def test_missing_classname_falls_back_to_name(self):
        # `classname` is technically optional; without it the test ID
        # is just the bare method name rather than emitting "::name".
        path = _write(
            self.tmp,
            "report.xml",
            """<?xml version="1.0"?>
<testsuite>
  <testcase name="bareName"/>
</testsuite>
""",
        )
        rc = subunit.JUnitXML2SubUnit([path], self.subunit)
        self.assertEqual(0, rc)
        statuses = self._statuses(self._events())
        self.assertIn(("bareName", "success"), statuses)

    def test_unparseable_xml_counts_as_failure(self):
        # A broken file is loud (stderr warning + non-zero exit) rather
        # than silently dropping the suite — broken XML in a CI report
        # almost always means a test runner crash.
        path = _write(self.tmp, "broken.xml", "<<not really xml>>")
        with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
            rc = subunit.JUnitXML2SubUnit([path], self.subunit)
        self.assertEqual(1, rc)
        self.assertIn("failed to parse", stderr.getvalue())

    def test_time_attribute_advances_synthetic_clock(self):
        # Each testcase's `time` attribute should determine the gap
        # between its inprogress and terminal packets, so the consumer
        # can recover the duration. Use distinct values per test to
        # confirm both make it through.
        path = _write(
            self.tmp,
            "report.xml",
            """<?xml version="1.0"?>
<testsuite>
  <testcase classname="A" name="testOne" time="0.5"/>
  <testcase classname="A" name="testTwo" time="1.5"/>
</testsuite>
""",
        )
        subunit.JUnitXML2SubUnit([path], self.subunit)
        events = self._events()

        # Pull the per-test (inprogress, terminal) timestamp pairs. The
        # ByteStreamToStreamResult emits a "time" event before each
        # status event when the packet carries a timestamp.
        # Easier: walk the events and pair them up by test_id.
        timestamps = {}
        for e in events:
            if e[0] != "status":
                continue
            test_id = e[1]
            ts = e[-1]
            if ts is None:
                continue
            timestamps.setdefault(test_id, []).append(ts)

        one = timestamps["A::testOne"]
        two = timestamps["A::testTwo"]
        self.assertEqual(2, len(one))
        self.assertEqual(2, len(two))
        # testOne spans 0.5s
        self.assertAlmostEqual(0.5, (one[1] - one[0]).total_seconds(), places=3)
        # testTwo spans 1.5s
        self.assertAlmostEqual(1.5, (two[1] - two[0]).total_seconds(), places=3)


class TestCollectFiles(TestCase):
    """Tests for the `--dir` walking logic in the script entrypoint."""

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp(prefix="junitxml2subunit-collect-")
        self.addCleanup(self._rmtree, self.tmp)

    def _rmtree(self, path):
        import shutil

        shutil.rmtree(path, ignore_errors=True)

    def test_dir_walks_xml_files_only(self):
        a = _write(self.tmp, "TEST-A.xml", "")
        _write(self.tmp, "ignored.txt", "")
        b = _write(self.tmp, "TEST-B.xml", "")
        out = junitxml2subunit.collect_files([self.tmp], [])
        self.assertEqual({a, b}, set(out))

    def test_dir_results_are_sorted_for_deterministic_output(self):
        # Lexical sort within a directory so the subunit stream is
        # reproducible across runs (and across filesystems with
        # different readdir order).
        b = _write(self.tmp, "TEST-B.xml", "")
        a = _write(self.tmp, "TEST-A.xml", "")
        out = junitxml2subunit.collect_files([self.tmp], [])
        self.assertEqual([a, b], out)

    def test_explicit_files_appended_after_dir_walks(self):
        a = _write(self.tmp, "TEST-A.xml", "")
        # Build an explicit file outside the walked dir to confirm it's
        # appended after the discovered files rather than re-walked.
        extra_dir = tempfile.mkdtemp(prefix="junitxml2subunit-extra-")
        self.addCleanup(self._rmtree, extra_dir)
        explicit = _write(extra_dir, "extra.xml", "")
        out = junitxml2subunit.collect_files([self.tmp], [explicit])
        self.assertEqual([a, explicit], out)

    def test_missing_dir_warned_and_skipped(self):
        with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
            out = junitxml2subunit.collect_files(["/nonexistent/junit/dir"], [])
        self.assertEqual([], out)
        self.assertIn("not a directory", stderr.getvalue())

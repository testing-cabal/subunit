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
    _expand_argv,
    _read_id_list,
    _select_ids_for_command,
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


class TestExpandArgv(TestCase):
    def test_listopt_expanded_in_list_mode(self):
        cmd = {"argv": ["runner", "$LISTOPT", "$IDOPTION"], "list_option": "--list"}
        self.assertEqual(
            ["runner", "--list"],
            _expand_argv(cmd, list_mode=True, test_ids=None, idfile_path=None),
        )

    def test_listopt_empty_when_not_listing(self):
        cmd = {"argv": ["runner", "$LISTOPT", "$IDOPTION"], "list_option": "--list"}
        self.assertEqual(
            ["runner"],
            _expand_argv(cmd, list_mode=False, test_ids=None, idfile_path=None),
        )

    def test_idoption_expanded_with_idfile(self):
        cmd = {
            "argv": ["runner", "$IDOPTION"],
            "id_option": "--load-list $IDFILE",
        }
        self.assertEqual(
            ["runner", "--load-list", "/tmp/ids"],
            _expand_argv(cmd, list_mode=False, test_ids=["a", "b"], idfile_path="/tmp/ids"),
        )

    def test_idlist_expanded(self):
        cmd = {"argv": ["runner", "$IDLIST"]}
        self.assertEqual(
            ["runner", "a", "b", "c"],
            _expand_argv(cmd, list_mode=False, test_ids=["a", "b", "c"], idfile_path=None),
        )

    def test_idoption_empty_without_ids(self):
        cmd = {
            "argv": ["runner", "$IDOPTION"],
            "id_option": "--load-list $IDFILE",
        }
        self.assertEqual(
            ["runner"],
            _expand_argv(cmd, list_mode=False, test_ids=None, idfile_path=None),
        )

    def test_literal_argv_entries_untouched(self):
        cmd = {"argv": ["runner", "--tag=$literal", "$IDLIST"]}
        self.assertEqual(
            ["runner", "--tag=$literal", "x"],
            _expand_argv(cmd, list_mode=False, test_ids=["x"], idfile_path=None),
        )


class TestSelectIdsForCommand(TestCase):
    def test_none_returns_none(self):
        self.assertIsNone(_select_ids_for_command({"prefix": "py/"}, None))

    def test_filters_by_prefix_and_strips(self):
        ids = ["py/one", "rs/two", "py/three"]
        self.assertEqual(["one", "three"], _select_ids_for_command({"prefix": "py/"}, ids))

    def test_no_prefix_returns_all(self):
        ids = ["one", "two"]
        self.assertEqual(ids, _select_ids_for_command({}, ids))
        self.assertIsNot(ids, _select_ids_for_command({}, ids))  # must copy

    def test_no_matches_returns_empty(self):
        self.assertEqual([], _select_ids_for_command({"prefix": "py/"}, ["rs/a"]))


class TestReadIdList(TestCase):
    def test_skips_blank_and_comments(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.unlink, path)
        with os.fdopen(fd, "w") as f:
            f.write("one\n\n# comment\ntwo # trailing\nthree\n")
        self.assertEqual(["one", "two", "three"], _read_id_list(path))


class TestCombineListAndFilter(TestCase):
    def _cmd_for(self, data):
        src = "import sys; sys.stdout.buffer.write({!r})".format(data)
        return [sys.executable, "-c", src]

    def _exists_stream(self, test_ids):
        buf = BytesIO()
        out = StreamResultToBytes(buf)
        for tid in test_ids:
            out.status(test_id=tid, test_status="exists")
        return buf.getvalue()

    def test_list_mode_substitutes_listopt(self):
        # Child emits ids only when --list is present: we simulate this by
        # embedding the argument directly in the command and asserting it's
        # what gets executed.
        list_stream = self._exists_stream(["foo", "bar"])
        src = (
            "import sys; args = sys.argv[1:]; assert args == ['--list'], args; sys.stdout.buffer.write({!r})"
        ).format(list_stream)
        commands = [
            {
                "prefix": "py/",
                "argv": [sys.executable, "-c", src, "$LISTOPT"],
                "list_option": "--list",
            }
        ]
        output = BytesIO()
        rc = combine(commands, output, list_mode=True)
        self.assertEqual(0, rc)
        self.assertEqual(
            [("py/foo", "exists"), ("py/bar", "exists")],
            _parse(output.getvalue()),
        )

    def test_listopt_absent_when_not_listing(self):
        # When list_mode is False, $LISTOPT should expand to nothing.
        run_stream = _stream_with_tests(["x"])
        src = ("import sys; args = sys.argv[1:]; assert args == [], args; sys.stdout.buffer.write({!r})").format(
            run_stream
        )
        commands = [
            {
                "argv": [sys.executable, "-c", src, "$LISTOPT"],
                "list_option": "--list",
            }
        ]
        output = BytesIO()
        rc = combine(commands, output)
        self.assertEqual(0, rc)

    def test_idoption_and_idfile_substituted(self):
        # The child asserts it received --load-list <file> with two ids in it.
        run_stream = _stream_with_tests(["one", "two"])
        src = (
            "import sys, pathlib; "
            "args = sys.argv[1:]; "
            "assert args[0] == '--load-list', args; "
            "contents = pathlib.Path(args[1]).read_text().splitlines(); "
            "assert contents == ['one', 'two'], contents; "
            "sys.stdout.buffer.write({!r})"
        ).format(run_stream)
        commands = [
            {
                "prefix": "py/",
                "argv": [sys.executable, "-c", src, "$IDOPTION"],
                "id_option": "--load-list $IDFILE",
            }
        ]
        output = BytesIO()
        rc = combine(commands, output, test_ids=["py/one", "py/two"])
        self.assertEqual(0, rc)

    def test_idlist_substituted(self):
        run_stream = _stream_with_tests(["a"])
        src = (
            "import sys; args = sys.argv[1:]; assert args == ['a', 'b'], args; sys.stdout.buffer.write({!r})"
        ).format(run_stream)
        commands = [
            {
                "prefix": "py/",
                "argv": [sys.executable, "-c", src, "$IDLIST"],
            }
        ]
        output = BytesIO()
        rc = combine(commands, output, test_ids=["py/a", "py/b"])
        self.assertEqual(0, rc)

    def test_command_with_no_matching_ids_is_skipped(self):
        # 'py/' receives ids; 'rs/' has no matching ids and must not run.
        py_stream = _stream_with_tests(["one"])
        py_src = "import sys; sys.stdout.buffer.write({!r})".format(py_stream)
        rs_src = "import sys; sys.exit('must not run')"
        commands = [
            {"prefix": "py/", "argv": [sys.executable, "-c", py_src]},
            {"prefix": "rs/", "argv": [sys.executable, "-c", rs_src]},
        ]
        output = BytesIO()
        rc = combine(commands, output, test_ids=["py/one"])
        self.assertEqual(0, rc)
        self.assertEqual(
            [("py/one", "inprogress"), ("py/one", "success")],
            _parse(output.getvalue()),
        )

    def test_cli_list_flag(self):
        list_stream = self._exists_stream(["foo"])
        src = (
            "import sys; args = sys.argv[1:]; assert args == ['--list'], args; sys.stdout.buffer.write({!r})"
        ).format(list_stream)
        config = {
            "commands": [
                {
                    "prefix": "py/",
                    "argv": [sys.executable, "-c", src, "$LISTOPT"],
                    "list_option": "--list",
                }
            ]
        }
        fd, path = tempfile.mkstemp(suffix=".yaml")
        self.addCleanup(os.unlink, path)
        with os.fdopen(fd, "w") as f:
            import yaml

            yaml.safe_dump(config, f)
        ps = subprocess.Popen(
            [sys.executable, "-m", "subunit.filter_scripts.subunit_combine", "--list", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = ps.communicate()
        self.assertEqual(0, ps.returncode, err)
        self.assertEqual([("py/foo", "exists")], _parse(out))

    def test_cli_positional_ids(self):
        run_stream = _stream_with_tests(["a"])
        src = ("import sys; args = sys.argv[1:]; assert args == ['a'], args; sys.stdout.buffer.write({!r})").format(
            run_stream
        )
        config = {
            "commands": [
                {
                    "prefix": "py/",
                    "argv": [sys.executable, "-c", src, "$IDLIST"],
                }
            ]
        }
        fd, path = tempfile.mkstemp(suffix=".yaml")
        self.addCleanup(os.unlink, path)
        with os.fdopen(fd, "w") as f:
            import yaml

            yaml.safe_dump(config, f)
        ps = subprocess.Popen(
            [sys.executable, "-m", "subunit.filter_scripts.subunit_combine", path, "py/a"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = ps.communicate()
        self.assertEqual(0, ps.returncode, err)
        self.assertEqual(
            [("py/a", "inprogress"), ("py/a", "success")],
            _parse(out),
        )

    def test_cli_load_list(self):
        run_stream = _stream_with_tests(["one"])
        src = ("import sys; args = sys.argv[1:]; assert args == ['one'], args; sys.stdout.buffer.write({!r})").format(
            run_stream
        )
        config = {
            "commands": [
                {
                    "prefix": "py/",
                    "argv": [sys.executable, "-c", src, "$IDLIST"],
                }
            ]
        }
        cfg_fd, cfg_path = tempfile.mkstemp(suffix=".yaml")
        self.addCleanup(os.unlink, cfg_path)
        with os.fdopen(cfg_fd, "w") as f:
            import yaml

            yaml.safe_dump(config, f)
        list_fd, list_path = tempfile.mkstemp(suffix=".list")
        self.addCleanup(os.unlink, list_path)
        with os.fdopen(list_fd, "w") as f:
            f.write("py/one\n")
        ps = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "subunit.filter_scripts.subunit_combine",
                "--load-list",
                list_path,
                cfg_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = ps.communicate()
        self.assertEqual(0, ps.returncode, err)
        self.assertEqual(
            [("py/one", "inprogress"), ("py/one", "success")],
            _parse(out),
        )

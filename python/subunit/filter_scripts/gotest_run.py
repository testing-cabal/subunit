#!/usr/bin/env python3
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

"""Run `go test` and emit a subunit v2 byte stream on stdout.

Designed to slot into testrepository / inquest as a single ``test_command``
that handles all three usage modes:

  * ``gotest-run --list`` enumerates available tests by running
    ``go test -json -list 'Test.*|Example.*' ./...`` and emitting subunit
    ``exists`` events. Subtests (created at runtime by ``t.Run``) cannot
    be statically discovered and are therefore absent from the listing.

  * ``gotest-run --id-file FILE`` runs only the tests named in FILE
    (one ``<package>::<TestName>`` per line). IDs are grouped by package
    and one ``go test -json -run <regex> <package>`` invocation is issued
    per package; the JSON streams are concatenated and converted to
    subunit on the fly.

  * ``gotest-run`` (no flags) runs the whole suite via
    ``go test -json ./...``.
"""

import argparse
import io
import json
import re
import subprocess
import sys

from subunit import GoJSON2SubUnit
from subunit.v2 import StreamResultToBytes


# Functions named TestX (capital T) and ExampleX are what `go test`
# executes by default; benchmarks and fuzz seeds aren't run unless the
# user opts in, so excluding them from listings keeps the discovered
# IDs runnable. Mirrors the regex passed to `go test -list`.
LIST_NAME_REGEX = "Test.*|Example.*"

# `-list`'s JSON output mixes per-package summary lines (e.g.
# `ok  example.com/foo  0.001s`) with the test names. Skip anything
# that doesn't look like a Go identifier (optionally followed by a
# `/subtest` suffix).
TEST_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9_]*(/.*)?$")


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Run go test and emit a subunit v2 stream on stdout.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--list",
        dest="list_tests",
        action="store_true",
        help="Enumerate tests as subunit `exists` events instead of running them.",
    )
    mode.add_argument(
        "--id-file",
        dest="id_file",
        metavar="FILE",
        help="Run only the tests whose IDs (one per line) are listed in FILE.",
    )
    parser.add_argument(
        "--package",
        dest="packages",
        action="append",
        default=[],
        help=("Restrict discovery / execution to these package patterns. Repeatable. Defaults to ./... ."),
    )
    parser.add_argument(
        "go_args",
        nargs=argparse.REMAINDER,
        help="Extra arguments forwarded to `go test`. Place after `--`.",
    )
    return parser.parse_args(argv)


def _strip_double_dash(go_args):
    # ``argparse.REMAINDER`` keeps the leading ``--`` when present; strip it
    # so callers don't have to think about it.
    if go_args and go_args[0] == "--":
        return go_args[1:]
    return go_args


def parse_id(test_id):
    """Split a ``<package>::<TestName>`` ID into its parts.

    Returns ``(package, test_name)`` on success, or ``None`` if the ID
    isn't in the expected form. The test_name may include a subtest
    suffix (``Parent/sub``).
    """
    if "::" not in test_id:
        return None
    package, _, test = test_id.rpartition("::")
    if not package or not test:
        return None
    return package, test


def group_ids_by_package(ids):
    """Group an iterable of test IDs into ``{package: [test_name, ...]}``.

    Malformed IDs are written to stderr and skipped — losing them silently
    would mask configuration errors.
    """
    groups = {}
    for raw in ids:
        raw = raw.strip()
        if not raw:
            continue
        parsed = parse_id(raw)
        if parsed is None:
            sys.stderr.write(
                "gotest-run: skipping malformed test ID '{}' (expected '<package>::<TestName>')\n".format(raw)
            )
            continue
        package, test = parsed
        groups.setdefault(package, []).append(test)
    return groups


def build_run_regex(test_names):
    """Build a `go test -run` regex matching exactly the named tests.

    Each Go test name is anchored at every ``/``-separated component, so
    a request for ``TestParent/sub_one`` becomes ``^TestParent$/^sub_one$``.
    Multiple tests are unioned at the top level.

    Special regex characters in test names are escaped — Go subtest names
    can contain almost anything (they're an arbitrary string passed to
    ``t.Run``).
    """
    alts = []
    for name in test_names:
        parts = name.split("/")
        anchored = "/".join("^{}$".format(re.escape(p)) for p in parts)
        alts.append(anchored)
    if len(alts) == 1:
        return alts[0]
    # Wrap each alternative so ``|`` doesn't bleed across components.
    return "|".join("(?:{})".format(alt) for alt in alts)


def run_go_test(args, output_stream):
    """Spawn ``go test ...`` and stream its JSON output through GoJSON2SubUnit.

    Returns the conversion's exit code (0 if no test failed, non-zero if any
    failed). Build / run failures from `go test` itself surface as
    package-level subunit failures via ``GoJSON2SubUnit``.
    """
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=sys.stderr)
    assert proc.stdout is not None
    text_stdout = io.TextIOWrapper(proc.stdout, encoding="utf-8", errors="replace")
    rc = GoJSON2SubUnit(text_stdout, output_stream)
    proc.wait()
    return rc


def run_subset(groups, packages_default, extra_args, output_stream):
    """Run `go test -json` once per package, streaming all results to subunit.

    A non-zero exit is returned if any package's results contained a
    failure (tracked by ``GoJSON2SubUnit``'s return value).
    """
    any_failed = False
    for package, tests in sorted(groups.items()):
        regex = build_run_regex(tests)
        cmd = ["go", "test", "-json", "-run", regex, package] + extra_args
        rc = run_go_test(cmd, output_stream)
        if rc != 0:
            any_failed = True
    if not groups:
        sys.stderr.write("gotest-run: no usable test IDs in id-file; nothing to run\n")
    _ = packages_default  # unused in subset mode (IDs already encode packages)
    return 1 if any_failed else 0


def list_tests(packages, output_stream):
    """Write subunit `exists` events for every discoverable test.

    Discovery uses ``go test -json -list ...`` per the supplied package
    patterns. Subtests aren't statically discoverable in Go and are
    therefore absent.
    """
    output = StreamResultToBytes(output_stream)
    cmd = ["go", "test", "-json", "-list", LIST_NAME_REGEX] + list(packages)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=sys.stderr, check=False)

    if proc.returncode != 0:
        # `go test -list` exits non-zero on build failures. The captured
        # JSON usually still contains the build-error output events; emit
        # them so the user sees what went wrong via the listing path.
        any_emitted = _emit_listing(proc.stdout, output)
        if not any_emitted:
            sys.stderr.write(
                "gotest-run: `go test -list` exited {} and produced no usable output; aborting listing\n".format(
                    proc.returncode
                )
            )
        return proc.returncode

    _emit_listing(proc.stdout, output)
    return 0


def _emit_listing(json_bytes, output):
    """Parse the captured `go test -json -list` output and emit `exists` events.

    Returns True if at least one test was emitted — used to distinguish
    "list ran but found nothing" from "list failed entirely".
    """
    text = json_bytes.decode("utf-8", errors="replace") if json_bytes else ""
    any_emitted = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except (TypeError, ValueError):
            continue
        if not isinstance(event, dict):
            continue
        if event.get("Action") != "output":
            continue
        package = event.get("Package")
        chunk = event.get("Output", "")
        if not package:
            continue
        for raw in chunk.splitlines():
            name = raw.strip()
            if not name:
                continue
            if not TEST_NAME_RE.match(name):
                # Skip the trailing "ok pkg/x 0.001s" summary lines and any
                # other non-identifier junk go test interleaves.
                continue
            test_id = "{}::{}".format(package, name)
            output.status(test_id=test_id, test_status="exists", eof=True)
            any_emitted = True
    return any_emitted


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    extra_args = _strip_double_dash(args.go_args)
    packages = args.packages or ["./..."]

    # The output stream needs to be binary; sys.stdout.buffer gives us that
    # without forcing the caller to know.
    output_stream = sys.stdout.buffer

    if args.list_tests:
        return list_tests(packages, output_stream)

    if args.id_file:
        with open(args.id_file, "r", encoding="utf-8") as fh:
            ids = list(fh)
        groups = group_ids_by_package(ids)
        return run_subset(groups, packages, extra_args, output_stream)

    cmd = ["go", "test", "-json"] + packages + extra_args
    return run_go_test(cmd, output_stream)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
#  subunit: extensions to python unittest to get test results from subprocesses.
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

"""Run multiple commands producing subunit v2 output and merge their streams.

The commands to run are described in a YAML configuration file. Each command
may have a test id ``prefix`` prepended to all test ids it emits, which makes
it possible to combine output from, for example, a Python and a Rust test
suite without test id collisions.

Example configuration::

    commands:
      - prefix: "python/"
        argv: ["python", "-m", "subunit.run", "mypkg.tests"]
      - prefix: "rust/"
        argv: ["cargo", "test", "--", "--format=subunit"]
        cwd: "rust"

The combined subunit v2 stream is written to stdout. The exit code is 0 if
all commands exited 0 and no tests failed, 1 otherwise.
"""

import os
import subprocess
import sys
from argparse import ArgumentParser
from typing import Optional

import yaml

from subunit import ByteStreamToStreamResult, StreamResultToBytes


class _PrefixingStreamResult:
    """Forward StreamResult events, prepending ``prefix`` to every test_id."""

    def __init__(self, target, prefix: str):
        self._target = target
        self._prefix = prefix

    def startTestRun(self):
        self._target.startTestRun()

    def stopTestRun(self):
        self._target.stopTestRun()

    def status(self, test_id=None, **kwargs):
        if test_id is not None:
            test_id = self._prefix + test_id
        self._target.status(test_id=test_id, **kwargs)


def load_config(path: str) -> list[dict]:
    """Load and validate a combine configuration file.

    Returns a list of command dictionaries.
    """
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level configuration must be a mapping")
    commands = data.get("commands")
    if not isinstance(commands, list) or not commands:
        raise ValueError(f"{path}: 'commands' must be a non-empty list")
    for i, cmd in enumerate(commands):
        if not isinstance(cmd, dict):
            raise ValueError(f"{path}: commands[{i}] must be a mapping")
        argv = cmd.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
            raise ValueError(f"{path}: commands[{i}].argv must be a non-empty list of strings")
        prefix = cmd.get("prefix", "")
        if not isinstance(prefix, str):
            raise ValueError(f"{path}: commands[{i}].prefix must be a string")
    return commands


def run_command(cmd: dict, output) -> int:
    """Run a single command and forward its subunit v2 output.

    The child's stdout is parsed as subunit v2 and re-emitted to ``output``
    (a :class:`StreamResultToBytes`) with each test_id prefixed with
    ``cmd['prefix']`` (if any).

    :return: The exit code of the child process.
    """
    prefix = cmd.get("prefix", "")
    cwd = cmd.get("cwd")
    env = os.environ.copy()
    extra_env = cmd.get("env")
    if extra_env:
        env.update(extra_env)

    proc = subprocess.Popen(
        cmd["argv"],
        stdout=subprocess.PIPE,
        cwd=cwd,
        env=env,
    )
    try:
        assert proc.stdout is not None
        result = _PrefixingStreamResult(output, prefix) if prefix else output
        ByteStreamToStreamResult(proc.stdout, non_subunit_name="stdout").run(result)
    finally:
        returncode = proc.wait()
    return returncode


def combine(commands: list[dict], output_stream) -> int:
    """Run ``commands`` and merge their subunit streams into ``output_stream``.

    :return: 0 if every command exited 0, 1 otherwise.
    """
    output = StreamResultToBytes(output_stream)
    output.startTestRun()
    failed = False
    try:
        for cmd in commands:
            rc = run_command(cmd, output)
            if rc != 0:
                failed = True
    finally:
        output.stopTestRun()
    return 1 if failed else 0


def make_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "config",
        help="Path to a YAML configuration file describing the commands to run.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = make_parser()
    options = parser.parse_args(argv)
    commands = load_config(options.config)
    sys.exit(combine(commands, sys.stdout))


if __name__ == "__main__":
    main()

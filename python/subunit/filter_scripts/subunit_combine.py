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
        argv: ["python", "-m", "subunit.run", "discover", ".", "$LISTOPT", "$IDOPTION"]
        list_option: "--list"
        id_option: "--load-list $IDFILE"
      - prefix: "rust/"
        argv: ["cargo", "test", "--", "--format=subunit"]
        cwd: "rust"

The combined subunit v2 stream is written to stdout. The exit code is 0 if
all commands exited 0, 1 otherwise.

testr-style substitutions
-------------------------

Each command's ``argv``, ``list_option`` and ``id_option`` entries may contain
the following placeholders, which are expanded per invocation:

* ``$LISTOPT`` -- expands to ``list_option`` when ``subunit-combine --list``
  is used, empty otherwise.
* ``$IDLIST`` -- space-separated list of (prefix-stripped) test ids to run
  for this command. Empty if no ids were requested or none match.
* ``$IDFILE`` -- path to a temporary file containing one test id per line.
* ``$IDOPTION`` -- expands to ``id_option`` (with ``$IDFILE`` further
  substituted) when ids are being supplied, empty otherwise.

Test ids can be passed as positional arguments after the config file or via
``--load-list FILE``. Ids that start with a command's ``prefix`` are routed
(with the prefix stripped) to that command; ids that don't match any prefix
are ignored for that command.
"""

import os
import re
import subprocess
import sys
import tempfile
from argparse import ArgumentParser
from typing import Optional

import yaml

from subunit import ByteStreamToStreamResult, StreamResultToBytes


_VARIABLE_RE = re.compile(r"\$(IDOPTION|IDFILE|IDLIST|LISTOPT)")


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
        for key in ("list_option", "id_option"):
            value = cmd.get(key)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{path}: commands[{i}].{key} must be a string")
    return commands


def _substitute(template: str, variables: dict[str, str]) -> list[str]:
    """Substitute $VAR placeholders in ``template`` and return a shell-split list.

    Empty values are expanded to the empty string; the resulting string is then
    split on whitespace so that e.g. an empty ``$LISTOPT`` disappears rather
    than leaving an empty argument behind.
    """

    def repl(match: re.Match) -> str:
        return variables.get(match.group(1), "")

    return re.sub(_VARIABLE_RE, repl, template).split()


def _expand_argv(
    cmd: dict,
    *,
    list_mode: bool,
    test_ids: Optional[list[str]],
    idfile_path: Optional[str],
) -> list[str]:
    """Expand testr-style placeholders in ``cmd['argv']``."""
    list_option = cmd.get("list_option", "") if list_mode else ""
    id_option_template = cmd.get("id_option", "")
    if test_ids is None or not id_option_template:
        id_option = ""
    else:
        id_option = re.sub(
            _VARIABLE_RE,
            lambda m: {"IDFILE": idfile_path or "", "IDLIST": " ".join(test_ids)}.get(m.group(1), ""),
            id_option_template,
        )
    variables = {
        "LISTOPT": list_option,
        "IDOPTION": id_option,
        "IDFILE": idfile_path or "",
        "IDLIST": " ".join(test_ids) if test_ids else "",
    }
    expanded: list[str] = []
    for piece in cmd["argv"]:
        if _VARIABLE_RE.search(piece):
            expanded.extend(_substitute(piece, variables))
        else:
            expanded.append(piece)
    return expanded


def _select_ids_for_command(cmd: dict, test_ids: Optional[list[str]]) -> Optional[list[str]]:
    """Return the ids that belong to ``cmd`` (with the prefix stripped).

    Returns None when no filtering should be applied (no ids were requested
    globally).
    """
    if test_ids is None:
        return None
    prefix = cmd.get("prefix", "")
    if not prefix:
        return list(test_ids)
    return [tid[len(prefix) :] for tid in test_ids if tid.startswith(prefix)]


def _write_idfile(test_ids: list[str]) -> str:
    fd, path = tempfile.mkstemp(prefix="subunit-combine-", suffix=".list")
    with os.fdopen(fd, "w") as f:
        for tid in test_ids:
            f.write(tid + "\n")
    return path


def run_command(
    cmd: dict,
    output,
    *,
    list_mode: bool = False,
    test_ids: Optional[list[str]] = None,
) -> int:
    """Run a single command and forward its subunit v2 output.

    The child's stdout is parsed as subunit v2 and re-emitted to ``output``
    (a :class:`StreamResultToBytes`) with each test_id prefixed with
    ``cmd['prefix']`` (if any).

    :param list_mode: If True, ``$LISTOPT`` is substituted with the command's
        ``list_option`` so the child lists tests rather than running them.
    :param test_ids: If not None, the list of (prefix-stripped) test ids to
        supply to the child via ``$IDLIST`` / ``$IDOPTION`` / ``$IDFILE``.
    :return: The exit code of the child process.
    """
    prefix = cmd.get("prefix", "")
    cwd = cmd.get("cwd")
    env = os.environ.copy()
    extra_env = cmd.get("env")
    if extra_env:
        env.update(extra_env)

    idfile_path: Optional[str] = None
    if test_ids is not None and test_ids:
        idfile_path = _write_idfile(test_ids)

    try:
        argv = _expand_argv(
            cmd,
            list_mode=list_mode,
            test_ids=test_ids,
            idfile_path=idfile_path,
        )
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, cwd=cwd, env=env)
        try:
            assert proc.stdout is not None
            result = _PrefixingStreamResult(output, prefix) if prefix else output
            ByteStreamToStreamResult(proc.stdout, non_subunit_name="stdout").run(result)
        finally:
            returncode = proc.wait()
    finally:
        if idfile_path is not None:
            try:
                os.unlink(idfile_path)
            except OSError:
                pass
    return returncode


def combine(
    commands: list[dict],
    output_stream,
    *,
    list_mode: bool = False,
    test_ids: Optional[list[str]] = None,
) -> int:
    """Run ``commands`` and merge their subunit streams into ``output_stream``.

    :param list_mode: Run each command in listing mode (``$LISTOPT`` expanded).
    :param test_ids: Optional list of test ids to restrict execution to.
        Each command only sees ids whose prefix matches; commands with no
        matching ids are skipped entirely.
    :return: 0 if every command exited 0, 1 otherwise.
    """
    output = StreamResultToBytes(output_stream)
    output.startTestRun()
    failed = False
    try:
        for cmd in commands:
            cmd_ids = _select_ids_for_command(cmd, test_ids)
            if test_ids is not None and not cmd_ids:
                # Ids were requested, but none match this command.
                continue
            rc = run_command(cmd, output, list_mode=list_mode, test_ids=cmd_ids)
            if rc != 0:
                failed = True
    finally:
        output.stopTestRun()
    return 1 if failed else 0


def _read_id_list(path: str) -> list[str]:
    """Read test ids from a file, one per line; blank lines and # comments are skipped."""
    ids = []
    with open(path) as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if line:
                ids.append(line)
    return ids


def make_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "config",
        help="Path to a YAML configuration file describing the commands to run.",
    )
    parser.add_argument(
        "test_ids",
        nargs="*",
        help="Optional test ids to restrict execution to. Ids whose prefix "
        "matches a command are routed to that command.",
    )
    parser.add_argument(
        "--list",
        dest="list_mode",
        action="store_true",
        help="List tests that would be run instead of running them. Each "
        "command is invoked with its configured list_option substituted for "
        "$LISTOPT.",
    )
    parser.add_argument(
        "--load-list",
        dest="load_list",
        metavar="FILE",
        help="Read test ids (one per line) from FILE to restrict execution.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = make_parser()
    options = parser.parse_args(argv)
    commands = load_config(options.config)

    test_ids: Optional[list[str]] = None
    if options.load_list:
        test_ids = _read_id_list(options.load_list)
    if options.test_ids:
        test_ids = (test_ids or []) + options.test_ids

    sys.exit(
        combine(
            commands,
            sys.stdout,
            list_mode=options.list_mode,
            test_ids=test_ids,
        )
    )


if __name__ == "__main__":
    main()

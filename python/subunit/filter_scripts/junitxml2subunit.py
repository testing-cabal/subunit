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

"""A filter that reads JUnit XML test reports and emits a subunit v2 stream.

JUnit XML is the de-facto interchange format for JVM test runners (Maven
Surefire, Gradle, Ant) and many other ecosystems. Maven and Gradle write
one XML file per test class into a reports directory, so this script
accepts directories as well as individual files.

Typical use with Maven::

    mvn clean test ; junitxml2subunit -d target/surefire-reports

Typical use with Gradle::

    gradle clean test ; junitxml2subunit -d build/test-results/test
"""

import argparse
import os
import sys

from subunit import JUnitXML2SubUnit


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description=(
            "Convert JUnit XML test reports to a subunit v2 stream on stdout. "
            "Pass individual files as positional arguments or use -d/--dir to "
            "walk a reports directory for *.xml files."
        ),
    )
    parser.add_argument(
        "-d",
        "--dir",
        dest="dirs",
        action="append",
        default=[],
        metavar="DIR",
        help=(
            "Directory to walk for *.xml report files. May be repeated. "
            "Files inside the directory are converted in lexical order so "
            "the output is deterministic across runs."
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Individual JUnit XML report files to convert.",
    )
    return parser.parse_args(argv)


def collect_files(dirs, files):
    """Combine `--dir DIR` walks with explicit FILE arguments.

    Within each directory we sort by filename so the resulting subunit
    stream is reproducible. Across directories we preserve the user's
    argv order (some workflows feed multiple module-specific report
    directories and care about the suite ordering).
    """
    out = []
    for d in dirs:
        if not os.path.isdir(d):
            sys.stderr.write("junitxml2subunit: not a directory: {}\n".format(d))
            continue
        for root, _dirs, names in sorted(os.walk(d)):
            for name in sorted(names):
                if name.endswith(".xml"):
                    out.append(os.path.join(root, name))
    out.extend(files)
    return out


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    inputs = collect_files(args.dirs, args.files)
    if not inputs:
        sys.stderr.write("junitxml2subunit: no input files found (pass FILE arguments or use -d DIR)\n")
        return 2
    return JUnitXML2SubUnit(inputs, sys.stdout.buffer)


if __name__ == "__main__":
    sys.exit(main())

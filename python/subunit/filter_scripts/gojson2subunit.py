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

"""A filter that reads a `go test -json` stream and outputs a subunit stream.

Pipe Go's structured test output into this script:

    go test -json ./... | gojson2subunit

The conversion preserves per-test elapsed time (via paired ``inprogress`` /
terminal subunit packets) and folds captured stdout/stderr lines into a
single ``text/plain`` attachment on each terminal packet.
"""

import sys

from subunit import GoJSON2SubUnit


def main():
    sys.exit(GoJSON2SubUnit(sys.stdin, sys.stdout.buffer))


if __name__ == "__main__":
    main()

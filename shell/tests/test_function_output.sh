#!/bin/sh
#  subunit shell bindings.
#  Copyright (C) 2006  Robert Collins <robertc@robertcollins.net>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#


# this script tests the output of the methods. As each is tested we start using
# it.
# So the first test manually implements the entire protocol, the next uses the
# start method and so on.
# it is assumed that we are running from the 'shell' tree root in the source
# of subunit, and that the library sourcing tests have all passed - if they 
# have not, this test script may well fail strangely.

# import the library.
. share/subunit.sh

echo 'test: subunit_start_test output'
func_output=$(subunit_start_test "foo bar")
func_status=$?
if [ $func_status == 0 -a "x$func_output" = "xtest: foo bar" ]; then
  echo 'success: subunit_start_test output'
else
  echo 'failure: subunit_start_test output ['
  echo 'got an error code or incorrect output:'
  echo "exit: $func_status"
  echo "output: '$func_output'"
  echo ']' ;
fi

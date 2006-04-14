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


# this script tests that we can source the subunit shell bindings successfully.
# It manually implements the control protocol so that it des not depend on the
# bindings being complete yet.

# we expect to be run from the 'shell' tree root.

echo 'test: shell bindings can be sourced'
# if any output occurs, this has failed to source cleanly
source_output=$(. share/subunit.sh 2>&1)
if [ $? == 0 -a "x$source_output" = "x" ]; then
  echo 'success: shell bindings can be sourced'
else
  echo 'failure: shell bindings can be sourced ['
  echo 'got an error code or output during sourcing.:'
  echo $source_output
  echo ']' ;
fi

# now source it for real
. share/subunit.sh

# we should have a test-start function
echo 'test: subunit_start_test exists'
found_type=$(type -t subunit_start_test)
status=$?
if [ $status == 0 -a "x$found_type" = "xfunction" ]; then
  echo 'success: subunit_start_test exists'
else
  echo 'failure: subunit_start_test exists ['
  echo 'subunit_start_test is not a function:'
  echo "type -t status: $status"
  echo "output: $found_type"
  echo ']' ;
fi

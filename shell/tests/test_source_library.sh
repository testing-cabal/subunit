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
. share/subunit.sh
echo 'success: shell bindings can be sourced'

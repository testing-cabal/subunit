/**
 *
 *  subunit C child-side bindings: report on tests being run.
 *  Copyright (C) 2006  Robert Collins <robertc@robertcollins.net>
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 **/

#include <stdio.h>
#include <string.h>

/* these functions all flush to ensure that the test runner knows the action
 * that has been taken even if the subsequent test etc takes a long time or
 * never completes (i.e. a segfault).
 */

void
subunit_test_start(char const * const name)
{
  fprintf(stdout, "test: %s\n", name);
  fflush(stdout);
}


void
subunit_test_pass(char const * const name)
{
  fprintf(stdout, "success: %s\n", name);
  fflush(stdout);
}


void
subunit_test_fail(char const * const name, char const * const error)
{
  fprintf(stdout, "failure: %s [\n", name);
  fprintf(stdout, "%s", error);
  if (error[strlen(error) - 1] != '\n')
    fprintf(stdout, "\n");
  fprintf(stdout, "]\n");
  fflush(stdout);
}


void
subunit_test_error(char const * const name, char const * const error)
{
  fprintf(stdout, "error: %s [\n", name);
  fprintf(stdout, "%s", error);
  if (error[strlen(error) - 1] != '\n')
    fprintf(stdout, "\n");
  fprintf(stdout, "]\n");
  fflush(stdout);
}

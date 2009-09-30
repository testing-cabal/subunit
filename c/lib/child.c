/**
 *
 *  subunit C child-side bindings: report on tests being run.
 *  Copyright (C) 2006  Robert Collins <robertc@robertcollins.net>
 *
 *  Licensed under either the Apache License, Version 2.0 or the BSD 3-clause
 *  license at the users choice. A copy of both licenses are available in the
 *  project source as Apache-2.0 and BSD. You may not use this file except in
 *  compliance with one of these two licences.
 *  
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under these licenses is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the license you chose for the specific language governing permissions
 *  and limitations under that license.
 **/

#include <stdio.h>
#include <string.h>
#include "subunit/child.h"

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

/**
 *
 *  subunit C bindings.
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

#include <stdlib.h>
#include <unistd.h>
#include <check.h>

#include "subunit/child.h"

/**
 * Helper function to capture stdout, run some call, and check what
 * was written.
 * @expected the expected stdout content
 * @function the function to call.
 **/
static void
test_stdout_function(char const * expected,
                     void (*function)(void))
{
    /* test that the start function emits a correct test: line. */
    int bytecount;
    int old_stdout;
    int new_stdout[2];
    char buffer[100];
    /* we need a socketpair to capture stdout in */
    fail_if(pipe(new_stdout), "Failed to create a socketpair.");
    /* backup stdout so we can replace it */
    old_stdout = dup(1);
    if (old_stdout == -1) {
      close(new_stdout[0]);
      close(new_stdout[1]);
      fail("Failed to backup stdout before replacing.");
    }
    /* redirect stdout so we can analyse it */
    if (dup2(new_stdout[1], 1) != 1) {
      close(old_stdout);
      close(new_stdout[0]);
      close(new_stdout[1]);
      fail("Failed to redirect stdout");
    }
    /* yes this can block. Its a test case with < 100 bytes of output.
     * DEAL.
     */
    function();
    /* restore stdout now */
    if (dup2(old_stdout, 1) != 1) {
      close(old_stdout);
      close(new_stdout[0]);
      close(new_stdout[1]);
      fail("Failed to restore stdout");
    }
    /* and we dont need the write side any more */
    if (close(new_stdout[1])) {
      close(new_stdout[0]);
      fail("Failed to close write side of socketpair.");
    }
    /* get the output */
    bytecount = read(new_stdout[0], buffer, 100);
    if (0 > bytecount) {
      close(new_stdout[0]);
      fail("Failed to read captured output.");
    }
    buffer[bytecount]='\0';
    /* and we dont need the read side any more */
    fail_if(close(new_stdout[0]), "Failed to close write side of socketpair.");
    /* compare with expected outcome */
    fail_if(strcmp(expected, buffer), "Did not get expected output [%s], got [%s]", expected, buffer);
}


static void
call_test_start(void)
{
    subunit_test_start("test case");
}


START_TEST (test_start)
{
    test_stdout_function("test: test case\n", call_test_start);
}
END_TEST


static void
call_test_pass(void)
{
    subunit_test_pass("test case");
}


START_TEST (test_pass)
{
    test_stdout_function("success: test case\n", call_test_pass);
}
END_TEST


static void
call_test_fail(void)
{
    subunit_test_fail("test case", "Multiple lines\n of error\n");
}


START_TEST (test_fail)
{
    test_stdout_function("failure: test case [\n"
                         "Multiple lines\n"
        		 " of error\n"
			 "]\n",
			 call_test_fail);
}
END_TEST


static void
call_test_error(void)
{
    subunit_test_error("test case", "Multiple lines\n of output\n");
}


START_TEST (error)
{
    test_stdout_function("failure: test case [\n"
                         "Multiple lines\n"
        		 " of output\n"
			 "]\n",
			 call_test_error);
}
END_TEST



Suite *
child_suite(void)
{
    Suite *s = suite_create("subunit_child");
    TCase *tc_core = tcase_create("Core");
    suite_add_tcase (s, tc_core);
    tcase_add_test (tc_core, test_start);
    tcase_add_test (tc_core, test_pass);
    tcase_add_test (tc_core, test_fail);
    return s;
}


int
main(void)
{
  int nf;
  Suite *s = child_suite();
  SRunner *sr = srunner_create(s);
  srunner_run_all(sr, CK_NORMAL);
  nf = srunner_ntests_failed(sr);
  srunner_free(sr);
  return (nf == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}

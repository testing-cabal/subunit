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


#ifdef __cplusplus
extern "C" {
#endif


/**
 * subunit_test_start:
 *
 * Report that a test is starting.
 * @name: test case name
 */
extern void subunit_test_start(char const * const name);


/**
 * subunit_test_pass:
 *
 * Report that a test has passed.
 *
 * @name: test case name
 */
extern void subunit_test_pass(char const * const name);


/**
 * subunit_test_fail:
 *
 * Report that a test has failed.
 * @name: test case name
 * @error: a string describing the error.
 */
extern void subunit_test_fail(char const * const name, char const * const error);


/**
 * subunit_test_error:
 *
 * Report that a test has errored. An error is an unintentional failure - i.e.
 * a segfault rather than a failed assertion.
 * @name: test case name
 * @error: a string describing the error.
 */
extern void subunit_test_error(char const * const name,
                               char const * const error);


#ifdef __cplusplus
}
#endif

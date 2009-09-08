EXTRA_DIST =  \
	INSTALL \
	Makefile.am \
	README \
	NEWS \
	c/README \
	c/check-subunit-0.9.3.patch \
	c/check-subunit-0.9.5.patch \
	c/check-subunit-0.9.6.patch \
	c++/README \
	c++/cppunit-subunit-1.10.2.patch \
	python/subunit/__init__.py \
	python/subunit/run.py \
	python/subunit/tests/TestUtil.py \
	python/subunit/tests/__init__.py \
	python/subunit/tests/sample-script.py \
	python/subunit/tests/sample-two-script.py \
	python/subunit/tests/test_subunit_filter.py \
	python/subunit/tests/test_subunit_stats.py \
	python/subunit/tests/test_subunit_tags.py \
	python/subunit/tests/test_tap2subunit.py \
	python/subunit/tests/test_test_protocol.py \
	python/subunit/tests/test_test_results.py \
	runtests.py \
	shell/README \
	shell/share/subunit.sh \
	shell/subunit-ui.patch \
	shell/tests/test_function_output.sh \
	shell/tests/test_source_library.sh

ACLOCAL_AMFLAGS = -I m4

SUBUNIT_CFLAGS = -Wall -Werror -Wextra -Wstrict-prototypes -Wmissing-prototypes \
	-Wwrite-strings -Wno-variadic-macros -I$(top_srcdir)/c/include
AM_CFLAGS = $(SUBUNIT_CFLAGS)

include_subunitdir = $(includedir)/subunit

dist_bin_SCRIPTS = \
	filters/subunit-filter \
	filters/subunit-ls \
	filters/subunit-stats \
	filters/subunit-tags \
	filters/subunit2gtk \
	filters/subunit2junitxml \
	filters/subunit2pyunit \
	filters/tap2subunit

TESTS_ENVIRONMENT = SHELL_SHARE='$(top_srcdir)/shell/share/' PYTHONPATH='$(abs_top_srcdir)/python':${PYTHONPATH} 
TESTS = runtests.py $(check_PROGRAMS)

## install libsubunit.pc
pcdatadir = $(libdir)/pkgconfig
pcdata_DATA = libsubunit.pc

pkgpython_PYTHON = \
	python/subunit/__init__.py \
	python/subunit/iso8601.py \
	python/subunit/run.py \
	python/subunit/test_results.py

lib_LTLIBRARIES = libsubunit.la

include_subunit_HEADERS = \
	c/include/subunit/child.h

check_PROGRAMS = \
	c/tests/test_child

check_SCRIPTS = \
	runtests.py

clean-local:
	find . -name "*.pyc" | xargs -r rm

libsubunit_la_SOURCES = \
	c/lib/child.c \
	c/include/subunit/child.h

tests_LDADD = @CHECK_LIBS@ $(top_builddir)/libsubunit.la
c_tests_test_child_CFLAGS = $(SUBUNIT_CFLAGS) @CHECK_CFLAGS@
c_tests_test_child_LDADD = $(tests_LDADD)

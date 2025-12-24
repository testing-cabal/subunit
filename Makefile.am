EXTRA_DIST =  \
	.gitignore \
	Apache-2.0 \
	BSD \
	INSTALL \
	Makefile.am \
	NEWS \
	README.md \
	all_tests.py \
	c++/README \
	c/README \
	c/check-subunit-0.9.3.patch \
	c/check-subunit-0.9.5.patch \
	c/check-subunit-0.9.6.patch \
 	python/tests/__init__.py \
 	python/tests/sample-script.py \
 	python/tests/sample-two-script.py \
 	python/tests/test_chunked.py \
 	python/tests/test_details.py \
 	python/tests/test_filters.py \
 	python/tests/test_filter_to_disk.py \
 	python/tests/test_output_filter.py \
 	python/tests/test_progress_model.py \
 	python/tests/test_run.py \
 	python/tests/test_subunit_filter.py \
 	python/tests/test_subunit_stats.py \
 	python/tests/test_subunit_tags.py \
 	python/tests/test_tap2subunit.py \
 	python/tests/test_test_protocol.py \
 	python/tests/test_test_protocol2.py \
 	python/tests/test_test_results.py \
	python/subunit/filter_scripts/__init__.py \
	python/subunit/filter_scripts/subunit_1to2.py \
	python/subunit/filter_scripts/subunit2csv.py \
	python/subunit/filter_scripts/subunit2disk.py \
	python/subunit/filter_scripts/subunit2gtk.py \
	python/subunit/filter_scripts/subunit2junitxml.py \
	python/subunit/filter_scripts/subunit2pyunit.py \
	python/subunit/filter_scripts/subunit_2to1.py \
	python/subunit/filter_scripts/subunit_filter.py \
	python/subunit/filter_scripts/subunit_ls.py \
	python/subunit/filter_scripts/subunit_notify.py \
	python/subunit/filter_scripts/subunit_output.py \
	python/subunit/filter_scripts/subunit_stats.py \
	python/subunit/filter_scripts/subunit_tags.py \
	python/subunit/filter_scripts/tap2subunit.py \
 	setup.py \
	shell/README \
	shell/share/subunit.sh \
	shell/subunit-ui.patch \
	shell/tests/test_function_output.sh \
	shell/tests/test_source_library.sh

ACLOCAL_AMFLAGS = -I m4

include_subunitdir = $(includedir)/subunit

TESTS = $(check_PROGRAMS)

## install libsubunit.pc
pcdatadir = $(libdir)/pkgconfig
pcdata_DATA = \
	libsubunit.pc \
	libcppunit_subunit.pc

pkgpython_PYTHON = \
	python/subunit/__init__.py \
	python/subunit/chunked.py \
	python/subunit/details.py \
	python/subunit/filters.py \
	python/subunit/progress_model.py \
	python/subunit/run.py \
	python/subunit/v2.py \
	python/subunit/test_results.py \
	python/subunit/_output.py \
	python/subunit/_to_disk.py

lib_LTLIBRARIES = libsubunit.la
lib_LTLIBRARIES +=  libcppunit_subunit.la

include_subunit_HEADERS = \
	c/include/subunit/child.h \
	c++/SubunitTestProgressListener.h

check_PROGRAMS = \
	c/tests/test_child

libsubunit_la_SOURCES = \
	c/lib/child.c \
	c/include/subunit/child.h

libcppunit_subunit_la_SOURCES = \
	c++/SubunitTestProgressListener.cpp \
	c++/SubunitTestProgressListener.h

tests_LDADD = @CHECK_LIBS@ $(top_builddir)/libsubunit.la
c_tests_test_child_CFLAGS = -I$(top_srcdir)/c/include $(SUBUNIT_CFLAGS) @CHECK_CFLAGS@
c_tests_test_child_LDADD = $(tests_LDADD)


check-local:
	SHELL_SHARE='$(top_srcdir)/shell/share/' \
	PYTHONPATH='$(abs_top_srcdir)/python':'$(abs_top_srcdir)':$${PYTHONPATH} \
	$(PYTHON) -m testtools.run all_tests.test_suite

clean-local:
	find . -type f -name "*.pyc" -exec rm {} ';'

distclean-local:
	-rm -r .hypothesis > /dev/null

PYTHONPATH:=$(shell pwd)/python:${PYTHONPATH}

all:

check:
	# check the core python bindings.
	PYTHONPATH=$(PYTHONPATH) python ./test_all.py $(TESTRULE)
	# shell bindings
	PYTHONPATH=$(PYTHONPATH) make -C shell check
	# C bindings
	PYTHONPATH=$(PYTHONPATH) make -C c check

.PHONY: all

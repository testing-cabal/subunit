PYTHONPATH:=$(shell pwd)/lib:${PYTHONPATH}

all:

check:
	# check the core python bindings.
	PYTHONPATH=$(PYTHONPATH) python ./test_all.py $(TESTRULE)
	PYTHONPATH=$(PYTHONPATH) make -C shell check

.PHONY: all

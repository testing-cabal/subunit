PYTHONPATH:=$(shell pwd)/lib:${PYTHONPATH}

all:

check:
	PYTHONPATH=$(PYTHONPATH) python ./test_all.py $(TESTRULE)

.PHONY: all

check:
	scons -Q check

all:
	scons -Q

clean:
	scons -Q -c

install:
	scons -Q install

.PHONY: all check clean install

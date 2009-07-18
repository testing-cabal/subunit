#!/usr/bin/env python
import sys
if len(sys.argv) == 2:
    print "test fail"
    print "error fail"
    sys.exit(0)
print "test old mcdonald"
print "success old mcdonald"
print "test bing crosby"
print "failure bing crosby ["
print "foo.c:53:ERROR invalid state"
print "]"
print "test an error"
print "error an error"
sys.exit(0)

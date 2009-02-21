# setup our tools
import os.path
import sys

# we want the subunit source in the path so we can use it to run
# the tests. Yes this does make everything fall over in a screaming
# heap when you break it - so dont break it
# the system subunit does not have tests installed. So ensure we
# use the devel copy.
sys.path.insert(0, os.path.abspath('python'))
import subunit

default_root = os.path.expanduser('~/local/')
DESTDIR=ARGUMENTS.get('DESTDIR', default_root)
if DESTDIR[-1] != '/':
  DESTDIR += '/'
include = os.path.join(DESTDIR, "include", "subunit")
lib = os.path.join(DESTDIR, "lib")
# bin = "#export/$PLATFORM/bin"
env = Environment()
tests = []
Export('env', 'lib', 'include', 'DESTDIR', 'tests')

# support tools
def run_test_scripts(source, target, env, for_signature):
    """Run all the sources as executable scripts which return 0 on success."""
    # TODO: make this cross platform compatible.
    return ["LD_LIBRARY_PATH=%s %s" % (os.path.join(str(target[0].dir), 
                                env['LIBPATH']), a_source) for a_source in source]
test_script_runner = Builder(generator=run_test_scripts)
def run_python_scripts(source, target, env, for_signature):
    """Run all the sources as executable scripts which return 0 on success."""
    return ["PYTHONPATH=%s python %s" % (env['PYTHONPATH'], a_source) for a_source in source]
python_test_runner = Builder(generator=run_python_scripts)
env.Append(BUILDERS = {'TestRC' : test_script_runner,
                       'TestPython' : python_test_runner})

# tests
tests.append(env.TestPython('check_python', 'runtests.py', PYTHONPATH='python'))

SConscript(dirs=['c', 'c++', 'filters', 'python', 'shell'])

env.Alias('check', tests)

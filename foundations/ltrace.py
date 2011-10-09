# -*- coding: utf-8 -*-
"""
Licorn foundations - http://dev.licorn.org/documentation/foundations

ltrace - light procedural trace (debug only)

	set environment variable LICORN_TRACE={all,configuration,core,…} and
	watch your terminal	flooded with information. You can combine values with
	pipes:
		export LICORN_TRACE=all
		export LICORN_TRACE=configuration
		export LICORN_TRACE="configuration|openldap"
		export LICORN_TRACE="users|backends|plugins"
		export LICORN_TRACE="groups|openldap"
		export LICORN_TRACE="machines|dnsmasq"
		(and so on…)

Copyright (C) 2010 Olivier Cortès <olive@deep-ocean.net>
Licensed under the terms of the GNU GPL version 2.
"""
import sys, os, threading, traceback
from time  import time, localtime, strftime
from types import *

# WARNING: please do not import anything from licorn here, except styles.
from styles  import *
from ltraces import *

try:
	from pygments import highlight
	from pygments.lexers import PythonLexer
	from pygments.formatters import Terminal256Formatter

	lexer = PythonLexer()
	formatter = Terminal256Formatter()
except ImportError:
	highlight = lambda x, y, z: x
	lexer     = ''
	formatter = ''

def dumpstacks(signal=None, frame=None):
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append(_("\n# Thread: %s(%d)") % (id2name[threadId], threadId))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append(_('	File: "%s", line %d, in %s') % (filename, lineno, name))
            if line:
                code.append("	  %s" % (line.strip()))
    return highlight("\n".join(code), lexer, formatter)
def dump_one(obj_to_dump, long_output=False):
	try:
		return obj_to_dump.dump_status(long_output=long_output)

	except AttributeError:
		if long_output:
			return '%s %s:\n%s' % (
				str(obj_to_dump.__class__),
				stylize(ST_NAME, obj_to_dump.name),
				'\n'.join(['%s(%s): %s' % (
					stylize(ST_ATTR, key),
					type(getattr(obj_to_dump, key)),
					getattr(obj_to_dump, key))
						for key in dir(obj_to_dump)]))
		else:
			return '%s %s: %s' % (
				str(obj_to_dump.__class__),
				stylize(ST_NAME, obj_to_dump.name),
				[ key for key in dir(obj_to_dump)])
def dump(*args, **kwargs):
	data = u'\n'.join(dump_one(arg) for arg in args)
	data += u'\n'.join(dump_one(value) for key, value in kwargs)
	return data
def fulldump(*args, **kwargs):
	data = u'\n'.join(dump_one(arg, True) for arg in args)
	data += u'\n'.join(dump_one(value, True) for key, value in kwargs)
	return data
def mytime():
	""" close http://dev.licorn.org/ticket/46 """
	t = time()
	return '[%s%s]' % (
		strftime('%Y/%d/%m %H:%M:%S', localtime(t)), ('%.4f' % (t%1))[1:])

# the new LTRACE env variable takes precedence, then we try the old one
# LICORN_TRACE.
new_trace = os.getenv('LTRACE', None)
old_trace = os.getenv('LICORN_TRACE', None)

if new_trace != None or old_trace != None:

	if new_trace:
		env_trace = new_trace
	else:
		env_trace = old_trace

	ltrace_level = ltrace_str_to_int(env_trace)

	def ltrace(module, message, *args):
		if  ltrace_level & module:
			if args:
				message = message.format(*(stylize(*x)
											if type(x) == TupleType
											else x
											for x in args))

			sys.stderr.write('%s %s: %s\n' % (
				stylize(ST_COMMENT, '   %s' % mytime()),
				stylize(ST_DEBUG, 'TRACE ' + module.name.rjust(TRACES_MAXWIDTH)), message))
		return True

	def insert_ltrace():
		# in trace mode, use python interpreter directly to avoid the -OO
		# inserted in all our executables.
		# NOTE: don't use assert ltrace here, this will fail to display the
		# message on first launch, where -OO is active.
		sys.stderr.write('Licorn®: %s for %s\n' % (
					stylize(ST_IMPORTANT, 'LTRACE enabled'),
					stylize(ST_COMMENT, env_trace)))
		return ['python']

else:
	def ltrace(a, b, *args):
		return True
	def insert_ltrace():
		return []

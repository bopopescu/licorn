# -*- coding: utf-8 -*-
"""
Licorn foundations: classes - http://docs.licorn.org/

:copyright:
	* 2005-2010 Olivier Cortès <olive@deep-ocean.net>
	* partial 2010 RobinLucbernet <robinlucbernet@gmail.com>

:license: GNU GPL version 2

"""

import sys, os, time

# PLEASE do not import "logging" here.
import exceptions, pyutils, fsapi
from styles    import *
from ltrace    import ltrace
from base      import Enumeration
from licorn.foundations.pyutils import add_or_dupe_enumeration
from licorn.foundations import readers, logging
from licorn.foundations.styles    import *

class ConfigFile(Enumeration):
	""" A Configuration file class which handles adds/removes cleverly and loads
		from one of our readers, provided the reader returns a dict.

		.. versionadded:: 1.3
			this class was created by Robin in the 1.3 development cycle.
	"""

	def __init__(self, filename, name=None, reader=readers.generic_reader,
		separator=None):
		assert ltrace('objects', '| ConfigFile.__init__(filename=%s, name=%s)' %
			(filename, name))
		Enumeration.__init__(self, name=name if name else filename)

		self._filename = filename
		if not os.path.exists(filename):
			fsapi.touch(filename)

		self._separator = separator
		self._reader = reader

		self.reload()
	def __str__(self):
		data = ''

		for key, value in self.iteritems():
			if hasattr(value, '__iter__'):
				for v in value:
					data += '%s%s%s\n' % (key, self._separator if
						self._separator is not None else '',
						v if v is not None else '')
			else:
				data += '%s%s%s\n' % (key, self._separator  if
						self._separator is not None else '',
						value if value is not None else '')

		return data
	def reload(self, filename=None):
		""" load or reload the data, eventually from another configuration
			file. Lock the file while reading it. """

		if filename is None:
			filename = self._filename

		with FileLock(self, filename):
			if self._separator is None:
				func = self._reader(filename)
			else:
				func = self._reader(filename, self._separator)

			for key, value in func.iteritems():
				if hasattr(value, '__iter__'):
					for v in value:
						add_or_dupe_enumeration(self, key, v)
				else:
					self[key] = value
	def backup(self):
		return fsapi.backup_file(self._filename)
	def save(self, filename=None):
		""" Write the configuration file contents back to the disk. """

		if filename is None:
			filename = self._filename

		assert ltrace('objects', '| ConfigFile.save(%s)' % filename)

		data = ('#-------------------------------------------------------\n'
				'# %s configuration file generated by Licorn®. \n'
				'#-------------------------------------------------------\n\n'
					% self.name) + str(self)

		with FileLock(self, filename):
			open(filename, 'w').write(data)
	def has(self, key, value=None):
		""" Return true or false if config is already in. """

		if key in self.keys() and (value is None or value in self[key]):
			assert ltrace('objects', "%s: '%s %s' detected" % (
				self.name, key, self[key]))
			return True
		return False
	def add(self, key, value, dont_check=False, replace=False):
		""" TODO. """
		if replace:
			self[key] = value
			logging.progress('%s: %s configuration key %s with value %s' % (
				stylize(ST_PATH, self.name), stylize(ST_OK, "modified"), 
				stylize(ST_NAME, key), stylize(ST_NAME, value)))
			assert ltrace('objects', "%s: overwritten '%s %s'" % (
				self.name, key, value))
		elif dont_check or not self.has(key, value):
			pyutils.add_or_dupe_enumeration(self, key, value)
			logging.progress('%s: %s configuration key %s with value %s' % (
				stylize(ST_PATH, self.name), stylize(ST_OK, "added"), 
				stylize(ST_NAME, key), stylize(ST_NAME, value)))
			assert ltrace('objects', "%s: added '%s %s'" % (
					self.name, key, value))
	def remove(self, key, value=None, dont_check=False):
		""" TODO. """

		if dont_check or self.has(key, value):
			if hasattr(self[key], '__iter__'):
				self[key].remove(value)
				if self[key] in ('', []):
					del self[key]
			else:
				del self[key]
			logging.progress('%s: %s configuration key %s with value %s' % (
				stylize(ST_PATH, self.name), stylize(ST_BAD, "removed"), 
				stylize(ST_NAME, key), stylize(ST_NAME, value)))
			assert ltrace('objects', "%s: removed '%s%s'" % (
				self.name, key, ' ' + value if value else ''))
class FileLock:
	"""
		This FileLock class is a reimplementation of basic locks with files.
		This is needed to be compatible with adduser/login binaries, which
		use /etc/{passwd,group}.lock to signify that the system files are locked.

	"""

	def __init__(self, configuration, filename, waitmax=10, verbose=True):

		# TODO: don't blow up if user_dir isn't set (which is the case for daemon user)

		self.pretty_name = str(self.__class__).rsplit('.', 1)[1]

		if filename is None :
			raise exceptions.LicornRuntimeError("please specify a file to lock")

		self.filename = filename + '.lock'
		self.lockname = filename.rsplit('/', 1)[1]

		assert ltrace('objects', '%s: new instance with %s.' % (self.pretty_name,
			stylize(ST_PATH, self.filename)))

		self.waitmax = waitmax
		self.wait    = waitmax
		self.verbose = verbose

	#
	# Make FileLock be usable as a context manager.
	#
	def __enter__(self):
		self.Lock()
	def __exit__(self, type, value, tb):
		self.Unlock()

	def Lock(self):
		"""Acquire a lock, i.e. create $file.lock."""
		assert ltrace('objects', '%s: pseudo-locking %s.' % (self.pretty_name,
			stylize(ST_PATH, self.lockname)))

		try:
			self.wait = self.waitmax
			while os.path.exists(self.filename) and self.wait >= 0:
				if self.verbose:
					sys.stderr.write("\r %s waiting %d second(s) for %s lock to be released… " \
						% (stylize(ST_NOTICE, '*'), self.wait, self.lockname))
					sys.stderr.flush()
				self.wait = self.wait - 1
				time.sleep(1)

			if self.wait <= 0:
				sys.stderr.write("\n")
				raise IOError, "%s lockfile still present, can't acquire lock after timeout !" % self.lockname

			else:
				try:
					open(self.filename, "w")
				except (IOError, OSError):
					raise IOError, "Can't create lockfile %s." % self.filename

		except KeyboardInterrupt:
			sys.stderr.write("\n")
			raise

		assert ltrace('objects', '%s: successfully locked %s.' % (self.pretty_name,
			stylize(ST_PATH, self.filename)))

	def Unlock(self):
		"""Free the lock by removing the associated lockfile."""

		assert ltrace('objects', '%s: removing lock on %s.' % (self.pretty_name,
			stylize(ST_PATH, self.lockname)))

		if os.path.exists(self.filename):
			try:
				os.unlink(self.filename)
			except (OSError):
				raise OSError, "can't remove lockfile %s." % self.filename

		assert ltrace('objects', '%s: successfully unlocked %s.' % (self.pretty_name,
			stylize(ST_PATH, self.filename)))

	def IsLocked(self):
		"""Tell if a file is currently locked by looking if the associated lock
		is present."""
		return os.path.exists(self.filename)
class StateMachine:
	"""
		A Finite state machine design pattern.
		Found at http://www.ibm.com/developerworks/library/l-python-state.html , thanks to David Mertz.
	"""
	def __init__(self):
		self.handlers = {}
		self.startState = None
		self.endStates = []

	def add_state(self, name, handler, end_state = False):
		self.handlers[name] = handler
		if end_state:
			 self.endStates.append(name)

	def set_start(self, name):
		self.startState = name

	def run(self, data):
		try:
			 handler = self.handlers[self.startState]
		except:
			 raise exceptions.LicornRuntimeError("LSM: must call .set_start() before .run()")

		if not self.endStates:
				 raise exceptions.LicornRuntimeError("LSM: at least one state must be an end_state.")

		while True:
			(newState, data) = handler(data)
			if newState in self.endStates:
				break
			else:
				handler = self.handlers[newState]

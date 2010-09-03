# -*- coding: utf-8 -*-
"""
Licorn foundations - http://dev.licorn.org/documentation/foundations

objects - ultra basic objects, used as base classes.

Copyright (C) 2005-2008 Olivier Cortès <olive@deep-ocean.net>
Licensed under the terms of the GNU GPL version 2

"""
import sys, os, time
from sys                import version_info
from Queue              import Queue
from threading          import Thread, Event

# licorn internals
import exceptions, styles
from ltrace import ltrace

class LicornConfigObject:
	""" a base class just to be able to add/remove custom attributes
		to other custom attributes (build a tree simply).
	"""
	def __init__(self, fromdict = {}, level = 1):
		for key in fromdict.keys():
			setattr(self, key, fromdict[key])
		self._level = level
	def __str__(self):
		data = ""
		for i in self.__dict__:
			if i[0] == '_': continue
			if type(getattr(self, i)) == type(self):
				data += u'%s\u21b3 %s:\n%s' % ('\t'*self._level, i, str(getattr(self, i)))
			else:
				data += u"%s\u21b3 %s = %s\n" % ('\t'*self._level, str(i), str(getattr(self, i)))
		return data
class Singleton(object):
	__instances = {}
	def __new__(cls, *args, **kargs):
		if Singleton.__instances.get(cls) is None:
			Singleton.__instances[cls] = object.__new__(cls)
		#ltrace('objects', 'Singleton 2.6+: %s:%s.' % (cls, Singleton.__instances[cls]))
		return Singleton.__instances[cls]
class LicornThread(Thread):
	"""
		A simple thread with an Event() used to stop it properly, and a Queue() to
		get events from other threads asynchronically.

		Every subclass must implement a process_message() method, which will be called
		by the main loop until the thread stops.
	"""

	def __init__(self, pname = '<unknown>'):
		Thread.__init__(self)

		self.name  = "%s/%s" % (
			pname, str(self.__class__).rsplit('.', 1)[1].split("'")[0])

		self._stop_event  = Event()
		self._input_queue = Queue()
		ltrace('thread', '%s: thread initialized.' % self.name)
	def dispatch_message(self, msg):
		""" get an incoming message in a generic way. """
		self._input_queue.put(msg)
	def run(self):
		""" Process incoming messages until stop Event() is set. """

		ltrace('thread', '%s: thread started.' % self.name)

		while not self._stop_event.isSet():
			data = self._input_queue.get()
			if data is None:
				break
			self.process_message(data)
			self._input_queue.task_done()

		ltrace('thread', '%s: thread ended.' % self.name)
	def stop(self):
		""" Stop current Thread
		and put a special None entry in the queue, to be
		sure that self.run() method exits properly. """
		ltrace('thread', '%s: stopping thread.' % self.name)
		self._stop_event.set()
		self._input_queue.put(None)
class FileLock:
	"""
		This FileLock class is a reimplementation of basic locks with files.
		This is needed to be compatible with adduser/login binaries, which
		use /etc/{passwd,group}.lock to signify that the system files are locked.

	"""

	def __init__(self, configuration, filename = None, waitmax = 10, verbose = True):

		# TODO: don't blow up if user_dir isn't set (which is the case for daemon user)

		self.pretty_name = str(self.__class__).rsplit('.', 1)[1]

		if filename is None :
			raise exceptions.LicornRuntimeError("please specify a file to lock")

		if filename[0] == '/':
			self.filename = filename + '.lock'
			self.lockname = filename.rsplit('/', 1)[1]
		else:
			self.filename = "%s/%s.lock" % (configuration.user_dir, filename)
			self.lockname = filename

		ltrace('objects', '%s: new instance with %s.' % (self.pretty_name,
			styles.stylize(styles.ST_PATH, self.filename)))

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
		ltrace('objects', '%s: pseudo-locking %s.' % (self.pretty_name,
			styles.stylize(styles.ST_PATH, self.lockname)))

		try:
			self.wait = self.waitmax
			while os.path.exists(self.filename) and self.wait >= 0:
				if self.verbose:
					sys.stderr.write("\r %s waiting %d second(s) for %s lock to be released... " \
						% (styles.stylize(styles.ST_NOTICE, '*'), self.wait, self.lockname))
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

		ltrace('objects', '%s: successfully locked %s.' % (self.pretty_name,
			styles.stylize(styles.ST_PATH, self.filename)))

	def Unlock(self):
		"""Free the lock by removing the associated lockfile."""

		ltrace('objects', '%s: removing lock on %s.' % (self.pretty_name,
			styles.stylize(styles.ST_PATH, self.lockname)))

		if os.path.exists(self.filename):
			try:
				os.unlink(self.filename)
			except (OSError):
				raise OSError, "can't remove lockfile %s." % self.filename

		ltrace('objects', '%s: successfully unlocked %s.' % (self.pretty_name,
			styles.stylize(styles.ST_PATH, self.filename)))

	def IsLocked(self):
		"""Tell if a file is currently locked by looking if the associated lock
		is present."""
		return os.path.exists(self.filename)
class UGMBackend:
	"""
		Abstract backend class allowing access to users and groups data. The
		UGMBackend presents an homogeneous API for operations on these
		objects at a system level.

		Please refer to http://dev.licorn.org/wiki/DynamicUGMBackendSystem for
		a more general documentation.
	"""
	configuration = None
	users         = None
	groups        = None
	machines      = None

	def __str__(self):
		return self.name
	def __repr__(self):
		return self.name
	def __init__(self, configuration, users=None, groups=None, warnings=True):

		self.name      = "UGMBackend"

		ltrace('objects', '| UGMBackend.__init__()')

		self.warnings      = warnings
		self.available = False
		self.enabled   = False
		self.compat    = ()
		self.priority  = 0
		self.plugins   = {}


		UGMBackend.configuration = configuration

		if users:
			self.set_users_controller(users)

		if groups:
			self.set_groups_controller(groups)

		#
		# everything else __init__() should be done by a real implementation.
		#

		return False
	def enable(self):
		return False
	def disable(self):
		return False
	def initialize(self, active=True):
		"""
		For an abstract backend, initialize() always return False.

		"active" is filled by core.configuration and gives a hint about the
		system configuration:
			- active will be true if the underlying system is configured to
				use the backend. That doesn't imply the backend CAN be used,
				for exemple on a partially configured system.
			- active will be false if the backend is deactivated in the system
				configuration. The backend can be fully operationnal anyway. In
				this case "active" means that the backend will be used (or not)
				by Licorn.

		"""

		# return "self".enabled instead of UGMBackend.enabled, to get the
		# instance attribute, if modified.
		return self.enabled
	def check(self, batch=False, auto_answer=None):
		""" default check method. """
		pass
	def set_users_controller(self, users):
		""" save a reference of the UsersController for future use. """
		UGMBackend.users = users
		if users.groups is not None:
			UGMBackend.groups = users.groups
	def set_groups_controller(self, groups):
		""" save a reference of the GroupsController for future use. """
		UGMBackend.groups = groups
		if groups.users is not None:
			UGMBackend.users = groups.users
	def set_machines_controller(self, machines):
		UGMBackend.machines = machines
	def connect_plugin(self, plugin):
		""" """
		ltrace('objects', '| UGMBackend.connect_plugin()')

		if self.name in plugin.backend_compat:
			ltrace('objects', '  UGMBackend.connect_plugin(%s <-> %s)' % (
				self.name, plugin.name))
			self.plugins[plugin.name] = plugin
			plugin.set_backend(self)
			return True
		return False
	def load_defaults(self):
		""" A real backend will setup its own needed attributes with values
		*strictly needed* to work. This is done in case these values are not
		present in configuration files.

		Any configuration file containing these values, will be loaded
		afterwards and will overwrite these attributes. """
		pass
	def load_machines(self):
		""" gather the list of all known machines on the system. """

		ltrace('objects', '| UGMBackend.load_machines(%s)' % self.plugins)

		for p in self.plugins:
			if self.plugins[p].purpose == 'machines':
				return self.plugins[p].load_machines()

		return {}, {}

	def save_users(self):
		""" Take all users from UGMBackend.users (typically in a for loop) and
		save them into the backend. """
		pass
	def save_groups(self):
		""" Take all groups from UGMBackend.groups (typically in a for loop) and
		save them into the backend. """
		pass
	def save_machines(self):
		""" Take all machines from UGMBackend.machines (typically in a for loop)
		and	save them into the backend. """
		pass
	def save_user(self, uid):
		""" save one user into the backend. Useful on system which have loads
		of users/groups, to avoid saving all of them when there is only a small
		update.	"""
		pass
	def save_group(self, gid):
		""" save one group into the backend. Useful on system which have loads
		of users/groups, to avoid saving all of them when there is only a small
		update.	"""
		pass
	def save_machine(self, mid):
		""" save one machine into the backend. Useful on system which have loads
		of machines, to avoid saving all of them when there is only a small
		update.	"""
		pass
	def save_all(self, users=None, groups=None, machines=None):
		""" Save all internal data to backend. This is just a wrapper. """
		self.save_users()
		self.save_groups()
		self.save_machines()
	def compute_password(self, password):
		""" Encode a password in a way the backend can understand.
		For example the unix backend will use crypt() function, whereas
		the LDAP backend will use the SHA1 hash only with a base64 encoding and
		a '{SHA}' text header. """
		pass
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

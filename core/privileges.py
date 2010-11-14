# -*- coding: utf-8 -*-
"""
Licorn core - http://dev.licorn.org/documentation/core

privileges - everything internal to system privileges management

Copyright (C) 2005-2010 Olivier Cortès <olive@deep-ocean.net>,
Partial Copyright (C) 2005 Régis Cobrun <reg53fr@yahoo.fr>
Licensed under the terms of the GNU GPL version 2
"""

import Pyro.core
from threading import RLock

from licorn.foundations           import logging, exceptions
from licorn.foundations           import readers
from licorn.foundations.styles    import *
from licorn.foundations.ltrace    import ltrace
from licorn.foundations.base      import Singleton
from licorn.foundations.constants import filters

from licorn.core         import LMC
from licorn.core.objects import LicornCoreObject

class PrivilegesWhiteList(list, Singleton, LicornCoreObject):
	""" Manage privileges whitelist. """

	init_ok = False
	load_ok = False
	def __init__(self, conf_file=None):
		""" Read the configuration file and populate ourselves. """

		assert ltrace('privileges', '> PrivilegesWhiteList.__init__(%s)' %
			PrivilegesWhiteList.init_ok)

		if PrivilegesWhiteList.init_ok:
			return

		LicornCoreObject.__init__(self, 'privileges')

		if conf_file is None:
			self.conf_file = LMC.configuration.privileges_whitelist_data_file
		else:
			self.conf_file = conf_file

		self.changed = False

		PrivilegesWhiteList.init_ok = True
		assert ltrace('privileges', '< PrivilegesWhiteList.__init__(%s)' %
			PrivilegesWhiteList.init_ok)
	def load(self):
		if PrivilegesWhiteList.load_ok:
			return
		else:
			assert ltrace('privileges', '| load()')
			# make sure our dependancies are OK.
			LMC.groups.load()
			self.reload()
			PrivilegesWhiteList.load_ok = True
	def __del__(self):
		""" destructor. """
		# just in case it wasn't done before (in batched operations, for example).
		if self.changed:
			self.WriteConf()
	def reload(self):
		""" reload internal data  """

		with self.lock():
			self[:] = []

			try:
				self.extend(readers.very_simple_conf_load_list(self.conf_file))
			except IOError, e:
				if e.errno == 2:
					pass
				else:
					raise e
			# TODO: si le fichier contient des doublons, faire plutot:
			# map(lambda (x): self.append(x),
			# readers.very_simple_conf_load_list(conf_file))
	def add(self, privileges, listener=None):
		""" One-time multi-add method (list as argument).
			This method doesn't need locking, all sub-methods are already.
		"""
		for priv in privileges:
			self.append(priv, listener=listener)
		self.WriteConf()
	def delete(self, privileges, listener=None):
		""" One-time multi-delete method (list as argument).
			This method doesn't need locking, all sub-methods are already.
		"""
		for priv in privileges:
			self.remove(priv, listener=listener)
		self.WriteConf()
	def append(self, privilege, listener=None):
		""" Set append like: no doubles."""
		with self.lock():
			try:
				self.index(privilege)
			except ValueError:
				if LMC.groups.is_system_group(privilege):
					list.append(self, privilege)
					logging.info('Added privilege %s to whitelist.' %
						stylize(ST_NAME, privilege),
						listener=listener)
				else:
					logging.warning('''group %s can't be promoted as '''
						'''privilege, it is not a system group.''' % \
						stylize(ST_NAME, privilege),
						listener=listener)
			else:
				logging.info("privilege %s already whitelisted, skipped." % \
					stylize(ST_NAME, privilege), listener=listener)
	def remove(self, privilege, listener=None):
		""" Remove without throw of exception """

		assert ltrace('privileges','| remove(%s)' % privilege)

		with self.lock():
			try:
				list.remove(self, privilege)
				logging.info('Removed privilege %s from whitelist.' %
					stylize(ST_NAME, privilege),
					listener=listener)
			except ValueError:
				logging.info('''privilege %s is already not present in the '''
					'''whitelist, skipped.''' % \
						stylize(ST_NAME, privilege),
						listener=listener)
	def Select(self, filter_string):
		""" filter self against various criteria and return a list of matching
			privileges. """
		with self.lock():
			privs = self[:]
			filtered_privs = []
			if filters.ALL == filter_string:
				filtered_privs = privs
			return filtered_privs
	def confirm_privilege(self, priv):
		""" return a UID if it exists in the database. """
		if priv in self:
			return priv
		else:
			raise exceptions.DoesntExistsException(
				"Privilege %s doesn't exist" % priv)
	def guess_identifier(self, priv):
		if priv in self:
			return priv
	def ExportCLI(self):
		""" present the privileges whitelist on command-line: one by line. """
		with self.lock():
			return '%s%s' % (
				'\n'.join(self),
				'\n' if len(self)>0 else ''
				)
	def ExportXML(self):
		with self.lock():
			return '''<?xml version='1.0' encoding=\"UTF-8\"?>
<privileges-whitelist>\n%s%s</privileges-whitelist>\n''' % (
				'\n'.join(['	<privilege>%s</privilege>' % x for x in self]),
				'\n' if len(self)>0 else '')
	def WriteConf(self):
		""" Serialize internal data structures into the configuration file. """
		assert ltrace('privileges', '| WriteConf()')
		with self.lock():
			self.sort()
			open(self.conf_file, 'w').write('%s\n' % '\n'.join(self))

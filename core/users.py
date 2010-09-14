# -*- coding: utf-8 -*-
"""
Licorn foundations - http://dev.licorn.org/documentation/foundations

Copyright (C) 2005-2010 Olivier Cortès <olive@deep-ocean.net>,
Partial Copyright (C) 2006 Régis Cobrun <reg53fr@yahoo.fr>
Licensed under the terms of the GNU GPL version 2
"""

import os, crypt, sys
from time import time, strftime, gmtime

from licorn.foundations         import logging, exceptions, process, hlstr
from licorn.foundations         import pyutils, styles, fsapi
from licorn.foundations.objects import Singleton
from licorn.foundations.ltrace  import ltrace

class UsersController(Singleton):

	users        = None # (dictionary)
	login_cache  = None # (dictionary)
	init_ok      = False

	# cross-references to other common objects
	configuration = None # (LicornConfiguration)
	profiles      = None # (ProfilesController)
	groups        = None # (GroupsController)

	# Filters for Select() method.
	FILTER_STANDARD = 1
	FILTER_SYSTEM   = 2

	def __init__(self, configuration):
		""" Create the user accounts list from the underlying system.
			The arguments are None only for get (ie Export and ExportXml) """

		if UsersController.init_ok:
			return

		if UsersController.configuration is None:
			UsersController.configuration = configuration

		# see Select()
		self.filter_applied = False

		UsersController.backends = self.configuration.backends
		for bkey in UsersController.backends.keys():
			if bkey=='prefered':
				continue
			UsersController.backends[bkey].set_users_controller(self)

		if UsersController.users is None:
			self.reload()

		UsersController.init_ok = True
	def __getitem__(self, item):
		return UsersController.users[item]
	def __setitem__(self, item, value):
		UsersController.users[item]=value
	def keys(self):
		return UsersController.users.keys()
	def has_key(self, key):
		return UsersController.users.has_key(key)
	def reload(self):
		""" Load (or reload) the data structures from the system files. """

		UsersController.users       = {}
		UsersController.login_cache = {}

		for bkey in UsersController.backends.keys():
			if bkey=='prefered':
				continue
			u, c = self.backends[bkey].load_users()
			UsersController.users.update(u)
			UsersController.login_cache.update(c)

	def SetProfiles(self, profiles):
		UsersController.profiles = profiles
	def SetGroups(self, groups):
		UsersController.groups = groups
	def WriteConf(self, uid=None):
		""" Write the user data in appropriate system files."""

		ltrace('users', 'saving data structures to disk.')

		if uid:
			UsersController.backends[
				UsersController.users[uid]['backend']
				].save_one_user(uid)
		else:
			for bkey in UsersController.backends.keys():
				if bkey=='prefered':
					continue
				UsersController.backends[bkey].save_users()

	def Select(self, filter_string):
		""" Filter user accounts on different criteria.
		Criteria are:
			- 'system users': show only «system» users (root, bin, daemon,
				apache...), not normal user account.
			- 'normal users': keep only «normal» users, which includes Licorn
				administrators
			- more to come...
		"""

		#
		# filter_applied is used to note if something has been selected (or
		# tried to). Without this, «get users» on a system with no users
		# returns all system accounts, but it should return nothing, except
		# when given --all of course. Even if nothing match the filter given
		# we must note that a filter has been applied, in order to output a
		# coherent result.
		#
		self.filter_applied = True
		self.filtered_users = []

		uids = UsersController.users.keys()
		uids.sort()

		if UsersController.FILTER_STANDARD == filter_string:
			def keep_uid_if_not_system(uid):
				if not UsersController.is_system_uid(uid):
					self.filtered_users.append(uid)

			map(keep_uid_if_not_system, uids)

		elif UsersController.FILTER_SYSTEM == filter_string:
			def keep_uid_if_system(uid):
				if UsersController.is_system_uid(uid):
					self.filtered_users.append(uid)

			map(keep_uid_if_system, uids)

		else:
			import re
			uid_re = re.compile("^uid=(?P<uid>\d+)")
			uid = uid_re.match(filter_string)
			if uid is not None:
				uid = int(uid.group('uid'))
				self.filtered_users.append(uid)
	def AddUser(self, login=None, system=False, password=None, gecos=None,
		desired_uid=None, primary_gid=None, profile=None, skel=None,
		home=None, lastname=None, firstname=None, batch=False, force=False):
		"""Add a user and return his/her (uid, login, pass)."""

		ltrace('users', '''> AddUser(login=%s, system=%s, pass=%s, '''
			'''uid=%s, gid=%s, profile=%s, skel=%s, gecos=%s, first=%s, '''
			'''last=%s, home=%s)''' % (login, system, password, desired_uid,
			primary_gid, profile, skel, gecos, firstname, lastname, home))

		# if an UID is given, it must be free.
		if UsersController.users.has_key(desired_uid):
			raise exceptions.AlreadyExistsError('''The UID you want (%s) '''
				'''is already taken by another user (%s). Please choose '''
				'''another one.''' % (
					styles.stylize(styles.ST_UGID, desired_uid),
					styles.stylize(styles.ST_NAME,
						UsersController.users[desired_uid]['login'])))

		# to create a user account, we must have a login. autogenerate it
		# if not given as argument.
		if login is None:
			if firstname is None or lastname is None:
				raise exceptions.BadArgumentError(
					logging.SYSU_SPECIFY_LGN_FST_LST)
			else:
				login_autogenerated = True
				login = UsersController.make_login(lastname, firstname)
		else:
			login_autogenerated = False

		if gecos is None:
			gecos_autogenerated = True

			if firstname is None or lastname is None:
				gecos = "Compte %s" % login
			else:
				gecos = "%s %s" % (firstname, lastname.upper())
		else:
			gecos_autogenerated = False

			if firstname and lastname:
				raise exceptions.BadArgumentError(
					logging.SYSU_SPECIFY_LF_OR_GECOS)
			# else: all is OK, we have a login and a GECOS field

		# then verify that the login match all requisites and all constraints.
		# it can be wrong, even if autogenerated with internal tools, in rare
		# cases, so check it without conditions.
		if not hlstr.cregex['login'].match(login):
			if login_autogenerated:
				raise exceptions.LicornRuntimeError(
					"Can't build a valid login (%s) with the " \
					"firstname/lastname (%s/%s) you provided." % (
					login, firstname, lastname) )
			else:
				raise exceptions.BadArgumentError(
					logging.SYSU_MALFORMED_LOGIN % (
						login, styles.stylize(styles.ST_REGEX,
						hlstr.regex['login'])))

		if not login_autogenerated and \
			len(login) > UsersController.configuration.users.login_maxlenght:
			raise exceptions.LicornRuntimeError(
				"Login %s too long (currently %d characters," \
				" but must be shorter or equal than %d)." % (
					login, len(login),
					UsersController.configuration.users.login_maxlenght) )

		# then, verify that other arguments match the system constraints.
		if not hlstr.cregex['description'].match(gecos):
			if gecos_autogenerated:
				raise exceptions.LicornRuntimeError(
					"Can't build a valid GECOS (%s) with the" \
					" firstname/lastname (%s/%s) or login you provided." % (
						gecos, firstname, lastname) )
			else:
				raise exceptions.BadArgumentError(
					logging.SYSU_MALFORMED_GECOS % (
						gecos, styles.stylize(styles.ST_REGEX,
						hlstr.regex['description']) ) )

		if primary_gid:
			# this will raise a DoesntExistsError() if wrong, don't need
			# to check if it exists twice.
			pg_gid = UsersController.groups.name_to_gid(primary_gid)

		if skel and skel not in UsersController.configuration.users.skels:
			raise exceptions.BadArgumentError(
				"The skel you specified doesn't exist on this system." \
				" Valid skels are: %s." % \
					UsersController.configuration.users.skels)

		tmp_user_dict = {}

		# Verify prior existence of user account
		if login in UsersController.login_cache:
			if (system and UsersController.is_system_login(login)) \
				or (not system and UsersController.is_standard_login(login)):
				raise exceptions.AlreadyExistsException(
					"User account %s already exists !" % login)
			else:
				raise exceptions.AlreadyExistsError(
					'''A user account %s already exists but has not the same '''
					'''type. Please choose another login for your user.'''
					% styles.stylize(styles.ST_NAME, login))

		# Due to a bug of adduser/deluser perl script, we must check that there
		# is no group which the same name than the login. There should not
		# already be a system group with the same name (we are just going to
		# create it...), but it could be a system inconsistency, so go on to
		# recover from it.
		#
		# {add,del}user logic is:
		#	- a system account must always have a system group as primary group,
		# 		else if will be «nogroup» if not specified.
		#   - when deleting a system account, a corresponding system group will
		#		be deleted if existing.
		#	- no restrictions for a standard account
		#
		# the bug is that in case 2, deluser will delete the group even if this
		#  is a standard group (which is bad). This could happen with:
		#	addgroup toto
		#	adduser --system toto --ingroup root
		#	deluser --system toto
		#	(group toto is deleted but it shouldn't be ! And it is deleted
		#	without *any* message !!)
		#
		if login in UsersController.groups.name_cache and not force:
			raise exceptions.UpstreamBugException, \
				"A group named `%s' exists on the system," \
				" this could eventually conflict in Debian/Ubuntu system" \
				" tools. Please choose another user's login, or use " \
				"--force argument if you really want to add this user " \
				"on the system." % login

		# generate an UID if None given, else verify it matches constraints.
		if desired_uid is None:
			if system:
				uid = pyutils.next_free(self.users.keys(),
					self.configuration.users.system_uid_min,
					self.configuration.users.system_uid_max)
			else:
				uid = pyutils.next_free(self.users.keys(),
					self.configuration.users.uid_min,
					self.configuration.users.uid_max)

			logging.progress('Autogenerated UID for user %s: %s.' % (
				styles.stylize(styles.ST_LOGIN, login),
				styles.stylize(styles.ST_SECRET, uid)))
		else:
			if (system and UsersController.is_system_uid(desired_uid)) \
				or (not system and UsersController.is_standard_uid(
					desired_uid)):
					uid = desired_uid
			else:
				raise exceptions.BadArgumentError('''UID out of range '''
					'''for the kind of user account you specified. System '''
					'''UID must be between %d and %d, standard UID must be '''
					'''between %d and %d.''' % (
						self.configuration.users.system_uid_min,
						self.configuration.users.system_uid_max,
						self.configuration.users.uid_min,
						self.configuration.users.uid_max)
					)

		# autogenerate password if not given.
		if password is None:
			# TODO: call cracklib2 to verify passwd strenght.
			password = hlstr.generate_password(
				UsersController.configuration.mAutoPasswdSize)
			logging.notice(logging.SYSU_AUTOGEN_PASSWD % (
				styles.stylize(styles.ST_LOGIN, login),
				styles.stylize(styles.ST_SECRET, password)))

		groups_to_add_user_to = []

		skel_to_apply = "/etc/skel"
		# 3 cases:
		if profile is not None:
			# Apply the profile after having created the home dir.
			try:
				tmp_user_dict['loginShell'] = \
					UsersController.profiles.profiles[profile]['profileShell']
				tmp_user_dict['gidNumber'] = \
					UsersController.groups.name_to_gid(
					UsersController.profiles.profiles[profile]['groupName'])
				# fix #58.
				tmp_user_dict['homeDirectory'] = ("%s/%s" % (
					UsersController.configuration.users.base_path, login))

				if UsersController.profiles.profiles[profile]['memberGid'] != []:
					groups_to_add_user_to = \
						UsersController.profiles.profiles[profile]['memberGid']

					# don't directly add the user to the groups. prepare the
					# groups to use the Licorn API later, to create the groups
					# symlinks while adding user to them.
					#
					# useradd_options.append("-G " + ",".join(
					# UsersController.profiles.profiles[profile]['groups']))

				if skel is None:
					skel_to_apply = \
						UsersController.profiles.profiles[profile]['profileSkel']
			except KeyError, e:
				# fix #292
				raise exceptions.DoesntExistsError(
					"The profile %s doesn't exist on this system (was: %s) !" \
						% (profile, e))
		elif primary_gid is not None:
			tmp_user_dict['gidNumber']     = pg_gid
			tmp_user_dict['loginShell']    = \
				UsersController.configuration.users.default_shell
			tmp_user_dict['homeDirectory'] = home if home is not None \
				and system else "%s/%s" % (
					UsersController.configuration.users.base_path, login)

			# FIXME: use is_valid_skel() ?
			if skel is None and \
				os.path.isdir(
					UsersController.groups.groups[pg_gid]['groupSkel']):
				skel_to_apply = \
					UsersController.groups.groups[pg_gid]['groupSkel']
		else:
			tmp_user_dict['gidNumber'] = \
				UsersController.configuration.users.default_gid
			tmp_user_dict['loginShell'] = \
				UsersController.configuration.users.default_shell
			tmp_user_dict['homeDirectory'] = home if home is not None \
				and system else "%s/%s" % (
					UsersController.configuration.users.base_path, login)
			# if skel is None, system default skel will be applied

		# FIXME: is this necessary here ? not done before ?
		if skel is not None:
			skel_to_apply = skel

		tmp_user_dict['userPassword'] = \
			UsersController.backends['prefered'].compute_password(password)

		tmp_user_dict['shadowLastChange'] = str(int(time()/86400))

		# create home directory and apply skel
		if not os.path.exists(tmp_user_dict['homeDirectory']):
			import shutil
			# copytree automatically creates tmp_user_dict['homeDirectory']
			shutil.copytree(skel_to_apply, tmp_user_dict['homeDirectory'])
		#
		# else: the home directory already exists, we don't overwrite it
		#

		tmp_user_dict['uidNumber']      = uid
		tmp_user_dict['gecos']          = gecos
		tmp_user_dict['login']          = login
		# prepare the groups cache.
		tmp_user_dict['groups']         = set()
		tmp_user_dict['shadowInactive'] = ''
		tmp_user_dict['shadowWarning']  = 7
		tmp_user_dict['shadowExpire']   = ''
		tmp_user_dict['shadowMin']      = 0
		tmp_user_dict['shadowMax']      = 99999
		tmp_user_dict['shadowFlag']     = ''
		tmp_user_dict['backend']        = \
			UsersController.backends['prefered'].name

		# Add user in internal list and in the cache
		UsersController.users[uid]         = tmp_user_dict
		UsersController.login_cache[login] = uid

		#
		# we can't skip the WriteConf(), because this would break Samba stuff,
		# and AddUsersInGroup stuff too:
		# Samba needs Unix account to be present in /etc/* before creating the
		# Samba account. We thus can't delay the WriteConf() call, even if we
		# are in batch / import users mode. This is roughly the same with group
		# Additions: the user must be present, prior to additions.
		#
		# DO NOT UNCOMMENT -- if not batch:
		UsersController.users[uid]['action'] = 'create'
		UsersController.backends[
			UsersController.users[uid]['backend']
			].save_user(uid)

		# Samba: add Samba user account.
		# TODO: put this into a module.
		try:
			sys.stderr.write(process.execute(['smbpasswd', '-a', login, '-s'],
				'%s\n%s\n' % (password, password))[1])
		except (IOError, OSError), e:
			if e.errno not in (2, 32):
				raise e

		if groups_to_add_user_to != []:
			for group in groups_to_add_user_to:
				UsersController.groups.AddUsersInGroup(group, [login])

		# Set quota
		if profile is not None:
			try:
				pass
				#os.popen2( [ 'quotatool', '-u', str(uid), '-b', UsersController.configuration.defaults.quota_device, '-l' '%sMB' % UsersController.profiles.profiles[profile]['quota'] ] )[1].read()
				#logging.warning("quotas are disabled !")
				# XXX: Quotatool can return 2 without apparent reason
				# (the quota is etablished) !
			except exceptions.LicornException, e:
				logging.warning( "ROLLBACK create user because '%s'." % str(e))
				self.DeleteUser(login, True)
				return (False, False, False)

		self.CheckUsers([ login ], batch = True)

		logging.info(logging.SYSU_CREATED_USER % (
			styles.stylize(styles.ST_LOGIN, login),
			styles.stylize(styles.ST_UGID, uid)))

		ltrace('users', '< AddUser()')
		return (uid, login, password)
	def DeleteUser(self, login=None, no_archive=False, uid=None, batch=False):
		""" Delete a user """
		if login is None and uid is None:
			raise exceptions.BadArgumentError(logging.SYSU_SPECIFY_LGN_OR_UID)

		if uid is None:
			uid = UsersController.login_to_uid(login)

		elif login is None:
			# «login» is needed for deluser system command.
			login = UsersController.users[uid]["login"]

		ltrace('users', "| DeleteUser() %s(%s), groups %s." % (
			login, str(uid), UsersController.users[uid]['groups']) )

		# Delete user from his groups
		# '[:]' to fix #14, see
		# http://docs.python.org/tut/node6.html#SECTION006200000000000000000
		for group in UsersController.users[uid]['groups'].copy():
			UsersController.groups.RemoveUsersFromGroup(group, [ login ],
				batch=True)

		try:
			# samba stuff
			sys.stderr.write(process.execute(['smbpasswd', '-x', login])[1])
		except (IOError, OSError), e:
			if e.errno not in (2, 32):
				raise e

		# keep the homedir path, to backup it if requested.
		homedir = UsersController.users[uid]["homeDirectory"]

		# keep the backend, to notice the deletion
		backend = UsersController.users[uid]['backend']

		# Delete user from users list
		del(UsersController.login_cache[login])
		del(UsersController.users[uid])
		logging.info(logging.SYSU_DELETED_USER % \
			styles.stylize(styles.ST_LOGIN, login))

		# TODO: try/except and reload the user if unable to delete it
		# delete the user in the backend after deleting it locally, else
		# Unix backend will not know what to delete (this is quite a hack).
		UsersController.backends[backend].delete_user(login)

		# user is now wiped out from the system.
		# Last thing to do is to delete or archive the HOME dir.

		if no_archive:
			import shutil
			try:
				shutil.rmtree(homedir)
			except OSError, e:
				logging.warning("Problem deleting home dir %s (was: %s)" % (
					styles.stylize(styles.ST_PATH, homedir), e))

		else:
			UsersController.configuration.check_base_dirs(minimal = True,
				batch = True)
			user_archive_dir = "%s/%s.deleted.%s" % (
				UsersController.configuration.home_archive_dir,
				login, strftime("%Y%m%d-%H%M%S", gmtime()))
			try:
				os.rename(homedir, user_archive_dir)
				logging.info(logging.SYSU_ARCHIVED_USER % (homedir,
					styles.stylize(styles.ST_PATH, user_archive_dir)))
			except OSError, e:
				if e.errno == 2:
					logging.warning(
						"Home dir %s doesn't exist, thus not archived." % \
							styles.stylize(styles.ST_PATH, homedir))
				else:
					raise e

	def ChangeUserPassword(self, login, password = None, display = False):
		""" Change the password of a user
		"""
		if login is None:
			raise exceptions.BadArgumentError(logging.SYSU_SPECIFY_LOGIN)
		if password is None:
			password = hlstr.generate_password(
				UsersController.configuration.mAutoPasswdSize)
		elif password == "":
			logging.warning(logging.SYSU_SET_EMPTY_PASSWD % \
				styles.stylize(styles.ST_LOGIN, login))
			#
			# SECURITY concern: if password is empty, shouldn't we
			# automatically remove user from remotessh ?
			#

		uid = UsersController.login_to_uid(login)

		UsersController.users[uid]['userPassword'] = \
		UsersController.backends[
			UsersController.users[uid]['backend']
			].compute_password(password)

		# 3600*24 to have the number of days since epoch (fixes #57).
		UsersController.users[uid]['shadowLastChange'] = str(
			int(time()/86400) )

		UsersController.users[uid]['action'] = 'update'
		UsersController.backends[
			UsersController.users[uid]['backend']
			].save_user(uid)

		if display:
			logging.notice("Set user %s's password to %s." % (
				styles.stylize(styles.ST_NAME, login),
				styles.stylize(styles.ST_IMPORTANT, password)))
		else:
			logging.info('Changed password for user %s.' % \
				styles.stylize(styles.ST_NAME, login))

		try:
			# samba stuff
			sys.stderr.write(process.execute(['smbpasswd', login, '-s'],
				"%s\n%s\n" % (password, password))[1])
		except (IOError, OSError), e:
			if e.errno != 32:
				raise e
	def ChangeUserGecos(self, login, gecos = ""):
		""" Change the gecos of a user
		"""
		if login is None:
			raise exceptions.BadArgumentError(logging.SYSU_SPECIFY_LOGIN)

		if not hlstr.cregex['description'].match(gecos):
			raise exceptions.BadArgumentError(logging.SYSU_MALFORMED_GECOS % (
				gecos,
				styles.stylize(styles.ST_REGEX, hlstr.regex['description'])))

		uid = UsersController.login_to_uid(login)
		UsersController.users[uid]['gecos'] = gecos

		UsersController.users[uid]['action'] = 'update'
		UsersController.backends[
			UsersController.users[uid]['backend']
			].save_user(uid)
	def ChangeUserShell(self, login, shell = ""):
		""" Change the shell of a user. """
		if login is None:
			raise exceptions.BadArgumentError(logging.SYSU_SPECIFY_LOGIN)

		uid = UsersController.login_to_uid(login)

		if shell not in UsersController.configuration.users.shells:
			raise exceptions.LicornRuntimeError(
				"Invalid shell ! valid shells are %s." % \
					UsersController.configuration.users.shells)

		UsersController.users[uid]['loginShell'] = shell

		UsersController.users[uid]['action'] = 'update'
		UsersController.backends[
			UsersController.users[uid]['backend']
			].save_user(uid)

	def LockAccount(self, login, lock = True):
		"""(Un)Lock a user account."""
		if login is None:
			raise exceptions.BadArgumentError(logging.SYSU_SPECIFY_LOGIN)

		# update internal data structures.
		uid = UsersController.login_to_uid(login)

		if lock:
			if UsersController.users[uid]['locked']:
				logging.info('account %s already locked.' %
					styles.stylize(styles.ST_NAME, login))
			else:
				UsersController.users[uid]['userPassword'] = '!' + \
					UsersController.users[uid]['userPassword']
				logging.info('Locked user account %s.' % \
					styles.stylize(styles.ST_LOGIN, login))
		else:
			if UsersController.users[uid]['locked']:
				UsersController.users[uid]['userPassword'] = \
					UsersController.users[uid]['userPassword'][1:]
				logging.info('Unlocked user account %s.' % \
					styles.stylize(styles.ST_LOGIN, login))
			else:
				logging.info('account %s already unlocked.' %
					styles.stylize(styles.ST_NAME, login))

		UsersController.users[uid]['locked'] = lock

		UsersController.users[uid]['action'] = 'update'
		UsersController.backends[
			UsersController.users[uid]['backend']
			].save_user(uid)

	def ApplyUserSkel(self, login, skel):
		""" Apply a skel on a user """
		if login is None:
			raise exceptions.BadArgumentError(logging.SYSU_SPECIFY_LOGIN)
		if skel is None:
			raise exceptions.BadArgumentError, "You must specify a skel"
		if not os.path.isabs(skel) or not os.path.isdir(skel):
			raise exceptions.AbsolutePathError(skel)

		uid = UsersController.login_to_uid(login)
		# not force option with shutil.copytree
		process.syscmd("cp -r %s/* %s/.??* %s" % (skel, skel,
			UsersController.users[uid]['homeDirectory']) )

		# set permission (because root)
		for fileordir in os.listdir(skel):
			try:
				# FIXME: do this with os.chmod()... and map() it.
				process.syscmd("chown -R %s %s/%s" % (
					UsersController.users[uid]['login'],
					UsersController.users[uid]['homeDirectory'], fileordir) )
			except Exception, e:
				logging.warning(str(e))

	def ExportCLI( self, long_output = False):
		""" Export the user accounts list to human readable («passwd») form.
		"""
		if self.filter_applied:
			uids = self.filtered_users
		else:
			uids = UsersController.users.keys()

		uids.sort()

		def build_cli_output_user_data(uid, users = UsersController.users):
			account = [	users[uid]['login'],
						"x",
						str(uid),
						str(users[uid]['gidNumber']),
						users[uid]['gecos'],
						users[uid]['homeDirectory'],
						users[uid]['loginShell'],
						]
			if long_output:
				account.append(','.join(UsersController.users[uid]['groups']))
				account.append('[%s]' % styles.stylize(styles.ST_LINK, users[uid]['backend']))

			return ':'.join(account)

		data = '\n'.join(map(build_cli_output_user_data, uids)) + '\n'

		return data
	def ExportCSV( self, long_output = False):
		"""Export the user accounts list to CSV."""

		if self.filter_applied:
			uids = self.filtered_users
		else:
			uids = UsersController.users.keys()

		uids.sort()

		def build_csv_output_licorn(uid):
			return ';'.join(
				[
					UsersController.users[uid]['gecos'],
					UsersController.users[uid]['login'],
					str(UsersController.users[uid]['gidNumber']),
					','.join(UsersController.users[uid]['groups']),
					UsersController.users[uid]['backend']
				]
				)

		data = '\n'.join(map(build_csv_output_licorn, uids)) +'\n'

		return data
	def ExportXML( self, long_output = False):
		""" Export the user accounts list to XML. """

		if self.filter_applied:
			uids = self.filtered_users
		else:
			uids = UsersController.users.keys()

		uids.sort()

		def build_xml_output_user_data(uid):
			data = '''
	<user>
		<login>%s</login>
		<uid>%d</uid>
		<gid>%d</gid>
		<gecos>%s</gecos>
		<homeDirectory>%s</homeDirectory>
		<loginShell>%s</loginShell>\n''' % (
					UsersController.users[uid]['login'],
					uid,
					UsersController.users[uid]['gidNumber'],
					UsersController.users[uid]['gecos'],
					UsersController.users[uid]['homeDirectory'],
					UsersController.users[uid]['loginShell']
				)
			if long_output:
				data += '''		<groups>%s</groups>
		<backend>%s</backend>\n''' % (
					','.join(UsersController.users[uid]['groups']),
					UsersController.users[uid]['backend'])

			return data + "	</user>"

		data = "<?xml version='1.0' encoding=\"UTF-8\"?>\n<users-list>\n" \
			+ '\n'.join(map(build_xml_output_user_data, uids)) \
			+ "\n</users-list>\n"

		return data

	def CheckUsers(self, users_to_check = [], minimal = True, batch = False,
		auto_answer = None):
		"""Check user accounts and account data consistency."""

		if users_to_check == []:
			users_to_check = UsersController.login_cache.keys()

		# dependancy: base dirs must be OK before checking users's homes.
		UsersController.configuration.check_base_dirs(minimal, batch, auto_answer)

		def check_user(user, minimal = minimal, batch = batch,
			auto_answer = auto_answer):

			all_went_ok = True
			uid         = UsersController.login_to_uid(user)

			if UsersController.is_system_uid(uid):

				logging.progress("Checking system account %s..." % \
					styles.stylize(styles.ST_NAME, user))

				if os.path.exists(self.users[uid]['homeDirectory']):
					home_dir_info = [ {
						'path'       : self.users[uid]['homeDirectory'],
						'user'       : user,
						'group'      : self.groups.groups[
							self.users[uid]['gidNumber']]['name'],
						'mode'       : 00700,
						'content_mode': 00600
						} ]

					all_went_ok &= fsapi.check_dirs_and_contents_perms_and_acls(
						home_dir_info, batch, auto_answer,
						UsersController.groups, self)
			else:
				logging.progress("Checking user %s..." % \
					styles.stylize(styles.ST_LOGIN, user))

				gid       = self.users[uid]['gidNumber']
				group     = self.groups.groups[gid]['name']
				user_home = self.users[uid]['homeDirectory']

				logging.progress("Checking user account %s..." % \
					styles.stylize(styles.ST_NAME, user))

				acl_base                  = "u::rwx,g::---,o:---"
				file_acl_base             = "u::rw@UE,g::---,o:---"
				acl_mask                  = "m:rwx"
				acl_restrictive_mask      = "m:r-x"
				file_acl_mask             = "m:rw@GE"
				file_acl_restrictive_mask = "m:rw@GE"

				#
				# first build a list of dirs (located in ~/) to be excluded
				# from the home dir check, because they must have restrictive
				# permission (for confidentiality reasons) and don't need any
				# ACLs. In the same time (for space optimization reasons),
				# append them to special_dirs[] (which will be checked *after*
				# home dir).
				#
				home_exclude_list = [ '.ssh', '.gnupg', '.gnome2_private',
										'.gvfs' ]
				special_dirs      = []

				special_dirs.extend([ {
					'path'       : "%s/%s" % (user_home, dir),
					'user'       : user,
					'group'      : group,
					'mode'       : 00700,
					'content_mode': 00600
					} for dir in home_exclude_list if \
						os.path.exists('%s/%s' % (user_home, dir)) ])

				if os.path.exists('%s/public_html' % user_home):

					home_exclude_list.append('public_html')

					special_dirs.append ( {
						'path'      : "%s/public_html" % user_home,
						'user'      : user,
						'group'     : 'acl',
						'access_acl': "%s,g:%s:r-x,g:www-data:r-x,%s" % (
							acl_base,
							UsersController.configuration.defaults.admin_group,
							acl_restrictive_mask),
						'default_acl': "%s,g:%s:rwx,g:www-data:r-x,%s" % (
							acl_base,
							UsersController.configuration.defaults.admin_group,
							acl_mask),
						'content_acl': "%s,g:%s:rw-,g:www-data:r--,%s" % (
							file_acl_base,
							UsersController.configuration.defaults.admin_group,
							file_acl_mask),
						} )

				#
				# if we are in charge of building the user's mailbox, do it and
				# check it. This is particularly important for ~/Maildir
				# because courier-imap will hog CPU time if the Maildir doesn't
				# exist prior to the daemon launch...
				if UsersController.configuration.users.mailbox_auto_create and \
					UsersController.configuration.users.mailbox_type == \
					UsersController.configuration.MAIL_TYPE_HOME_MAILDIR:

					maildir_base = '%s/%s' % (user_home,
						UsersController.configuration.users.mailbox)

					# WARNING: "configuration.users.mailbox" is assumed to have
					# a trailing slash if it is a Maildir, because that's the
					# way it is in postfix/main.cf and other MTA configuration.
					# Without the "/", the mailbox is assumed to be an mbox or
					# an MH. So we use [:-1] to skip the trailing "/", else
					# fsapi.minifind() won't match the dir name properly in the
					# exclusion list.

					home_exclude_list.append(
						UsersController.configuration.users.mailbox[:-1])

					for dir in ( maildir_base, '%stmp' % maildir_base,
						'%scur' % maildir_base,'%snew' % maildir_base ):
						special_dirs.append ( {
							'path'       : dir,
							'user'       : user,
							'group'      : group,
							'mode'       : 00700,
							'content_mode': 00600
						} )


				# this will be handled in another manner later in this function.
				# .procmailrc: fix #589
				home_exclude_file_list = [ ".dmrc", ".procmailrc" ]
				for file in home_exclude_file_list:
					if os.path.exists('%s/%s' % (user_home, file)):
						home_exclude_list.append(file)
						all_went_ok &= fsapi.check_posix_ugid_and_perms(
							'%s/%s' % (user_home, file), uid, gid, 00600,
								batch, auto_answer, self.groups, self)

				# Now that the exclusion list is complete, we can check the home
				# dir. For that we need a dir_info with the correct information.

				home_dir_info = {
					'path'      : UsersController.users[uid]['homeDirectory'],
					'user'      : user,
					'group'     : 'acl',
					'access_acl': "%s,g:%s:r-x,g:www-data:--x,%s" % (
						acl_base,
						UsersController.configuration.defaults.admin_group,
						acl_restrictive_mask),
					'default_acl': "%s,g:%s:rwx,%s" % (acl_base,
						UsersController.configuration.defaults.admin_group,
						acl_mask),
					'content_acl': "%s,g:%s:rw@GE,%s" % (file_acl_base,
						UsersController.configuration.defaults.admin_group,
						file_acl_mask),
					'exclude'   : home_exclude_list
					}

				if not batch:
					logging.progress("Checking user home dir %s contents,"
						" this can take a while..." % styles.stylize(
						styles.ST_PATH, user_home))

				try:
					all_went_ok &= fsapi.check_dirs_and_contents_perms_and_acls(
						[ home_dir_info ], batch, auto_answer,
						UsersController.groups, self)
				except exceptions.LicornCheckError:
					logging.warning("User home dir %s is missing,"
						" please repair this first." % styles.stylize(
						styles.ST_PATH, user_home))
					return False

				if special_dirs != []:
					all_went_ok &= fsapi.check_dirs_and_contents_perms_and_acls(
						special_dirs, batch, auto_answer,
						UsersController.groups, self)

				if not minimal:
					logging.warning(
						"Extended checks are not yet implemented for users.")
					# TODO:
					#	logging.progress("Checking symlinks in user's home dir, this can take a while..." % styles.stylize(styles.ST_NAME, user))
					#	if not self.CleanUserHome(login, batch, auto_answer):
					#		all_went_ok = False

					# TODO: tous les groupes de cet utilisateur existent et
					# sont OK (CheckGroups recursif) WARNING: Forcer
					# minimal = True pour éviter les checks récursifs avec
					# CheckGroups().

				return all_went_ok

		if reduce(pyutils.keep_false, map(check_user, users_to_check)) is False:
			# NOTICE: don't test just "if reduce():", the result could be None
			# and everything is OK when None...
			raise exceptions.LicornCheckError(
				"Some user(s) check(s) didn't pass, or weren't corrected.")

	@staticmethod
	def user_exists(uid = None, login = None):
		if uid:
			return UsersController.users.has_key(uid)
		if login:
			return UsersController.login_cache.has_key(login)

		raise exceptions.BadArgumentError(
			"You must specify an UID or a login to test existence of.")

	@staticmethod
	def check_password(login, password):
		crypted_passwd1 = UsersController.users[
			UsersController.login_cache[login]]['userPassword']
		crypted_passwd2 = UsersController.backends[
			UsersController.users[UsersController.login_cache[login]
				]['backend']].compute_password(password, crypted_passwd1)
		ltrace('users', 'comparing 2 crypted passwords:\n%s\n%s' % (
			crypted_passwd1, crypted_passwd2))
		return (crypted_passwd1 == crypted_passwd2)

	@staticmethod
	def login_to_uid(login):
		""" Return the uid of the user 'login'
		"""
		try:
			# use the cache, Luke !
			return UsersController.login_cache[login]
		except KeyError:
			try:
				int(login)
				logging.warning("You passed an uid to login_to_uid():"
					" %d (guess its login is « %s » )." % (
						login, UsersController.users[login]['login']))
			except ValueError:
				pass
			raise exceptions.DoesntExistsException(
				logging.SYSU_USER_DOESNT_EXIST % login)

	@staticmethod
	def is_system_uid(uid):
		""" Return true if uid is system."""
		return uid < UsersController.configuration.users.uid_min or \
			uid > UsersController.configuration.users.uid_max

	@staticmethod
	def is_standard_uid(uid):
		""" Return true if gid is standard (not system). """
		return uid >= UsersController.configuration.users.uid_min \
			and uid <= UsersController.configuration.users.uid_max
	@staticmethod
	def is_system_login(login):
		""" return true if login is system. """
		try:
			return UsersController.is_system_uid(
				UsersController.login_cache[login])
		except KeyError:
			raise exceptions.DoesntExistsException(
				logging.SYSU_USER_DOESNT_EXIST % login)
	@staticmethod
	def is_standard_login(login):
		""" Return true if login is standard (not system). """
		try:
			return UsersController.is_standard_uid(
				UsersController.login_cache[login])
		except KeyError:
			raise exceptions.DoesntExistsException(
				logging.SYSU_USER_DOESNT_EXIST % login)
	@staticmethod
	def make_login(lastname = "", firstname = "", inputlogin = ""):
		""" Make a valid login from  user's firstname and lastname."""

		if inputlogin == "":
			login = hlstr.validate_name(str(firstname + '.' + lastname),
				maxlenght = UsersController.configuration.users.login_maxlenght)
		else:
			# use provided login and verify it.
			login = hlstr.validate_name(str(inputlogin),
				maxlenght = UsersController.configuration.users.login_maxlenght)

		if not hlstr.cregex['login'].match(login):
			raise exceptions.BadArgumentError(
				"Can't build a valid login (got %s, which doesn't verify %s)"
				" with the firstname/lastname you provided (%s %s)." % (
					login, hlstr.regex['login'], firstname, lastname) )

		return login

		# TODO: verify if the login doesn't already exist.
		#while potential in UsersController.users:

	@staticmethod
	def primary_gid(login = None, uid = None):
		if login:
			return UsersController.users[
				UsersController.login_cache[login]]['primary_gid']
		if uid:
			return UsersController.users[uid]['primary_gid']

		raise exceptions.BadArgumentError(
			"You must specify an UID or a login to get primary_gid of.")


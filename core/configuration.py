	# -*- coding: utf-8 -*-
"""
Licorn core - http://dev.licorn.org/documentation/core

configuration - Unified Configuration API for an entire linux server system

Copyright (C) 2005-2010 Olivier Cortès <olive@deep-ocean.net>,
Partial Copyright (C) 2005 Régis Cobrun <reg53fr@yahoo.fr>
Licensed under the terms of the GNU GPL version 2
"""

import sys, os, re
import Pyro.core
from gettext import gettext as _

from licorn.foundations           import logging, exceptions, fsapi
from licorn.foundations           import styles, readers
from licorn.foundations.constants import distros, servers, mailboxes
from licorn.foundations.ltrace    import ltrace
from licorn.foundations.objects   import LicornConfigObject, Singleton, \
	FileLock
from licorn.core.privileges       import PrivilegesWhiteList

class LicornConfiguration(Singleton, Pyro.core.ObjBase):
	""" Contains all the underlying system configuration as attributes.
		Defines some methods for modifying the configuration.
	"""

	# bypass multiple init and del calls (we are a singleton)
	init_ok     = False
	del_ok      = False

	def __init__(self, minimal=False):
		""" Gather underlying system configuration and load it for licorn.* """

		if LicornConfiguration.init_ok:
			return

		ltrace('configuration', '> __init__(minimal=%s)' % minimal)

		Pyro.core.ObjBase.__init__(self)

		if sys.getdefaultencoding() == "ascii":
			reload(sys)
			sys.setdefaultencoding("utf-8")

		self.app_name = 'Licorn'
		self.controllers = LicornConfigObject()

		self.mta         = None
		self.ssh         = None

		# THIS install_path is used in keywords / keywords gui, not elsewhere.
		# it is a hack to be able to test guis when Licorn is not installed.
		# → this is for developers only.
		self.install_path = os.getenv("LICORN_ROOT", "/usr")
		if self.install_path == '.':
			self.share_data_dir = '.'
		else:
			self.share_data_dir = "%s/share/licorn" % self.install_path

		try:
			import tempfile
			self.tmp_dir = tempfile.mkdtemp()

			#
			# WARNING: beside this point, order of method is VERY important,
			# their contents depend on each other.
			#

			self.VerifyPythonMods()

			self.SetBaseDirsAndFiles()
			self.FindUserDir()

			if not minimal:

				self.LoadManagersConfiguration()
				self.set_acl_defaults()

				self.FindDistro()

				self.LoadShells()
				self.LoadSkels()
				self.detect_services()

			# this has to be done LAST, in order to eventually override any
			# other configuration directive (eventually coming from
			# Ubuntu/Debian, too).
			self.LoadBaseConfiguration()
			self.SetMissingMandatoryDefauts()

			if not minimal:
				self.load_nsswitch()
				# TODO: monitor configuration files from a thread !

				self.load_backends()
				self.load_plugins()
				self.connect_plugins()

		except exceptions.LicornException, e:
			raise exceptions.BadConfigurationError(
				'''Configuration initialization failed:\n\t%s''' % e)

		LicornConfiguration.init_ok = True
		ltrace('configuration', '< __init__()')

	#
	# make configuration be usable as a context manager.
	#
	def __enter__(self):
		pass
	def __exit__(self, type, value, tb):
		self.CleanUp()
	def set_controller(self, name, controller):
		setattr(self.controllers, name, controller)
	def CleanUp(self, listener=None):
		"""This is a sort of destructor. Clean-up before being deleted…"""

		if LicornConfiguration.del_ok:
			return

		ltrace('configuration', '> CleanUp(%s)' % LicornConfiguration.del_ok)

		try:
			import shutil
			# this is safe because tmp_dir was created with tempfile.mkdtemp()
			shutil.rmtree(self.tmp_dir)
		except (OSError, IOError), e:
			if e.errno == 2:
				logging.warning2('''Temporary directory %s has vanished during '''
					'''run, or already been wiped by another process.''' %
					self.tmp_dir, listener=listener)
			else:
				raise e

		LicornConfiguration.del_ok = True
		ltrace('configuration', '< CleanUp()')
	def VerifyPythonMods(self):
		""" verify all required python modules are present on the system. """

		ltrace('configuration', '> VerifyPythonMods().')

		mods = (
			('posix1e', 'python-pylibacl'),
			('xattr',   'python-xattr or python-pyxattr'),
			('gamin',   'python-gamin')
			)

		for mod, package in mods:
			try:
				exec('import %s' % mod)
			except:
				logging.error('You miss %s python module (package %s).' % (
					mod, package))

		ltrace('configuration', '< VerifyPythonMods().')
	def SetBaseDirsAndFiles(self):
		""" Find and create temporary, data and working directories."""

		ltrace('configuration', '> SetBaseDirsAndFiles().')


		self.config_dir              = "/etc/licorn"
		self.main_config_file        = self.config_dir + "/licorn.conf"
		self.backup_config_file      = self.config_dir + "/backup.conf"

		# system profiles, compatible with gnome-system-tools
		self.profiles_config_file    = self.config_dir + "/profiles.xml"

		self.privileges_whitelist_data_file = (
			self.config_dir + "/privileges-whitelist.conf")
		self.keywords_data_file             = self.config_dir + "/keywords.conf"

		# extensions to /etc/group
		self.extendedgroup_data_file = self.config_dir + "/groups"

		self.SetDefaultNamesAndPaths()

		self.home_backup_dir         = (
			"%s/backup" % self.defaults.home_base_path)
		self.home_archive_dir        = (
			"%s/archives" % self.defaults.home_base_path)

		# TODO: is this to be done by package maintainers or me ?
		self.CreateConfigurationDir()

		ltrace('configuration', '< SetBaseDirsAndFiles().')

	def FindUserDir(self):
		""" if ~/ is writable, use it as user_dir to store some data, else
			use a tmp_dir."""
		try:
			home = os.environ["HOME"]
		except KeyError:
			home = None

		if home and os.path.exists(home):

			try:
				# if our home exists and we can write in it,
				# assume we are a standard user.
				fakefd = open(home + "/.licorn.fakefile", "w")
				fakefd.close()
				os.unlink(home + "/.licorn.fakefile")
				self.user_dir			= home + "/.licorn"
				self.user_config_file	= self.user_dir + "/config"

			except (OSError, IOError):
				# we are «apache» or another special user (aesd…), we don't
				# have a home, but need a dir to put lock-files in.
				self.user_dir			= self.tmp_dir
				self.user_config_file	= None
		else:
			# we are «apache» or another special user (aesd…), we don't
			# have a home, but need a dir to put lock-files in.
			self.user_dir			= self.tmp_dir
			self.user_config_file	= None

		self.user_data_dir		= self.user_dir + "/data"

		if not os.path.exists(self.user_dir):
			try:
				os.makedirs(self.user_data_dir)
				import stat
				os.chmod(self.user_dir,
					stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR )
				logging.info("Automatically created %s." % \
					styles.stylize(styles.ST_PATH, self.user_dir + "[/data]"))
			except OSError, e:
				raise exceptions.LicornRuntimeError(
					'''Can't create / chmod %s[/data]:\n\t%s''' % (
						self.user_dir, e))
	def _load_configuration(self, conf):
		""" Build the licorn configuration object from a dict. """

		ltrace('configuration', '| _load_configuration(%s)' % conf)

		for key in conf.keys():
			subkeys = key.split('.')
			if len(subkeys) > 1:
				curobj = self
				level  = 1
				for subkey in subkeys[:-1]:
					if not hasattr(curobj, subkey):
						setattr(curobj, subkey, LicornConfigObject(level=level))
					#down one level.
					curobj = getattr(curobj, subkey)
					level += 1
				if not hasattr(curobj, subkeys[-1]):
					setattr(curobj, subkeys[-1], conf[key])
			else:
				if not hasattr(self, key):
					setattr(self, key,conf[key])
	def noop(self):
		""" No-op function, called when connecting pyro, to check if link
		is OK betwwen the server and the client. """
		ltrace('configuration', '| noop(True)')
		return True
	def SetMissingMandatoryDefauts(self):
		""" The defaults set here are expected to exist
			by other parts of the programs. """

		ltrace('configuration', '| SetMissingMandatoryDefaults()')

		mandatory_dict = {
			'licornd.wmi.enabled': True,
			'licornd.wmi.listen_address': 'localhost',
			'licornd.role': 'server',
			'licornd.pyro.max_retries': 3
			}

		self._load_configuration(mandatory_dict)
	def LoadBaseConfiguration(self):
		"""Load main configuration file, and set mandatory defaults
			if it doesn't exist."""

		ltrace('configuration', '> LoadBaseConfiguration()')

		try:
			self._load_configuration(readers.shell_conf_load_dict(
				self.main_config_file,
				convert='full'))
		except IOError, e:
			if e.errno != 2:
				# errno == 2 is "no such file or directory" -> don't worry if
				# main config file isn't here, this is not required.
				raise e

		ltrace('configuration', '< LoadBaseConfiguration()')
	def load_nsswitch(self):
		""" Load the NS switch file. """

		self.nsswitch = (
			readers.simple_conf_load_dict_lists('/etc/nsswitch.conf'))
	def save_nsswitch(self):
		""" write the nsswitch.conf file. This method is meant to be called by
		a backend which has modified. """

		ltrace('configuration', '| save_nsswitch()')

		nss_data = ''

		for key in self.nsswitch:
			nss_data += '%s:%s%s\n' % (key,
			' ' * (15-len(key)),
			' '.join(self.nsswitch[key]))

		nss_lock = FileLock(self, '/etc/nsswitch.conf')
		nss_lock.Lock()
		open('/etc/nsswitch.conf', 'w').write(nss_data)
		nss_lock.Unlock()
	def enable_backend(self, backend, listener=None):
		""" try to enable a given backend. what to do exactly is left to the
		backend itself."""

		ltrace('configuration', '| enable_backend()')

		if backend in self.backends.keys():
			logging.notice('%s backend already enabled.' % backend,
				listener=listener)
			return

		if self.available_backends[backend].enable():
			self.available_backends[backend].initialize()
			self.backends[backend] = self.available_backends[backend]
			del self.available_backends[backend]

			logging.notice('''successfully enabled %s backend, reloading '''
				'''controllers.''' % backend, listener=listener)

			self.find_new_prefered_backend(listener=listener)

			for controller in self.controllers:
				controller.reload()
	def disable_backend(self, backend, listener=None):
		""" try to disable a given backend. what to do exactly is left to the
		backend itself."""

		ltrace('configuration', '| disable_backend()')

		if backend in self.available_backends.keys():
			logging.notice('%s backend already disabled.' % backend,
				listener=listener)
			return

		got_to_find_new_prefered = False
		if self.backends[backend].disable():
			if self.backends['prefered'] == self.backends[backend]:
				del self.backends['prefered']
				got_to_find_new_prefered = True
			self.available_backends[backend] = self.backends[backend]
			del self.backends[backend]
			logging.notice('''successfully disabled %s backend, reloading '''
				'''controllers.''' % backend, listener=listener)

			if got_to_find_new_prefered:
				self.find_new_prefered_backend(listener=listener)

			for controller in self.controllers:
				controller.reload()

	def find_new_prefered_backend(self, listener=None):
		""" iterate through active backends and find the prefered one.
			We use a copy, in case there is no prefered yet: self.backends
			will change and this would crash the for_loop. """
		for backend_name in self.backends.copy():
			if self.backends.has_key('prefered'):
				if self.backends[backend_name].priority \
					> self.backends['prefered'].priority:
					self.backends['prefered'] = \
						self.backends[backend_name]
			else:
				self.backends['prefered'] = self.backends[backend_name]

		# FIXME: this doesn't belong here, but could help fixing #380.
		#reload(fsapi.posix1e)
		reload(fsapi)
		logging.info('''reloaded fsapi module.''', listener=listener)
	def load_plugins(self):
		""" Load Configuration backends, and put the one with the greatest
		priority at the beginning of the backend list. This makes it accessible
		quickly on user/group/whatever creation. """

		ltrace('configuration', '> load_plugins().')

		from licorn.core.backends.plugins import plugins
		self.plugins           = {}
		self.available_plugins = {}

		for plugin in plugins:
			p = plugin(self)

			if p.initialize():
				ltrace('configuration', '  load_plugins(%s) OK' % p.name)

				self.plugins[p.name] = p
			else:
				self.available_plugins[p.name] = p

		ltrace('configuration', '< load_plugins().')
	def connect_plugins(self):
		""" add the enabled plugins to the enabled backends. """
		ltrace('configuration', '| connect_plugins()')
		for p in self.plugins:
			for b in self.backends:
				if self.backends[b].connect_plugin(self.plugins[p]):
					# add the plugin to only one backend. the first enabled one
					# is ok, just break.
					ltrace('configuration', '  connect_plugins(%s/%s) OK' % (
						b,p))
					break
	def load_backends(self):
		""" Load Configuration backends, and put the one with the greatest
		priority at the beginning of the backend list. This makes it accessible
		quickly on user/group/whatever creation. """

		ltrace('configuration', '> load_backends().')

		from licorn.core.backends import backends
		self.backends           = {}
		self.available_backends = {}

		for backend in backends:
			b = backend(self)

			#ltrace('configuration', 'testing %s (%s).' % (
			#	b.name, [
			#	val for val in self.nsswitch['passwd'] if val in b.compat]))

			if [val for val in self.nsswitch['passwd'] if val in b.compat] != []:
				if b.initialize():
					ltrace('configuration', '  load_backends(%s) OK' % b)

					self.backends[b.name] = b

				else:
					self.available_backends[b.name] = b
			else:
				# we don't care if the backend succeeds to initialize() or not
				# but subsequent method calls expect it to be run prior to
				# anything else.
				b.initialize(enabled=False)
				self.available_backends[b.name] = b

		self.find_new_prefered_backend()

		ltrace('configuration', '< load_backends().')

		if self.backends == []:
			raise exceptions.LicornRuntimeError(
			'''No suitable backend found. this shouldn't happen…''' )

	def CreateConfigurationDir(self):
		"""Create the configuration dir if it doesn't exist."""

		if not os.path.exists(self.config_dir):
			try:
				os.makedirs(self.config_dir)
				logging.info("Automatically created %s." % \
					styles.stylize(styles.ST_PATH, self.config_dir))
			except (IOError,OSError), e:
				# user is not root, forget it !
				pass

	def FindDistro(self):
		""" Determine which Linux / BSD / else distro we run on. """

		self.distro = None

		if os.name is "posix":
			if os.path.exists( '/etc/lsb-release' ):
				lsb_release = readers.shell_conf_load_dict('/etc/lsb-release')

				if lsb_release['DISTRIB_ID'] == 'Licorn':
					self.distro = distros.UBUNTU
				elif lsb_release['DISTRIB_ID'] == "Ubuntu":
					if lsb_release['DISTRIB_CODENAME'] in ('maverick', 'lucid',
						'karmik', 'jaunty'):
						self.distro = distros.UBUNTU
					else:
						raise exceptions.LicornRuntimeError(
							'''This Ubuntu version is not '''
							'''supported, sorry !''')
			else:
				# OLD / non-lsb compatible system or BSD
				if  os.path.exists( '/etc/gentoo-release' ):
					raise exceptions.LicornRuntimeError(
						"Gentoo is not yet supported, sorry !")
				elif  os.path.exists( '/etc/debian_version' ):
					raise exceptions.LicornRuntimeError(
						"Old Debian systems are not supported, sorry !")
				elif  os.path.exists( '/etc/SuSE-release' ) \
					or os.path.exists( '/etc/suse-release' ):
					raise exceptions.LicornRuntimeError(
						"SuSE are not yet supported, sorry !")
				elif  os.path.exists( '/etc/redhat_release' ) \
					or os.path.exists( '/etc/redhat-release' ):
					raise exceptions.LicornRuntimeError(
						"RedHat/Mandriva is not yet supported, sorry !")
				else:
					raise exceptions.LicornRuntimeError(
						"Unknown Linux Distro, sorry !")
		else:
			raise exceptions.LicornRuntimeError(
				"Not on a supported system ! Please send a patch ;-)")

		del(lsb_release)
	def detect_services(self):
		""" Concentrates all calls for service detection on the current system
		"""
		self.detect_OpenSSH()

		self.FindMTA()
		self.FindMailboxType()
	def detect_OpenSSH(self):
		""" OpenSSH related code.
			 - search for OpenSSHd configuration.
			 - if found, verify remotessh group exists.
			 - TODO: implement sshd_config modifications to include
				'AllowGroups remotessh'
		"""
		self.ssh = LicornConfigObject()

		piddir   = "/var/run"
		spooldir = "/var/spool"

		#
		# Finding Postfix
		#

		if self.distro in (
			distros.LICORN,
			distros.UBUNTU,
			distros.DEBIAN,
			distros.REDHAT,
			distros.GENTOO,
			distros.MANDRIVA,
			distros.NOVELL
			):

			if os.path.exists("/etc/ssh/sshd_config"):
				self.ssh.enabled = True
				self.ssh.group = 'remotessh'

			else:
				self.ssh.enabled = False

		else:
			logging.progress(_("SSH detection not supported yet on your system."
				"Please get in touch with %s." % \
				LicornConfiguration.developers_address))

		return self.ssh.enabled
	def check_OpenSSH(self, batch=False, auto_answer=None):
		""" Verify mandatory defaults for OpenSSHd. """
		if not self.ssh.enabled:
			return

		if not self.controllers.groups.exists(name = self.ssh.group):

			self.controllers.groups.AddGroup(name=self.ssh.group,
				description=_('Users allowed to connect via SSHd'),
				system=True, batch=True)
	def FindMTA(self):
		"""detect which is the underlying MTA."""

		self.mta = None

		piddir   = "/var/run"
		spooldir = "/var/spool"

		#
		# Finding Postfix
		#

		if self.distro == distros.UBUNTU:
			# postfix is chrooted on Ubuntu Dapper.
			if os.path.exists("/var/spool/postfix/pid/master.pid"):
				self.mta = servers.MTA_POSTFIX
				return
		else:
			if os.path.exists("%s/postfix.pid" % piddir):
				self.mta = servers.MTA_POSTFIX
				return

		#
		# Finding NullMailer
		#
		if os.path.exists("%s/nullmailer/trigger" % spooldir):
			self.mta = servers.MTA_NULLMAILER
			return

		self.mta = servers.MTA_UNKNOWN
		logging.progress('''MTA not installed or unsupported, please get in '''
			'''touch with dev@licorn.org.''')
	def FindMailboxType(self):
		"""Find how the underlying system handles Mailboxes
			(this can be Maidlir, mail spool,
			and we must find where they are)."""

		# a sane (but arbitrary) default.
		# TODO: detect this from /etc/…
		self.users.mailbox_auto_create = True

		if self.mta == servers.MTA_POSTFIX:

			if self.distro in (distros.UBUNTU,
				distros.DEBIAN,
				distros.GENTOO):
				postfix_main_cf = \
					readers.shell_conf_load_dict('/etc/postfix/main.cf')

			try:
				self.users.mailbox_base_dir = \
					postfix_main_cf['mailbox_spool']
				self.users.mailbox_type     = \
					mailboxes.VAR_MBOX
			except KeyError:
				pass

			try:
				self.users.mailbox = \
					postfix_main_cf['home_mailbox']

				if self.users.mailbox[-1:] == '/':
					self.users.mailbox_type = \
						mailboxes.HOME_MAILDIR
				else:
					self.users.mailbox_type = \
						mailboxes.HOME_MBOX

			except KeyError:
				pass

			logging.debug2("Mailbox type is %d and base is %s." % (
				self.users.mailbox_type,
				self.users.mailbox))

		elif self.mta == servers.MTA_NULLMAILER:

			# mail is not handled on this machine, forget the mailbox creation.
			self.users.mailbox_auto_create = False

		elif self.mta == servers.MTA_UNKNOWN:

			# totally forget about mail things.
			self.users.mailbox_auto_create = False

		else:
			# totally forget about mail things.
			self.users.mailbox_auto_create = False
			logging.progress('''Mail{box,dir} system not supported yet. '''
				'''Please get in touch with dev@licorn.org.''')
	def LoadShells(self):
		"""Find valid shells on the local system"""

		self.users.shells = []

		# specialty on Debian / Ubuntu: /etc/shells contains shells that
		# are not installed on the system. What is then the purpose of this
		# file, knowing its definitions:
		# «/etc/shells contains the valid shells on a given system»…
		# specialty 2: it does not contains /bin/false…

		for shell in readers.very_simple_conf_load_list("/etc/shells"):
			if os.path.exists(shell):
				self.users.shells.append(shell)

		if "/bin/false" not in self.users.shells:
			self.users.shells.append("/bin/false")

		# hacker trick !
		if os.path.exists("/usr/bin/emacs"):
			self.users.shells.append("/usr/bin/emacs")
	def LoadSkels(self):
		"""Find skel dirs on the local system."""

		self.users.skels = []

		if os.path.isdir("/etc/skel"):
			self.users.skels.append("/etc/skel")

		import stat

		for skel_path in ("%s/skels" % \
			self.defaults.home_base_path, "/usr/share/skels"):
			if os.path.exists(skel_path):
				try:
					for new_skel in fsapi.minifind(path=skel_path,
						type=stat.S_IFDIR, mindepth=2, maxdepth=2):
						self.users.skels.append(new_skel)
				except OSError, e:
					logging.warning('''Custom skels must have at least %s '''
						'''perms on dirs and %s on files:\n\t%s''' % (
							styles.stylize(styles.ST_MODE,
								"u+rwx,g+rx,o+rx"),
							styles.stylize(styles.ST_MODE,
								"u+rw,g+r,o+r"), e))

	### Users and Groups ###
	def LoadManagersConfiguration(self):
		""" Load Users and Groups managements configuration. """

		# WARNING: don't change order of these.
		self.SetUsersDefaults()
		self.SetGroupsDefaults()

		groups_dir = "%s/%s" % (self.defaults.home_base_path,
			self.groups.names.plural)

		# defaults to False, because this is mostly annoying. Administrator must
		# have a good reason to hide groups.
		self.groups.hidden = None

		add_user_conf = self.CheckAndLoadAdduserConf()
		self.users.min_passwd_size = 8
		self.users.uid_min         = add_user_conf['FIRST_UID']
		self.users.uid_max         = add_user_conf['LAST_UID']
		self.groups.gid_min        = add_user_conf['FIRST_GID']
		self.groups.gid_max        = add_user_conf['LAST_GID']
		self.users.system_uid_min  = \
			add_user_conf['FIRST_SYSTEM_UID']
		self.users.system_uid_max  = \
			add_user_conf['LAST_SYSTEM_UID']
		self.groups.system_gid_min = \
			add_user_conf['FIRST_SYSTEM_GID']
		self.groups.system_gid_max = \
			add_user_conf['LAST_SYSTEM_GID']

		# fix #74: map uid/gid above 300/500, to avoid interfering with
		# Ubuntu/Debian/RedHat/whatever system users/groups. This will raise
		# chances for uid/gid synchronization between servers (or client/server)
		# to success (avoid a machine's system users/groups to take identical
		# uid/gid of another machine system users/groups ; whatever the name).
		if self.users.system_uid_min < 300:
			self.users.system_uid_min = 300
		if self.groups.system_gid_min < 300:
			self.groups.system_gid_min = 300

		#
		# WARNING: these values are meant to be used like this:
		#
		#  |<-               privileged              ->|<-                            UN-privileged                           ->|
		#    (reserved IDs)  |<- system users/groups ->|<-  standard users/groups ->|<- system users/groups ->|  (reserved IDs)
		#  |-------//--------|------------//-----------|--------------//------------|-----------//------------|------//---------|
		#  0            system_*id_min             *id_min                       *id_max             system_*id_max           65535
		#
		# in unprivileged system users/groups, you will typically find www-data, proxy, nogroup, samba machines accounts…
		#

		#
		# The default values are referenced in CheckAndLoadAdduserConf() too.
		#
		for (attr_name, conf_key) in (
			('base_path', 'DHOME'),
			('default_shell', 'DSHELL'),
			('default_skel',  'SKEL'),
			('default_gid',   'USERS_GID')
			):
			val = add_user_conf[conf_key]
			setattr(self.users, attr_name, val)

		# first guesses to find Mail system.
		self.users.mailbox_type = 0
		self.users.mailbox      = ""

		try:
			self.users.mailbox      = add_user_conf["MAIL_FILE"]
			self.users.mailbox_type = \
				mailboxes.HOME_MBOX
		except KeyError:
			pass

		try:
			self.users.mailbox_base_dir = \
				add_user_conf["MAIL_DIR"]
			self.users.mailbox_type     = \
				mailboxes.VAR_MBOX
		except KeyError:
			pass

		# ensure /etc/login.defs  and /etc/defaults/useradd comply with
		# /etc/adduser.conf tweaked for Licorn®.
		self.CheckLoginDefs()
		self.CheckUserAdd()
	def SetDefaultNamesAndPaths(self):
		""" *HARDCODE* some names before we pull them out
			into configuration files."""

		self.defaults =  LicornConfigObject()

		self.defaults.home_base_path = '/home'

		# WARNING: Don't translate this. This still has to be discussed.
		# TODO: move this into a plugin
		self.defaults.admin_group = 'admins'

		self.defaults.needed_groups = [ 'users', 'acl' ]


		# TODO: autodetect this & see if it not autodetected elsewhere.
		#self.defaults.quota_device = "/dev/hda1"
	def SetUsersDefaults(self):
		"""Create self.users attributes and start feeding it."""

		self.users  = LicornConfigObject()

		# see groupadd(8), coming from addgroup(8)
		self.users.login_maxlenght = 31

		# the _xxx variables are needed for gettextized interfaces
		# (core and CLI are NOT gettextized)
		self.users.names = LicornConfigObject()
		self.users.names.singular = 'user'
		self.users.names.plural = 'users'
		self.users.names._singular = _('user')
		self.users.names._plural = _('users')

	def SetGroupsDefaults(self):
		"""Create self.groups attributes and start feeding it."""

		self.groups = LicornConfigObject()
		self.groups.guest_prefix = 'gst-'
		self.groups.resp_prefix = 'rsp-'

		# maxlenght comes from groupadd(8), itself coming from addgroup(8)
		# 31 - len(prefix)
		self.groups.name_maxlenght = 27

		# the _xxx variables are needed for gettextized interfaces
		# (core and CLI are NOT gettextized)
		self.groups.names = LicornConfigObject()
		self.groups.names.singular = 'group'
		self.groups.names.plural = 'groups'
		self.groups.names._singular = _('group')
		self.groups.names._plural = _('groups')
	def set_acl_defaults(self):
		""" Prepare the basic ACL configuration inside us. """

		ltrace("configuration", '| set_acl_defaults()')

		self.posix1e = LicornConfigObject()
		self.posix1e.groups_dir = "%s/%s" % (
			self.defaults.home_base_path,
			self.groups.names.plural)
		self.posix1e.acl_base = 'u::rwx,g::---,o:---'
		self.posix1e.acl_mask = 'm:rwx'
		self.posix1e.acl_admins_ro = 'g:%s:r-x' % \
			self.defaults.admin_group
		self.posix1e.acl_admins_rw = 'g:%s:rwx' % \
			self.defaults.admin_group
		self.posix1e.acl_users = '--x' \
			if self.groups.hidden else 'r-x'
	def CheckAndLoadAdduserConf(self, batch=False, auto_answer=None):
		""" Check the contents of adduser.conf to be compatible with Licorn.
			Alter it, if not.
			Then load it in a way i can be used in LicornConfiguration.
		"""

		adduser_conf       = '/etc/adduser.conf'
		adduser_conf_alter = False
		adduser_data       = open(adduser_conf, 'r').read()
		adduser_dict       = readers.shell_conf_load_dict(data=adduser_data)

		# warning: the order is important: in a default adduser.conf,
		# only {FIRST,LAST}_SYSTEM_UID are
		# present, and we assume this during the file patch.
		defaults = (
			('DHOME', '%s/users' % \
				self.defaults.home_base_path),
			('DSHELL', '/bin/bash'),
			('SKEL',   '/etc/skel'),
			('GROUPHOMES',  'no'),
			('LETTERHOMES', 'no'),
			('USERGROUPS',  'no'),
			('USERS_GID', 100),
			('LAST_GID',  29999),
			('FIRST_GID', 10000),
			('LAST_UID',  29999),
			('FIRST_UID', 1000),
			('LAST_SYSTEM_UID',  999),
			('FIRST_SYSTEM_UID', 100),
			('LAST_SYSTEM_GID',  9999),
			('FIRST_SYSTEM_GID', 100),
			)

		for (directive, value) in defaults:
			if directive in adduser_dict.keys():
				if type(value) == type(1):
					if value > adduser_dict[directive]:
						logging.warning('''In %s, directive %s should be at '''
							'''least %s, but it is %s.'''
							% (styles.stylize(styles.ST_PATH, adduser_conf),
								directive, value, adduser_dict[directive]))
						adduser_dict[directive] = value
						adduser_conf_alter      = True
						adduser_data            = re.sub(r'%s=.*' % directive,
							r'%s=%s' % (directive, value), adduser_data)
				else:
					if value != adduser_dict[directive]:
						logging.warning('''In %s, directive %s should be set '''
							'''to %s, but it is %s.''' % (
								styles.stylize(styles.ST_PATH, adduser_conf),
								directive, value, adduser_dict[directive]))
						adduser_dict[directive] = value
						adduser_conf_alter      = True
						adduser_data            = re.sub(r'%s=.*' % directive,
							r'%s=%s' % (directive, value), adduser_data)

				# else: everything's OK !
			else:
				logging.warning(
					'''In %s, directive %s is missing. Setting it to %s.'''
					% (styles.stylize(styles.ST_PATH, adduser_conf),
						directive, value))
				adduser_dict[directive] = value
				adduser_conf_alter      = True
				adduser_data            = re.sub(r'(LAST_SYSTEM_UID.*)',
					r'\1\n%s=%s' % (directive, value), adduser_data)

		if adduser_conf_alter:
			if batch or logging.ask_for_repair(
				'''%s lacks mandatory configuration directive(s).'''
							% styles.stylize(styles.ST_PATH, adduser_conf),
								auto_answer):
				try:
					open(adduser_conf, 'w').write(adduser_data)
					logging.notice('Tweaked %s to match Licorn pre-requisites.'
						% styles.stylize(styles.ST_PATH, adduser_conf))
				except (IOError, OSError), e:
					if e.errno == 13:
						raise exceptions.LicornRuntimeError(
							'''Insufficient permissions. '''
							'''Are you root?\n\t%s''' % e)
					else: raise e
			else:
				raise exceptions.LicornRuntimeError('''Modifications in %s '''
					'''are mandatory for Licorn to work properly with other '''
					'''system tools (adduser/useradd). Can't continue '''
					'''without this, sorry!''' % adduser_conf)

		return adduser_dict
	def CheckLoginDefs(self, batch=False, auto_answer=None, listener=None):
		""" Check /etc/login.defs for compatibility with Licorn.
			Load data, alter it if needed and save the new file.
		"""

		self.check_system_file_generic(filename="/etc/login.defs",
			reader=readers.simple_conf_load_dict,
			defaults=(
				('UID_MIN', self.users.uid_min),
				('UID_MAX', self.users.uid_max),
				('GID_MIN', self.groups.gid_min),
				('GID_MAX', self.groups.gid_max),
				('SYS_GID_MAX', self.groups.system_gid_max),
				('SYS_GID_MIN', self.groups.system_gid_min),
				('SYS_UID_MAX', self.users.system_uid_max),
				('SYS_UID_MIN', self.users.system_uid_min),
				('USERGROUPS_ENAB', 'no'),
				('CREATE_HOME', 'yes')
			),
			separator='	',
			batch=batch,
			auto_answer=auto_answer, listener=listener)
	def CheckUserAdd(self, batch=False, auto_answer=None, listener=None):
		""" Check /etc/defaults/useradd if it exists, for compatibility with
			Licorn®.
		"""

		self.check_system_file_generic(filename="/etc/default/useradd",
			reader=readers.shell_conf_load_dict,
			defaults=(
				('GROUP', self.users.default_gid),
				('HOME', self.users.base_path)
			),
			separator='=',
			check_exists=True,
			batch=batch,
			auto_answer=auto_answer, listener=listener)
	def check_system_file_generic(self, filename, reader, defaults, separator,
		check_exists=False, batch=False, auto_answer=None, listener=None):

		if check_exists and not os.path.exists(filename):
			logging.warning2('''%s doesn't exist on this system.''' % filename,
				listener=listener)
			return

		alter_file = False
		file_data  = open(filename, 'r').read()
		data_dict  = reader(data=file_data)

		for (directive, value) in defaults:
			try:
				if data_dict[directive] != value:
					logging.warning('''In %s, directive %s should be %s,'''
						''' but it is %s.''' % (
							styles.stylize(styles.ST_PATH, filename),
							directive, value, data_dict[directive]),
							listener=listener)
					alter_file           = True
					data_dict[directive] = value
					file_data            = re.sub(r'%s.*' % directive,
						r'%s%s%s' % (directive, separator, value), file_data)
			except KeyError:
				logging.warning('''In %s, directive %s isn't present but '''
					'''should be, with value %s.''' % (
						styles.stylize(styles.ST_PATH, filename),
						directive, value),
						listener=listener)
				alter_file           = True
				data_dict[directive] = value
				file_data += '%s%s%s\n' % (directive, separator, value)

		if alter_file:
			if batch or logging.ask_for_repair(
				'''%s should be altered to be in sync with Licorn®. Fix it ?'''
				% styles.stylize(styles.ST_PATH, filename), auto_answer,
				listener=listener):
				try:
					open(filename, 'w').write(file_data)
					logging.notice('Tweaked %s to match Licorn pre-requisites.'
						% styles.stylize(styles.ST_PATH, filename),
						listener=listener)
				except (IOError, OSError), e:
					if e.errno == 13:
						raise exceptions.LicornRuntimeError(
							'''Insufficient permissions. '''
							'''Are you root?\n\t%s''' % e)
					else:
						raise e
			else:
				raise exceptions.LicornRuntimeError('''Modifications in %s '''
					'''are mandatory for Licorn to work properly. Can't '''
					'''continue without this, sorry!''' % filename)

	### EXPORTS ###
	def Export(self, doreturn=True, args=None, cli_format='short'):
		""" Export «self» (the system configuration) to a human
			[styles.stylized and] readable form.
			if «doreturn» is True, return a "string", else write output
			directly to stdout.
		"""

		if args is not None:
			data = ""

			if cli_format == "bourne":
				cli = {
					'prefix': "export ",
					'name': True,
					'equals': "=",
					'suffix': ""
					}
			elif  cli_format == "cshell":
				cli = {
					'prefix': "setenv ",
					'name': True,
					'equals': " ",
					'suffix': ""
					}
			elif  cli_format == "PHP":
				cli = {
					'prefix': "$",
					'name': True,
					'equals': "=",
					'suffix': ";"
					}
			elif  cli_format == "short":
				cli = {
					'prefix': "",
					'name': False,
					'equals': "=",
					'suffix': ""
					}
			else:
				raise exceptions.BadArgumentError(
					"Bad CLI output format « %s » !" % cli_format)

			if args[0] == "shells":
				for shell in self.users.shells:
					data += "%s\n" % shell

			elif args[0] == "skels":
				for skel in self.users.skels:
					data += "%s\n" % skel

			elif args[0] == 'backends':
				for b in self.backends:
					if b == 'prefered': continue
					data += '%s%s\n' % (self.backends[b].name,
						styles.stylize(styles.ST_INFO, '*') \
						if self.backends[b].name == self.backends['prefered'].name else '')
				for b in self.available_backends:
					data += '%s\n' % self.available_backends[b].name

			elif args[0] in ("config_dir", "main_config_file",
				"backup_config_file", "extendedgroup_data_file", "app_name"):

				varname = args[0].upper()

				if args[0] == "config_dir":
					varval = self.config_dir
				elif args[0] == "main_config_file":
					varval = self.main_config_file
				elif args[0] == "backup_config_file":
					varval = self.backup_config_file
				elif args[0] == "extendedgroup_data_file":
					varval = self.extendedgroup_data_file
				elif args[0] == "app_name":
					varval = self.app_name

				if cli["name"]:
					data +=	 "%s%s%s\"%s\"%s\n" % (
						cli["prefix"],
						varname,
						cli["equals"],
						varval,
						cli["suffix"]
						)
				else:
					data +=	 "%s\n" % (varval)
			elif args[0] in ('sysgroups', 'system_groups', 'system-groups'):

				for group in self.defaults.needed_groups:
					data += "%s\n" % styles.stylize(styles.ST_SECRET, group)

				data += "%s\n" % styles.stylize(styles.ST_SECRET,
					self.defaults.admin_group)

				for priv in self.privileges_whitelist:
					data += "%s\n" % priv

			elif args[0] in ('priv', 'privs', 'privileges'):

				for priv in self.controllers.privileges:
					data += "%s\n" % priv

			else:
				raise NotImplementedError(
					"Sorry, outputing selectively %s is not yet implemented !" \
						% args[0])

		else:
			data = self._export_all()

		if doreturn is True:
			return data
		else:
			sys.stdout.write(data + "\n")
	def _export_all(self):
		"""Export all configuration data in a visual way."""

		data = "%s\n" % styles.stylize(styles.ST_APPNAME, "LicornConfiguration")

		for attr in dir(self):
			if callable(getattr(self, attr)) \
				or attr[0] in '_ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
				or attr in ('tmp_dir', 'init_ok', 'del_ok', 'objectGUID',
					'lastUsed', 'delegate', 'daemon', 'controllers'):
				# skip methods, python internals, pyro internals and
				# too-much-moving targets which bork the testsuite.
				continue

			data += u"\u21b3 %s: " % styles.stylize(styles.ST_ATTR, attr)

			if attr in ('app_name', 'distro', 'mta'):
				data += "%s\n" % styles.stylize(styles.ST_ATTRVALUE,
					str(self.__getattribute__(attr)))
				# cf http://www.reportlab.com/i18n/python_unicode_tutorial.html
				# and http://web.linuxfr.org/forums/29/9994.html#599760
				# and http://evanjones.ca/python-utf8.html
			elif attr.endswith('_dir') or attr.endswith('_file') \
				or attr.endswith('_path') :
				data += "%s\n" % styles.stylize(styles.ST_PATH,
					str(getattr(self, attr)))
			elif type(getattr(self, attr)) == type(LicornConfigObject()):
				data += "\n%s" % str(getattr(self, attr))
			elif type(getattr(self, attr)) in (
				type([]), type(''), type(()), type({})):
				data += "\n\t%s\n" % str(getattr(self, attr))
			else:
				data += ('''%s, to be implemented in '''
					'''licorn.core.configuration.Export()\n''') % \
					styles.stylize(styles.ST_IMPORTANT, "UNREPRESENTABLE YET")

		return data
	def ExportXML(self):
		""" Export «self» (the system configuration) to XML. """
		raise NotImplementedError(
			'''LicornConfig::ExportXML() not yet implemented !''')

	### MODIFY ###
	def ModifyHostname(self, new_hostname):
		"""Change the hostname of the running system."""

		if new_hostname == self.mCurrentHostname:
			return

		if not re.compile("^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
			re.IGNORECASE).match(new_hostname):
			raise exceptions.BadArgumentError(
				'''new hostname must be composed only of letters, digits and '''
				'''hyphens, but not starting nor ending with an hyphen !''')

		logging.progress("Doing preliminary checks…")
		self.CheckHostname()

		try:
			etc_hostname = file("/etc/hostname", 'w')
			etc_hostname.write(new_hostname)
			etc_hostname.close()
		except (IOError, OSError), e:
			raise exceptions.LicornRuntimeError(
				'''can't modify /etc/hostname, verify the file is still '''
				'''clean:\n\t%s)''' % e)

	### CHECKS ###
	def check(self, minimal=True, batch=False, auto_answer=None, listener=None):
		""" Check all components of system configuration and repair
		if asked for."""

		ltrace('configuration', '> check()')

		# users and groups must be OK before everything.
		# for this, backends must be ready and configured.
		# check the first.
		self.check_backends(batch=batch, auto_answer=auto_answer)

		self.check_base_dirs(minimal=minimal, batch=batch,
			auto_answer=auto_answer, listener=listener)

		self.check_OpenSSH(batch=batch, auto_answer=auto_answer)

		# not yet ready.
		#self.CheckHostname(minimal, auto_answer)
		ltrace('configuration', '< check()')
	def check_backends(self, batch=False, auto_answer=None):
		""" check all enabled backends, except the 'prefered', which is one of
		the enabled anyway.

		Checking them will make them configure themselves, and configure the
		underlying system daemons and tools.

		FIXME listener=listener
		"""

		ltrace('configuration', '> check_backends()')

		for backend_name in self.backends:
			if backend_name == 'prefered':
				continue
			self.backends[backend_name].check(batch, auto_answer)
			# FIXME listener=listener

		# check the available_backends too. It's the only way to make sure they
		# can be fully usable before enabling them.
		for backend_name in self.available_backends:
			self.available_backends[backend_name].check(batch, auto_answer)

		ltrace('configuration', '< check_backends()')
	def check_base_dirs(self, minimal=True, batch=False, auto_answer=None,
		listener=None):
		"""Check and eventually repair default needed dirs."""

		ltrace('configuration', '> check_base_dirs()')

		try:
			os.makedirs(self.users.base_path)
		except (OSError, IOError), e:
			if e.errno != 17:
				raise e

		self.CheckSystemGroups(minimal, batch, auto_answer, listener=listener)

		p = self.posix1e

		dirs_to_verify = [ {
			'path'      : p.groups_dir,
			'user'      : 'root',
			'group'     : 'acl',
			'access_acl': "%s,%s,g:www-data:--x,g:users:%s,%s" % (
				p.acl_base, p.acl_admins_ro,
				p.acl_users, p.acl_mask),
			'default_acl': ""
			} ]

		try:
			# batch this because it *has* to be corrected
			# for system to work properly.
			fsapi.check_dirs_and_contents_perms_and_acls( dirs_to_verify,
				batch=batch, allgroups=self.controllers.groups,
				allusers=self.controllers.users, listener=listener)

		except (IOError, OSError), e:
			if e.errno == 95:
				# this is the *first* "not supported" error encountered (on
				# config load of first licorn command). Try to make the error
				# message kind of explicit and clear, to let administrator know
				# he/she should mount the partition with 'acl' option.
				raise exceptions.LicornRuntimeError(
					'''Filesystem must be mounted with 'acl' option:\n\t%s''' \
						% e)
			else:
				raise e

		home_backup_dir_info = {
			'path'      : self.home_backup_dir,
			'user'      : 'root',
			'group'     : 'acl',
			'access_acl': "%s,%s,%s" % (p.acl_base,
				p.acl_admins_ro, p.acl_mask),
			'default_acl': "%s,%s,%s" % (p.acl_base,
				p.acl_admins_ro, p.acl_mask)
			}

		if not minimal:
			# check the contents of these dirs, too (fixes #95)
			home_backup_dir_info['content_acl'] = ("%s,%s,%s" % (
				p.acl_base, p.acl_admins_ro, p.acl_mask)
				).replace('r-x', 'r--').replace('rwx', 'rw-')

		all_went_ok = True

		all_went_ok &= fsapi.check_dirs_and_contents_perms_and_acls(
			[ home_backup_dir_info ], batch=True,
			allgroups=self.controllers.groups, allusers=self.controllers.users,
			listener=listener)

		all_went_ok &= self.check_archive_dir(batch=batch,
			auto_answer=auto_answer, listener=listener)

		ltrace('configuration', '< check_base_dirs(%s)' % all_went_ok)
		return all_went_ok
	def check_archive_dir(self, subdir=None, minimal=True, batch=False,
		auto_answer=None, listener=None):
		""" Check only the archive dir, and eventually even only one of its
			subdir. """

		ltrace('configuration', '> check_archive_dir(%s)' % subdir)

		p = self.posix1e

		home_archive_dir_info = {
			'path'       : self.home_archive_dir,
			'user'       : 'root',
			'group'      : 'acl',
			'access_acl' : "%s,%s,%s" % (
				p.acl_base, p.acl_admins_rw, p.acl_mask),
			'default_acl': "%s,%s,%s" % (
				p.acl_base, p.acl_admins_rw, p.acl_mask),
			}

		if subdir:

			if os.path.dirname(subdir) == self.home_archive_dir:

				subdir_info = {
					'path'       : self.home_archive_dir,
					'user'       : 'root',
					'group'      : 'acl',
					'access_acl' : "%s,%s,%s" % (
						p.acl_base, p.acl_admins_rw, p.acl_mask),
					'default_acl': "%s,%s,%s" % (
						p.acl_base, p.acl_admins_rw, p.acl_mask),
					'content_acl': ("%s,%s,%s" % (
						p.acl_base, p.acl_admins_rw, p.acl_mask)
							).replace('r-x', 'r--').replace('rwx', 'rw-')
					}
			else:
				logging.warning(
					'the subdir you specified is not inside %s, skipped.' %
						styles.stylize(styles.ST_PATH, self.home_archive_dir),
						listener=listener)
				subdir=False

		elif not minimal:
			home_archive_dir_info['content_acl'] = ("%s,%s,%s" % (
				p.acl_base, p.acl_admins_rw, p.acl_mask)
				).replace('r-x', 'r--').replace('rwx', 'rw-')

		dirs_to_verify = [ home_archive_dir_info ]

		if subdir:
			dirs_to_verify.append(subdir_info)

		ltrace('configuration', '< check_archive_dir()')

		return fsapi.check_dirs_and_contents_perms_and_acls(dirs_to_verify,
			batch=batch, auto_answer=auto_answer,
			allgroups=self.controllers.groups, allusers=self.controllers.users,
			listener=listener)
	def CheckSystemGroups(self, minimal=True, batch=False, auto_answer=None,
		listener=None):
		"""Check if needed groups are present on the system, and repair
			if asked for."""

		ltrace('configuration', '> CheckSystemGroups(minimal=%s, batch=%s)' %
			(minimal, batch))

		needed_groups = self.defaults.needed_groups + [
			self.defaults.admin_group ]

		if not minimal \
			and self.controllers.privileges != []:
			# 'skels', 'remotessh', 'webmestres' [and so on] are not here
			# because they will be added by their respective packages
			# (plugins ?), and they are not strictly needed for Licorn to
			# operate properly.

			for groupname in self.controllers.privileges:
				if groupname not in needed_groups:
					needed_groups.append(groupname)

		for group in needed_groups:
			# licorn.core.groups is not loaded yet, and it would create a
			# circular dependancy to import it now. We HAVE to do this manually.
			if not self.controllers.groups.exists(name=group):
				if batch or logging.ask_for_repair(
					logging.CONFIG_SYSTEM_GROUP_REQUIRED % \
						styles.stylize(styles.ST_NAME, group), auto_answer,
						listener=listener):
					if group == 'users' and self.distro in (
						distros.UBUNTU,
						distros.DEBIAN):

						# this is a special case: on deb.*, the "users" group
						# has a reserved gid of 100. Many programs rely on this.
						gid = 100
					else:
						gid = None

					self.controllers.groups.AddGroup(group, system=True,
						desired_gid=gid, listener=listener)
					del gid
				else:
					raise exceptions.LicornRuntimeError(
						'''The system group « %s » is mandatory but doesn't '''
						''' exist on your system !\nUse « licorn-check '''
						'''config --yes » or « licorn-add group --system '''
						'''--name "%s" » to solve the problem.''' % (
							group, group)
						)

		ltrace('configuration', '< CheckSystemGroups()')
	def CheckHostname(self, batch = False, auto_answer = None):
		""" Check hostname consistency (by DNS/reverse resolution),
			and check /etc/hosts against flakynesses."""

		import stat
		hosts_mode = os.stat("/etc/hosts").st_mode
		if not stat.S_IMODE(hosts_mode) & stat.S_IROTH:
			#
			# nsswitch will fail to resolve localhost/127.0.0.1 if
			# /etc/hosts don't have sufficient permissions.
			#
			raise exceptions.BadConfigurationError(
				'''/etc/hosts must have at least o+r permissions.''')


		line = open("/etc/hostname").readline()
		if line[:-1] != self.mCurrentHostname:
			raise exceptions.BadConfigurationError(
				'''current hostname and /etc/hostname are not in sync !''')

		import socket

		# DNS check for localhost.
		hostname_ip = socket.gethostbyname(self.mCurrentHostname)

		if hostname_ip != '127.0.0.1':
			raise exceptions.BadConfigurationError(
				'''hostname %s doesn't resolve to 127.0.0.1 but to %s, '''
				'''please check /etc/hosts !''' % (
					self.mCurrentHostname, hostname_ip) )

		# reverse DNS check for localhost. We use gethostbyaddr() to allow
		# the hostname to be in the aliases (this is often the case for
		# localhost in /etc/hosts).
		localhost_data = socket.gethostbyaddr('127.0.0.1')

		if not ( self.mCurrentHostname == localhost_data[0]
				or self.mCurrentHostname in localhost_data[1] ):
			raise exceptions.BadConfigurationError(
				'''127.0.0.1 doesn't resolve back to hostname %s, please '''
				'''check /etc/hosts and/or DNS !''' % self.mCurrentHostname)

		import licorn.tools.network as network

		dns = []
		for ns in network.nameservers():
			dns.append(ns)

		logging.debug2("configuration|DNS: " + str(dns))

		# reverse DNS check for eth0
		eth0_ip = network.iface_address('eth0')

		#
		# FIXME: the only simple way to garantee we are on an licorn server is
		# to check dpkg -l | grep licorn-server. We should check this to enforce
		# there is only 127.0.0.1 in /etc/resolv.conf if licorn-server is
		# installed.
		#

		#
		# FIXME2: when implementing previous FIXME, we should not but
		# administrator if /etc/licorn_is_installing is present (for example),
		# because during installation not everything is ready to go in
		# production and this is totally normal.
		#

		logging.debug2("configuration|eth0 IP: %s" % eth0_ip)

		try:
			eth0_hostname = socket.gethostbyaddr(eth0_ip)

			logging.debug2('configuration|eth0 hostname: %s' % eth0_hostname)

		except socket.herror, e:
			if e.args[0] == 1:
				#
				# e.args[0] == h_errno == 1 is «Unknown host»
				# the IP doesn't resolve, we could be on a standalone host (not
				# an Licorn server), we must verify.
				#
				if '127.0.0.1' in dns:
					raise exceptions.BadConfigurationError('''can't resolve '''
						'''%s (%s), is the dns server running on 127.0.0.1? '''
						'''Else check DNS files syntax !''' % (
							eth0_ip, e.args[1]))
				elif eth0_ip in dns:
					# FIXME put 127.0.0.1 automatically in configuration ?
					raise exceptions.BadConfigurationError(
						'''127.0.0.1 *must* be in /etc/resolv.conf on an '''
						'''Licorn server.''')
				#
				# if we reach here, this is the end of the function.
				#
		except Exception, e:
			raise exceptions.BadConfigurationError(
				'''Problem while resolving %s, please check '''
				'''configuration:\n\terrno %d, %s''' % (
					eth0_ip, e.args[0], e.args[1]))

		else:

			# hostname DNS check fro eth0. use [0] (the hostname primary record)
			# to enforce the full [reverse] DNS check is OK. This is needed for
			# modern SMTP servers, SSL web certificates to be validated, among
			# other things.
			eth0_reversed_ip = socket.gethostbyname(eth0_hostname[0])

			if eth0_reversed_ip != eth0_ip:
				if eth0_ip in dns:
					# FIXME put 127.0.0.1 automatically in configuration ?
					raise exceptions.BadConfigurationError(
						'''127.0.0.1 *must* be the only nameserver in '''
						'''/etc/resolv.conf on an Licorn server.''')
				elif '127.0.0.1' in dns:
					raise exceptions.BadConfigurationError(
						'''DNS seems not properly configured (%s doesn't '''
						'''resolve back to itself).''' % eth0_ip)
				else:
					logging.warning(
						'''DNS not properly configured (%s doesn't resolve '''
						'''to %, but to %s)''' % (
							eth0_hostname, eth0_ip, eth0_reversed_ip))

			# everything worked, but it is safer to have 127.0.0.1 as the
			# nameserver, inform administrator.
			if eth0_ip in dns or '127.0.0.1':
				# FIXME put 127.0.0.1 automatically in configuration ?
				logging.warning('''127.0.0.1 should be the only nameserver '''
					'''in /etc/resolv.conf on an Licorn server.''')

		# FIXME: vérifier que l'ip d'eth0 et son nom ne sont pas codés en dur
		# dans /etc/hosts, la série de tests sur eth0 aurait pu marcher grâce
		# à ça et donc rien ne dit que la conf DNS est OK…
	def CheckMailboxConfigIntegrity(self, batch=False, auto_answer=None):
		"""Verify "slaves" configuration files are OK, else repair them."""

		"""
			if mailbox:
				warning(unsupported)
			elif maildir:
				if courier-*:
					if batch or …:

					else:
						warning()
				else:
					raise unsupported.
			else:
				raise unsupported

		"""

		pass
	def SetHiddenGroups(self, hidden=True, listener=None):
		""" Set (un-)restrictive mode on the groups base directory. """

		self.groups.hidden = hidden
		self.check_base_dirs(batch=True, listener=listener)

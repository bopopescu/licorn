# -*- coding: utf-8 -*-
"""
Licorn OpenLDAP backend - http://docs.licorn.org/core/backends/openldap.html

:copyright: 2010 Olivier Cortès <olive@deep-ocean.net>
:license: GNU GPL version 2

.. versionadded:: 1.3
	This backend was previously known as **ldap**, but has been
	renamed **openldap** during the 1.2 ⇢ 1.3 development cycle, to
	better match reality and avoid potential name conflicts.

.. TODO: implement auto-setup part: if backends.openldap.available is forced to
   True in licorn.conf, we should auto-install packages, setup dirs, LDAP
   dn, etc.

"""

import os
import ldap as pyldap
import hashlib
from base64 import encodestring, decodestring

from licorn.foundations           import logging, exceptions
from licorn.foundations           import readers, process, pyutils, ldaputils
from licorn.foundations.styles    import *
from licorn.foundations.ltrace    import ltrace
from licorn.foundations.ltraces import *
from licorn.foundations.base      import Enumeration, Singleton
from licorn.foundations.constants import backend_actions

from licorn.core                  import LMC
from licorn.core.users            import User
from licorn.core.groups           import Group
from licorn.core.backends         import NSSBackend, UsersBackend, GroupsBackend

class OpenldapBackend(Singleton, UsersBackend, GroupsBackend):
	""" OpenLDAP Backend for users and groups.

	"""

	init_ok = False

	def __init__(self):
		""" Init the LDAP backend instance. """

		if OpenldapBackend.init_ok:
			return

		assert ltrace(TRACE_OPENLDAP, '> __init__()')

		NSSBackend.__init__(self, name='openldap', nss_compat=('ldap',), priority=5)

		self.files             = Enumeration()
		self.files.openldap_conf   = '/etc/ldap.conf'
		self.files.openldap_secret = '/etc/ldap.secret'

		OpenldapBackend.init_ok = True
		assert ltrace(TRACE_OPENLDAP, '< __init__(%s)' % OpenldapBackend.init_ok)
	def __del__(self):
		try:
			self.openldap_conn.unbind_s()
		except:
			pass
	def load_defaults(self):
		""" Return mandatory defaults needed for LDAP Backend.

		TODO: what the hell is good to set defaults if pam-ldap and libnss-ldap
		are not used ? If they are in use, everything is already set up in
		system files, no ? This needs to be rethought, to avoid doing the job
		twice.
		"""

		assert ltrace(TRACE_OPENLDAP, '| load_defaults().')

		if LMC.configuration.licornd.role == 'client':
			waited = 0.1
			while LMC.configuration.server_main_address is None:
				#
				time.sleep(0.1)
				waited += 0.1
				if waited > 5:
					# FIXME: this is not the best thing to do, but server
					# detection needs a little more love and thinking.
					raise exceptions.LicornRuntimeException(
						'No server detected, bailing out…' )
			server = LMC.configuration.server_main_address

		else:
			server = '127.0.0.1'

		# Stay local (unix socket) for nows
		# if server is None:
		self.uri             = 'ldapi:///'
		self.base            = 'dc=meta-it,dc=local'
		self.rootbinddn      = 'cn=admin,%s' % self.base
		self.secret          = 'metasecret'
		self.nss_base_group  = 'ou=Groups'
		self.nss_base_passwd = 'ou=People'
		self.nss_base_shadow = 'ou=People'
	def initialize(self):
		"""	try to start it without any tests (it should work if it's
			installed) and become available.
			If that fails, try to guess a little and help user resolving issue.
			else, just fail miserably.

		setup the backend, by gathering LDAP related configuration in system
		files. """

		assert ltrace(TRACE_OPENLDAP, '> initialize()')

		self.load_defaults()

		try:
			for (key, value) in readers.simple_conf_load_dict(
					self.files.openldap_conf).iteritems():
				setattr(self, key, value)

		except (IOError, OSError), e:
			if e.errno != 2:
				if os.path.exists(self.files.openldap_conf):
					logging.warning('''Problem initializing the LDAP backend.'''
					''' LDAP seems installed but not configured or unusable. '''
					'''Please run 'sudo chk config -evb' to correct. '''
					'''(was: %s)''' % e)
			elif e.errno == 2:
				# ldap.conf not present -> pam-ldap not installed -> just
				# discard the LDAP backend completely.
				pass
			else:
				# another problem worth noticing.
				raise e
		else:
			# add the self.base extension to self.nss_* if not present.
			for attr in (
				'nss_base_group',
				'nss_base_passwd',
				'nss_base_shadow'):
				value = getattr(self, attr)
				try:
					value.index(self.base)
				except ValueError:
					setattr(self, attr, '%s,%s' % (value, self.base))

			# assume we are not admin, then see if we are.
			self.bind_as_admin = False

			try:
				# if we have access to /etc/ldap.secret, we are root.

				self.secret = open(self.files.openldap_secret).read().strip()
				self.bind_dn = self.rootbinddn
				self.bind_as_admin = True

			except (IOError, OSError), e:
				if e.errno == 13:
					# permission denied.
					# we will bind as current user.
					self.bind_dn = 'uid=%s,%s' % (process.whoami(), self.base)
					#
					# NOTE 1: ask the user for his/her password, because the
					# server will refuse a binding without a password.
					#
					# NOTE 2: if the current user is not in the LDAP tree, we
					# must bind with external SASL, which will likely not work
					# because any other user than root / cn=admin has no right
					# on the LDAP tree.
					#
					# CONCLUSION: this case is not handled yet, because on
					# a regular LDAP-enabled Licorn system, the user:
					#	- is either root, thus cn=admin
					#	- is a LDAP user, and thus can bind correctly.

				elif e.errno == 2:
					# no such file or directory. Assume we are root and fill
					# the default password in the file. This will make
					# everything go smoother.

					logging.notice('''seting up default password in %s. You '''
						'''can change it later if you want by running '''
						'''FIXME_COMMAND_HERE.''' % (
						stylize(ST_PATH, self.files.openldap_secret)))

					open(self.files.openldap_secret, 'w').write(self.secret)
					self.bind_dn = self.rootbinddn
					self.bind_as_admin = True

				else:
					raise

			self.check_defaults()

			self.openldap_conn = pyldap.initialize(self.uri)

			self.available = True

		assert ltrace(TRACE_OPENLDAP, '< initialize(%s)' % self.available)
		return self.available
	def is_enabled(self):

		if NSSBackend.is_enabled(self):

			try:
				self.sasl_bind()
				return True

			except pyldap.SERVER_DOWN:
				logging.warning(_(u'{0}: server {1} is down, disabling '
					'backend. This will produce timeouts because {2} '
					'is enabled in NSS configuration.').format(
						stylize(ST_NAME, self.name),
						stylize(ST_URL, self.uri),
						stylize(ST_COMMENT, 'ldap')))
				self.enabled = False
				return False

		else:
			# not enabled at NSS level, sufficient to notice we are not used.
			return False

	def check_defaults(self):
		""" create defaults if they don't exist in current configuration. """

		assert ltrace(TRACE_OPENLDAP, '| check_defaults()')

		defaults = (
			('nss_base_passwd', 'ou=People'),
			('nss_base_shadow', 'ou=People'),
			('nss_base_group', 'ou=Groups'),
			('nss_base_hosts', 'ou=Hosts')
			)

		for (key, value) in defaults :
			if not hasattr(self, key):
				setattr(self, key, value)
	def enable(self):
		""" Do whatever is needed on the underlying system for the LDAP backend
		to be fully operational (this is really a "force_enable" method).
		This includes:
			- verify everything is installed
			- setup PAM-LDAP system files (the system must follow the licorn
				configuration and vice-versa)
			- setup slapd
			- setup nsswitch.conf

		-> raise an exception at any level if anything goes wrong.
		-> return True if succeed (this is probably useless due to to previous
		point).
		"""

		assert ltrace(TRACE_OPENLDAP, '| enable_backend()')

		if not ('ldap' in LMC.configuration.nsswitch['passwd'] and \
			'ldap' in LMC.configuration.nsswitch['shadow'] and \
			'ldap' in LMC.configuration.nsswitch['group']) :

			LMC.configuration.nsswitch['passwd'].append('ldap')
			LMC.configuration.nsswitch['shadow'].append('ldap')
			LMC.configuration.nsswitch['group'].append('ldap')
			LMC.configuration.save_nsswitch()

		self.check_system_files(batch=True)

		self.check(batch=True)

		"""
		for expression in (
			('passwd:.*ldap.*', ''),
			('passwd:.*ldap.*', ''),
			('passwd:.*ldap.*', ''),
		re.susbt(r'')
		"""
		return True
	def disable(self):
		""" make the LDAP backend inoperant. The receipe is simple, and follows
		what the system sees: just modify nsswitch.conf, and neither licorn nor
		PAM nor anything will use LDAP anymore.

		We don't "unsetup" slapd nor PAM-ldap because we think this is a bad
		thing thing to empty them if they have been in use. It is left to the
		system administrator to clean them up if wanted.
		"""

		assert ltrace(TRACE_OPENLDAP, '| disable_backend()')

		for key in ('passwd', 'shadow', 'group'):
			try:
				LMC.configuration.nsswitch[key].remove('ldap')
			except KeyError:
				pass

		LMC.configuration.save_nsswitch()

		return True
	def check(self, batch=False, auto_answer=None):
		""" check the OpenLDAP daemon configuration and set it up if needed. """

		if not self.available:
			return

		assert ltrace(TRACE_OPENLDAP, '> check(%s)' % (batch))

		if process.whoami() != 'root' and not self.bind_as_admin:
			logging.warning('''%s: you must be root or have cn=admin access'''
			''' to continue.''' % self.name)
			return

		self.sasl_bind()

		try:
			# load all config objects from the daemon.
			# there may be none, eg on a fresh install.
			#
			openldap_result = self.openldap_conn.search_s(
				'cn=config',
				pyldap.SCOPE_SUBTREE,
				'(objectClass=*)',
				['dn', 'cn'])

			# they will be checked later, extract them and keep them hot.
			dn_already_present = [ x for x,y in openldap_result ]

		except pyldap.NO_SUCH_OBJECT:
			dn_already_present = []

		try:
			# search for the frontend, which is not in cn=config
			openldap_result = self.openldap_conn.search_s(
				self.base,
				pyldap.SCOPE_SUBTREE,
				'(objectClass=*)',
				['dn', 'cn'])

			dn_already_present.extend([ x for x,y in openldap_result ])
		except pyldap.NO_SUCH_OBJECT:
			# just forget this error, the schema will be automatically added
			# if not found.
			pass

		# DEVEL DEBUG
		#
		#print dn_already_present
		#for dn, entry in openldap_result:
		#	ltrace(TRACE_OPENLDAP, '%s -> %s' % (dn, entry))

		# Here follows a list of which DN to check for presence, associated to
		# which openldap_schema to load if the corresponding DN is not present in
		# slapd configuration.
		defaults = (
			# SKIP dn: cn=config (should be already there at fresh install)
			# SKIP dn: cn=schema,cn=config (filled by followers)
			('cn={0}core,cn=schema,cn=config', 'core'),
			('cn={1}cosine,cn=schema,cn=config', 'cosine'),
			('cn={2}nis,cn=schema,cn=config', 'nis'),
			('cn={3}inetorgperson,cn=schema,cn=config', 'inetorgperson'),
			('cn={4}samba,cn=schema,cn=config', 'samba'),
			('cn={5}licorn,cn=schema,cn=config', 'licorn'),
			('cn=module{0},cn=config', 'backend.module'),
			('olcDatabase={1}hdb,cn=config', 'backend.hdb'),
			# ALREADY INCLUDED olcDatabase={-1}frontend,cn=config
			# ALREADY INCLUDED olcDatabase={0}config,cn=config
			# and don't forget the frontend, handled in a special way (not with
			# root user, but LDAP cn=admin).
			(self.base, 'frontend')
			)

		for dn, schema in defaults:
			if not dn in dn_already_present:
				if batch or logging.ask_for_repair('%s: %s lacks mandatory '
					'schema %s.' % (self.name, stylize(ST_PATH, 'slapd'),
						schema), auto_answer):

					# circumvent https://bugs.launchpad.net/ubuntu/+source/openldap/+bug/612525
					if schema == 'backend.hdb':
						try:
							logging.notice('disabling AppArmor profile for slapd.')
							os.system('echo -n /usr/sbin/slapd > /sys/kernel/security/apparmor/.remove')
						except Exception, e:
							logging.warning(e)

					if schema == 'frontend':
						# the frontend is a special case which can't be filled by root.
						# We have to bind as cn=admin, else it will fail with
						# "Insufficient privileges" error.
						self.bind()

					logging.info('%s: loading schema %s into slapd.' % (
						self.name, schema))

					for (dn, entry) in \
							ldaputils.LicornSmallLDIFParser(schema).get():
						try:
							logging.progress('''adding %s -> %s into '''
								'''schema %s.''' % (dn, entry, schema))

							self.openldap_conn.add_s(dn, ldaputils.addModlist(entry))
						except pyldap.ALREADY_EXISTS:
							logging.notice('skipping already present dn %s.' % dn)

					# circumvent https://bugs.launchpad.net/ubuntu/+source/openldap/+bug/612525
					if schema == 'backend.hdb':
						try:
							logging.notice('enabling AppArmor profile for slapd.')
							os.system('/sbin/apparmor_parser --write-cache --replace -- /etc/apparmor.d/usr.sbin.slapd')
						except Exception, e:
							logging.warning(e)

				else:
					# all these schemas are mandatory for Licorn to work,
					# we should not reach here.
					raise exceptions.LicornRuntimeError(
						'''Can't continue without altering slapd '''
						'''configuration.''')

		assert ltrace(TRACE_OPENLDAP, '< check()')
	def check_system_files(self, batch=False, auto_answer=None):
		""" Check that the underlying system is ready to go LDAP. """

		assert ltrace(TRACE_OPENLDAP, '> check_system_files()')

		if pyutils.check_file_against_dict(self.files.openldap_conf,
				(
					('base',         None),
					('uri',          None),
					('rootbinddn',   None),
					('pam_password', 'md5'),
					('ldap_version', 3)
				),
				LMC.configuration):

			# keep the values inside ourselves, to use afterwards.
			for (key, value) in readers.simple_conf_load_dict(
				self.files.openldap_conf).iteritems():
				setattr(self, key, value)

			#
			# TODO: check superfluous and custom directives.
			#

		try:
			if not os.path.exists(self.files.openldap_secret) or \
				open(self.files.openldap_secret).read().strip() == '':
				if batch or logging.ask_for_repair(_(u'{0}: {1} should '
								'contain your LDAP system password, but '
								'is currently empty. Fill it with a '
								'random password?').format(
								self.name,
								stylize(ST_SECRET, self.files.openldap_secret)),
							auto_answer=auto_answer):
					try:
						from licorn.foundations import hlstr
						genpass = hlstr.generate_password(
						LMC.configuration.users.min_passwd_size)

						logging.notice(_(u'{0}: autogenerated password for '
							'LDAP user {1}: "{2}". It is up to you to update '
							'the LDAP database with it, now.').format(self.name,
								stylize(ST_LOGIN, 'manager'),
								stylize(ST_SECRET, genpass)))

						open(self.files.openldap_secret, 'w').write(genpass + '\n')

						#
						# TODO: update the LDAP database… Without this point, the
						# purpose of this method is pretty pointless.
						#
					except (IOError, OSError), e:
						if e.errno == 13:
							raise exceptions.LicornRuntimeError(
								'''Insufficient permissions. '''
								'''Are you root?\n\t%s''' % e)
						else:
							raise
				else:
					raise exceptions.LicornRuntimeError(_(u'{0}: {1} is '
							'mandatory for {2} to work properly. Cannot '
							'continue without this, sorry!').format(self.name,
					self.files.openldap_secret, LMC.configuration.app_name))
		except (OSError, IOError), e :
			if e.errno != 13:
				raise

		#
		# TODO: check openldap_conf contents, or verify by researcu that it is
		# useless nowadays.
		#

		assert ltrace(TRACE_OPENLDAP, '< check_system() %s.' % stylize(
			ST_OK, 'True'))
		return True

	# LDAP specific methods
	def sasl_bind(self):
		"""
		Gain superadmin access to the OpenLDAP server.
		This is far more than simple "cn=admin,*" access.
		We are going to navigate the configuration and setup
		the server if needed.

		by the way, fix #133.
		"""

		assert ltrace(TRACE_OPENLDAP, 'binding as root in SASL/external mode.')

		import ldap.sasl as pyldapsasl
		auth=pyldapsasl.external()
		self.openldap_conn.sasl_interactive_bind_s('', auth)
	def bind(self, need_write_access=True):
		""" Bind as admin or user, when LDAP needs a stronger authentication."""
		assert ltrace(TRACE_OPENLDAP,'binding as %s.' % (
			stylize(ST_LOGIN, self.bind_dn)))

		if self.bind_as_admin:
			try:
				self.openldap_conn.bind_s(self.bind_dn, self.secret, pyldap.AUTH_SIMPLE)
			except pyldap.INVALID_CREDENTIALS:
				# in rare cases, the error could raise because the LDAP DB is
				# totally empty.
				# try to bind as root as a last resort, in case we can correct
				# the problem (we are probably in the first intialization of the
				# backend, checking for everything).
				self.sasl_bind()
		else:
			if process.whoami() == 'root':
				self.sasl_bind()
			else:
				if need_write_access:
					#
					# this will lamentably fail if current user is not in LDAP tree,
					# eg any system non-root user, any shadow user, etc. see
					# self.initialize() for details.
					#
					import getpass
					self.openldap_conn.bind_s(self.bind_dn,
						getpass.getpass('Please enter your LDAP password: '),
						pyldap.AUTH_SIMPLE)
				#else:
				# do nothing. We hit this case in all "get" commands, which
				# don't need write access to the LDAP tree. With this, standard
				# users can query the LDAP tree, without beiing bothered by a
				# password-ask; they will get back only the data they have read
				# access to, which seems quite fine.

	# backend implementation
	def load_Users(self):
		""" Load user accounts from /etc/{passwd,shadow} """

		def password_decode(value):
			try:
				# get around an error where password is not base64 encoded.
				password = decodestring(value.split('}',1)[1])
			except Exception:
				password = value
			return password
		def gecos_decode(value):
			try:
				# get around an error where password is not base64 encoded.
				gecos = decodestring(value)
			except:
				gecos = value

			return gecos

		assert ltrace(TRACE_OPENLDAP, '> load_users() %s' % self.nss_base_shadow)

		if process.whoami() == 'root':
			self.bind(False)

		try:
			openldap_result = self.openldap_conn.search_s(
									self.nss_base_shadow,
									pyldap.SCOPE_SUBTREE,
									'(objectClass=shadowAccount)')
		except pyldap.NO_SUCH_OBJECT:
			return

		try:
			for dn, entry in openldap_result:

				assert ltrace(TRACE_OPENLDAP, '  load_user(%s)' % entry)

				uid = int(entry['uidNumber'][0])

				yield uid, User(
					# Get the cn from the dn here, else we could end in a situation
					# where the user could not be deleted if it was created manually
					# and the cn is inconsistent.
					login=dn.split(',')[0][4:],     # rip out uid=
					uidNumber=uid,
					gidNumber=int(entry['gidNumber'][0]),
					homeDirectory=entry['homeDirectory'][0],
					loginShell=entry['loginShell'][0],
					gecos=gecos_decode(entry['gecos'][0]),
					userPassword=password_decode(entry['userPassword'][0]),
					shadowLastChange=entry.get('shadowLastChange', [ 0 ])[0],
					shadowMin=entry.get('shadowMax', [ 99999 ])[0],
					shadowMax=entry.get('shadowMin', [ 0 ])[0],
					shadowWarning=entry.get('shadowWarning', [ 7 ])[0],
					shadowInactive=entry.get('shadowInactive', [ 0 ])[0],
					shadowExpire=entry.get('shadowExpire', [ 0 ])[0],
					shadowFlag=entry.get('shadowFlag', [ '' ])[0],
					backend=self
					)

				"""
								shadowLastChange=int(entry['shadowLastChange'][0])
										if 'shadowLastChange' in entry else 0,
					shadowMin=int(entry['shadowMax'][0])
									if 'shadowMax' in entry else 99999,
					shadowMax=int(entry['shadowMin'][0])
									if 'shadowMin' in entry else 0,
					shadowWarning=int(entry['shadowWarning'][0])
									if 'shadowWarning' in entry else 7,
					shadowInactive=int(entry['shadowInactive'][0])
									if 'shadowInactive' in entry else 0,
					shadowExpire=int(entry['shadowExpire'][0])
									if 'shadowExpire' in entry else 0,
					shadowFlag=str(entry['shadowFlag'][0])
									if 'shadowFlag' in entry else '',
				"""

				#ltrace(TRACE_OPENLDAP, 'userPassword: %s' % temp_user_dict['userPassword'])
		except KeyError, e:
			logging.warning(_(u'{0}: skipped account {1} (was: '
				'KeyError on field {2}).').format(
					stylize(ST_NAME, self.name),
					stylize(ST_NAME, dn),
					e))
			pass

		assert ltrace(TRACE_OPENLDAP, '< load_users()')
	def load_Groups(self):
		""" Load groups from /etc/{group,gshadow} and /etc/licorn/group. """

		assert ltrace(TRACE_OPENLDAP, '> load_groups() %s' % self.nss_base_group)

		try:
			openldap_result = self.openldap_conn.search_s(
				self.nss_base_group,
				pyldap.SCOPE_SUBTREE,
				'(objectClass=posixGroup)')
		except pyldap.NO_SUCH_OBJECT:
			return

		for dn, entry in openldap_result:

			assert ltrace(TRACE_OPENLDAP, '  load_group(%s).' % entry)

			gid  = int(entry['gidNumber'][0])


			for key, func in (
				):
				if entry.has_key(key):
					temp_group_dict[key] = func(entry[key][0])

			yield gid, Group(
				# Get the cn from the dn here, else we could end in a situation
				# where the group could not be deleted if it was created manually
				# and the cn is inconsistent.
				name=dn.split(',')[0][3:],
				gidNumber=gid,
				memberUid=entry.get('memberUid', []),
				userPassword=entry.get('userPassword', [ 'x' ])[0],
				groupSkel=entry.get('groupSkel', [ None ])[0],
				description=entry.get('description', [ '' ])[0],
				backend=self
				)

		assert ltrace(TRACE_OPENLDAP, '< load_groups()')
	def save_Users(self, users):
		""" save users into LDAP, but only those who need it. """

		for user in users:
			if user.backend.name != self.name:
				continue

			self.save_User(user)
	def save_Groups(self, groups):
		""" Save groups into LDAP, but only those who need it. """

		for group in groups:
			if group.backend.name != self.name:
				continue

			self.save_Group(group)
	def save_User(self, orig_user, mode):
		""" Save one user in the LDAP backend.
			If updating, the entry will be dropped prior of insertion. """

		# we have to duplicate the data, to avoid #206
		# in fact, this allows to keep only what we want in the backend,
		# without bothering about other backends / extensions additions.
		user = {
				# Create these required fields.
				'cn'            : orig_user.login,
				'uid'           : orig_user.login,
				'sn'            : orig_user.gecos,
				'givenName'     : orig_user.gecos,
				# basic shadow data.
				'uidNumber'     : orig_user.uidNumber,
				'gidNumber'     : orig_user.gidNumber,
				'loginShell'    : orig_user.loginShell,
				'homeDirectory' : orig_user.homeDirectory,
				# GECOS is IA5 only (ASCII 7bit). Anyway, it seems not used
				# nowadays, and CN is prefered. We fill it for [put anything
				# usefull here] purposes only.
				'gecos'         : encodestring(orig_user.gecos).strip(),

				# prepare this field in the form slapd expects it.
				'userPassword'  : '{SHA}%s' % encodestring(
												orig_user.userPassword).strip()
			}

		# OpenLDAP behaves differently than shadow, when talking about
		# rarely or unused shadow* attributes. We must protect them.
		if orig_user.shadowExpire != 0:
			user['shadowExpire'] = orig_user.shadowExpire

		if orig_user.shadowFlag != '':
			user['shadowFlag'] = orig_user.shadowFlag

		if orig_user.shadowInactive != '':
			user['shadowInactive'] = orig_user.shadowInactive

		# keep other shadow attributes
		user['shadowMin']        = orig_user.shadowMin
		user['shadowMax']        = orig_user.shadowMax
		user['shadowWarning']    = orig_user.shadowWarning
		user['shadowLastChange'] = orig_user.shadowLastChange

		try:
			self.bind()

			if mode == backend_actions.UPDATE:

				(dn, old_entry) = self.openldap_conn.search_s(
									self.nss_base_shadow,
									pyldap.SCOPE_SUBTREE,
									'(uid=%s)' % orig_user.login)[0]

				assert ltrace(TRACE_OPENLDAP, 'update user %s: %s\n%s' % (
					stylize(ST_LOGIN, orig_user.login),
					old_entry,
					ldaputils.modifyModlist(old_entry, user,
						ignore_oldexistent=1)))

				self.openldap_conn.modify_s(dn, ldaputils.modifyModlist(
					old_entry, user, ignore_oldexistent=1))

			elif mode == backend_actions.CREATE:

				# prepare the LDAP entry like the LDAP daemon assumes it will
				# be : add or change necessary fields.
				user['objectClass'] = [
						'inetOrgPerson',
						'posixAccount',
						'shadowAccount'
					]

				assert ltrace(TRACE_OPENLDAP, 'add user %s: %s' % (
					stylize(ST_LOGIN, orig_user.login),
					ldaputils.addModlist(user)))

				self.openldap_conn.add_s('uid=%s,%s' % (
					orig_user.login, self.nss_base_shadow),
					ldaputils.addModlist(user))
			else:
				logging.warning('%s: unknown mode %s for user %s(uid=%s).' %(
					self.name, mode, orig_user.login, orig_user.uid))
		except (
				pyldap.NO_SUCH_OBJECT,
				pyldap.INVALID_CREDENTIALS,
				pyldap.STRONG_AUTH_REQUIRED
			), e:
			logging.warning(e[0]['desc'])
	def save_Group(self, orig_group, mode):
		""" Save one group in the LDAP backend.
			If updating, the entry will be dropped prior of insertion. """

		# we have to duplicate into a dict, because pyldap wants that. This
		# allows to ignore extensions and Licorn® specific data without
		# bothering about new attributes.
		group = {
				# LDAP specific fields.
				'cn'          : orig_group.name,
				# our fields, shadow ones.
				# cn IS name. 'name' is forbidden.
				#'name'        : orig_group.name,
				'gidNumber'   : orig_group.gidNumber,
				'memberUid'   : orig_group.memberUid,
				'description' : orig_group.description,
			}

		if orig_group.is_standard:
			group['groupSkel'] = orig_group.groupSkel

		# not yet
		#group['memberGid'] = orig_group.memberGid

		try:
			self.bind()

			if mode == backend_actions.UPDATE:

				(dn, old_entry) = self.openldap_conn.search_s(
									self.nss_base_group,
									pyldap.SCOPE_SUBTREE,
									'(cn=%s)' % orig_group.name)[0]

				assert ltrace(TRACE_OPENLDAP,'updating group %s.' % \
					stylize(ST_LOGIN, orig_group.name))

				self.openldap_conn.modify_s(dn, ldaputils.modifyModlist(
					old_entry, group, ignore_oldexistent=1))
			elif mode == backend_actions.CREATE:

				assert ltrace(TRACE_OPENLDAP,'creating group %s.' % (
					stylize(ST_LOGIN, orig_group.name)))

				group['objectClass'] = [
						'posixGroup',
						'licornGroup'
					]

				self.openldap_conn.add_s('cn=%s,%s' % (
					orig_group.name, self.nss_base_group),
					ldaputils.addModlist(group))
			else:
				logging.warning('%s: unknown mode %s for group %s(gid=%s).' % (
					self.name, mode, orig_group.name, orig_group.gid))
		except (
				pyldap.NO_SUCH_OBJECT,
				pyldap.INVALID_CREDENTIALS,
				pyldap.STRONG_AUTH_REQUIRED
			), e:
			# there is also e['info'] on ldap.STRONG_AUTH_REQUIRED, but
			# it is just repeat.
			logging.warning(e[0]['desc'])
	def delete_User(self, user):
		""" Delete one user from the LDAP backend. """
		assert ltrace(TRACE_OPENLDAP, '| delete_User(%s)' % user.login)

		try:
			self.bind()
			self.openldap_conn.delete_s('uid=%s,%s' % (
										user.login, self.nss_base_shadow))

		except pyldap.NO_SUCH_OBJECT:
			pass
		# except BAD_BIND:
		#	pass
	def delete_Group(self, group):
		""" Delete one group from the LDAP backend. """
		assert ltrace(TRACE_OPENLDAP, '| delete_Group(%s)' % group.name)

		try:
			self.bind()
			self.openldap_conn.delete_s('cn=%s,%s' % (
										group.name, self.nss_base_group))

		except pyldap.NO_SUCH_OBJECT:
			pass
		# except BAD_BIND:
		#	pass
	def compute_password(self, password, salt=None):
		assert ltrace(TRACE_OPENLDAP, '| compute_password(%s, %s)' % (password, salt))
		return hashlib.sha1(password).digest()

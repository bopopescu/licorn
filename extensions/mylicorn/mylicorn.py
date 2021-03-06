# -*- coding: utf-8 -*-
"""
Licorn extensions: mylicorn - http://docs.licorn.org/extensions/mylicorn

:copyright: 2012 Olivier Cortès <olive@licorn.org>

:license: GNU GPL version 2

"""

import os, time, urllib2, random, errno, socket


from licorn.foundations           import exceptions, logging, settings
from licorn.foundations           import events, json, hlstr, pyutils
from licorn.foundations.workers   import workers
from licorn.foundations.styles    import *
from licorn.foundations.ltrace    import *
from licorn.foundations.ltraces   import *
from licorn.foundations.threads   import Event, RLock

from licorn.foundations.base      import ObjectSingleton, Enumeration
from licorn.foundations.constants import host_types, priorities, host_status

from licorn.daemon.threads        import LicornJobThread

from licorn.core                  import LMC, version
from licorn.core.classes          import only_if_enabled
from licorn.extensions            import LicornExtension

# local imports; get the constants in here for easy typing/using.
from constants import *

LicornEvent = events.LicornEvent

# We communicate with MyLicorn® via the JSON-RPC protocol.
from licorn.contrib import jsonrpc

def random_delay(delay_min=900, delay_max=5400):
	return float(random.randint(delay_min, delay_max))
def print_web_exception(e):

	try:
		error = json.loads(e.read())['error']

	except:
		# if 'error' is not present, the remote server is not in debug mode.
		# Do not try to display anything detailled, there won't be.
		logging.warning('Remote web exception: %s\n\tRequest:\n\t\t%s\n\t%s' % (e,
			str(e.info()).replace('\n', '\n\t\t'),
			str(json.loads(e.read())).replace('\n', '\n\t\t')))

	else:
		try:
			logging.warning('Remote web exception: %s\n\tRequest:\n\t\t%s\n\t%s' % (e,
				str(e.info()).replace('\n', '\n\t\t'), error['stack'].replace('\n', '\n\t\t')))
		except:
			logging.warning('Remote web exception: %s\n\tRequest:\n\t\t%s\n\t%s' % (e,
				str(e.info()).replace('\n', '\n\t\t'), str(error).replace('\n', '\n\t\t')))

class MylicornExtension(ObjectSingleton, LicornExtension):
	""" Provide auto-retrying connection and remote calls to the
		``my.licorn.org`` services and API.

		.. versionadded:: 1.4
	"""
	def __init__(self):
		assert ltrace_func(TRACE_MYLICORN)
		LicornExtension.__init__(self, name='mylicorn')

		# advertise if we are connected via a standard event.
		self.events.connected = Event()

		self.paths.config_file = os.path.join(settings.config_dir, 'mylicorn.conf')

		self.result = Enumeration()
		self.result.code = None
		self.result.mesg = None

		# unknown reachable status
		self.__is_reachable = None
	@property
	def reachable(self):
		""" R/O property indicating if the current server can be reached from
			internet.

			The return value is one of:

			* ``True`` if it is.
			* ``False`` if it is not.
			* ``None`` if undetermined. This will be the case until the central
				server has tried to reach us from the outside. Every time the
				local server's authenticates, or its public address changes,
				the status will be “ `unknown` ” for a few seconds (at most 30,
				but this depends on the central server load, too).
		"""
		return self.__is_reachable
	@property
	def connected(self):
		""" R/O property that returns ``True`` if the daemon is currently
			connected to the central `MyLicorn®` service, which means that:

			* it has successfully authenticated,
			* the regular updater thread is running.

			``False`` will be returned until the first updater call has
			completed, which is nearly immediate after authentication.
		"""
		return self.events.connected.is_set()
	@property
	def api_key(self):
		""" R/W property to set or get the current `MyLicorn®` API key. """
		return self.__api_key
	@api_key.setter
	def api_key(self, api_key):
		if not hlstr.cregex['api_key'].match(api_key):
			raise exceptions.BadArgumentError(_(u'Bad API key "{0}", must '
						u'match "{1}/i"').format(api_key, hlstr.regex['api_key']))

		# TODO: if connected: check the API key is valid.

		self.__api_key = api_key

		self.__save_configuration(api_key=self.__api_key)
	def initialize(self):
		""" Module related method. The MyLicorn® extension is considered always
			available, it has no external service dependancy.

			At worst is it “ disconnected ” when there is no internet
			connection, but that's not enough to disable it.

			This method will make usage of an optional environment variable
			named after ``MY_LICORN_URI``, that should contain an address to
			any central server of your choice providing the `MyLicorn®`
			JSON-RPC API. The default is ``http://my.licorn.org/``. It is

			.. note:: no need to include the trailing ``/json/`` in the web
				address, it will be automatically added.

		"""

		assert ltrace_func(TRACE_MYLICORN)
		self.available = True

		# Allow environment override for testing / development.
		if 'MY_LICORN_URI' in os.environ:
			MY_LICORN_URI = os.environ.get('MY_LICORN_URI')
			logging.notice(_(u'{0}: using environment variable {1} pointing '
				u'to {2}.').format(self.pretty_name,
					stylize(ST_NAME, 'MY_LICORN_URI'),
					stylize(ST_URL, MY_LICORN_URI)))
		else:
			# default value, pointing to official My Licorn® webapp.
			MY_LICORN_URI = 'http://my.licorn.org/'

		if MY_LICORN_URI.endswith('/'):
			MY_LICORN_URI = MY_LICORN_URI[:-1]

		if not MY_LICORN_URI.endswith('/json'):
			# The ending '/' is important, else POST returns 301,
			# GET returns 400, and everything fails in turn…
			MY_LICORN_URI += '/json/'

		self.my_licorn_uri = MY_LICORN_URI

		defaults = { 'api_key': None }
		data     = defaults.copy()

		try:
			with open(self.paths.config_file) as f:
				data.update(json.load(f))

		except (OSError, IOError), e:
			if e.errno != errno.ENOENT:
				raise e

		except:
			logging.warning(_(u'{0}: configuration file {1} seems '
								u'corrupt; not using it.').format(self,
							stylize(ST_PATH, self.paths.config_file)))

		klass = self.__class__.__name__

		# only take in data the parameters we know, avoiding collisions.
		for key in defaults:
			setattr(self, '_%s__%s' % (klass, key), data[key])

		self.anonymize = pyutils.resolve_attr(
				'settings.extensions.mylicorn.datasrc.all.anonymize.enabled',
					{'settings': settings}, False)

		self.anonymize_full = pyutils.resolve_attr(
				'settings.extensions.mylicorn.datasrc.all.anonymize.full',
					{'settings': settings}, False)

		return self.available
	def is_enabled(self):
		""" Module related method. Always returns ``True``, unless the extension
			is manually ignored in the server configuration. """

		self.service = jsonrpc.ServiceProxy(self.my_licorn_uri)

		logging.info(_(u'{0}: extension always enabled unless manually '
							u'ignored in {1}.').format(self.pretty_name,
								stylize(ST_PATH, settings.main_config_file)))
		return True
	def enable(self):
		logging.warning(_(u'{0}: not meant to be disabled. Ignore the '
						u'extension in {2} if you really want this.').format(
							self.pretty_name, stylize(ST_ATTR, 'disable()'),
								stylize(ST_PATH, settings.main_config_file)))
		return True
	def disable(self):
		logging.warning(_(u'{0}: not meant to be disabled. Mark the extension '
						u'ignored in {2} if you really want this.').format(
							self.pretty_name, stylize(ST_ATTR, 'disable()'),
								stylize(ST_PATH, settings.main_config_file)))
		return False
	def __save_configuration(self, **kwargs):

		basedict = {}

		if os.path.exists(self.paths.config_file):
			basedict.update(json.load(open(self.paths.config_file, 'r')))

		basedict.update(kwargs)

		json.dump(basedict, open(self.paths.config_file, 'w'))

		LicornEvent('extension_mylicorn_configuration_changed', **kwargs).emit()

	@events.handler_method
	@only_if_enabled
	def licornd_cruising(self, *args, **kwargs):
		""" Event handler that will start the authentication process when
			Licornd is `cruising`, which means “ `everything is ready, boys` ”. """

		self.authenticate()

	@events.handler_method
	# Doesn't need @only_if_enabled, it won't be trigerred unless enabled.
	def extension_mylicorn_authenticated(self, *args, **kwargs):
		""" Event handler that will start the updater thread once we are
			successfully authenticated on the central server. """

		# We authenticated, the server will eventually
		# update our reachability status if our public
		# IP changed. Get this information back.
		workers.network_enqueue(priorities.NORMAL,
								self.update_reachability,
								# Wait a little for the server
								# to have performed the test.
								job_delay=20.0)

		self.__start_updater_thread()

	@events.handler_method
	# Doesn't need @only_if_enabled, it won't be trigerred unless enabled.
	def extension_mylicorn_configuration_changed(self, *args, **kwargs):
		""" Event handler triggered by an API key change; will call
			:meth:`disconnect` and then :meth:`authenticate` to benefit from
			the new API key. """

		if 'api_key' in kwargs:
			self.disconnect()
			self.authenticate()

	@events.handler_method
	@only_if_enabled
	def system_sleeping(self, *args, **kwargs):
		self.disconnect(host_status.SLEEPING)

	@events.handler_method
	@only_if_enabled
	def system_resuming(self, *args, **kwargs):
		# wait a little for network interfaces to be back UP,
		# even more if we are only on wifi, it can take ages.

		self.retrigger_authenticate(short=True)

	@events.handler_method
	@only_if_enabled
	def daemon_is_restarting(self, *args, **kwargs):
		self.disconnect(host_status.BOOTING)

	@events.handler_method
	@only_if_enabled
	def daemon_shutdown(self, *args, **kwargs):
		""" Event handler that will disconnect from the central server when
			the daemon shuts down.

			Any exception will be just printed with no other consequence.

			Obviously, this handler runs only if the extension is enabled.
		"""

		self.disconnect(host_status.OFFLINE)

	def __start_updater_thread(self):

		if not self.events.connected.is_set():
			self.events.connected.set()

			self.threads.updater = LicornJobThread(
								target=self.update_remote_informations,
								# informations are updated every half-hour by default.
								delay=1800,
								tname='extensions.mylicorn.updater',
								# first noop() is in half an hour,
								# we have just authenticated.
								time=(time.time()+1800),
								)

			self.threads.updater.start()

			logging.info(_(u'{0}: updater thread started.').format(self.pretty_name))
			self.licornd.collect_and_start_threads(collect_only=True,
													full_display=False)
	def __stop_updater_thread(self):

		if self.events.connected.is_set():
			try:
				self.threads.updater.stop()
				del self.threads.updater

			except:
				logging.exception(_(u'{0}: exception while stopping '
										u'updater thread'),	self.pretty_name)

			# Back to "unknown" reachable state
			self.__is_reachable = None

			# and not connected, because not emitting to central.
			self.events.connected.clear()

			logging.info(_(u'{0}: updater thread stopped.').format(self.pretty_name))
	def __remote_call(self, rpc_func, *args, **kwargs):

		with self.locks._global:

			# In case we want to know precisely what crashed.
			self.result.func   = rpc_func
			self.result.args   = args
			self.result.kwargs = kwargs

			try:
				result = rpc_func(*args, **kwargs)

			except Exception, e:
				if isinstance(e, urllib2.HTTPError):
					try:
						print_web_exception(e)

					except:
						logging.exception(_(u'{0}: error decoding web exception '
											u'{1} from failed execution of {2}'),
												self.pretty_name, e, rpc_func.__name__)
				else:
					logging.exception(_(u'{0}: error while executing {1}'),
												self.pretty_name, rpc_func.__name__)

				self.result.code = common.FAILED
				self.result.mesg = _(u'Remote call of procedure “%s” failed '
						u'(network or MyLicorn® issue).') % rpc_func.__name__

			else:
				self.result.code = result['result']
				self.result.mesg = result['message']

			# return it in an easy usable form for callers.
			return self.result.code, self.result.mesg
	def retrigger_authenticate(self, short=False):

		if short:
			# We need to wait a little, wifi interface can take
			# ages to reconnect on resume.
			#
			# TODO: use network-manager instead of just delaying
			# after resume.
			delay_min = 45
			delay_max = 90

		else:
			# a standard retrigger (after an error) should wait,
			# but not that much in case the failure was transient.
			delay_min = 300
			delay_max = 900

		delay = random_delay(delay_min=delay_min, delay_max=delay_max)

		logging.info(_(u'{0}: reprogramming authentication in {1}.').format(
						self.pretty_name, pyutils.format_time_delta(delay)))

		workers.network_enqueue(priorities.NORMAL, self.authenticate, job_delay=delay)
	def __auth_infos(self):
		""" Return all arguments for the `authenticate()` RPC call. """

		try:
			system_start_time = time.time() - float(
								open('/proc/uptime').read().split(" ")[0])

		except:
			system_start_time = None

		try:
			os_version = open('/proc/version_signature').read().strip()

		except:
			os_version = '<undetermined>'

		try:
			hostname = socket.gethostname()

		except:
			hostname = '<undetermined>'

		return 	(
					LMC.configuration.system_uuid,
					self.api_key,
					system_start_time,
					self.licornd.dstart_time,
					version,
					# TODO: do not hardcode this.
					host_types.LINUX,
					os_version,
					LMC.configuration.distro,
					LMC.configuration.distro_version,
					LMC.configuration.distro_codename,
					hostname
				)
	def disconnect(self, status=None):
		""" Disconnect from the central server, and BTW stop advertising our
			status regularly there. """
		assert ltrace_func(TRACE_MYLICORN)

		if self.connected:

			LicornEvent('extension_mylicorn_disconnects').emit(synchronous=True)

			self.__stop_updater_thread()

			code, message = self.__remote_call(self.service.disconnect,
										status or host_status.SHUTTING_DOWN)

			if code < 0:
				# if authentication goes wrong, we won't even try to do anything
				# more. Every RPC call needs authentication.
				logging.warning(_(u'{0}: failed to disconnect (code: {1}, '
									u'message: {2})').format(
										self.pretty_name,
										stylize(ST_UGID, disconnect[code]),
										stylize(ST_COMMENT, message)))

			else:
				logging.info(_(u'{0}: sucessfully disconnected (code: {1}, '
								u'message: {2})').format(
									self.pretty_name,
									stylize(ST_UGID, disconnect[code]),
									stylize(ST_COMMENT, message)))

				LicornEvent('extension_mylicorn_disconnected').emit()

		else:
			logging.warning(_(u'{0}: already disconnected, not trying '
									u'again.').format(self.pretty_name))
	def authenticate(self):
		""" Authenticate ourselves on the central server. """

		assert ltrace_func(TRACE_MYLICORN)

		if self.connected:
			logging.warning(_(u'{0}: already connected, not doing '
									u'it again.').format(self.pretty_name))
			return

		if LMC.configuration.system_uuid in (None, ''):
			logging.warning(_(u'{0}: system UUID not found, aborting. There '
									u'may be a serious problem '
									u'somewhere.').format(self.pretty_name))
			return

		# NOTE: the arguments must match the ones from the
		# My.Licorn.org `authenticate()` JSON-RPC method.
		code, message = self.__remote_call(self.service.authenticate, *self.__auth_infos())

		if code < 0:
			# if authentication goes wrong, we won't even try to do anything
			# more. Every RPC call needs authentication.
			logging.warning(_(u'{0}: failed to authenticate (code: {1}, '
								u'message: {2})').format(self.pretty_name,
									stylize(ST_UGID, authenticate[code]),
									stylize(ST_COMMENT, message)))
			self.retrigger_authenticate()
		else:
			logging.info(_(u'{0}: sucessfully authenticated (code: {1}, '
							u'message: {2})').format(self.pretty_name,
								stylize(ST_UGID, authenticate[code]),
								stylize(ST_COMMENT, message)))

			LicornEvent('extension_mylicorn_authenticated').emit()
	def update_reachability(self):
		""" Ask the central server if we are reachable from the
			Internet or not. This call gives an immediate answer, however
			the answer can be “ undetermined ” (``None``), which means we
			will have to retry later to get a real ``True`` / ``False``
			satisfying value.
		"""

		# Unknown status by default
		self.__is_reachable = None

		code, message = self.__remote_call(self.service.is_reachable)

		if code == is_reachable.SUCCESS:
			self.__is_reachable = True

		elif code == is_reachable.UNREACHABLE:
			self.__is_reachable = False

		logging.info(_(u'{0}: our reachability state is now {1}.').format(
					self.pretty_name, stylize(ST_ATTR, is_reachable[code]
												if code in (is_reachable.SUCCESS, is_reachable.UNREACHABLE)
												else _('UNKNOWN'))))
	def update_remote_informations(self):
		""" Method meant to be run from the updater Thread, which can also be
			run manually at will from the daemon's console. It will run ``noop()``
			remotely, to trigger a remote information update from the HTTP
			request contents. From our point of view, this is just a kind of
			``ping()``.
		"""
		code, message = self.__remote_call(self.service.noop)

		if code < 0:
			logging.warning(_(u'{0}: problem noop()\'ing {1} (was: code={2}, '
									u'message={3}).').format(self.pretty_name,
										stylize(ST_URL, self.my_licorn_uri),
										stylize(ST_UGID, authenticate[code]),
										stylize(ST_COMMENT, message)))

			# any [remote] exception will halt the current thread, and
			# re-trigger a full pass of "authentication-then-regularly-update"
			# after having waited one hour to make things settle.
			self.__stop_updater_thread()

			workers.network_enqueue(priorities.NORMAL, self.authenticate,
													job_delay=random_delay())

		else:
			logging.info(_(u'{0}: successfully noop()\'ed {1}.').format(
						self.pretty_name, stylize(ST_URL, self.my_licorn_uri)))

			# wait a little for the central server to have tested our
			# reachability before asking for it back.
			workers.network_enqueue(priorities.NORMAL, self.update_reachability,
																job_delay=20.0)

			workers.network_enqueue(priorities.LOW, self.update_histories)
	def update_histories(self):

		def upload_latest_data(history_name, last_known_sha1):
			import_sym_path = 'licorn.extensions.mylicorn.datasrc.%s' % history_name
			data_src_class_ = history_name.title() + 'DataSource'
			data_src_module = __import__(import_sym_path, fromlist=[import_sym_path])
			data_src_klass  = getattr(data_src_module, data_src_class_)

			anonymize = pyutils.resolve_attr(
				'settings.extensions.mylicorn.datasrc.{0}.anonymize.enabled'.format(
					history_name), {'settings': settings}, self.anonymize)

			anonymize_full = pyutils.resolve_attr(
				'settings.extensions.mylicorn.datasrc.{0}.anonymize.full'.format(
					history_name), {'settings': settings}, self.anonymize_full)

			logging.progress(_(u'{0}: uploading {1}{2} history data, starting '
								u'from hash {3}…').format(self.pretty_name,
									_(u'fully anonymized ')
										if anonymize and anonymize_full
										else _(u'anonymized ')
											if anonymize else u'',
									stylize(ST_ATTR, history_name),
									stylize(ST_COMMENT, last_known_sha1)))

			data_to_upload = list(data_src_klass(last=last_known_sha1,
											anonymize=anonymize,
											anonymize_full=anonymize_full).iter())

			if data_to_upload:
				code, message = self.__remote_call(self.service.update_history,
												history_name, data_to_upload)

				if code < 0:
					logging.warning(_(u'{0}: problem uploading {1} history '
								u'data (was: code={2}, message={3}).').format(
									self.pretty_name,
									stylize(ST_ATTR, history_name),
									stylize(ST_UGID, update_history[code]),
									stylize(ST_COMMENT, message)))

				else:
					logging.info(_(u'{0}: successfully uploaded / updated {1} '
									u'history data at {2}.').format(
										self.pretty_name,
										stylize(ST_ATTR, history_name),
										stylize(ST_URL, self.my_licorn_uri)))
			else:
				logging.info(_(u'{0}: no new data to send for {1} '
								u'history since last upload.').format(
									self.pretty_name,
									stylize(ST_ATTR, history_name)))

		for history_name in ('wtmp', ):
			code, message = self.__remote_call(self.service.update_history,
										# history_name, history_data, query_last
										history_name,	None, 			True)

			if code < 0:
				logging.warning(_(u'{0}: problem querying for last {1} history '
							u'value, skipping to next (was: code={2}, '
							u'message={3}).').format(self.pretty_name,
											stylize(ST_ATTR, history_name),
											stylize(ST_UGID, update_history[code]),
											stylize(ST_COMMENT, message)))

			else:
				upload_latest_data(history_name, message)

__all__ = ('MylicornExtension', )

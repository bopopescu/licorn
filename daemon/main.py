#!/usr/bin/python -OO
# -*- coding: utf-8 -*-
"""
Licorn® daemon:
  - monitor shared group dirs and other special paths, and reapply posix
	perms and posix1e ACsL the Way They Should Be (TM) (as documented in posix1e
	manuals).
  - crawls against all shared group dirs, indexes metadata and provides a global
    search engine for all users.

This daemon exists:
  - to add user functionnality to Licorn® systems.
  - because of bugs in external apps (which don't respect posix1e semantics and
	can't or won't be fixed easily).

Copyright (C) 2005-2010 Olivier Cortès <olive@deep-ocean.net>.
Licensed under the terms of the GNU GPL version 2.
"""

# import this first, this will initialize start_time.
# these objects are just containers which are empty yet.
from licorn.daemon import dname, dthreads, dqueues, dchildren

_app = {
	"name"       : "licornd",
	"description": '''Licorn® Daemon: posix1e ACL auto checker, Web ''' \
		'''Management Interface server and file meta-data crawler''',
	"author"     : "Olivier Cortès <olive@deep-ocean.net>"
	}

import os, signal, time
from Queue     import Queue
from threading import Thread

from licorn.foundations           import options, logging, exceptions
from licorn.foundations           import process, network
from licorn.foundations.styles    import *
from licorn.foundations.ltrace    import ltrace
from licorn.foundations.constants import licornd_roles

from licorn.core                  import LMC

from licorn.daemon                import terminate, setup_signals_handler
from licorn.daemon.core           import  exit_if_already_running, \
										refork_if_not_running_root_or_die, \
										eventually_daemonize, \
										licornd_parse_arguments
from licorn.daemon.wmi            import fork_wmi
from licorn.daemon.threads        import LicornJobThread, \
									LicornPoolJobThread, \
									LicornInteractorThread, \
									thread_periodic_cleaner
from licorn.daemon.aclchecker     import ACLChecker
from licorn.daemon.inotifier      import INotifier
from licorn.daemon.cmdlistener    import CommandListener
from licorn.daemon.network        import pool_job_pinger, \
										pool_job_pyrofinder, \
										pool_job_reverser, \
										pool_job_arppinger, \
										thread_network_links_builder, \
										thread_periodic_scanner
#from licorn.daemon.scheduler     import BasicScheduler
#from licorn.daemon.cache         import Cache
#from licorn.daemon.searcher      import FileSearchServer
#from licorn.daemon.syncer        import ServerSyncer, ClientSyncer

if __name__ == "__main__":

	LMC.init_conf(batch=True)

	exit_if_already_running()
	refork_if_not_running_root_or_die()

	(opts, args) = licornd_parse_arguments(_app)

	# BATCH is needed generally in the daemon, because it is per nature a
	# non-interactive process. At first launch, it will have to tweak the system
	# a little (in some conditions), and won't be able to as user / admin if
	# forked in the background. It must have the ability to solve relatively
	# simple problems on its own. Only --force related questions will make it
	# stop, and there should not be any of these in its daemon's life.
	opts.batch = True
	options.SetFrom(opts)
	del opts, args

	pname = '%s/master@%s' % (dname,
		licornd_roles[LMC.configuration.licornd.role].lower())

	process.set_name(pname)
	eventually_daemonize()

	pids_to_wake = []

	if options.pid_to_wake:
		pids_to_wake.append(options.pid_to_wake)

	if LMC.configuration.licornd.role == licornd_roles.SERVER:
		# the WMI must be launched before the setup of signals.
		if LMC.configuration.licornd.wmi.enabled and options.wmi_enabled:
			dchildren.wmi_pid = fork_wmi()
			pids_to_wake.append(dchildren.wmi_pid)
		else:
			logging.info('''%s: not starting WMI, disabled on command line '''
				'''or by configuration directive.''' % pname)

	# log things after having daemonized, else it doesn't show in the log,
	# but on the terminal.
	logging.notice("%s(%d): starting all threads." % (
		pname, os.getpid()))

	setup_signals_handler(pname)

	LMC.init()

	# FIXME: why do that ?
	options.msgproc = LMC.msgproc

	if LMC.configuration.licornd.role == licornd_roles.CLIENT:

		dthreads.cmdlistener = CommandListener(dname,
			pids_to_wake=pids_to_wake)

		#dthreads.syncer = ClientSyncer(dname)

		# TODO: get the cache from the server, it has the
		# one in sync with the NFS-served files.

	else: # licornd_roles.SERVER

		#dthreads.syncer   = ServerSyncer(dname)
		#dthreads.searcher = FileSearchServer(dname)
		#dthreads.cache    = Cache(keywords, dname)

		if LMC.configuration.licornd.threads.pool_members == 0:
			logging.warning('''Status gathering of unmanaged network '''
					'''clients disabled by configuration rule.''')
		else:
			# launch a machine status update every 30 seconds. The first update
			# will be run ASAP (in 1 second), else we don't have any info to display
			# if opening the WMI immediately.
			dthreads.network_builder = LicornJobThread(dname,
				target=thread_network_links_builder,
				time=(time.time()+1.0), count=1, tname='NetworkLinksBuilder')

		#dthreads.periodic_scanner = LicornJobThread(dname,
		#	target=LMC.machines.thread_periodic_scanner,
		#	time=(time.time()+10.0), delay=30.0, tname='PeriodicNetworkScanner')

		dthreads.cleaner = LicornJobThread(dname,
			target=thread_periodic_cleaner,
			time=(time.time()+30.0),
			delay=LMC.configuration.licornd.threads.wipe_time,
			tname='PeriodicThreadsCleaner')

		dthreads.aclchecker = ACLChecker(None, dname)

		if LMC.configuration.licornd.inotifier.enabled:
			dthreads.inotifier = INotifier(dname, options.no_boot_check)

		dthreads.cmdlistener = CommandListener(dname=dname,
			pids_to_wake=pids_to_wake)

		# machines to be pinged across the network, to see if up or not.
		dqueues.pings = Queue()

		# machines to be arp pinged across the network, to find ether address.
		dqueues.arppings = Queue()

		# IPs to be reverse resolved to hostnames.
		dqueues.reverse_dns = Queue()

		# machines to be scanned for pyro presence
		dqueues.pyrosys = Queue()

		for i in range(0, LMC.configuration.licornd.threads.pool_members):
			tname = 'Pinger-%d' % i
			setattr(dthreads, tname.lower(), LicornPoolJobThread(pname=dname,
				tname=tname, in_queue=dqueues.pings,
				target=pool_job_pinger, daemon=True))

			tname = 'ArpPinger-%d' % i
			setattr(dthreads, tname.lower(), LicornPoolJobThread(pname=dname,
				tname=tname, in_queue=dqueues.arppings,
				target=pool_job_arppinger, daemon=True))

			# any socket.gethostbyaddr() can block or timeout on DNS call, make
			# the thread daemonic to not block master daemon stop.
			tname = 'Reverser-%d' % i
			setattr(dthreads, tname.lower(), LicornPoolJobThread(pname=dname,
				tname=tname, in_queue=dqueues.reverse_dns,
				target=pool_job_reverser, daemon=True))

			# Pyrofinder threads are daemons, because they can block a very long
			# time on a host (TCP timeout on routers which drop packets), and
			# during the time they block, the daemon cannot terminate and seems
			# to hang. Setting these threads to daemon will permit the main
			# thread to exit, even if some are still left and running.
			tname = 'Pyrofinder-%d' % i
			setattr(dthreads, tname.lower(), LicornPoolJobThread(pname=dname,
				tname=tname, in_queue=dqueues.pyrosys,
				target=pool_job_pyrofinder,	daemon=True))

	if not options.daemon:
		# set up the interaction with admin on stdin / stdout. Only if we do not
		# fork into the background.
		dthreads._interactor = LicornInteractorThread()
		dthreads._interactor.start()

	for (thname, th) in dthreads.iteritems():
		assert ltrace('daemon', 'starting thread %s.' % thname)
		th.start()

	logging.notice('''%s(%s): all threads started, going to sleep waiting '''
		'''for signals.''' % (pname, os.getpid()))

	while True:
		signal.pause()

	terminate(None, None)

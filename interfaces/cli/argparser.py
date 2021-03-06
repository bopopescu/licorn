# -*- coding: utf-8 -*-
"""
Licorn CLI - http://dev.licorn.org/documentation/cli

argparser - command-line argument parser library.
Contains all argument parsers for all licorn system tools (get, add, modify, delete, check)

Copyright (C) 2005-2010 Olivier Cortès <olive@deep-ocean.net>,
Copyright (C) 2005,2007 Régis Cobrun <reg53fr@yahoo.fr>
Licensed under the terms of the GNU GPL version 2.

"""
import os, getpass

from optparse import OptionParser, OptionGroup, SUPPRESS_HELP

from licorn.foundations           import exceptions, hlstr, settings
from licorn.foundations.styles    import *
from licorn.foundations.ltrace    import *
from licorn.foundations.ltraces   import *
from licorn.foundations.base      import LicornConfigObject
from licorn.foundations.pyutils   import add_or_dupe_obj
from licorn.foundations.argparser import build_version_string, \
											common_behaviour_group

from licorn.core import LMC, version

### General / common arguments ###
def common_filter_group(app, parser, tool, mode):
	"""Build Filter OptionGroup for all get variants."""

	big_help_string = (
		""" WARNING: filters are only partially cumulative. Order """
		"""of operations: %s %s """
		"""takes precedence on other inclusive filters (if it is """
		"""present, any other inclusive filter is purely discarded). In this """
		"""case, %s is equal to all %s. %s if %s is not used, other """
		"""inclusive filters are union'ed to construct the %s of """
		"""%s. %s Then all exclusive filters are union'ed in turn too, to """
		"""construct an %s of %s. %s The %s is """
		"""substracted from the %s, and the result is used in the """
		"""calling CLI tool to operate onto.""" % (
			stylize(ST_LIST_L1, '(1)'),
			stylize(ST_NOTICE, '--all'),
			stylize(ST_DEFAULT, 'include_list'),
			mode,
			stylize(ST_LIST_L1, '(2)'),
			stylize(ST_NOTICE, '--all'),
			stylize(ST_DEFAULT, 'include_list'),
			mode,
			stylize(ST_LIST_L1, '(3)'),
			stylize(ST_DEFAULT, 'exclude_list'),
			mode,
			stylize(ST_LIST_L1, '(4)'),
			stylize(ST_DEFAULT, 'exclude_list'),
			stylize(ST_DEFAULT, 'include_list')
			)
		)

	filtergroup = OptionGroup(parser,
		stylize(ST_OPTION, _(u'Filter options')),
		"""Filter %s.%s""" % (mode,
			big_help_string if mode != 'configuration' else '')
		)

	if tool == 'add' and mode == 'volumes':
		filtergroup.add_option('-a', '--all',
			action="store_true", dest="all", default=False,
			help=_(u'Also select system data. I.e. '
					u'output system %s too.') % mode)

	if tool in ('get', 'mod', 'del'):
		if mode in ('volumes', 'users', 'groups', 'profiles', 'privileges',
			'machines', 'tasks'):
			filtergroup.add_option('-a', '--all',
				action="store_true", dest="all", default=False,
				help=_(u'Also select system data. I.e. '
						u'output system %s too.') % mode)

		if mode in ('users', 'groups', 'profiles', 'privileges', 'machines'):
			filtergroup.add_option('-X', '--not', '--exclude',
				action="store", dest="exclude", default=None,
				help=_(u'exclude {0} from the selection. Can be IDs or {1} '
						u'names. Separated by commas without spaces.').format(
						mode, mode[:-1]))

	if tool is 'get':
		if mode in ('daemon_status', 'users', 'groups', 'machines', 'tasks'):
			filtergroup.add_option('-l', '--long', '--full', '--long-output',
				action="store_true", dest="long_output", default=False,
				help=_(u'long output (all info, attributes, etc). '
						u'Default: %s.') % stylize(ST_DEFAULT, _(u'no')))

		if mode == 'daemon_status':
			filtergroup.add_option('--detail', '--details',
				'-p', '--precision', '--precisions', '--pinpoint',
				action="store", dest="precision", default=None,
				help=_(u'long output (all info, attributes, etc). '
						u'Default: %s.') % stylize(ST_DEFAULT, _(u'no')))

			filtergroup.add_option('--monitor', '-m', '--stay-connected',
				action="store_true", dest="monitor", default=False,
				help=_(u'Stay connected to the daemon and update the status '
						u'every given interval (see below). '
						u'Default: %s.') % stylize(ST_DEFAULT, _(u'no')))

			filtergroup.add_option('-i', '--interval', '--monitor-interval',
				action="store", type="int", dest="monitor_interval", default=1,
				help=_(u'Monitoring interval (in seconds). Default: %s.') %
					stylize(ST_DEFAULT, _(u'1 sec')))

			filtergroup.add_option('-c', '--count', '--monitor-count',
				action="store", type="int", dest="monitor_count", default=None,
				help=_(u'Monitor a given number of count. Default: %s.') %
					stylize(ST_DEFAULT, _(u'infinite')))

			filtergroup.add_option('-d', '--duration', '--monitor-duration',
				action="store", type="int", dest="monitor_time", default=None,
				help=_(u'Monitor during a time period, in seconds. Default: %s.') %
					stylize(ST_DEFAULT, _(u'infinite')))

			filtergroup.add_option('--no-clear', '--continuous',
				action="store_false", dest="monitor_clear", default=True,
				help=_(u'Do not clear the screen between each monitor output. '
					u'Default: %s.') % stylize(ST_DEFAULT, _(u'no')))

	if tool is 'chk':
		if mode in ( 'users', 'groups', 'configuration', 'profiles'):
			filtergroup.add_option('-a', '--all',
				action="store_true", dest="all", default=False,
				help=_(u'{0} {1}: this can be a very long operation{2}').format(
						_(u'Check *all* %s on the system.') %
							stylize(ST_MODE, mode) \
							if mode != 'configuration' \
							else _(u'Check every bit of the configuration.'),
						stylize(ST_IMPORTANT, _(u"WARNING")),
						_(u", depending of the current number of %s.") %
							mode if mode != 'configuration' else ''))

		if mode in ('users', 'groups', 'profiles'):
			filtergroup.add_option('-X', '--not', '--exclude',
				action="store", dest="exclude", default=None,
				help=_(u'Exclude {0} from the selection. Can be IDs or {1} '
					u'names. Separated by commas without spaces.').format(mode,
					mode[:-1]))

	if mode is 'users':
		filtergroup.add_option('--login', '--logins', '--username',
			'--usernames', '--name', '--names',
			action="store", type="string", dest="login", default=None,
			help=_(u"Specify user(s) by their login (separated by commas "
				"without spaces)."))

		filtergroup.add_option('--uid', '--uids',
			action="store", type="string", dest="uid", default=None,
			help=_(u"Specify user(s) by their UID (separated by commas "
				"without spaces)."))

	if mode is 'users' or (tool is 'mod' and mode is 'profiles'):
		filtergroup.add_option('--system', '--system-groups', '--sys',
			action="store_true", dest="system", default=False,
			help=_(u"Only select system accounts."))

		filtergroup.add_option('--no-sys', '--not-sys', '--no-system',
			'--not-system', '--exclude-sys','--exclude-system',
			action="store_true", dest="not_system", default=False,
			help=_(u"Only select non-system accounts."))

		filtergroup.add_option('--not-user',
			'--exclude-user', '--not-users',
			'--exclude-users', '--not-login',
			'--exclude-login', '--not-logins',
			'--exclude-logins',  '--not-username',
			'--exclude-username', '--not-usernames',
			'--exclude-usernames',
			action="store", type="string", dest="exclude_login", default=None,
			help=_(u'Specify account(s) excluded from current operation, by '
				'their *login* (separated by commas without spaces).'))

		filtergroup.add_option('--not-uid', '--exclude-uid',
			'--not-uids', '--exclude-uids',
			action="store", type="string", dest="exclude_uid", default=None,
			help=_(u'Specify account(s) excluded from current operation by '
				'their UID (separated by commas without spaces).'))

	if tool in ('get', 'mod', 'del', 'chk'):
		if mode in ('users', 'groups', 'profiles', 'machines'):
			# TODO: "if has_attr(controller, 'word_match'):
			filtergroup.add_option('-g', '--grep', '--fuzzy', '--word-match',
				action="store", dest="word_match", default='',
				help=_(u'grep / fuzzy word match on the login/name/hostname.'))
			filtergroup.add_option('-G', '--exclude-grep', '--exclude-fuzzy',
				'--exclude-word-match',
				action="store", dest="exclude_word_match", default='',
				help=_(u'exclude login/name/hostname if grep / fuzzy word match.'))

	if tool in ('get', 'chk', 'del') and mode in ('users', 'groups'):
			# for GET/CHK/DEL, we can select the group with the -w flag.
			filtergroup.add_option('-w', '--watched', '--inotified',
				action="store_true", dest="inotified", default=False,
				help=_(u'Include all watched {0}.').format(_(mode)))

			filtergroup.add_option('-W', '--not-watched', '--not-inotified',
				action="store_true", dest="not_inotified", default=False,
				help=_(u'Include all non-watched {0}. Handy for checking all '
					u'of them at once in a cron script.').format(_(mode)))

	elif tool == 'mod' and mode in ('users', 'groups'):
			# for MOD, there would be a conflict between the selector flag
			# and the modifier flag. We choose to assign the short ones to
			# the modifier, like it is for 'add'
			filtergroup.add_option('--watched', '--inotified',
				action="store_true", dest="inotified", default=False,
				help=_(u'Include all watched {0}.').format(_(mode)))

			filtergroup.add_option('--not-watched', '--not-inotified',
				action="store_true", dest="not_inotified", default=False,
				help=_(u'Include all non-watched {0}. Handy for checking all '
					u'of them at once in a cron script.').format(_(mode)))

	if mode is 'groups':
		filtergroup.add_option('--name', '--names', '--group', '--groups',
			'--group-name', '--group-names',
			action="store", type="string", dest="name", default=None,
			help=_(u'Specify group(s) by their name (separated by commas '
				'without spaces).'))

		filtergroup.add_option('--gid', '--gids',
			action="store", type="string", dest="gid", default=None,
			help=_(u'Specify group(s) by their GID (separated by commas '
				'without spaces).'))

		filtergroup.add_option('--system', '--system-groups', '--sys',
			action="store_true", dest="system", default=False,
			help=_(u"Only select system groups."))

		filtergroup.add_option('--no-sys', '--not-sys', '--no-system',
			'--not-system', '--exclude-sys','--exclude-system',
			action="store_true", dest="not_system", default=False,
			help=_(u"Only select non-system groups."))

		filtergroup.add_option('--privileged', '--priv', '--privs', '--pri',
			'--privileged-groups',
			action="store_true", dest="privileged", default=False,
			help=_(u"Only select privileged groups."))

		filtergroup.add_option('--no-priv', '--not-priv', '--no-privs',
			'--not-privs', '--no-privilege', '--not-privilege',
			'--no-privileges', '--not-privileges ', '--exclude-priv',
			'--exclude-privs','--exclude-privilege','--exclude-privileges',
			action="store_true", dest="not_privileged", default=False,
			help=_(u"Only select non-privileged groups."))

		filtergroup.add_option('--responsibles', '--rsp',
			'--responsible-groups',
			action="store_true", dest="responsibles", default=False,
			help=_(u"Only select responsibles groups."))

		filtergroup.add_option('--no-rsp', '--not-rsp', '--no-resp',
			'--not-resp', '--not-responsible', '--no-responsible',
			'--exclude-responsible', '--exclude-resp', '--exclude-rsp',
			action="store_true", dest="not_responsibles", default=False,
			help=_(u"Only select non-responsible groups."))

		filtergroup.add_option('--guests', '--gst', '--guest-groups',
			action="store_true", dest="guests", default=False,
			help=_(u"Only select guests groups."))

		filtergroup.add_option('--no-gst', '--not-gst', '--no-guest',
			'--not-guest', '--exclude-gst','--exclude-guest',
			action="store_true", dest="not_guests", default=False,
			help=_(u"Only select non-guest groups."))

		filtergroup.add_option('--empty', '--empty-groups',
			action="store_true", dest="empty", default=False,
			help=_(u"Only select empty groups."))

	if mode is 'groups' or (tool is 'mod' and mode is 'profiles'):
		filtergroup.add_option('--not-group',
			'--exclude-group', '--not-groups',
			'--exclude-groups', '--not-groupname',
			'--exclude-groupname', '--not-groupnames',
			'--exclude-groupnames',
			action="store", type="string", dest="exclude_group", default=None,
			help=_(u'Specify group(s) to exclude from current operation, by '
				'their *name* (separated by commas without spaces).'))

		filtergroup.add_option('--not-gid', '--exclude-gid',
			'--not-gids', '--exclude-gids',
			action="store", type="string", dest="exclude_gid", default=None,
			help=_(u'Specify group(s) to exclude from current operation by '
				'their *GID* (separated by commas without spaces).'))

	if mode is 'profiles':
		filtergroup.add_option('--profile', '--profiles', '--profile-name',
			'--profile-names', '--name', '--names',
			action="store", type="string", dest="name", default=None,
			help=_(u'Specify profile by its common name (separated by commas '
				'without spaces, when possible. If name contains spaces, '
				'use --group instead). %s.') % stylize(ST_IMPORTANT,
					_(u"one of --name or --group is required")))

		filtergroup.add_option('--group', '--groups', '--profile-group',
			'--profile-groups',
			action="store", type="string", dest="group", default=None,
			help=_(u'specify profile by its primary group (separated by '
				'commas without spaces).'))

	if mode is 'machines':
		filtergroup.add_option('--hostname', '--hostnames', '--name', '--names',
			'--client-name', '--client-names',
			action="store", type="string", dest="hostname", default=None,
			help=_(u'Specify machine(s) by their hostname (separated by '
				'commas without spaces).'))

		filtergroup.add_option('--mid', '--mids', '--ip', '--ips',
			'--ip-address', '--ip-addresses',
			action="store", type="string", dest="mid", default=None,
			help=_(u'Specify machine(s) by their IP address (separated by '
				'commas without spaces).'))

		if tool in ('get', 'mod', 'chk'):
			filtergroup.add_option('--unknown', '--unknown-machines',
				action="store_true", dest="unknown", default=False,
				help=_(u"Only select machines whose status is totally unknown."))

			filtergroup.add_option('--offline', '--offline-machines',
				action="store_true", dest="offline", default=False,
				help=_(u"Only select offline machines (this includes shutdown,"
					"going to sleep, asleep, shutting down and pyro shutdown "
					"machine)."))

			filtergroup.add_option('--going-to-sleep',
				'--going-to-sleep-machines',
				action="store_true", dest="going_to_sleep", default=False,
				help=_(u"Only select going to sleep machines."))

			filtergroup.add_option('--asleep', '--asleep-machines',
				action="store_true", dest="asleep", default=False,
				help=_(u"Only select asleep machines."))

			filtergroup.add_option('--online', '--online-machines',
				action="store_true", dest="online", default=False,
				help=_(u"Only select online machines (%s, and includes "
					"booting, idle, active and loaded machines).") %
					stylize(ST_DEFAULT, _(u"this is the default behaviour")))

			filtergroup.add_option('--booting', '--booting-machines',
				action="store_true", dest="booting", default=False,
				help=_(u"Only select booting machines."))

			filtergroup.add_option('--idle', '--idle-machines',
				action="store_true", dest="idle", default=False,
				help=_(u"Only select idle machines."))

			filtergroup.add_option('--active', '--active-machines',
				action="store_true", dest="active", default=False,
				help=_(u"Only select active machines."))

			filtergroup.add_option('--loaded', '--loaded-machines',
				action="store_true", dest="loaded", default=False,
				help=_(u"Only select loaded machines."))


	if mode == "tasks":
		filtergroup.add_option('--extinction-tasks', '-e', '--extinction',
			action="store_true", dest="extinction", default=False,
			help=_(u"Only select 'extinction' tasks"))

	return filtergroup
def check_opts_and_args(opts_and_args):

	opts, args = opts_and_args

	if len(LMC.rwi.groups_backends_names()) <= 1:
		opts.in_backend = None
		opts.move_to_backend = None

	if hasattr(opts, 'force') and opts.force \
				and hasattr(opts, 'batch') and opts.batch:
		raise exceptions.BadArgumentError(_(u'options --force and '
										u'--batch are mutually exclusive!'))

	if hasattr(opts, 'filename') :
		if opts.filename is not None and (
				((hasattr(opts, 'name') and opts.name)
				or (hasattr(opts, 'gid') and opts.gid)
				or len(args) > 1)
			or
				((hasattr(opts, 'login') and opts.login)
				or (hasattr(opts, 'uid') and opts.uid)
				or len(args) > 1)
			):
			raise exceptions.BadArgumentError(
				_(u'option --filename cannot be used '
				'with other individual specifiers.'))

		if opts.filename and opts.filename != '-':
			# resolve the complete filename, else the daemon won't find it because
			# it doesn't have the same CWD as the calling user.
			opts.filename = os.path.abspath(opts.filename)

	# note the current user for diverses mod_user operations
	opts.current_user = getpass.getuser()

	return (opts, args)
def general_parse_arguments(app, modes):
	"""Common options and arguments to all Licorn System Tools,
		with specialties."""

	# FIXME: 20100914 review this function, its contents seems outdated.

	usage_text = "\n\t%s %s [[%s] …]\n\n\t%s" % (
			stylize(ST_APPNAME, "%prog"),
			'|'.join(stylize(ST_MODE, mode) for mode in modes),
			stylize(ST_OPTION, "options"),
			_(u'(you can use partial and fuzzy matching on modes, eg. "{0}" '
				'will call "{1}", "{2}" will match "{3}", '
				'and so on)').format(
					stylize(ST_COMMENT, 'gr'),
					stylize(ST_MODE, 'groups'),
					stylize(ST_COMMENT, 'kw'),
					stylize(ST_MODE, 'keywords')
				))

	parser = OptionParser(usage=usage_text,
						version=build_version_string(app, version))

	return parser.parse_args()

### Getent arguments ###
def __get_output_group(app, parser, mode):
	"""TODO"""

	outputgroup = OptionGroup(parser,
		stylize(ST_OPTION, _(u"Output options")),
			_(u"Modify how data is printed/exported."))

	if mode is 'configuration':
		outputgroup.add_option("-s", "--short",
			action="store_const", const = "short", dest="cli_format",
			default="short",
			help=_(u'Like previous option, but export the configuration '
				'subset in the shortest form factor (only the values '
				'when possible ; %s).') %
				stylize(ST_DEFAULT, _(u"this is the default")))

		outputgroup.add_option("-b", "--bourne-shell",
			action="store_const", const = "bourne", dest="cli_format",
			default="short",
			help=_(u'When using configuration %s to output a subset of the '
				'system configuration, export it in a useful way to be '
				'used in a bourne shell environment (i.e. export '
				'VAR="value").') % stylize(ST_OPTION, _(u"sub-category")))

		outputgroup.add_option("-c", "--c-shell",
			action="store_const", const = "cshell", dest="cli_format",
			default="short",
			help=_(u'Like previous option, but export the configuration '
				'subset in a useful way to be used in a C shell '
				'environment (i.e. setenv VAR "value").'))

		outputgroup.add_option("-p", "--php", "--php-code",
			action="store_const", const = "PHP", dest="cli_format",
			default="short",
			help=_('Like previous option, but export the configuration '
				'subset in a usefull way to be included in PHP code (i.e. '
				'$VAR="value", use it with eval(`…`)).'))
	else:
		outputgroup.add_option("-t", "--script", "--to-script", "--script-output",
			action="store", type="string", dest="to_script", default='',
			help=_(u'Output data to script (no colors, no verbose). All '
				u'attributes are usable for any core object, eg. {user.login}, '
				u'{user.homeDirectory} and al. for users, {group.name}, '
				u'{group.gidNumber} and al. for groups and the like for other '
				u'core objects. For convenience and compacity reasons, aliases '
				u'are available: "u" for "user", "g" for "group", "m" for '
				u'"machine". "self" is always available too. Default: %s.') %
				stylize(ST_DEFAULT, _(u"'' (the empty string)")))

		outputgroup.add_option("-s", "--separator", "--script-separator",
			action="store", type="string", dest="script_sep", default='\n',
			help=_(u'Script entry separator. Default: %s, can be a space, a '
				u'comma, another complex string. Whatever you want. It is up '
				u'to you to be sure the separator will not be found in any '
				u'of the entries data.') % stylize(ST_DEFAULT, _(u"'\n' (new line)")))

		outputgroup.add_option("-x", "--xml", "--xml-output",
			action="store_true", dest="xml", default=False,
			help=_(u'Output data as XML (no colors, no verbose). '
				'Default: %s, output for CLI, human-readable.') %
				stylize(ST_DEFAULT, _(u"NO XML")))

		outputgroup.add_option("--dump",
			action="store_true", dest="dump", default=False,
			help=_(u'Dump nearly RAW data on stdout. Used for debugging '
				'internal data structures. WARNING: dump output can easily '
				' flood your terminal.'))

	return outputgroup
def get_users_parse_arguments(app):
	""" Integrated help and options / arguments for « get user(s) »."""

	usage_text = "\n\t%s %s [[%s] …]" \
		% (
			stylize(ST_APPNAME, "%prog"),
			stylize(ST_MODE, "users"),
			stylize(ST_OPTION, "option")
		)

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'get'))
	parser.add_option_group(common_filter_group(app, parser, 'get', 'users'))
	parser.add_option_group(__get_output_group(app, parser,'users'))

	return parser.parse_args()
def get_events_parse_arguments(app):
	""" Integrated help and options / arguments for « get user(s) »."""

	usage_text = "\n\t%s %s [[%s] …]" \
		% (
			stylize(ST_APPNAME, "%prog"),
			stylize(ST_MODE, "events"),
			stylize(ST_OPTION, "option")
		)

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'get'))
	parser.add_option_group(common_filter_group(app, parser, 'get', 'events'))
	parser.add_option_group(__get_output_group(app, parser, 'events'))

	events = OptionGroup(parser,
		stylize(ST_OPTION, _(u"Events listing/monitoring options")))


	events.add_option('-m', '--monitor',
		action='store_true', dest='monitor', default=False,
		help=_(u'Stay connected to the daemon and dump events in "monitor" '
			u'mode. You can filter events with -f. Without this flag, all '
			u' valid events will only be listed, with their handlers and '
			u'callbacks if you add -v.'))

	events.add_option('-f', '--facilities',
		action='store', type='string', dest='facilities', default=None,
		help=_(u'Specify facilities when monitor. Default: %s (see online '
			u'documentation for possible values).') %
				stylize(ST_DEFAULT, _(u"std")))

	parser.add_option_group(events)

	return parser.parse_args()
def get_inside_parse_arguments(app):
	""" Integrated help and options / arguments for « get user(s) »."""

	usage_text = "\n\t%s %s" \
		% (
			stylize(ST_APPNAME, "%prog"),
			stylize(ST_MODE, "inside"),
		)

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'get'))
	# no behaviour / filter change here
	#parser.add_option_group(common_filter_group(app, parser, 'get', 'inside'))

	return parser.parse_args()
def get_privileges_parse_arguments(app):
	""" Integrated help and options / arguments for « get user(s) »."""

	usage_text = "\n\t%s %s" \
		% (
			stylize(ST_APPNAME, "%prog"),
			stylize(ST_MODE, "priv[ilege][s]")
		)

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'get'))
	# no filter yet for privileges
	#parser.add_option_group(common_filter_group(app, parser, 'get', 'privileges'))
	parser.add_option_group(__get_output_group(app, parser,'privileges'))

	return parser.parse_args()
def get_groups_parse_arguments(app):
	""" Integrated help and options / arguments for « get group(s) »."""

	usage_text = "\n\t%s %s [[%s] …]" \
		% (
			stylize(ST_APPNAME, "%prog"),
			stylize(ST_MODE, "groups"),
			stylize(ST_OPTION, "option")
		)

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'get'))
	parser.add_option_group(common_filter_group(app, parser, 'get', 'groups'))
	parser.add_option_group(__get_output_group(app, parser,'groups'))

	return parser.parse_args()
def get_keywords_parse_arguments(app):
	""" Integrated help and options / arguments for « get keyword(s) »."""

	usage_text = "\n\t%s %s [[%s] …]" \
		% (
			stylize(ST_APPNAME, "%prog"),
			stylize(ST_MODE, "keywords"),
			stylize(ST_OPTION, "option")
		)

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'get'))
	parser.add_option_group(__get_output_group(app, parser,'keywords'))

	return parser.parse_args()
def get_profiles_parse_arguments(app):
	""" Integrated help and options / arguments for « get profile(s) »."""

	usage_text = "\n\t%s %s [[%s] …]" \
		% (
			stylize(ST_APPNAME, "%prog"),
			stylize(ST_MODE, "profiles"),
			stylize(ST_OPTION, "option")
		)

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'get'))
	parser.add_option_group(common_filter_group(app, parser, 'get', 'profiles'))
	parser.add_option_group(__get_output_group(app, parser,'profiles'))

	return parser.parse_args()
def get_machines_parse_arguments(app):
	""" Integrated help and options / arguments for « get user(s) »."""

	usage_text = "\n\t%s %s [[%s] …]" \
		% (
			stylize(ST_APPNAME, "%prog"),
			stylize(ST_MODE,
				"client[s]|machine[s]|workstation[s]"),
			stylize(ST_OPTION, "option")
		)

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'get'))
	parser.add_option_group(common_filter_group(app, parser, 'get', 'machines'))
	parser.add_option_group(__get_output_group(app, parser,'machines'))

	return parser.parse_args()
def get_tasks_parse_arguments(app):
	""" Integrated help and options / arguments for « get task(s) »."""

	usage_text = "\n\t%s %s [[%s] …]" \
		% (
			stylize(ST_APPNAME, "%prog"),
			stylize(ST_MODE,
				"task[s]"),
			stylize(ST_OPTION, "option")
		)

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))
	parser.add_option_group(common_behaviour_group(app, parser, 'get'))
	parser.add_option_group(common_filter_group(app, parser, 'get', 'tasks'))
	parser.add_option_group(__get_output_group(app, parser,'tasks'))


	return parser.parse_args()
def get_configuration_parse_arguments(app):
	""" Integrated help and options / arguments for « get »."""

	usage_text = "\n\t%s config [[%s] …]\n" % (
		stylize(ST_APPNAME, "%prog"),
		stylize(ST_OPTION, "option")) \
		+ "\t%s config [[%s] …] %s [--short|--bourne-shell|--c-shell|--php-code] ]\n" % (
		stylize(ST_APPNAME, "%prog"),
		stylize(ST_OPTION, "option"),
		stylize(ST_OPTION, "category")) \
		+ ('''%s is one of: app_name, names, shells, skels, '''
			'''priv|privs|privileges, config_dir, '''
			'''sysgroups|system_group|system-groups '''
			'''main_config_file, extendedgroup_data_file.''' % \
				stylize(ST_OPTION, "category"))

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'get'))
	parser.add_option_group(__get_output_group(app, parser, 'configuration'))

	return parser.parse_args()
def get_volumes_parse_arguments(app):
	""" Integrated help and options / arguments for « get »."""

	usage_text = "\n\t%s volumes\n" % (
		stylize(ST_APPNAME, "%prog"))

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'get'))
	parser.add_option_group(__get_output_group(app, parser, 'volumes'))

	return parser.parse_args()
def parse_daemon_precision(precision):
	""" split a precision string and build a precision bare pseudo object for
		detailled daemon status. """

	if precision is None:
		return None

	precision_obj = LicornConfigObject()
	values = precision.split(',')

	for value in values:
		vtype, vident = value.split(':')
		if vtype in ('g', 'grp', 'group'):
			vtype = 'groups'
		elif vtype in ('u', 'usr', 'user'):
			vtype = 'users'
		else:
			# unknown vtype, skip
			continue

		add_or_dupe_obj(precision_obj, vtype, vident)

	return precision_obj
def get_daemon_status_parse_arguments(app):
	""" Integrated help and options / arguments for « get »."""

	usage_text = "\n\t%s daemon_status [--full|--long]\n" % (
		stylize(ST_APPNAME, "%prog"))
	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'get'))
	parser.add_option_group(
		common_filter_group(app, parser, 'get', 'daemon_status'))
	parser.add_option_group(__get_output_group(app, parser, 'daemon_status'))

	opts, args = parser.parse_args()

	opts.precision = parse_daemon_precision(opts.precision)

	return opts, args
### Add arguments ###
def add_user_parse_arguments(app):
	"""Integrated help and options / arguments for « add user »."""

	assert ltrace(TRACE_ARGPARSER, '> add_user_parse_arguments()')

	usage_text = _("""
	{1}

	{0} user [--login] <login>

	{0} user [--login] <login>
		[-s|--system]
		[-p|--password "<cleartext_password>"]
		[-g|--gid=<primary_gid|primary_group>]
		[-r|--profile=<profile_name|profile_group|profile_gid>]
		[-K|--skel=<absolute_path_to_skel>]
		[-e|--gecos=<given name>]
		[-H|--home=<home_dir>]
		[other options…]

	{2}
	(Will automatically create users groups during the process)

	{0} users --filename=<file> --profile=<profile_name|profile_group|profile_gid>
		[--lastname-column=<COL>] [--firstname-column=<COL>] [ --gecos-column=<COL>]
		[--group-column=<COL>] [--login-column=<COL>] [--profile-column=<COL>]
		[--password-column=<COL>]
		[--separator=<SEP>]
		[--confirm-import]
		[--no-sync]
""").format(stylize(ST_APPNAME, "%prog"),
	stylize(ST_OPTION, _(u"Individual user creation:")),
	stylize(ST_OPTION, _(u"Massive users creation:")))

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'add_user'))

	user = OptionGroup(parser,
		stylize(ST_OPTION, _(u"Individual user creation options")))

	user.add_option('-l', "--login", "--name",
		action="store", type="string", dest="login", default=None,
		help=_(u"Specify user's login (%s).") % stylize(
			ST_IMPORTANT,
			_(u"one of login or firstname+lastname arguments is required")))

	user.add_option('--force-bad-login', '--force-badname',
		action="store_true", dest="force_badname", default=False,
		 help=SUPPRESS_HELP)

	user.add_option('-e', "--gecos",
		action="store", type="string", dest="gecos", default=None,
		help=_(u"Specify user's GECOS field. If given, GECOS takes precedence "
			"on --firstname and --lastname, which will be silently "
			"discarded. Default: autogenerated from firstname & lastname "
			"if given, else %s.") % stylize(ST_DEFAULT,
				_(u'autogenerated from login')))

	user.add_option('-p', "--password",
		action="store", type="string", dest="password", default=None,
		help=_(u"Specify user's password (else will be autogenerated, %d "
			"chars long).") % LMC.rwi.configuration_get('users.min_passwd_size'))

	user.add_option('-g', '--in-group', '--primary-group', '--gid',
			'--primary-gid', '--group',
		action="store", type="string", dest="primary_gid", default=None,
		help=_(u"Specify user's future primary group (at your preference as "
			"a group name or a GID). This parameter is overriden by the "
			"profile argument if you specify both. Default: %s.") %
				LMC.rwi.configuration_get('users.default_gid'))

	user.add_option('-G', '--in-groups', '--auxilliary-groups',
		'--add-to-groups', '--aux-groups', '--secondary-groups', '--groups',
		action="store", type="string", dest="in_groups", default=None,
		help=_(u'Specify future user\'s auxilliary groups (at your preference '
			'as groupnames or GIDs, which can be mixed, and separated by '
			'commas without spaces). These supplemental groups are added '
			'to the list of groups defined by the profile, if you specify '
			'both. Default: None.'))

	user.add_option('-s', "--system",
		action="store_true", dest="system", default = False,
		help=_(u"Create a system account instead of a standard user (root only)."))

	user.add_option('-r', "--profile",
		action="store", type="string", dest="profile", default=None,
		help=_(u"Profile which will be applied to the user. Default: None. "
			"This argument overrides the primary group / GID if both are "
			"specified. %s.") % stylize(ST_DEFAULT,
				_(u'It can be used for massive imports, too')))

	user.add_option('-u', "--uid", '--desired-uid',
		action="store", type="int", dest="uid", default=None,
		help=_(u"manually specify an UID for the new user. This UID must be "
			"free and inside the range {0} - {1} for a standard user, and "
			"outside the range for a system account, else it will be "
			"rejected and the user account won't be created. Default: "
			"next free UID in the selected range.").format(
			stylize(ST_DEFAULT, LMC.rwi.configuration_get('users.uid_min')),
			stylize(ST_DEFAULT, LMC.rwi.configuration_get('users.uid_max'))))

	user.add_option('-H', "--home",
		action="store", type="string", dest="home", default=None,
		help=_(u'Specify the user\'s home directory. Only valid for a system '
			'account, else discarded because standard accounts have a '
			'fixed home dir "%s".') % stylize(ST_PATH,
				'%s/login' % LMC.rwi.configuration_get('users.base_path')))

	user.add_option("-S", "--shell",
		action="store", type="string", dest="shell", default=None,
		help=_(u"Specify user's shell, from the ones given by command "
			"`get config shells`. Default: %s") % stylize(ST_COMMENT,
			LMC.rwi.configuration_get('users.default_shell')))

	user.add_option('-K', "--skel",
		action="store", type="string", dest="skel", default=None,
		help=_(u'Specify a particular skeleton to apply to home dir after '
			'creation, instead of the profile or the primary-group '
			'implicit skel. Default: the profile skel if a profile is given, '
			'else %s.' % stylize(ST_COMMENT,
				LMC.rwi.configuration_get('users.default_skel'))))

	user.add_option("--firstname",
		action="store", type="string", dest="firstname", default=None,
		help=_(u'Specify user\'s first name (required if --lastname is given, '
			'overriden by GECOS).'))

	user.add_option("--lastname",
		action="store", type="string", dest="lastname", default=None,
		help=_(u'Specify user\'s last name (required if --firstname is given, '
			'overriden by GECOS).'))

	user.add_option("--no-create-home",
		action="store_true", dest="no_create_home", default=False,
		help=_(u"do not create the home directory when creating account. This "
			"is valid only for system accounts, because standard accounts "
			"must always have a home."))

	user.add_option("-W", "--not-watched", "--set-not-watched",
						"--not-inotified", "--set-not-inotified",
		action="store_false", dest="set_inotified", default=True,
		help=_(u"Do not watch the home directory of the user for content "
			u"changes. Usefull for big directories which slow down licornd. "
			u"You have to manually run {0} on non-watched users. (default: "
			u"{1})").format(
				stylize(ST_DEFAULT, 'chk'),
				stylize(ST_DEFAULT, _(u"watched"))))

	user.add_option("--disabled-password",
		action="store_true", dest="disabled_password", default=False,
		help=_(u"The user will have an unusable password, rendering the "
			u"account unloggable from the console (but not from SSH with keys)."))

	user.add_option("--disabled-login",
		action="store_true", dest="disabled_login", default=False,
		help=_(u"The user will not be able to login after the account "
			u"creation (shell set to /bin/false)."))

	# we don't mind using the group backends, because groups and users are
	# tied in the same prefered backend all the time.
	backends = LMC.rwi.groups_backends_names()

	if len(backends) > 1:
		user.add_option('-B', '--backend', '--in-backend',
			action='store', dest='in_backend',
			default=None,
			help=_(u'Specify backend in which to store the user account '
				'(default: {0}; possible choices: {1}; {2}).').format(
				stylize(ST_DEFAULT, LMC.rwi.prefered_groups_backend_name()),
					', '.join(stylize(ST_NAME, backend)
						for backend in backends),
				stylize(ST_DEFAULT, _(u'this argument can be used for '
					'massive imports, too'))))

	parser.add_option_group(user)

	addimport = OptionGroup(parser,
				stylize(ST_OPTION, _(u"Massive users creation options")))

	addimport.add_option("--filename",
		action="store", type="string", dest="filename", default=None,
		help=_(u"path of the file you want to import accounts from "
			"(must point to a valid CSV file). %s." % stylize(ST_IMPORTANT,
				_(u"Required in massive imports mode"))))

	addimport.add_option("--lastname-column",
		action="store", type="int", dest="lastname_col", default = 0,
		help=_(u"lastname column number in CSV file (default is %s).") %
			stylize(ST_DEFAULT, "0"))

	addimport.add_option("--firstname-column",
		action="store", type="int", dest="firstname_col", default = 1,
		help=_(u"firstname column number in CSV (default is %s).") %
			stylize(ST_DEFAULT, "1"))

	addimport.add_option("--gecos-column",
		action="store", type="int", dest="gecos_col", default = None,
		help=_(u"gecos column number in CSV (default is %s).") %
			stylize(ST_DEFAULT, "None"))

	addimport.add_option("--profile-column",
		action="store", type="int", dest="profile_col", default = None,
		help=_(u"profile column (default is %s).") %
			stylize(ST_DEFAULT, "None"))

	addimport.add_option("--group-column",
		action="store", type="int", dest="group_col", default = 2,
		help=_(u"{0} column number in CSV file (default is {1}).").format(
			stylize(ST_SPECIAL, LMC.rwi.configuration_get('groups._plural')),
			stylize(ST_DEFAULT, "2")))

	addimport.add_option("--login-column",
		action="store", type="int", dest="login_col", default=None,
		help=_(u"{0} column number in CSV file (default: {1}, "
			"login will be guessed from firstname and lastname).").format(
				stylize(ST_SPECIAL, "login"),
				stylize(ST_DEFAULT, "None")))

	addimport.add_option("--password-column",
		action="store", type="int", dest="password_col", default=None,
		help=_(u"{0} column number in CSV file (default: {1}: password "
			"will be randomly generated and {2} chars long).").format(
				stylize(ST_SPECIAL, _(u"password")),
				stylize(ST_DEFAULT, _(u"none")),
				LMC.rwi.configuration_get('users.min_passwd_size')))

	addimport.add_option("--separator",
		action="store", type="string", dest="separator", default = ";",
		help=_(u"Separator for the CSV fields (default: %s, by sniffing in "
			"the file).") % stylize(ST_DEFAULT, _("determined automatically")))

	addimport.add_option("--confirm-import",
		action="store_true", dest="confirm_import", default = False,
		help=_("Really do the import. %s on the system, but only give "
			"you an example of what will be done, which is useful to "
			"verify your file has been correctly parsed (fields order, "
			"separator…).") % stylize(ST_IMPORTANT,
						_(u"Without this flag the program will do nothing")))

	addimport.add_option("--no-sync",
		action="store_true", dest="no_sync", default = False,
		help=_(u"Commit changes only after all modifications (currently "
			"%s because extensions need things to be commited to work).") %
			stylize(ST_IMPORTANT, _(u'disabled')))

	parser.add_option_group(addimport)

	assert ltrace(TRACE_ARGPARSER, '< add_user_parse_arguments()')

	return check_opts_and_args(parser.parse_args())
def add_group_parse_arguments(app):
	"""Integrated help and options / arguments for « add group »."""

	assert ltrace(TRACE_ARGPARSER, '> add_group_parse_arguments()')

	usage_text = "\n\t%s group --name=<nom_groupe> [--permissive] [--gid=<gid>]\n" % stylize(ST_APPNAME, "%prog") \
		+ "\t\t[--skel=<nom_squelette>] [--description=<description>]\n" \
		+ "\t\t[--system]"

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'add_group'))

	group = OptionGroup(parser,
		stylize(ST_OPTION, 'Add group options '))

	group.add_option('--name',
		action='store', type='string', dest='name', default=None,
		help=_(u"Specify group's name (%s).") %
			stylize(ST_IMPORTANT, _(u'required')))

	group.add_option('-p', '--permissive',
		action="store_true", dest="permissive", default=False,
		help=_(u"Will the shared group directory be permissive? "
				u"(default: {0}).".format(
				stylize(ST_DEFAULT, _(u"not permissive")))))

	group.add_option("-W", "--not-watched", "--set-not-watched",
		"--not-inotified", "--set-not-inotified",
		action="store_false", dest="set_inotified", default=True,
		help=_(u"Do not watch the shared directory of the group for content "
			u"changes. Usefull for big directories which slow down licornd. "
			u"You have to manually run {0} on non-watched groups. (default: "
			u"{1})").format(
				stylize(ST_DEFAULT, 'chk'),
				stylize(ST_DEFAULT, _(u"watched"))))

	group.add_option('-g', '--gid',
		action="store", type="int", dest="gid", default=None,
		help=_(u"Specify the GID (root / @admin members only)."))

	group.add_option('-d', '--description', '-c', '--comment',
		action="store", type="string", dest="description", default=None,
		help=_(u"Description of the group (free text, "
			u"but must match /%s/i).") % stylize(ST_COMMENT,
				hlstr.regex['description']))

	group.add_option('-S', '--skel', '--skeleton',
		action='store', type='string', dest='skel',
		default=LMC.rwi.configuration_get('users.default_skel'),
		help=_(u"skeleton directory for the group (default: %s).") %
		stylize(ST_DEFAULT, LMC.rwi.configuration_get('users.default_skel')))

	group.add_option('-s', '--system', '--system-group', '--sysgroup',
		action='store_true', dest='system', default=False,
		help=_(u"The group will be a system group (only root or %s members "
			u"can decide this, but this is not enforced yet).") %
				stylize(ST_NAME, settings.defaults.admin_group))

	group.add_option('-u', '--users', '--add-users', '--members',
		action='store', dest='users_to_add', default=None,
		help=_(u"Users to make members of this group just after creation."))

	backends = LMC.rwi.groups_backends_names()

	if len(backends) > 1:
		group.add_option('-B', '--backend', '--in-backend',
			action='store', dest='in_backend',
			default=None,
			help=_(u"Specify backend in which to store the group (default: "
				u"{0}; possible choices: {1}; {2}).").format(
				stylize(ST_DEFAULT, LMC.rwi.prefered_groups_backend_name()),
				', '.join(stylize(ST_NAME, backend)
					for backend in backends),
				stylize(ST_DEFAULT, _(u'this argument can be used for '
					u'massive imports, too'))))

	parser.add_option_group(group)

	assert ltrace(TRACE_ARGPARSER, '< add_group_parse_arguments()')

	return check_opts_and_args(parser.parse_args())
def add_profile_parse_arguments(app):
	"""Integrated help and options / arguments for « add profile »."""

	usage_text = "\n\t%s profile [--name=]<name> [-g|--group=<groupName>] [--description=<descr>]\n" % stylize(ST_APPNAME, "%prog") \
		+ "\t\t[--shell=<shell>] [--quota=<quota>] [--skel=<nom_squelette>]\n" \
		+ "\t\t[-a|--[add-]groups=<groupe1>[[,groupe2][,…]] [--force-existing]"

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'add_profile'))

	profile = OptionGroup(parser, stylize(ST_OPTION, _(u"Add profile options")))

	profile.add_option("--name", '--profile-name', '--profile',
		action="store", type="string", dest="name", default=None,
		help=_(u"The profile's name (ie: « Administrator », « Power user », "
			u"« Webmaster », « Guest »). It must conform to {0} word. {1}.").format(
				stylize(ST_COMMENT, hlstr.regex['profile_name']),
				stylize(ST_IMPORTANT, _(u"It is required"))))

	profile.add_option('-g', "--group", '--profile-group',
		action="store", type="string", dest="group", default=None,
		help=_(u"Group name (or GID) identifying the profile on the system "
			u"(ie: «administrators», «power-users», «webmasters», «guests»). "
			u"It should be a plural world and will become a system group. %s.")
				% stylize(ST_IMPORTANT, _(u"It is required")))

	profile.add_option('-d', "--description", '-c', '--comment',
		action="store", type="string", dest="description", default=None,
		help=_(u"Description of the profile (free text, but must "
			u"conform to /%s/i).") % stylize(ST_COMMENT,
				hlstr.regex['description']))

	profile.add_option("--shell",
		action="store", type="string", dest="shell",
		default=LMC.rwi.configuration_get('users.default_shell'),
		help=_(u"Default shell for this profile (defaults: %s).") %
			stylize(ST_DEFAULT, LMC.rwi.configuration_get('users.default_shell')))

	profile.add_option("--quota",
		action="store", type="int", dest="quota", default=None,
		help=_(u"User data quota in Mb (a soft quota, defaults: %s).") %
			stylize(ST_DEFAULT, "1024"))

	profile.add_option('-G', "--groups", "--add-groups",
		action="store", type="string", dest="groups", default=None,
		help=_("Groups users of this profile will become members of."
			u"Separated by commas without spaces."))

	profile.add_option("--skel",
		action="store", type="string", dest="skeldir",
		default=LMC.rwi.configuration_get('users.default_skel'),
		help=_(u"Skeleton dir for this profile (must be an absolute path, "
			u"defaults to %s).") % stylize(ST_DEFAULT,
				LMC.rwi.configuration_get('users.default_skel')))

	profile.add_option("--force-existing", '--use-existing',
		action="store_true", dest="force_existing", default=False,
		help=_(u"Confirm the use of a previously created system group "
			u"for the profile. %s, but in some cases it is needed and "
			u"perfectly safe (when the group is created by another package "
			u"or script).") % stylize(ST_IMPORTANT,
				_(u"This can be risky in some situations")))

	parser.add_option_group(profile)

	return parser.parse_args()
def add_keyword_parse_arguments(app):
	"""Integrated help and options / arguments for « add keyword »."""

	usage_text = "\n\t%s kw|tag|keyword|keywords --name=<keyword> [--parent=<parent_keyword> --description=<description>]\n" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'add_keyword'))

	keyword = OptionGroup(parser, stylize(ST_OPTION, _(u"Add keyword options")))

	keyword.add_option("--name",
		action="store", type="string", dest="name", default=None,
		help=_(u"The keyword's name. It should be a singular word and %s.") %
			stylize(ST_IMPORTANT, _(u"it is required")))

	keyword.add_option("--parent",
		action="store", type="string", dest="parent", default = "",
		help=_(u"Keyword's parent name."))

	keyword.add_option("--description",
		action="store", type="string", dest="description", default = "",
		help=_(u"Description of the keyword (free text)."))

	parser.add_option_group(keyword)

	return parser.parse_args()
def add_event_parse_arguments(app):
	"""Integrated help and options / arguments for « add keyword »."""

	usage_text = _(u"\n\t{0} backup [--force] [{1}]\n\n"
					u"\tWhere {1} is optionnal, and will bu fuzzy matched "
					u"against device names, volume labels and GUIDs "
					u"if provided. If not specified, the program will "
					u"auto-select the first available volume.").format(
					stylize(ST_APPNAME, u"%prog"),
					stylize(ST_PATH, u"backup_volume"))

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'add_backup'))

	event = OptionGroup(parser, stylize(ST_OPTION, _(u"Add keyword options")))

	event.add_option("--name",
		action="store", type="string", dest="event_name", default=None,
		help=_(u"The event name. A singular word with underscores "
			u"but no spaces or commas. {0}. {1} will display a list of valid "
			u"event names.").format(
				stylize(ST_IMPORTANT, _(u"Required")),
				stylize(ST_COMMENT, _(u"get events")),
				))

	event.add_option("--args",
		action="store", type="string", dest="event_args", default=None,
		help=_(u"The event unnamed arguments (usually known as 'args' in "
			u"Python).\n\nIt should be a string representing a python "
			u"list in JSON syntax (it will be parsed with "
			u"`json.loads()`).\n\nIt's currently impossible "
			u"to give resolvable "
			u" arguments (eg. `LMC.users.by_name('my_user')`) so you are "
			u"stuck with only simple events to send. Some of them support IDs "
			u"and do dynamic resolution when found, but that's currently "
			u"not the global rule."))

	event.add_option('-k', "--kwargs",
		action="store", type="string", dest="event_kwargs", default=None,
		help=_(u"The event keywords arguments, usually known as 'kwargs' "
			u"in Python.\n\nThe same JSON rules and restrictions apply, "
			u"except that kwargs must obviously represent a dictionnary."))

	event.add_option('-p', "--priority",
		action="store", type="string", dest="event_priority", default=None,
		help=_(u"The event priority, a string like 'LOW', 'NORMAL' (default), "
			u"or 'HIGH'."))

	event.add_option('-s', "--sync", "--synchronous",
		action="store_true", dest="event_synchronous", default=False,
		help=_(u"Run the event synchronously, eg. wait for handlers and "
			u"callbacks to terminate before giving back hand. Default: "
			u"{0}.").format(stylize(ST_SPECIAL, _(u"False"))))

	parser.add_option_group(event)

	return parser.parse_args()
def add_backup_parse_arguments(app):
	"""Integrated help and options / arguments for « add keyword »."""

	usage_text = _(u"\n\t{0} event [--name] <event_name> [options…]\n\n"
					u"Manually send en event inside the Licorn® daemon.\n"
					u"Use with caution, as you can generate any kind of "
					u"event.").format(stylize(ST_APPNAME, u"%prog"))

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'add_event'))



	return parser.parse_args()
def add_privilege_parse_arguments(app):
	"""Integrated help and options / arguments for « add keyword »."""

	usage_text = "\n\t%s priv|privs|privilege|privileges [--name|--names=]privilege1[[,privilege2],…]\n" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'add_privilege'))

	priv = OptionGroup(parser, stylize(ST_OPTION, _(u"Add privilege options")))

	priv.add_option("--name", "--names",
		action="store", type="string", dest="privileges_to_add", default=None,
		help=_(u"The privilege's name(s), which is really a system group name "
		u"(only system groups can be promoted to privileges). %s and can be a "
		u"single word or multiple ones, separated by commas." %
			stylize(ST_IMPORTANT, _(u"It is required"))))

	parser.add_option_group(priv)

	return parser.parse_args()
def add_machine_parse_arguments(app):
	"""Integrated help and options / arguments for « add user »."""

	usage_text = """
	%s user [--login] <login>
	%s user --firstname <firstname> --lastname <lastname>
		[--system] [--password "<password>"]
		[--gid=<primary_gid>] [--profile=<profile>] [--skel=<skel>]
		[--gecos=<given name>] [--home=<home_dir>] […]""" % (
			stylize(ST_APPNAME, "%prog"),
			stylize(ST_APPNAME, "%prog"))

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'add_machine'))

	machine = OptionGroup(parser,
		stylize(ST_OPTION, "Add machine options "))

	machine.add_option("--discover", '--scan', '--scan-network',
		action="store", dest="discover", default=None,
		help=_(u"Scan a network for online hosts and attach them to the "
			u"system. Syntax: 192.168.0.0/24 or 10.0.0.0/8 and the like."))

	machine.add_option('-a', '--auto-discover', '--auto-scan',
		action='store_true', dest='auto_scan', default=False,
		help=_(u"Scan the local area network(s), looking for unattached hosts."))

	parser.add_option_group(machine)

	opts,args = parser.parse_args()

	"""
	TODO: TO BE ACTIVATED
	if opts.discover and opts.anything:
		raise exceptions.BadArgumentError('discovering network is a '
			'self-running task, no other options allowed, sorry.')
	"""

	return opts, args
def add_volume_parse_arguments(app):

	usage_text = ("\n\t%s volume[s] <vol1[,vol2[,…]]>" %
		stylize(ST_APPNAME, "%prog"))

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'add_volume'))
	parser.add_option_group(common_filter_group(app, parser, 'add', 'volumes'))

	volume = OptionGroup(parser, stylize(ST_OPTION, _(u"Add volume(s) options")))
	parser.add_option_group(volume)

	volume.add_option('--rescan', '-r', action="store_true", dest="rescan",
		default=False, help=SUPPRESS_HELP)

	return check_opts_and_args(parser.parse_args())
def add_task_parse_arguments(app):

	usage_text = """
	%s task [--name] <name> --action <action>
		[--year <year>] [--month <month>] [--day <day>] [--week-day <week-day>] [--hour <hour>] [--minute <minute>] [--second <second>]
		[--delay-until-year <year>] [--delay-until-month <month>] [--delay-until-day <day>] [--delay-until-hour <hour>] [--delay-until-minute <minute>] [--delay-until-second <second>]
		[--args <args>] [--kwargs <kwargs>]
		[--do-not-defer-resolution]"""% (
			stylize(ST_APPNAME, "%prog"))


	parser = OptionParser(usage=usage_text,
							version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'add_task'))
	#parser.add_option_group(common_filter_group(app, parser, 'add', 'tasks'))

	tasks = OptionGroup(parser, stylize(ST_OPTION, _(u"Add task(s) options")))
	parser.add_option_group(tasks)


	tasks.add_option('--name', '-n', action="store", type="string", dest="name",
		default="", help=_(u"Specify name for the task, {0}". format(
			stylize(ST_IMPORTANT, _(u"This argument is required")))))
	tasks.add_option('--action', '-a', action="store", type="string", dest="action",
		default="", help=_(u"Specify action for the task, {0}".format(
			stylize(ST_IMPORTANT, _(u"This argument is required")))))

	tasks.add_option('--year', '-y', action="store", type="string",
		dest="year", default=None, help=_(u"Specify year for the action, use the following syntax [*|*/n|n-m|n[,m[...]]]^[n[,m[...]]]."
			" Only used in mode 'single'"))
	tasks.add_option('--month', '-m', action="store", type="string",
		dest="month", default=None, help=_(u"Specify month for the action, use the following syntax [*|*/n|n-m|n[,m[...]]]^[n[,m[...]]].."
			" Only used in mode 'single'"))
	tasks.add_option('--day', '-d', action="store", type="string",
		dest="day", default=None, help=_(u"Specify day for the action, use the following syntax [*|*/n|n-m|n[,m[...]]]^[n[,m[...]]].."
			" Only used in mode 'single'"))
	tasks.add_option('--hour', '-H', action="store", type="string",
		dest="hour", default=None, help=_(u"Specify hour for the action, use the following syntax [*|*/n|n-m|n[,m[...]]]^[n[,m[...]]].."))
	tasks.add_option('--minute', '-M', action="store", type="string",
		dest="minute", default=None, help=_(u"Specify minute for the action, use the following syntax [*|*/n|n-m|n[,m[...]]]^[n[,m[...]]].."))
	tasks.add_option('--second', '-s', action="store", type="string",
		dest="second", default=None, help=_(u"Specify second for the action, use the following syntax [*|*/n|n-m|n[,m[...]]]^[n[,m[...]]].."))
	tasks.add_option('--week-day', action="store", type="string",
		dest="week_day", default=None, help=_(u"Specify week days for the action, use the following syntax [*|*/n|n-m|n[,m[...]]]^[n[,m[...]]].."))

	tasks.add_option('--delay-until-year', action="store", type="string",
		dest="delay_until_year", default=None, help=_(u"Specify a year to start the task, integer."))
	tasks.add_option('--delay-until-month', action="store", type="string",
		dest="delay_until_month", default=None, help=_(u"Specify a month to start the task, integer."))
	tasks.add_option('--delay-until-day', action="store", type="string",
		dest="delay_until_day", default=None, help=_(u"Specify a day to start the task, integer."))
	tasks.add_option('--delay-until-hour', action="store", type="string",
		dest="delay_until_hour", default=None, help=_(u"Specify an hour to start the task, integer."))
	tasks.add_option('--delay-until-minute', action="store", type="string",
		dest="delay_until_minute", default=None, help=_(u"Specify an hour to start the task, integer."))
	tasks.add_option('--delay-until-second', action="store", type="string",
		dest="delay_until_second", default=None, help=_(u"Specify a second to start the task, integer."))

	tasks.add_option('--args', action="store", type="string",
		dest="args", default="", help=_(u"Specify args for the action, format: --args=\"arg1[;arg2[;arg3[...]]]\""))
	tasks.add_option('--kwargs', action="store", type="string",
		dest="kwargs", default="", help=_(u"Specify kwargs for the action, format: --kwargs=\"k1=v1[;k2=v2[;k3=v3[...]]]\""))
	tasks.add_option('--do-not-defer-resolution', action="store_false",
		dest="defer_resolution", default=True, help=_(u"Specify if arguments "
		" will be resolved during execution or during task's load. Default is during task's execution"))

	opts, args = check_opts_and_args(parser.parse_args())

	if opts.name is '' and len(args) == 2:
		opts.name = args[1]
		del args[1]

	if opts.name=='' and opts.action=='' and len(args) == 3:
		opts.name = args[1]
		opts.action = args[2]

	if opts.action == '' or opts.name == '':
		raise exceptions.BadArgumentError(_(u'You must specify one of '
											u'"--name" or "--action"!'))

	return opts, args

### Delete arguments ###
def del_user_parse_arguments(app):
	"""Integrated help and options / arguments for « delete user »."""

	usage_text = "\n\t%s user < --login=<login> | --uid=UID > [--no-archive]" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'del_user'))
	parser.add_option_group(common_filter_group(app, parser, 'del', 'users'))

	user = OptionGroup(parser, stylize(ST_OPTION, _(u"Delete user options")))

	user.add_option("--no-archive",
		action="store_true", dest="no_archive", default = False,
		help=_(u"Don't make a backup of user's home directory in %s "
				u"(Default: home directory will be archived)." %
					stylize(ST_PATH, settings.home_archive_dir)))

	parser.add_option_group(user)
	return check_opts_and_args(parser.parse_args())
def del_task_parse_arguments(app):
	"""Integrated help and options / arguments for « delete task »."""

	usage_text = "\n\t%s task < --name=<name> | --id=ID >" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'del_task'))
	parser.add_option_group(common_filter_group(app, parser, 'del', 'tasks'))

	user = OptionGroup(parser, stylize(ST_OPTION, _(u"Delete user options")))

	user.add_option("--name", action="store", type="string", dest="name",
		default=None, help=_(u"name of the task to delete)."))

	user.add_option("--id", action="store", type="int", dest="id",
		default=0, help=_(u"id of the task to delete)."))

	parser.add_option_group(user)
	return check_opts_and_args(parser.parse_args())
def del_group_parse_arguments(app):
	"""Integrated help and options / arguments for « delete group »."""

	usage_text = "\n\t%s group <--name=<nom_groupe>|--gid=GID|--filename=<file> [[--del-users] [--no-archive]]" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'del_group'))
	parser.add_option_group(common_filter_group(app, parser, 'del', 'groups'))

	group = OptionGroup(parser, stylize(ST_OPTION, _(u"Delete group options")))

	group.add_option("--filename", '--from-file',
		action="store", type="string", dest="filename", default=None,
		help=_(u"get the list of groups from a file (can be stdin, "
			"just specify '-' as the filename)."))

	group.add_option("--del-users",
		action="store_true", dest="del_users", default=False,
		help=_(u"Delete the group primary members (user accounts) too "
			u"(default: {0}, the program will annoy you with a sane "
			u"warning.").format(stylize(ST_DEFAULT, _(u"NO"))))

	group.add_option("--no-archive",
		action="store_true", dest="no_archive", default=False,
		help=_(u"Don't make a backup of users home directories in {0} when "
			u"deleting members (default: {1}).").format(
				stylize(ST_PATH, settings.home_archive_dir),
				stylize(ST_DEFAULT,
					_(u"archive deleted group shared directories"))))

	parser.add_option_group(group)

	return check_opts_and_args(parser.parse_args())
def del_profile_parse_arguments(app):
	"""Integrated help and options / arguments for « delete profile »."""

	usage_text = "\n\t%s profile --group=<nom> [[--del-users] [--no-archive] [--no-sync]]" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(
		common_behaviour_group(app, parser, 'del_profile'))
	parser.add_option_group(common_filter_group(app, parser, 'del', 'profiles'))

	profile = OptionGroup(parser, stylize(ST_OPTION,
		_(u"Delete profile options")))

	profile.add_option("--del-users",
		action="store_true", dest="del_users", default=False,
		help=_(u"the profile's users will be deleted (%s).") %
			stylize(ST_IMPORTANT, _(u'Use with caution')))

	profile.add_option("--no-archive",
		action="store_true", dest="no_archive", default = False,
		help=_(u"Don't make a backup of user's home when deleting them."))

	parser.add_option_group(profile)

	return check_opts_and_args(parser.parse_args())
def del_keyword_parse_arguments(app):
	"""Integrated help and options / arguments for « delete keyword »."""

	usage_text = "\n\t%s keyword --name=<nom>" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'del_keyword'))

	keyword = OptionGroup(parser, stylize(ST_OPTION, _(u"Delete keyword options")))

	keyword.add_option("--name",
		action="store", type="string", dest="name", default=None,
		help=_(u"Specify the keyword to delete."))

	keyword.add_option("--del-children",
		action="store_true", dest="del_children", default=False,
		help=_(u"Delete the parent and his children."))

	parser.add_option_group(keyword)

	return parser.parse_args()
def del_privilege_parse_arguments(app):
	"""Integrated help and options / arguments for « add keyword »."""

	usage_text = "\n\t%s priv|privs|privilege|privileges [--name|--names=]privilege1[[,privilege2],…]\n" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'del_privilege'))
	parser.add_option_group(common_filter_group(app, parser, 'del', 'privileges'))


	priv = OptionGroup(parser, stylize(ST_OPTION, _(u"Delete privilege options")))

	priv.add_option("--name", "--names",
		action="store", type="string", dest="privileges_to_remove", default=None,
		help=_(u"The privilege's name(s). %s and can be a single word "
			u"or multiple ones, separated by commas.") %
				stylize(ST_IMPORTANT, _(u"This argument is required")))

	parser.add_option_group(priv)

	return check_opts_and_args(parser.parse_args())
def del_volume_parse_arguments(app):

	usage_text = ("\n\t%s volume[s] [--force] <vol1[,vol2[,…]]>" %
		stylize(ST_APPNAME, "%prog"))

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'del_volume'))
	parser.add_option_group(common_filter_group(app, parser, 'del', 'volumes'))

	#volume = OptionGroup(parser, stylize(ST_OPTION, "Delete volume(s) options "))
	#parser.add_option_group(volume)

	return check_opts_and_args(parser.parse_args())

### Modify arguments ###
def mod_user_parse_arguments(app):

	usage_text = "\n\t%s user --login=<login> [--gecos=<new GECOS>] [--password=<new passwd> | --auto-password] [--password-size=<size>]\n" % stylize(ST_APPNAME, "%prog") \
		+ '\t\t[--lock|--unlock] [--add-groups=<group1[[,group2][,…]]>] [--del-groups=<group1[[,group2][,…]]>]\n' \
		+ '\t\t[--shell=<new shell>]\n'  \
		"\t%s user --login=<login> --apply-skel=<squelette>" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'mod_user'))
	parser.add_option_group(common_filter_group(app, parser, 'mod', 'users'))

	user = OptionGroup(parser, stylize(ST_OPTION, _(u"Modify user options")))

	user.add_option("--password", '-p',
		dest="newpassword", default=None,
		help=_(u"Specify user's new password on the command line "
			u"(%s, it can be written in your shell history file).") %
			stylize(ST_IMPORTANT, 'insecure'))

	user.add_option("--change-password", '-C', '--interactive-password',
		action="store_true", dest="interactive_password", default=False,
		help=_(u"Ask for a new password for the user. If changing your own "
			u"password, you will be asked for the old, too."))

	user.add_option("--auto-password", '-P', '--random-password',
		action="store_true", dest="auto_passwd", default=False,
		help=_(u"let the system generate a random password for this user."))

	user.add_option("--password-size", '-S',
		type='int', dest="passwd_size",
		default=LMC.rwi.configuration_get('users.min_passwd_size'),
		help=_(u"choose the new password length (default %s).") %
			LMC.rwi.configuration_get('users.min_passwd_size'))

	user.add_option('-e', "--gecos",
		dest="newgecos", default=None,
		help=_(u"Specify user's new GECOS string (generaly "
			u"first and last names)."))

	user.add_option('-s', "--shell",
		dest="newshell", default=None,
		help=_(u"Specify user's new shell (generaly /bin/something, must "
			u"be taken from %s).") % ', '.join(stylize(ST_COMMENT, shell)
				for shell in LMC.rwi.configuration_get('users.shells')))

	user.add_option('-l', "--lock",
		action="store_true", dest="lock", default=None,
		help=_(u"lock the account (user wn't be able to login under Linux "
			u"and Windows/MAC until unlocked)."))

	user.add_option('-L', "--unlock",
		action="store_false", dest="lock", default=None,
		help=_(u"unlock the user account and restore login ability."))

	# the --watched flag is used as a selector, thus not here in modifiers
	user.add_option("-w", "--set-watched", "--set-inotified",
		action="store_true", dest="set_inotified", default=None,
		help=_(u"(Re-)watch the home directory of the user for content changes."))

	# the --not-watched flag is used as a selector, thus not here in modifiers
	user.add_option("-W", "--set-not-watched", "--set-not-inotified",
		action="store_false", dest="set_inotified", default=None,
		help=_(u"Do not watch the home directory of the user for content "
			u"changes. Usefull for big directory which slow down licornd. You "
			u"have to manually run {0} on non-watched groups.").format(
				stylize(ST_DEFAULT, 'chk')))

	user.add_option("--add-groups",
		dest="groups_to_add", default=None,
		help=_(u"make user member of these groups."))

	user.add_option("--del-groups",
		dest="groups_to_del", default=None,
		help=_(u"remove user from these groups."))

	user.add_option("--apply-skel",
		action="store", type="string", dest="apply_skel", default=None,
		help=_(u"Re-apply the user's skel, or another skel you specify on "
			u"the command line. (use with caution, it will "
			u"overwrite the dirs/files provided by the skel in the "
			u"user's home dir."))

	user.add_option('--restore-watches',
		action='store_true', dest='restore_watch', default=False,
		help=_(u"Restore the INotifier watch for this account home directory. "
			u"This is particularly useful after a directory move."))

	parser.add_option_group(user)
	try:
		opts, args = parser.parse_args()
	except Exception, e:
		lprint(e)

	if opts.newpassword is None and not opts.non_interactive:
		pass

	# note the current user for diverses mod_user operations
	opts.current_user = getpass.getuser()

	return opts, args
def mod_machine_parse_arguments(app):

	usage_text = "\n\t%s machine[s] [[--shutdown] [--warn-users]] [--upgrade]" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'mod_machine'))
	parser.add_option_group(common_filter_group(app, parser, 'mod', 'machines'))

	machine = OptionGroup(parser, stylize(ST_OPTION, _(u"Modify machine(s) options")))

	machine.add_option('--shutdown', '-s',
		action='store_true', dest="shutdown", default=False,
		help=_(u"remotely shutdown specified machine(s)."))

	machine.add_option('--warn-user', '--warn-users', '-w',
		action="store_false", dest="warn_users", default=True,
		help=_(u'Display a warning message to connected user(s) before '
			u'shutting system(s) down.'))

	machine.add_option('--upgrade', '-u', '--do-upgrade',
		'--update',
		'--do-updates', '--install-updates',
		'--unattended-upgrades', '--do-unattended-upgrades',
		action='store_true', dest="do_upgrade", default=False,
		help=_(u"remotely upgrade pending packages (do security updates)."))

	parser.add_option_group(machine)

	return check_opts_and_args(parser.parse_args())
def mod_task_parse_arguments(app):

	usage_text = "\n\t%s task[s] : Not yet implement, please delete the task " \
	" and create a new one." % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'mod_task'))
	parser.add_option_group(common_filter_group(app, parser, 'mod', 'task'))

	return check_opts_and_args(parser.parse_args())
def mod_volume_parse_arguments(app):

	usage_text = ("\n\t%s volume[s] [--enable|--disable] <vol1[,vol2[,…]]>" %
		stylize(ST_APPNAME, "%prog"))

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'mod_volume'))
	#parser.add_option_group(common_filter_group(app, parser, 'mod', 'volumes'))

	volume = OptionGroup(parser,
					stylize(ST_OPTION, _(u"Modify volume(s) options")))

	volume.add_option('-e', '--enable', '--enable-volume',  '--enable-volumes',
		action='store', dest="enable_volumes", default=None,
		help=_(u"Specify one or more volume(s) to enable (mark as available "
			"and reserved for %s internal use), either by giving its "
			"device path or mount point.") %
				stylize(ST_NAME, LMC.rwi.configuration_get('app_name')))

	volume.add_option('-E', '-d', '--disable', '--disable-volume',
		'--disable-volumes', action="store", dest="disable_volumes",
		default=None, help=_(u"specify one or more volume(s) to disable "
			u"(unmark as available for %s), either by giving its device "
			u"path or mount point.") %
				stylize(ST_NAME, LMC.rwi.configuration_get('app_name')))

	volume.add_option('-m', '--mount', '--mount-volume',  '--mount-volumes',
		action='store', dest="mount_volumes", default=None,
		help=_(u"specify one or more volume(s) to (re-)mount."))

	volume.add_option('-u', '-M', '--umount', '--unmount', '--umount-volume',
		'--unmount-volume', '--umount-volumes', '--unmount-volumes',
		action="store", dest="unmount_volumes", default=None,
		help=_(u"specify one or more volume(s) to unmount."))

	# manually add, remove or rescan the system for added or removed devices,
	# to maintain an up-to-date list of volumes. This is meant to be called
	# by udev and scripts only, thus we suppress help.
	volume.add_option('--add', '--add-volume', '--add-volumes', action="store",
		dest="add_volumes", default=None, help=SUPPRESS_HELP)

	volume.add_option('--del', '--del-volume', '--del-volumes', action="store",
		dest="del_volumes", default=None, help=SUPPRESS_HELP)

	volume.add_option('--rescan', '-r', action="store_true", dest="rescan",
		default=False, help=SUPPRESS_HELP)

	parser.add_option_group(volume)

	return check_opts_and_args(parser.parse_args())
def mod_group_parse_arguments(app):

	usage_text = "\n\t%s group --name=<nom_actuel> [--rename=<nouveau_nom>]\n" % stylize(ST_APPNAME, "%prog") \
		+ "\t\t[--add-users=<user1[[,user2][,…]]>] [--del-users=<user1[[,user2][,…]]>]\n" \
		+ "\t\t[--add-resps=<user1[[,user2][,…]]>] [--delete-resps=<user1[[,user2][,…]]>]\n" \
		+ "\t\t[--add-guests=<user1[[,user2][,…]]>] [--delete-guests=<user1[[,user2][,…]]>]\n" \
		+ "\t\t[--permissive|--not-permissive] [--skel=<new skel>] [--description=<new description>]"

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'mod_group'))
	parser.add_option_group(common_filter_group(app, parser, 'mod', 'groups'))

	group = OptionGroup(parser, stylize(ST_OPTION, _(u"Modify group options")))

	group.add_option("--rename",
		action="store", type="string", dest="newname", default=None,
		help=_(u"Specify group's new name (not yet implemented)."))

	group.add_option("--skel",
		action="store", type="string", dest="newskel", default=None,
		help=_(u"Specify group's new skel dir."))

	group.add_option("--description",
		action="store", type="string", dest="newdescription", default=None,
		help=_(u"Specify new group's description"))

	group.add_option("-p", "--permissive", "--set-permissive",
		action="store_true", dest="permissive", default=None,
		help=_(u"Set the shared directory of the group permissive."))

	group.add_option("-P", "--not-permissive", "--set-not-permissive",
		action="store_false", dest="permissive", default=None,
		help=_(u"Set the shared directory of the group not permissive."))

	# the --watched flag is used as a selector, thus not here in modifiers
	group.add_option("-w", "--set-watched", "--set-inotified",
		action="store_true", dest="set_inotified", default=None,
		help=_(u"(Re-)watch the shared directory of the group for content changes."))

	# the --not-watched flag is used as a selector, thus not here in modifiers
	group.add_option("-W", "--set-not-watched", "--set-not-inotified",
		action="store_false", dest="set_inotified", default=None,
		help=_(u"Do not watch the shared directory of the group for content "
			u"changes. Usefull for big directory which slow down licornd. You "
			u"have to manually run {0} on non-watched groups.").format(
				stylize(ST_DEFAULT, 'chk')))

	group.add_option('--restore-watches',
		action='store_true', dest='restore_watch', default=False,
		help=_(u"Restore the INotifier watch for the group home directory. "
			u"This is particularly useful after a directory move."))

	group.add_option("--add-users",
		action="store", type="string", dest="users_to_add", default=None,
		help=_(u"Add users to the group. The users are separated "
			u"by commas without spaces."))

	group.add_option("--del-users",
		action="store", type="string", dest="users_to_del", default=None,
		help=_(u"Delete users from the group. The users are separated "
			u"by commas without spaces."))

	group.add_option("--add-resps",
		action="store", type="string", dest="resps_to_add", default=None,
		help=_(u"Add responsibles to the group. The responsibles are "
			u"separated by commas without spaces."))

	group.add_option("--del-resps",
		action="store", type="string", dest="resps_to_del", default=None,
		help=_(u"Delete responsibles from the group. The responsibles "
			u"are separated by commas without spaces."))

	group.add_option("--add-guests",
		action="store", type="string", dest="guests_to_add", default=None,
		help=_(u"Add guests to the group. The guests are separated "
			u"by commas without spaces."))

	group.add_option("--del-guests",
		action="store", type="string", dest="guests_to_del", default = None,
		help=_(u"Delete guests from the group. The guests are separated "
			u"by commas without spaces."))

	group.add_option("--add-granted-profiles",
		action="store", type="string", dest="granted_profiles_to_add", default=None,
		help=_(u"Add the profiles which the users can access to the "
			u"group's shared directory. The profiles are separated by "
			u"commas without spaces."))

	group.add_option("--del-granted-profiles",
		action="store", type="string", dest="granted_profiles_to_del", default=None,
		help=_(u"Delete the profiles which the users can access "
			u"to the group's shared directory. The profiles are "
			u"separated by commas without spaces."))

	backends = LMC.rwi.groups_backends_names()

	if len(backends) > 1:
		group.add_option('--move-to-backend', '--change-backend', '--move-backend',
			action="store", type="string", dest="move_to_backend", default=None,
			help=_(u'Move the group from its current backend to another, '
				u'where it will definitely be stored (specify new backend '
				u'name as argument, taken from %s).') %
				u', '.join(stylize(ST_NAME, backend) for backend in backends))

	parser.add_option_group(group)

	return check_opts_and_args(parser.parse_args())
def mod_profile_parse_arguments(app):

	usage_text = "\n\t%s profile --group=<nom> [--name=<nouveau_nom>] [--rename-group=<nouveau_nom>]\n" % stylize(ST_APPNAME, "%prog") \
		+ "\t\t[--comment=<nouveau_commentaire>] [--shell=<nouveau_shell>] [--skel=<nouveau_skel>]\n" \
		+ "\t\t[--quota=<nouveau_quota>] [--add-groups=<groupes>] [--del-groups=<groupes>]\n" \
		+ "\t%s profile <--apply-groups|--apply-skel|--apply-all> [--force]\n" % stylize(ST_APPNAME, "%prog") \
		+ "\t\t[--to-users=<user1[[,user2][,…]]>] [--to-groups=<group1[[,group2][,…]]>]\n" \
		+ "\t\t[--to-all] [--to-members] [--no-instant-apply] [--no-sync]"

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(
		common_behaviour_group(app, parser, 'mod_profile'))
	parser.add_option_group(common_filter_group(app, parser, 'mod', 'profiles'))

	profile = OptionGroup(parser, stylize(ST_OPTION, "Modify profile options "))

	profile.add_option("--rename", '--new-name',
		action="store", type="string", dest="newname", default=None,
		help=_(u"specify profile's new name"))

	profile.add_option("--rename-group", '--new-group-name',
		action="store", type="string", dest="newgroup", default=None,
		help=_(u"Rename primary group (NOT IMPLEMENTED)."))

	profile.add_option("--description",
		action="store", type="string", dest="description", default=None,
		help=_(u"Change profile's description."))

	profile.add_option("--shell",
		action="store", type="string", dest="newshell", default=None,
		help=_(u"Change profile shell (defaults to %s "
			"if you specify --shell without argument)"
			"Instant-applyed to current members if not specified otherwise.") %
				stylize(ST_DEFAULT, LMC.rwi.configuration_get('users.default_shell')))

	profile.add_option("--quota",
		action="store", type="int", dest="newquota", default=None,
		help=_(u"Change profile's user quota (in Mb, defaults "
			u"to %s if you specify --quota without argument)."
			u"Instant-applyed to current members if not specified otherwise.") %
				stylize(ST_DEFAULT, "1024"))

	profile.add_option("--skel",
		action="store", type="string", dest="newskel", default=None,
		help=_(u"Change profile skel (specify a skel dir as an absolute "
			u"pathname, defaults to %s if you give --skel without argument)."
			u"Instant-applyed to current members if not specified otherwise.") %
				stylize(ST_DEFAULT, LMC.rwi.configuration_get('users.default_skel')))

	profile.add_option("--add-groups",
		action="store", type="string", dest="groups_to_add", default=None,
		help=_(u"Add one or more group(s) to default memberships of "
			u"profile (separate groups with commas without spaces)."
			u"Instant-applyed to current members if not specified otherwise."))

	profile.add_option("--del-groups",
		action="store", type="string", dest="groups_to_del", default=None,
		help=_(u"Delete one or more group(s) from default memberships "
			u"of profile (separate groups with commas without spaces). "
			u"Instant-applyed to current members if not specified otherwise."))

	profile.add_option("--apply-groups",
		action="store_true", dest="apply_groups", default=False,
		help=_(u"Re-apply only the default group memberships of the profile."))

	profile.add_option("--apply-skel",
		action="store_true", dest="apply_skel", default=False,
		help=_(u"Re-apply only the skel of the profile."))

	profile.add_option("--apply-all",
		action="store_true", dest="apply_all_attributes", default=False,
		help=_(u"Re-apply all the profile's attributes (groups and skel)."))

	profile.add_option("--to-users",
		action="store", type="string", dest="apply_to_users", default=None,
		help=_(u"Re-apply to specific users accounts (separate them "
			"with commas without spaces)."))

	profile.add_option("--to-groups",
		action="store", type="string", dest="apply_to_groups", default=None,
		help=_(u"Re-apply to all members of one or more groups "
			u"(separate groups with commas without spaces). "
			u"You can mix --to-users and --to-groups."))

	profile.add_option("--to-members",
		action="store_true", dest="apply_to_members", default = False,
		help=_(u"Re-apply to all users members of the profile."))

	profile.add_option("--to-all",
		action="store_true", dest="apply_to_all_accounts", default=None,
		help=_(u"Re-apply to all user accounts on the system "
			u"(LENGHTY operation !)."))

	profile.add_option("--no-instant-apply",
		action="store_false", dest="instant_apply", default=True,
		help=_(u"Don't apply group addition/deletion and other parameters "
			u"instantly to all members of the modified profile "
			u"(%s; use this only if you know what you're doing).") %
				stylize(ST_IMPORTANT, u"this is not recommended"))

	profile.add_option("--no-sync",
		action="store_true", dest="no_sync", default = False,
		help=_(u"Commit changes only after all modifications "
			u"(currently disabled)."))

	parser.add_option_group(profile)

	opts, args = check_opts_and_args(parser.parse_args())

	if opts.apply_all_attributes:
		opts.apply_skel = True
		opts.apply_groups = True

	return opts, args
def mod_keyword_parse_arguments(app):

	usage_text = "\n\t%s keyword --name=<nom> [--rename=<nouveau_nom>] [--parent=<nouveau_parent>]\n" % stylize(ST_APPNAME, "%prog") \
		+ "\t\t[--remove-parent] [--recursive]"

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'mod_profile'))

	keyword = OptionGroup(parser, stylize(ST_OPTION, _(u"Modify keyword options")))

	keyword.add_option("--name",
		action="store", type="string", dest="name", default=None,
		help=_(u"Specify keyword to modify (%s).") %
			stylize(ST_IMPORTANT, "required"))

	keyword.add_option("--rename",
		action="store", type="string", dest="newname", default=None,
		help=_(u"Rename keyword"))

	keyword.add_option("--parent",
		action="store", type="string", dest="parent", default=None,
		help=_(u"Change keyword's parent."))

	keyword.add_option("--remove-parent",
		action="store_true", dest="remove_parent", default=False,
		help=_(u"Remove parent."))

	keyword.add_option("--recursive",
		action="store_true", dest="recursive", default=False,
		help=_(u"Modify all file in all subdirs."))

	keyword.add_option("--description",
		action="store", type="string", dest="description", default=None,
		help=_(u"Remove parent."))

	parser.add_option_group(keyword)

	return parser.parse_args()
def mod_path_parse_arguments(app):

	usage_text = "\n\t%s path [--path=]<fichier_ou_repertoire> [--add-keywords=<kw1[,kw1,…]>] [--del-keywords=<kw1[,kw1,…]>]\n" % stylize(ST_APPNAME, "%prog") \
		+ "\t\t[--clear-keywords] [--recursive]"

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# common behaviour group
	parser.add_option_group(common_behaviour_group(app, parser, 'mod_path'))

	path = OptionGroup(parser, stylize(ST_OPTION, _(u"Modify keyword options")))

	path.add_option("--path",
		action="store", type="string", dest="path", default=None,
		help=_(u"specify path of the file/directory to tag (%s).") %
			stylize(ST_IMPORTANT, _(u"required")))

	path.add_option("--add-keywords",
		action="store", type="string", dest="keywords_to_add", default=None,
		help=_(u"Add keywords."))

	path.add_option("--del-keywords",
		action="store", type="string", dest="keywords_to_del", default=None,
		help=_(u"Remove keywords."))

	path.add_option("--clear-keywords",
		action="store_true", dest="clear_keywords", default = False,
		help=_(u"Remove all keywords."))

	path.add_option("--recursive",
		action="store_true", dest="recursive", default = False,
		help=_(u"Set modifications to all subdirs."))

	path.add_option("--description",
		action="store", type="string", dest="description", default = False,
		help=_(u"Remove parent."))

	parser.add_option_group(path)

	return parser.parse_args()
def mod_configuration_parse_arguments(app):

	usage_text = "\n\t%s config[uration] [--hide-groups|--set-hidden-groups|--unhide-groups|-u|-U] [--set-hostname <new hostname>] [--restrictive] [--set-ip-address <NEW.ETH0.IP.ADDR>]" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	# FIXME: review common_behaviour_group to set eventual special options
	# (for modify config ?).
	parser.add_option_group(common_behaviour_group(app, parser, 'mod_config'))

	configuration_group = OptionGroup(parser, stylize(ST_OPTION,
		_(u"Modify configuration options")))

	configuration_group.add_option("--setup-shared-dirs",
		action="store_true", dest="setup_shared_dirs", default=False,
		help=_(u'create system groups, directories and settings from system '
			u'configuration (PARTIALLY OBSOLETED, TOTALLY UNSUPPORTED AND '
			u'VERY DANGEROUS, USE WITH CAUTION).'))

	configuration_group.add_option("-r", "--restrictive", "--set-restrictive",
		action="store_true", dest="restrictive", default=False,
		help=_(u'When creating system groups and directories, apply '
			u'restrictive perms (710) on shared dirs instead of relaxed '
			u'ones (750).'))

	configuration_group.add_option("-u", "--hide-groups", "--set-groups-hidden",
		action="store_true", dest="hidden_groups", default=None,
		help=_(u"Set restrictive perms (710) on %s.") %
			stylize(ST_PATH, LMC.rwi.configuration_get('groups.base_path')))

	configuration_group.add_option("-U", "--unhide-groups",
		"--set-groups-visible",
		action="store_false", dest="hidden_groups", default=None,
		help=_(u"Set relaxed perms (750) on %s.") % stylize(ST_PATH,
			LMC.rwi.configuration_get('groups.base_path')))

	configuration_group.add_option('-b', "--enable-backends",
		action="store", dest="enable_backends", default=None,
		help=_(u'Enable given backend(s) on the current system (separated '
			u'by commas without spaces). List of available backends with '
			u'`%s`.') % stylize(ST_MODE, 'get config backends'))

	configuration_group.add_option('-B', "--disable-backends",
		action="store", dest="disable_backends", default=None,
		help=_(u'Disable given backend(s) on the current system (separated '
			u'by commas without spaces). List of available backends with '
			u'`%s`.') % stylize(ST_MODE, 'get config backends'))

	configuration_group.add_option('-e', "--enable-extensions",
		action="store", dest="enable_extensions", default=None,
		help=_(u'Enable given extension(s) on the current system (separated '
			u'by commas without spaces). List of available extensions with '
			u'`%s`.') % stylize(ST_MODE, 'get config extensions'))

	configuration_group.add_option('-E', "--disable-extensions",
		action="store", dest="disable_extensions", default=None,
		help=_(u'Disable given extension(s) on the current system (separated '
			u'by commas without spaces). List of available extensions with '
			u'`%s`.') % stylize(ST_MODE, 'get config extensions'))

	configuration_group.add_option( "--set-hostname",
		action="store", type="string", dest="set_hostname", default=None,
		help=_(u"change machine hostname (not yet implemented)."))

	configuration_group.add_option("-i", "--set-ip-address",
		action="store", type="string", dest="set_ip_address", default=None,
		help=_(u"change machine's IP (for eth0 only) (not yet implemented)."))

	configuration_group.add_option("--add-privileges",
		action="store", type="string", dest="privileges_to_add", default=None,
		help=_(u"add privileges (system groups) to privileges whitelist."))

	configuration_group.add_option("--remove-privileges",
		action="store", type="string", dest="privileges_to_remove",
		default=None,
		help=_(u"remove privileges (system groups) from privileges whitelist."))

	parser.add_option_group(configuration_group)

	return parser.parse_args()

### Check arguments ###

def chk_user_parse_arguments(app):
	"""Integrated help and options / arguments for « check user(s) »."""

	usage_text = "\n\t%s user[s] --login login1[[,login2][…]] [--minimal] [--yes|--no]\n" % stylize(ST_APPNAME, "%prog") \
		+ "\t%s user[s] --uid uid1[[,uid2][…]] [--minimal] [--yes|--no]" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'check'))
	parser.add_option_group(common_filter_group(app, parser, 'chk', 'users'))

	return check_opts_and_args(parser.parse_args())
def chk_group_parse_arguments(app):
	"""Integrated help and options / arguments for « check group(s) »."""

	usage_text = "\n\t%s group[s] --name group1[[,group2][,…]]" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'check'))
	parser.add_option_group(common_filter_group(app, parser, 'chk', 'groups'))

	return check_opts_and_args(parser.parse_args())
def chk_profile_parse_arguments(app):
	"""Integrated help and options / arguments for « check profile(s) »."""

	usage_text = "\n\t%s profile[s] --name profile1[[,profile2][…]]" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'check'))
	parser.add_option_group(common_filter_group(app, parser, 'chk', 'profiles'))

	return check_opts_and_args(parser.parse_args())
def chk_configuration_parse_arguments(app):
	"""TODO"""

	usage_text = "\n\t%s config[uration] -a | (names|hostname)" % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'check'))
	parser.add_option_group(common_filter_group(app, parser, 'chk', 'configuration'))

	return parser.parse_args()
def chk_system_parse_arguments(app):
	"""TODO"""

	usage_text = "\n\t%s system -a [-w|--wmi-tests app1[,app2[,…]] " % stylize(ST_APPNAME, "%prog")

	parser = OptionParser(usage=usage_text,
		version=build_version_string(app, version))

	parser.add_option_group(common_behaviour_group(app, parser, 'check'))
	parser.add_option_group(common_filter_group(app, parser, 'chk', 'system'))

	group = OptionGroup(parser, stylize(ST_OPTION,
		_(u"Modify configuration options")))

	group.add_option('-w', '--wmi-test', '--wmi-tests',
		action='store', type='string', dest="wmi_test_apps", default='',
		help=_(u'Launch Django tests against the WMI2 apps, separated by '
				u'commas without spaces. Just type "all" if you want it.'))
	parser.add_option_group(group)

	return parser.parse_args()

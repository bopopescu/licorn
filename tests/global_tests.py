# -*- coding: utf-8 -*-
"""
Licorn Test Suite global tests.

:copyright:
	* 2010-2012 Olivier Cortès <oc@meta-it.fr>,
	* 2010-2012 META IT http://meta-it.fr

:license: GNU GPL version 2

"""

import sys, os, re, hashlib, tempfile
import gzip, time, shutil

from licorn.foundations import settings
from licorn.tests       import *

users_base_path  = configuration_get('users.base_path')
groups_base_path = configuration_get('groups.base_path')
resp_prefix      = configuration_get('groups.resp_prefix')
guest_prefix     = configuration_get('groups.guest_prefix')
home_base_path   = settings.defaults.home_base_path

CLIPATH='../interfaces/cli'
ADD    = PYTHON + [ CLIPATH + '/add.py']
DEL = PYTHON + [ CLIPATH + '/del.py']
MOD = PYTHON + [ CLIPATH + '/mod.py']
GET = PYTHON + [ CLIPATH + '/get.py']
CHK  = PYTHON + [ CLIPATH + '/chk.py']

def test_integrated_help(testsuite):
	"""Test extensively argmarser contents and intergated help."""

	commands = []

	for program in (GET, ADD, MOD, DEL, CHK):

		commands.extend([
			program + ['-h'],
			program + ['--help']])

		if program == ADD:
			modes = [ 'user', 'users', 'group', 'profile' ]
		elif program == MOD:
			modes = [ 'configuration', 'user', 'group', 'profile' ]
		elif program == DEL:
			modes = [ 'user', 'group', 'groups', 'profile' ]
		elif program == GET:
			modes = [ 'user', 'users', 'passwd', 'group', 'groups', 'profiles',
				'configuration' ]
		elif program == CHK:
			modes = [ 'user', 'users', 'group', 'groups', 'profile', 'profiles',
				'configuration' ]

		for mode in modes:
			if program == GET and mode == 'configuration':
				commands.append(program + [ mode ])
			else:
				commands.extend([
					program + [ mode, '-h' ],
					program + [ mode, '--help' ]
					])

	testsuite.add_scenario(ScenarioTest(commands, descr='''test integrated '''
	'''help of all CLI commands'''))
def test_get(context, testsuite):
	"""Test GET a lot."""

	commands = []

	for category in [ 'config_dir', 'main_config_file' ]:
		for mode in [ '', '-s', '-b', '--bourne-shell', '-c', '--c-shell',
			'-p', '--php-code' ]:
			commands.append(GET + [ 'configuration', category, mode ])

	for category in [ 'skels', 'shells', 'backends' ]:
		commands.append(GET + [ 'config', category ])

	commands += [
		# users
		GET + [ "users" ],
		GET + [ "users", "--xml" ],
		GET + [ "users", "--long" ],
		GET + [ "users", "--long", "--xml" ],
		GET + [ "users", "--all" ],
		GET + [ "users", "--xml", "--all" ],
		GET + [ "users", "--all", "--long" ],
		GET + [ "users", "--xml", "--all", "--long" ],
		# groups
		GET + [ "groups" ],
		GET + [ "groups", "--xml" ],
		GET + [ "groups", "--long" ],
		GET + [ "groups", "--long", "--xml" ],
		GET + [ "groups", "--xml", "--all" ],
		GET + [ "groups", "--xml", "--all", "--long" ],
		GET + [ "groups", "--xml", "--guests" ],
		GET + [ "groups", "--xml", "--guests", "--long" ],
		GET + [ "groups", "--xml", "--responsibles" ],
		GET + [ "groups", "--xml", "--responsibles", "--long" ],
		GET + [ "groups", "--xml", "--privileged" ],
		GET + [ "groups", "--xml", "--privileged", "--long" ],
		# Profiles
		GET + [ "profiles" ],
		GET + [ "profiles", '-x' ],
		GET + [ "profiles", "--xml" ],
		# Privileges
		GET + [ "privileges" ],
		GET + [ "privileges", "-x" ],
		GET + [ "privileges", "--xml" ],
		# Events (NO XML available)
		GET + [ "events" ],
		GET + [ "events", '-v' ],
		# should not produce more nor less than '-v'
		GET + [ "events", '-vv' ],
		]

	testsuite.add_scenario(ScenarioTest(commands, context=context, descr='''CLI get tests'''))
def test_find_new_indentifier(testsuite):
	""" TODO: this should go into foundations/pyutils_test.py and be
		reimplemented with py.test """

	assert(pyutils.next_free([5,6,48,2,1,4], 5, 30) == 7)
	assert(pyutils.next_free([5,6,48,2,1,4], 1, 30) == 3)
	assert(pyutils.next_free([1,3], 1, 30) == 2)

	try:
		pyutils.next_free([1,2], 1, 2)
	except:
		assert(True) # good behaviour
	else:
		assert(False)

	assert(pyutils.next_free([1,2], 1, 30) == 3)
	assert(pyutils.next_free([1,2,4,5], 3, 5) == 3)
def test_regexes(testsuite):
	""" Try funky strings to make regexes fail (they should not)."""

	# TODO: test regexes directly from defs in licorn.core….
	regexes_commands = []

	# groups related
	regexes_commands.extend([
		ADD + [ 'group', "--name='_-  -_'" ],
		CHK + [ 'group', "--name='_-  -_'" ],
		ADD + [ 'group', "--name=';-)'" ],
		ADD + [ 'group', "--name='^_^'" ],
		ADD + [ 'group', "--name='le copain des groupes'" ],
		CHK + [ 'group', '-v', "--name='le copain des groupes'" ],
		ADD + [ 'group', "--name='héhéhé'" ],
		ADD + [ 'group', "--name='%(\`ls -la /etc/passwd\`)'" ],
		ADD + [ 'group', "--name='echo print coucou | python | nothing'" ],
		ADD + [ 'group', "--name='**/*-'" ],
		CHK + [ 'group', '-v', "--name='**/*-'" ]
		])

	# users related
	regexes_commands.extend([
		ADD + [ 'user', "--login='_-  -_'" ],
		ADD + [ 'user', "--login=';-)'" ],
		ADD + [ 'user', "--login='^_^'" ],
		ADD + [ 'user', "--login='le copain des utilisateurs'" ],
		ADD + [ 'user', "--login='héhéhé'" ],
		ADD + [ 'user', "--login='%(\`ls -la /etc/passwd\`)'" ],
		ADD + [ 'user', "--login='echo print coucou | python'" ],
		ADD + [ 'user', "--login='**/*-'" ]
		])

	testsuite.add_scenario(ScenarioTest(regexes_commands,
							descr='Test internal regexes.'))
def test_groups(context, testsuite):
	"""Test ADD/MOD/DEL on groups in various ways."""
	gname = 'groupeA'

	def chk_acls_cmds(group, subdir=None):
		return [ 'getfacl', '-R', '%s/%s%s' % (
				groups_base_path, group,
				'/%s' % subdir if subdir else '') ]

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', '--name=%s' % gname, '-v' ],
		chk_acls_cmds(gname),
		ADD + [ 'group', gname ],
		ADD + [ 'group', gname, '-v' ],
		DEL + [ 'group', gname, '--no-archive' ],
		DEL + [ 'group', gname, '--no-archive' ],
		],
		context=context,
		descr='''create group, verify ACL, '''
			'''try to create again in short mode, '''
			'''remove various components then check, '''
			'''then delete group and try to re-delete.''', clean_num=2))

	gname = 'ACL_tests'

	# completeny remove the shared group dir and verify CHK repairs it.
	remove_group_cmds = [ "rm", "-vrf",	"%s/%s" % (groups_base_path, gname)]

	# idem with public_html shared subdir.
	remove_group_html_cmds = [ "rm", "-vrf",
							"%s/%s/public_html" % (groups_base_path, gname) ]

	# remove the posix ACLs and let CHK correct everything (after having
	# declared an error first with --auto-no).
	remove_group_acls_cmds = [ "setfacl", "-R", "-b",
								"%s/%s" % (groups_base_path, gname) ]

	# idem for public_html subdir.
	remove_group_html_acls_cmds = [ "setfacl", "-R", "-b",
							"%s/%s/public_html" % (groups_base_path, gname) ]

	bad_chown_group_cmds = [ 'chown', 'bin:daemon', '--changes',
								'%s/%s' % (groups_base_path, gname) ]

	bad_chown_group_html_cmds = [ 'chown', 'bin:daemon', '--changes',
							'%s/%s/public_html' % (groups_base_path, gname) ]

	# not yet anymore now that we don't support apache.
	#		(remove_group_html_cmds, chk_acls_cmds(gname, 'public_html')),
	#		(remove_group_html_acls_cmds, chk_acls_cmds(gname, 'public_html')),

	for break_acl_pre_cmd, chk_acl_cmd in (
				(remove_group_acls_cmds, chk_acls_cmds(gname)),
				(bad_chown_group_cmds, chk_acls_cmds(gname))):
		for subopt in ('--auto-no', '--auto-yes', '-vb'):

				testsuite.add_scenario(ScenarioTest([
					ADD + [ 'group', gname, '-v' ],
					break_acl_pre_cmd,
					# not needed anymore, the inotifier is damn fast.
					# [ 'sleep', '1' ],
					CHK + [ 'group', gname, subopt ],
					chk_acl_cmd,
					DEL + [ 'group', gname, '-v', '--no-archive' ]
				],
				descr='Various ACLs alteration tests on groups, which should '
					'be automatically corrected by inotifier (chk should do '
					'nothing).', context=context, clean_num=1))

	for break_acl_pre_cmd, chk_acl_cmd in (
		(remove_group_cmds, chk_acls_cmds(gname)), ):
		for subopt in ('--auto-no', '--auto-yes', '-vbe'):

				testsuite.add_scenario(ScenarioTest([
					ADD + [ 'group', gname, '-v' ],
					break_acl_pre_cmd,
					# not needed anymore, the inotifier is damn fast.
					# [ 'sleep', '1' ],
					CHK + [ 'group', gname, subopt ],
					chk_acl_cmd,
					DEL + [ 'group', gname, '-v', '--no-archive' ]
				],
				descr='Removing the group home should be corrected by chk, '
					'with either --auto-yes or -vb. It should restore the '
					'INotifier watch, too.',
				context=context, clean_num=1))

	gname = 'MOD_tests'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', gname, '-v' ],
		MOD + [ "group", "--name=%s" % gname, "--skel=/etc/doesntexist" ],
		MOD + [ "group", '--name=%s' % gname, '--not-permissive' ],
		# no need to wait here, groups are not permissive by default.
		chk_acls_cmds(gname),
		MOD + [ "group", "--name=%s" % gname, "--permissive" ],
		# we need to wait a short while for new permissions to be applyed in BG.
		['sleep', '1'],
		chk_acls_cmds(gname),
		MOD + [ "group", "--name=%s" % gname, "--permissive" ],
		DEL + [ 'group', gname, '-v' ]
		],
		descr='''modify with a non-existing profile, re-make not-permissive, '''
			'''make permissive.''',
		context=context, clean_num=1))

	gname = 'SYSTEM-test1'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', "--name=%s" % gname, "--system" ],
		GET + [ 'groups' ],
		CHK + [ "group", "-v", "--name=%s" % gname ],
		DEL + ["group", "--name", gname],
		GET + [ 'groups' ],
		CHK + [ "group", "-v", "--name=%s" % gname ]
		],
		descr='''add --system, check, delete and recheck.''',
		context=context, clean_num=3))

	gname = 'SYSTEM-test2'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', gname, '--gid=1520' ],
		GET + [ 'groups', '-la' ],
		DEL + ["group", gname, '--no-archive' ],
		GET + [ 'groups', '-la' ],
		ADD + [ 'group', gname, '--gid=15200', '--system' ],
		GET + [ 'groups', '-la' ],
		DEL + ["group", gname ],
		GET + [ 'groups', '-la' ],
		ADD + [ 'group', gname, '--gid=199', '--system' ],
		GET + [ 'groups', '-la' ],
		# will fail without --force
		DEL + ["group", gname ],
		DEL + ["group", gname, '--force' ],
		GET + [ 'groups', '-la' ]
		],
		context=context,
		descr='''ADD and DEL groups with fixed GIDs (TWO should fail).''',
		clean_num=2))

	gname = 'SKEL-tests'

	testsuite.add_scenario(ScenarioTest([
		ADD + ["group", "--name=%s" % gname, "--skel=/etc/skel",
			"--description='Vive les skel'"],
		GET + [ 'groups', '-la' ],
		DEL + ["group", gname ],
		GET + [ 'groups', '-la' ]
		],
		descr='''ADD group with specified skel and descr''',
		context=context, clean_num=2))

	gname = 'ARCHIVES-test'

	clean_dir_contents(settings.home_archive_dir)

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', gname, '-v' ],
		[ 'touch', "%s/%s/test.txt" % (groups_base_path, gname) ],
		[ 'mkdir', "%s/%s/testdir" % (groups_base_path, gname) ],
		[ 'touch', "%s/%s/testdir/testfile" % (groups_base_path, gname) ],
		# wait for the inotifier to complete ACLs application.
		['sleep', '1'],
		CHK + [ "group", "-vb", gname ],
		DEL + [ 'group', gname ],
		],
		context=context,
		descr='''verify the --archive option of DEL group and check on '''
				'''shared dir contents, ensure #256 if off.''', clean_num=1))

	clean_dir_contents(settings.home_archive_dir)

	uname = 'user_test1'
	gname = 'group_test1'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', '--login=%s' % uname ],
		ADD + [ 'group', '--name=%s' % gname ],
		MOD + [ 'user', '--login=%s' % uname, '--add-groups=%s' % gname ],
		GET + [ 'groups' ],
		GET + [ 'users', '--long' ],
		DEL + [ 'group', '--name=%s' % gname ],
		GET + [ 'groups' ],
		DEL + [ 'user', '--login=%s' % uname ],
		GET + [ 'users', '--long' ]
		],
		context=context,
		descr='''check if a user is assigned to a specified group and if'''
				''' the user list is up to date when the group is deleted.''',
		clean_num=4))

	uname = 'u259'
	gname = 'g259'

	#fix #259
	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', '--name=%s' % gname ],
		[ 'rm', '-vrf', "%s/%s" % (groups_base_path, gname) ],
		DEL + [ 'group', '--name=%s' % gname ],
		],
		context=context,
		descr='check the message when a group (wich group dir has been '
			'deleted) is deleted (avoids #259).', clean_num=1))

	uname = 'u262'
	gname = 'g262'

	testsuite.add_scenario(ScenarioTest([
		# should fail because gid 50 is "staff" on debian systems.
		ADD + [ 'group', '--name=%s' % gname, '--gid=50', '-v' ],
		GET + [ 'groups', '50' ],
		ADD + [ 'group', '--name=%s2' % gname, '--gid=15000', '-v' ],
		GET + [ 'groups', '15000' ],
		# should fail too, 150 is now taken.
		ADD + [ 'group', '--name=%s3' % gname, '--gid=15000', '-v' ],
		GET + [ 'groups', '15000' ],
		# should fail too, 150 is now taken.
		ADD + [ 'group', '--name=%s3' % gname, '--gid=15000',
			'--description=description', '-v' ],
		GET + [ 'groups', '15000' ],
		# should fail too, 150 is now taken.
		ADD + [ 'group', '--name=%s3' % gname, '--gid=15000', '--permissive',
			'-v' ],
		GET + [ 'groups', '15000' ],
		# should fail too, 150 is now taken.
		ADD + [ 'group', '--name=%s3' % gname, '--gid=15000', '--skel=/etc/skel',
			'-v' ],
		GET + [ 'groups', '15000' ],
		DEL + [ 'group', '--name=%s' % gname, '--no-archive' ],
		DEL + [ 'group', '%s2,%s3' % (gname, gname), '--no-archive' ],
		],
		context=context,
		descr='''check if add 2 groups with same GID produce an '''
			'''error (avoid #262)''', clean_num=2))

	uname = 'grp-acl-user'
	gname = 'GRP-ACL-test'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', uname, '-v' ],
		ADD + [ 'group', gname, '-v' ],
		chk_acls_cmds(gname),

		[ 'chown', '-R', '-c', uname, "%s/%s" % (groups_base_path, gname) ],
		# wait for the inotifier to complete ACLs application.
		['sleep', '1'],

		chk_acls_cmds(gname),
		CHK + [ 'group', gname, '-vb' ],
		chk_acls_cmds(gname),

		[ 'chgrp', '-R', '-c', 'audio', "%s/%s" % (groups_base_path, gname) ],
		# wait for the inotifier to complete ACLs application.
		['sleep', '1'],

		chk_acls_cmds(gname),
		CHK + [ 'group', gname, '-vb' ],
		chk_acls_cmds(gname),
		DEL + [ 'group', gname ],
		DEL + [ 'user', uname ]
		],
		context=context, descr='''avoid #268''', clean_num=2))

	# don't test this one on other context than Unix. The related code is
	# generic (doesn't lie in backends) and the conditions to reproduce it are
	# quite difficult with LDAP. The result will be the same anyway.
	if context == 'shadow' :

		uname = 'utest_267'
		gname = 'gtest_267'

		testsuite.add_scenario(ScenarioTest([
			ADD + [ 'user', uname, '-v' ],
			ADD + [ 'group', gname, '-v' ],
			GET + [ 'users', '-l' ],
			GET + [ 'groups' ],
			# should do nothing
			CHK + [ 'groups', '-avb' ],
			CHK + [ 'groups', '-aveb' ],
			[ 'sed', '-i', '/etc/group',
				'-e', r's/^\(root:.*\)$/\1nouser/',
				'-e', r's/^\(audio:.*\)$/\1,foobar,%s/' % uname,
				'-e', r's/^\(%s:.*\)$/\1foobar,%s/' % (gname, uname),
				'-e', r's/^\(adm:.*\)$/\1,perenoel,%s,schproudleboy/' % uname ],
			# wait for the inotifier to complete the reload (it is immediate in
			# 99% of cases, but we need to be sure, to avoid false-negatives).
			['sleep', '1'],

			# should display the dangling users
			GET + [ 'users', '-l' ],
			GET + [ 'groups' ],
			# should do nothing
			CHK + [ 'groups', '-avb' ],
			# should point the problems with dangling users
			CHK + [ 'groups', '-ave', '--auto-no' ],
			# should repair everything
			CHK + [ 'groups', '-aveb' ],
			GET + [ 'users', '-l' ],
			GET + [ 'groups' ],
			DEL + [ 'user', uname ],
			DEL + [ 'group', gname ]
			],
			context=context, descr='''avoid #267''', clean_num=2))

	#fix #297
	gname = 'g297'
	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', '--name=%s' % gname, '--system', '-v' ],
		[ 'get', 'group', gname ],
		ADD + [ 'privileges', '--name=%s' % gname, '-v'],
		GET + [ 'privileges' ],
		DEL + [ 'group', '--name=%s' % gname, '-v' ],
		GET + [ 'groups', gname ],
		GET + [ 'privileges' ]
		],
		context=context,
		descr='''Check if privilege list is up to date after group deletion '''
			'''(fix #297).''', clean_num=3))

	#fix #293
	gname = 'g293'
	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', '--name=%s' % gname, '--gid=15200', '-v' ],
		# should fail (gid already in use)
		ADD + [ 'group', '--name=%s2' % gname, '--gid=15200', '-v' ],
		ADD + [ 'group', '--name=%ssys' % gname, '--gid=199', '--system',
			'-v' ],
		# should fail (gid already in use)
		ADD + [ 'group', '--name=%ssys2' % gname, '--gid=199', '--system',
			'-v' ],
		GET + [ 'groups', '-la' ],
		DEL + [ 'group', '--name=%s' % gname, '-v', '--no-archive' ],
		DEL + [ 'group', '--name=%ssys' % gname, '-v', '--force', '--no-archive' ],
		],
		context=context,
		descr='''tests of groups commands with --gid option (fix #293)''',
		clean_num=2))

	# fix #286
	gname = 'g286'
	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', '--name=%s' % gname, '-v' ],
		GET + [ 'groups' ],
		GET + [ 'group', gname ],
		GET + [ 'group', gname, '-l' ],
		GET + [ 'group', '10000' ],
		GET + [ 'group', '10000' , '-l' ],
		#should fail (gid 11000 is not used)
		GET + [ 'group', '11000' ],
		GET + [ 'group', '11000' , '-l' ],
		GET + [ 'group', '%s,root' % gname ],
		GET + [ 'group', '0,root' ],
		DEL + [ 'group', '--name=%s' % gname, '-v' ],
		GET + [ 'group', 'root' ],
		GET + [ 'group', 'root', '-l' ],
		GET + [ 'group', '0' ],
		GET + [ 'group', '0', '-l' ],
		GET + [ 'group', '1' ],
		GET + [ 'group', '1', '-l' ],
		GET + [ 'groups' ],
		DEL + [ 'group', gname, '--no-archive' ],
		],
		context=context,
		descr='''test command get group <gid|group> (fix #286)''', clean_num=1))

	uname = 'uinteractive'
	gname = 'ginteractive'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '-v' ],
		GET + [ 'groups', '-l' ],
		MOD + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '''--description'''
			'''=This is a massive test description"''', '-iv', '--auto-no' ],
		GET + [ 'groups', '-l' ],
		MOD + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '''--description'''
			'''=This is a massive test description"''', '-iv', '--auto-yes' ],
		GET + [ 'groups', '-l' ],
		MOD + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '''--description'''
			'''=This is a massive test description2''', '-iv', '--batch' ],
		GET + [ 'groups', '-l' ],
		ADD + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '-v' ],
		MOD + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '''--add-users='''
			'''%s,%s2,%s3''' % (uname,uname,uname), '-iv', '--auto-no' ],
		GET + [ 'groups', '-l' ],
		MOD + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '''--add-users='''
			'''%s,%s2,%s3''' % (uname,uname,uname), '-iv', '--auto-yes' ],
		GET + [ 'groups', '-l' ],
		MOD + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '''--del-users='''
			'''%s,%s2,%s3''' % (uname,uname,uname), '-iv', '--batch' ],
		GET + [ 'groups', '-l' ],
		DEL + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '-v' ],
		CHK + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '-iv',
			'--auto-no' ],
		CHK + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '-iv',
			'--auto-yes' ],
		CHK + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '-iv', '--batch' ],
		DEL + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '-iv',
			'--auto-no' ],
		DEL + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '-iv',
			'--auto-yes' ],
		DEL + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '--no-archive' ],
		DEL + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '--no-archive'],
		],
		context=context,
		descr="test groups interactive commands", clean_num=2))

	gname = 'gmultibackend'

	if context == 'openldap':

		# there must be more than one backend for this to work.
		testsuite.add_scenario(ScenarioTest([
			ADD + [ 'group', '--name=%s' % gname, '-v',
				'--in-backend', 'shadow' ],
			GET + [ 'groups', '-l' ],
			ADD + [ 'group', '--name=%s' % gname, '-v', '--backend', context ],
			GET + [ 'groups', '-l' ],
			# this should fail saying that it will be done with std group
			MOD + [ 'group', resp_prefix + gname, '-v',
				'--move-to-backend', context ],
			# this will succeed
			MOD + [ 'group', gname, '-v', '--move-to-backend', context ],
			GET + [ 'groups', '-l', gname ],

			# these 3 should succeed
			ADD + ['group', '--system', 'sys' + gname, '-v',
				'--backend', 'shadow' ],
			MOD + [ 'group', 'sys' + gname, '-v',
				'--move-to-backend', context ],
			GET + [ 'groups', '-l', 'sys' + gname ],

			ADD + ['group', '--system', 'sys2' + gname, '-v',
				'--backend', 'shadow',
				'--gid', str(configuration_get('groups.system_gid_min') - 1) ],
			# this will fail because lacks --force
			MOD + [ 'group', 'sys2' + gname, '-v',
				'--move-to-backend', context ],
			# this will succeed
			MOD + [ 'group', 'sys2' + gname, '-v', '--move-to-backend', context,
				'--force'],
			GET + [ 'groups', '-l', 'sys2' + gname ],

			DEL + [ 'group', gname + ',sys' + gname + ',sys2' + gname, '--force', '--no-archive']
			],
			context=context,
			descr='test add group in manually specified backend and group'
				'backend move.', clean_num=1))
	else:
		testsuite.add_scenario(ScenarioTest([
			ADD + [ 'group', '--name=%s' % gname, '-v', '--backend', context ]
			],
			context=context,
			descr='test add group in manually specified backend (should fail).'
			))

	gname = 'gmultibackend2'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', '--name=%s' % gname, '-v',
			'--users', 'toto,proot' ],
		GET + [ 'groups', '-l' ],
		DEL + [ 'group', gname],
		ADD + [ 'group', '--system', '--name=%s' % gname, '-v',
			'-u', 'proot,toto,bin' ],
		GET + [ 'groups', '-l', gname ],
		DEL + [ 'group', gname],
		ADD + [ 'group', '--name=%s' % gname, '-v',
			'--members', 'foo,bar' ],
		GET + [ 'groups', '-l' ],
		DEL + [ 'group', gname],
		ADD + [ 'group', '--system', '--name=%s' % gname, '-v',
			'--add-users', 'root,toto,proot' ],
		GET + [ 'groups', '-l', gname ],
		DEL + [ 'group', gname, '--force', '--no-archive']
		],
		context=context,
		descr='''test add group --users flag.''', clean_num=1))

	gname = 'g440'
	uname = 'u440'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', uname, '-v' ],
		ADD + [ 'group', gname, '-v' ],
		ADD + [ 'user', uname,  guest_prefix + gname, '-v' ],
		ADD + [ 'user', uname,  gname, '-v' ],
		ADD + [ 'user', uname,  resp_prefix + gname, '-v' ],

		ADD + [ 'user', uname,  gname, '-v' ],
		ADD + [ 'user', uname,  gname, '-v' , '--force'],

		ADD + [ 'user', uname,  guest_prefix + gname, '-v' ],
		ADD + [ 'user', uname,  guest_prefix + gname, '-v', '--force'],

		ADD + [ 'user', uname,  resp_prefix + gname, '-v' ],

		ADD + [ 'user', uname,  guest_prefix + gname, '-v' ],
		ADD + [ 'user', uname,  guest_prefix + gname, '-v', '--force'],

		DEL + [ 'group', gname, '--no-archive'],
		DEL + [ 'user',  uname, '--no-archive']
		],
		context=context,
		descr='enforce #440 checks (mutual-exclusions for rsp-std-gst '
			'group memberships)', clean_num=2))

	# TODO: test other mod group arguments.

	# TODO:
	#FunctionnalTest(DEL + [ 'group', '--name', gname, '--del-users',
	#	'--no-archive'], context=context).Run()

	# RENAME IS NOT SUPPORTED YET !!
	#log_and_exec(MOD + " group --name=TestGroup_A --rename=leTestGroup_A/etc/power")

	# FIXME: get members of group for later verifications…
	#FunctionnalTest(DEL + ["group", "--name", gname, '--del-users',
	#	'--no-archive'],
	#	context=context).Run()
	# FIXME: verify deletion of groups + deletion of users…
	# FIXME: idem last group, verify users account were archived, shared dir ws archived.


def test_users(context, testsuite):

	def chk_acls_cmds(dir):
		return [ 'getfacl', '-R', dir ]

	uname = 'ushell1'
	gname = 'gshell1'
	pname = 'pshell1'

	"""Test ADD/MOD/DEL on user accounts in various ways."""

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', '--login=%s' % uname, '-v' ],
		GET + [ 'users' ],
		#should fail (incorrect shell)
		MOD + [ 'user', '--login=%s' % uname, '--shell=/bin/badshell' ],
		GET + [ 'users' ],
		MOD + [ 'user', '--login=%s' % uname, '--shell=/bin/sh', '-v' ],
		GET + [ 'users' ],
		DEL + [ 'user', '--login=%s' % uname ],
		],
		context=context,
		descr='''check if a user can be modified with an incorrect shell and '''
			'''with a correct shell''', clean_num=1))

	uname = 'u273275'
	gname = 'g273275'
	pname = 'p273275'

	# fix #275
	testsuite.add_scenario(ScenarioTest([
		GET + [ 'users', '-a' ],
		# should be OK
		ADD + [ 'user', '--login=%s' % uname, '--uid=1100' ],
		# should fail (already taken)
		ADD + [ 'user', '--login=%s2' % uname, '--uid=1100' ],
		# should fail, <1000 are for system accounts
		ADD + [ 'user', '--login=%s3' % uname, '--uid=200' ],
		# should be OK
		ADD + [ 'user', '--login=%ssys' % uname, '--system', '--uid=200' ],
		# should fail, >1000 are for standard accounts
		ADD + [ 'user', '--login=%ssys2' % uname, '--system', '--uid=1101' ],
		# should fail (already taken)
		ADD + [ 'user', '--login=%ssys3' % uname, '--system', '--uid=1' ],
		GET + [ 'users', '-a' ],
		DEL + [ 'user', '%s,%s2,%s3,%ssys,%ssys2,%ssys3' % (
			uname,uname,uname,uname,uname,uname), '--force', '--no-archive' ],
		],
		context=context,
		descr='''User tests with --uid option (avoid #273)''', clean_num=1))

	uname = 'u286'
	gname = 'g286'
	pname = 'p286'

	# fix #286
	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', '--name=%s' % uname, '-v' ],
		GET + [ 'users' ],
		GET + [ 'user', uname ],
		GET + [ 'user', uname, '-l' ],
		GET + [ 'user', '1001' ],
		GET + [ 'user', '1001' , '-l' ],
		#should fail (uid 1100 is not used)
		GET + [ 'user', '1100' ],
		GET + [ 'user', '1100' , '-l' ],
		GET + [ 'users', '%s,root' % uname ],
		GET + [ 'users', '0,root' ],
		DEL + [ 'user', '--name=%s' % uname, '-v' ],
		GET + [ 'user', 'root' ],
		GET + [ 'user', 'root', '-l' ],
		GET + [ 'user', '0' ],
		GET + [ 'user', '0', '-l' ],
		GET + [ 'user', '1' ],
		GET + [ 'user', '1', '-l' ],
		GET + [ 'users' ],
		DEL + [ 'user', uname, '--no-archive' ]
		],
		context=context,
		descr='test command get user <uid|user> (fix #286)', clean_num=1))

	uname = 'u284'
	gname = 'g284'
	pname = 'p284'

	#fix #284
	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', '--firstname=RobinNibor', '--lastname=Lucbernet', '-v' ],
		ADD + [ 'user', '--firstname=RobinNibor',
			'--lastname=LucbernetLucbernetLucbernetLucbernetLucbernetLucbernet',
			'-v' ],
		GET + [ 'users' ],
		DEL + [ 'user', '--login=robinnibor.lucbernet' ],
		GET + [ 'users' ],
		],
		context=context,
		descr='''test add user with --firstname and --lastname options '''
			'''(fix #284)''', clean_num=2))

	uname = 'u182181197'
	gname = 'g182181197'
	pname = 'p182181197'

	#fix #182
	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', '--name=%s' % gname, '-v' ],
		ADD + [ 'group', '--name=%s2' % gname, '-v' ],
		ADD + [ 'group', '--name=%s3' % gname, '-v' ],
		ADD + [ 'user', '--login=%s' % uname ],
		GET + [ 'user' , uname, '--long' ],
		MOD + [ 'user', '--login=%s' % uname, '--add-groups=%s' % gname ],
		GET + [ 'user' , uname, '--long' ],
		MOD + [ 'user', '--login=%s' % uname, '--add-groups=%s2,%s3' %
			(gname, gname), '--del-groups=%s' % gname,
			'--gecos=RobinNibor Lucbernet', '--shell=/bin/sh'  ],
		GET + [ 'user', uname, '--long' ],
		MOD + [ 'user', '--login=%s' % uname, '--add-groups=%s' % gname,
			'--del-groups=%s2,%s3' % (gname, gname) ],
		GET + [ 'user', uname, '--long' ],
		DEL + [ 'group', '%s,%s2,%s3' % (gname, gname, gname), '-v',
															'--no-archive' ],
		DEL + [ 'user', '--login=%s' % uname, '-v' ],
		],
		context=context,
		descr='''modify one or more parameters of a user (avoid #181 #197)''',
		clean_num=2))

	uname = 'u248'
	gname = 'g248'
	pname = 'p248'

	#fix #248
	testsuite.add_scenario(ScenarioTest([
		# should work but doesn't record the specfied home dir
		# (non sytem user can't specify home dir)
		ADD + [ 'user', '--login=%s' % uname, '--home=/home/users/folder_test',
			'-v' ],
		GET + [ 'users', uname, '--long' ],
		ADD + [ 'user', '--login=%ssys' % uname, '--system',
			'--home=/home/folder_test', '-v' ],
		chk_acls_cmds('/home/folder_test'),
		GET + [ 'users', '-a', '%ssys' %uname, '--long' ],
		DEL + [ 'user', '%s,%ssys' % (uname, uname), '--force', '--no-archive' ],
		],
		context=context,
		descr='''check option --home of user command (fix #248)''',
		clean_num=1))

	uname = 'u309'
	gname = 'g209'
	pname = 'p209'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', '--login=%s' % uname ],
		GET + [ 'users', uname, '--long' ],
		MOD + [ 'user', '--login=%s' % uname, '--lock', '-v' ],
		GET + [ 'users', uname, '--long' ],
		MOD + [ 'user', '--login=%s' % uname, '--lock', '-v' ],
		GET + [ 'users', uname, '--long' ],
		MOD + [ 'user', '--login=%s' % uname, '--unlock', '-v' ],
		GET + [ 'users', uname, '--long' ],
		MOD + [ 'user', '--login=%s' % uname, '--unlock', '-v' ],
		GET + [ 'users', uname, '--long' ],
		DEL + [ 'user', '--login=%s' % uname, '-v' ],
		],
		context=context,
		descr='''check messages of --lock and --unlock on mod user command '''
			'''and answer of get user --long (avoid #309)''', clean_num=1))

	uname = 'u277'
	gname = 'g277'
	pname = 'p277'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'profile', '--name', pname, '--group=%s' % gname,
			'-v' ],
		GET + [ 'profiles' ],
		ADD + [ 'user', '--login=%s' % uname, '--profile=%s' % pname, '-v' ],
		GET + [ 'users', uname, '--long' ],
		DEL + [ 'profile', '--group=%s' % gname, '--del-users', '-v' ],
		],
		context=context,
		descr='''Add a profil and check if it has been affected to a new '''
			'''user (avoid #277)''', clean_num=1))

	fname = 'niborrobin'
	lname = 'tenrebcul'
	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', '--firstname=%s' % fname, '--lastname=%s' % lname, '-v' ],
		GET + [ 'users' ],
		ADD + [ 'user', '--firstname=%s' % fname, '--lastname=%s' % lname, '-v' ],
		GET + [ 'users' ],
		ADD + [ 'user', '--firstname=.', '--lastname=%s' % lname, '-v' ],
		GET + [ 'users' ],
		ADD + [ 'user', '--firstname=%s' % fname, '--lastname=.', '-v' ],
		GET + [ 'users' ],
		ADD + [ 'user', '--firstname=', '--lastname=', '-v' ],
		ADD + [ 'user', '--firstname=%s2' % fname, '--lastname=', '-v' ],
		ADD + [ 'user', '--firstname=%s2' % fname, '--lastname=', '-v' ],
		ADD + [ 'user', '--firstname=', '--lastname=%s2' % lname, '-v' ],
		ADD + [ 'user', '--firstname=', '--lastname=%s2' % lname, '-v' ],
		DEL + [ 'user', '%s.%s,%s,%s,%s2,%s2' % (
			fname, lname, fname, lname, fname, lname), '-v', '--no-archive'],
		],
		context=context,
		descr='''check add user with --firstname and --lastname (avoid #303 '''
			'''#305)''', clean_num=1))

	uname = 'u184'
	gname = 'g184'
	pname = 'p184'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', uname, '--password=toto', '-v' ],
		GET + [ 'users' ],
		ADD + [ 'user', '%s2' % uname, '--password=toto', '--force', '-v' ],
		GET + [ 'users' ],
		ADD + [ 'user', '%s3' % uname, '-S 32', '-v' ],
		GET + [ 'users' ],
		MOD + [ 'user', uname, '-P', '-S 128', '-v' ],
		MOD + [ 'user', uname, '-p totototo', '-v' ],
		DEL + [ 'user', '%s,%s2,%s3' % (uname, uname, uname), '-v',
														'--no-archive' ],
		],
		context=context,
		descr='''various password change tests (avoid #184)''', clean_num=1))

	# scenario not tested with the debian command adduser because it is an
	# interactive command (for the password).
	testsuite.add_scenario(ScenarioTest([
		[ 'useradd', 'usertestdebian' ],
		# we have to sleep, else the MOD comes up too fast and changes from
		# debian tools are not yet integrated.
		[ 'sleep', '2' ],
		MOD + [ 'user', 'usertestdebian', '--add-groups=plugdev,adm', '-v' ],
		GET + [ 'users', '-l' ],
		GET + [ 'groups', 'plugdev,adm' ],
		DEL + [ 'user', 'usertestdebian' ],
		GET + [ 'groups', 'plugdev,adm' ],
		GET + [ 'users', '-l' ],
		],
		context=context, descr='''avoid #169''', clean_num=3))

	uname = 'u_not169'
	gname = 'g_not169'
	pname = 'p_not169'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', '%s,%s2,%s3' % (uname,uname,uname) ],
		GET + [ 'user', '-l' ],
		MOD + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '''--gecos=This '''
			'''is a massive test GECOS''', '-iv', '--auto-no' ],
		GET + [ 'user', '-l' ],
		MOD + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '''--gecos=This '''
			'''is a massive test GECOS''', '-iv', '--auto-yes' ],
		GET + [ 'user', '-l' ],
		MOD + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '''--gecos=This '''
			'''is a massive test GECOS2''', '-iv', '--batch' ],
		GET + [ 'user', '-l' ],
		MOD + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '--shell=/bin/sh',
			'-iv', '--auto-no' ],
		GET + [ 'user', '-l' ],
		MOD + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '--shell=/bin/sh',
			'-iv', '--auto-yes' ],
		GET + [ 'user', '-l' ],
		MOD + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '--shell=/bin/bash',
			'-iv', '--batch' ],
		GET + [ 'user', '-l' ],
		ADD + [ 'group', '%s,%s2' % (gname,gname) ],
		MOD + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '''--add-groups='''
			'''%s,%s2''' % (gname,gname), '-iv', '--auto-no' ],
		GET + [ 'user', '-l' ],
		MOD + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '''--add-groups='''
			'''%s,%s2''' % (gname,gname), '-iv', '--auto-yes' ],
		GET + [ 'user', '-l' ],
		MOD + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '''--del-groups='''
			'''%s,%s2''' % (gname,gname), '-iv', '--batch' ],
		GET + [ 'user', '-l' ],
		DEL + [ 'group', '%s,%s2' % (gname,gname) ],
		CHK + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '-iv',
			'--auto-no' ],
		CHK + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '-iv',
			'--auto-yes' ],
		CHK + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '-iv', '--batch' ],
		DEL + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '-iv',
			'--auto-no' ],
		DEL + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '-iv',
			'--auto-yes' ],
		DEL + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '-iv', '--batch' ],
		# just for the clean, to be sure.
		DEL + [ 'group', '%s,%s2' % (gname,gname), '--no-archive' ],
		DEL + [ 'user', '%s,%s2,%s3' % (uname,uname,uname), '--no-archive'],
		],
		context=context,
		descr="test user interactive commands", clean_num=2))

	uname = 'u_not169_2'
	gname = 'g_not169_2'
	pname = 'p_not169_2'

	testsuite.add_scenario(ScenarioTest([
		# should fail
		ADD + [ 'user', uname, '--system', '--home=/dev', '-v' ],
		ADD + [ 'user', uname, '--system', '--home=/dev', '--force', '-v' ],
		# should fail
		ADD + [ 'user', uname, '--system', '--home=/proc', '-v' ],
		ADD + [ 'user', uname, '--system', '--home=/proc', '--force', '-v' ],
		# should fail
		ADD + [ 'user', uname, '--system', '--home=/usr/share/homes/test',
			'-v' ],
		ADD + [ 'user', uname, '--system', '--home=/usr/share/homes/test',
			'--force', '-v' ],
		# should succeed
		ADD + [ 'user', '%s' % uname, '--system', '--home=/var/homes/test',
			'-v' ],
		DEL + [ 'user', uname, '-v' ],
		# should fail
		ADD + [ 'user', uname, '--system', '--home=/var/tmp', '-v' ],
		ADD + [ 'user', uname, '--system', '--home=/var/tmp', '--force', '-v' ],
		# should fail (it will create the user, but with another home dir)
		ADD + [ 'user', uname ],
		ADD + [ 'user', '%s2' % uname, '--home=/home/user/%s' % uname,
			'--force', '-v' ],
		DEL + [ 'user', '%s,%s2' % (uname, uname), '-v', '--no-archive' ],
		# should fail
		ADD + [ 'user', uname, '--system' ],
		ADD + [ 'user', '%s2' % uname, '--home=/home/users/%s' % uname,
			'--system', '-v' ],
		ADD + [ 'user', '%s2' % uname, '--home=/home/users/%s' % uname,
			'--system', '--force', '-v' ],
		DEL + [ 'user', '%s,%s2' % (uname, uname), '--force', '--no-archive' ],
		],
		context=context,
		descr="test adding user with specified --home option", clean_num=1))

	uname = 'u383384'
	gname = 'g383384'
	pname = 'p383384'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', '%s1' % uname, '--in-groups', 'audio,video', '-v' ],
		ADD + [ 'user', '%s2' % uname, '-G', 'prout,audio,15000,', '--force', '-v' ],
		ADD + [ 'user', '%s3' % uname, '--add-to-groups',
			',aucun,groupe,valide', '-v' ],
		ADD + [ 'user', '%s4' % uname, '--auxilliary-groups',
			'audio,video,puis,plus,rien!', '-v' ],
		GET + [ 'users' , '%s1,%s2,%s3,%s4' % (uname, uname, uname, uname),
			'-l' ],
		DEL + [ 'users', '%s1,%s2,%s3,%s4' % (uname, uname, uname, uname), '-v',
														'--no-archive'],
		],
		context=context,
		descr='''verify #383 implementation (fixes #384).''', clean_num=1))
def test_imports(context, testsuite):

	uname = 'uprofile1'
	gname = 'gprofile1'
	pname = 'pprofile1'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'profile', pname, '-v' ],
		ADD + [ 'users', '--filename=data/tests_users.csv',
			'--profile=%s' % pname ],
		ADD + [ 'users', '--filename=data/tests_users.csv',
			'--profile=%s' % pname, '--confirm-import' ],
		GET + [ 'users', '-l' ],
		GET + [ 'profiles' ],
		DEL + [ 'profiles', pname, '--del-users', '--no-archive' ],
		DEL + [ 'group', '--empty', '--no-archive', '-v' ],
		DEL + [ 'group', pname, '--no-archive', '--del-users', '--force', '-v' ],
		],
		context=context,
		descr='''test user import from csv file''', clean_num=3))

	uname = 'uprofile2'
	gname = 'gprofile2'
	pname = 'pprofile2'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'profile', pname, '-v' ],
		ADD + [ 'users', '--filename=data/tests_users.csv',
			'--profile=%s' % pname, '--lastname-column=0',
			'--firstname-column=1' ],
		ADD + [ 'users', '--filename=data/tests_users.csv',
			'--profile=%s' % pname, '--lastname-column=1',
			'--firstname-column=0', '--group-column=2',
			'--password-column=3', '--confirm-import', '-v' ],
		GET + [ 'users' ],
		DEL + [ 'profile', pname, '--del-users', '--no-archive', '-v' ],
		DEL + [ 'group', '%s,%s,cp,ce1,ce2,cm2' % (gname, pname),
												'--no-archive', '--del-users',
												'--force', '-v' ],
		],
		context=context,
		descr='''various test on user import''', clean_num=2))
def test_profiles(context, testsuite):
	"""Test the applying feature of profiles."""

	def chk_acls_cmd(user):
		return [ 'getfacl', '-R', '%s/%s' % (users_base_path, user) ]

	uname = 'u271219'
	gname = 'g271219'
	pname = 'p271219'

	#fix #271 & #219
	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'profile', '--name=%s' % pname, '-v' ],
		GET + [ 'profiles' ],
		# should fail
		MOD + [ 'profile', '--name=%s' % pname, '--add-groups=%s' %
			pname, '-v' ],
		ADD + [ 'group', '--name=%s' % gname, '--system', '-v' ],
		ADD + [ 'group', '--name=%s2' % gname, '--system', '-v' ],
		ADD + [ 'group', '--name=%s3' % gname, '--system', '-v' ],
		GET + [ 'privileges' ],
		ADD + [ 'privilege', '--name=%s' % gname ],
		GET + [ 'groups', '-a' ],
		GET + [ 'privileges' ],
		MOD + [ 'profile', '--name=%s' % pname, '--add-groups=%s,%s2,%s3' %
			(gname, gname, gname), '-v' ],
		GET + [ 'profiles' ],
		DEL + [ 'group', '--name=%s' % gname, '-v' ],
		GET + [ 'profiles' ],
		MOD + [ 'profile', '--name=%s' % pname, '--del-groups=%s' % gname,
			'-v' ],
		MOD + [ 'profile', '--name=%s' % pname, '--del-groups=%s2,%s3' %
			(gname, gname), '-v' ],
		GET + [ 'profiles' ],
		DEL + [ 'group', '%s,%s2,%s3,%s' % (gname, gname, gname, pname), '--force', '--no-archive' ],
		# don't work with --name option
		DEL + [ 'profile', pname, '--force', '--no-archive' ],
		DEL + [ 'privilege', gname, '--force' ],
		],
		context=context,
		descr='''scenario for ticket #271 - test some commands of mod profile'''
			''' --add-group and --del-groups & fix #219''', clean_num=3))

	uname = 'u271219_2'
	gname = 'g271219_2'
	pname = 'p271219_2'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'profile', '--name=%s' % pname, '-v' ],
		GET + [ 'profiles' ],
		#should fail
		MOD + [ 'profile', '--name=%s' % pname, '--add-groups=%s' %	gname,
			'-v' ],
		GET + [ 'profiles' ],
		DEL + [ 'profile', '--group=%s' % pname, '-v' ],
		],
		context=context,
		descr='''check if a error occurs when a non-existing group is added '''
			'''to a profile''', clean_num=1))

	uname = 'u300320'
	gname = 'g300320'
	pname = 'p300320'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', '--name=%s' % gname, '-v' ],
		#should fail (group already exists)
		ADD + [ 'profile', '--name=%s' % pname, '--group=%s' % gname,
			"--description='test_profil'", '-v' ],
		GET + [ 'profiles' ],
		#should fail (group is not a system group)
		ADD + [ 'profile', '--name=%s' % pname, '--group=%s' % gname,
			"--description='test_profil'", '-v', '--force-existing' ],
		GET + [ 'profiles' ],
		#should work (creating a new system group)
		ADD + [ 'group', '--name=%s2' % gname, '--system', '-v' ],
		ADD + [ 'profile', '--name=%s' % pname, '--group=%s2' % gname,
			"--description='test_profil'", '-v', '--force-existing' ],
		GET + [ 'profiles' ],
		DEL + [ 'profile', '--name=%s' % pname, '--force', '--no-archive' ],
		DEL + [ 'group', gname, '--force', '--no-archive' ],
		],
		context=context,
		descr='''Check if it is possible to force a profil group to a non '''
			'''system group (avoid #300 #320)''', clean_num=2))

	uname = 'u302'
	gname = 'g302'
	pname = 'p302'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'profile', '--name=%s' % pname, '-v' ],
		GET + [ 'profiles' ],
		DEL + [ 'group', '--name=%s' % pname],
		GET + [ 'profiles' ],
		GET + [ 'group', pname ],
		DEL + [ 'profile', pname, '-v' ],
		GET + [ 'group', pname ],
		],
		context=context,
		descr='''when a profile group is deleted, an error message has to be '''
			'''presented (avoid #302)''', clean_num=2))

	uname = 'u292'
	gname = 'g292'
	pname = 'p292'

	exclude_uid = open(state_files['owner']).read().split(',')[0]
	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'profile', '--name=Utilisagers', '--group=utilisagers',
			'--description="testsuite profile, feel free to delete."', '-v' ],
		ADD + [ 'profile', '--name=Responsibilisateurs',
			'--group=responsibilisateurs',
			'--groups=cdrom,lpadmin,plugdev,audio,video,scanner,fuse',
			'--description="power testsuite profile, feel free to delete"',
			'-v' ],
		GET + [ 'profiles' ],
		ADD + [ 'user', '--name=toto', '--profile=Utilisagers' ],
		ADD + [ 'user', '--name=tutu', '--profile=Utilisagers' ],
		ADD + [ 'user', '--name=tata', '--profile=Responsibilisateurs' ],
		GET + [ 'user', '-l' ],
		ADD + [ 'group', gname, '-v' ],
		MOD + [ 'profile', '--group=utilisagers', '--add-groups=%s' % gname,
			'-v' ],
		GET + [ 'profiles' ],
		MOD + [ 'profile', '--group=utilisagers', '--apply-groups',
			'--to-groups=utilisagers', '-v' ],
		GET + [ 'groups', '--long' ],
		MOD + [ 'profile', '--group=utilisagers', '--apply-groups',
			'--to-members', '-v' ],
		MOD + [ 'profile', '--group=utilisagers', '--apply-skel',
			'--to-users=toto', '--auto-no' ],
		chk_acls_cmd('toto'),
		MOD + [ 'profile', '--group=utilisagers', '--apply-skel',
			'--to-users=toto', '--auto-yes'],
		chk_acls_cmd('toto'),
		MOD + [ 'profile', '--group=utilisagers', '--apply-skel',
			'--to-users=toto', '--batch', '-v' ],
		chk_acls_cmd('toto'),
		MOD + [ 'profile', '--group=utilisagers', '--apply-groups',
			'--to-users=toto', '--auto-no' ],
		MOD + [ 'profile', '--group=utilisagers', '--apply-groups',
			'--to-users=toto', '--auto-yes' ],
		MOD + [ 'profile', '--group=utilisagers', '--apply-groups',
			'--to-users=toto', '--batch', '-v' ],
		MOD + [ 'profile', '--group=utilisagers', '--apply-all',
			'--to-users=toto', '--auto-no' ],
		MOD + [ 'profile', '--group=utilisagers', '--apply-all',
			'--to-users=toto', '--auto-yes' ],
		MOD + [ 'profile', '--group=utilisagers', '--apply-all',
			'--to-users=toto', '--batch', '-v' ],
		MOD + [ 'profile', '--group=utilisagers', '--apply-all',  '--to-all',
			'--exclude-uid', exclude_uid, '--auto-no' ],
		MOD + [ 'profile', '--group=utilisagers', '--apply-all',  '--to-all',
			'--exclude-uid', exclude_uid, '--auto-yes' ],
		MOD + [ 'profile', '--group=utilisagers', '--apply-all',  '--to-all',
			'--exclude-uid', exclude_uid, '--batch', '-v' ],
		DEL + [ 'profile', '--group=responsibilisateurs', '--no-archive',
			'--del-users', '-v' ],
		DEL + [ 'profile', '--group=utilisagers', '--del-users',
			'--no-archive', '-v' ],
		DEL + [ 'group', gname ]
		],
		context=context,
		descr='''various tests on profiles (fix #292)''', clean_num=3))

	uname = 'u292_2'
	gname = 'g292_2'
	pname = 'p292_2'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname), '-v' ],
		GET + [ 'profile' ],
		MOD + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname),
			'''--description=This is a test description''', '-iv',
			'--auto-no' ],
		GET + [ 'profile' ],
		MOD + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname),
			'''--description=This is a test description''', '-iv',
			'--auto-yes' ],
		GET + [ 'profile' ],
		MOD + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname),
			'''--description=This is a test description2''', '-iv', '--batch' ],
		GET + [ 'profile' ],
		ADD + [ 'group', '%s,%s2' % (gname,gname), '-v' ],
		MOD + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname),
			'''--add-groups=%s,%s2''' % (gname,gname), '-iv', '--auto-no' ],
		GET + [ 'profile' ],
		MOD + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname),
			'''--add-groups=%s,%s2''' % (gname,gname), '-iv', '--auto-yes' ],
		GET + [ 'profile' ],
		MOD + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname),
			'''--del-groups=%s,%s2''' % (gname,gname), '-iv', '--batch' ],
		GET + [ 'profile' ],
		DEL + [ 'group', '%s,%s2' % (gname,gname), '-v' ],
		GET + [ 'profile' ],
		CHK + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname), '-iv',
			'--auto-no' ],
		CHK + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname), '-iv',
			'--auto-yes' ],
		CHK + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname), '-iv',
			'--batch' ],
		DEL + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname), '-iv',
			'--auto-no' ],
		DEL + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname), '-iv',
			'--auto-yes' ],
		DEL + [ 'group', '%s,%s2' % (gname,gname), '--no-archive' ],
		DEL + [ 'profile', '%s,%s2,%s3' % (pname,pname,pname), '--batch',
															'--no-archive'],
		],
		context=context,
		descr="test profile interactive commands", clean_num=2))
def test_privileges(context, testsuite):
	# test features of privileges


	for cmd in [ 'priv', 'privs', 'privilege', 'privileges' ]:

		uname = 'u204174' + cmd
		gname = 'g204174' + cmd
		pname = 'p204174' + cmd

		testsuite.add_scenario(ScenarioTest([
			GET + [ cmd ],
			ADD + [ 'group', '--name=%s' % gname, '-v' ],
			ADD + [ cmd, '--name=%s' % gname, '-v' ],
			GET + [ cmd ],
			DEL + [ 'group', '--name=%s' % gname, '-v' ],
			ADD + [ 'group', '--name=%s' % gname, '--system', '-v' ],
			ADD + [ 'group', '--name=%s2' % gname, '--system', '-v' ],
			ADD + [ 'group', '--name=%s3' % gname, '--system', '-v' ],
			ADD + [ cmd, '--name=%s' % gname, '-v' ],
			GET + [ cmd ],
			ADD + [ cmd, '--name=%s2,%s3' % (gname, gname), '-v' ],
			GET + [ cmd ],
			DEL + [ cmd, '--name=%s' % gname, '-v' ],
			GET + [ cmd ],
			DEL + [ cmd, '--name=%s2,%s3' % (gname, gname), '-v' ],
			GET + [ cmd ],
			# combined del commands at the end, to be able to clean.
			DEL + [ cmd, '%s,%s2,%s3' % (gname, gname, gname), '--force' ],
			DEL + [ 'group', '%s,%s2,%s3' % (gname, gname, gname), '--force', '--no-archive' ],
			],
			context=context,
			descr='''test new privileges commands (using argument %s) '''
				'''(avoid #204 #174)''' % cmd, clean_num=2))

	uname = 'u204174_priv'
	gname = 'g204174_priv'
	pname = 'p204174_priv'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '--system', '-v' ],
		ADD + [ 'privilege', '%s,%s2,%s3' % (gname,gname,gname) ],
		GET + [ 'privileges' ],
		DEL + [ 'privilege', '%s,%s2,%s3' % (gname,gname,gname), '-iv',
			'--auto-no' ],
		DEL + [ 'privilege', '%s,%s2,%s3' % (gname,gname,gname), '-iv',
			'--auto-yes' ],
		DEL + [ 'privilege', '%s,%s2,%s3' % (gname,gname,gname), '-iv',
			'--batch' ],
		GET + [ 'privileges' ],
		DEL + [ 'group', '%s,%s2,%s3' % (gname,gname,gname), '--force', '--no-archive' ]
		],
		context=context,
		descr="test privilege interactive commands", clean_num=1))
def test_short_syntax(testsuite):
	uname = 'ushort_ug'
	gname = 'gshort_ug'
	pname = 'pshort_ug'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', uname, '-v' ],
		GET + [ 'user', uname ],
		ADD + [ 'group', gname, '-v' ],
		GET + [ 'group', gname ],
		ADD + [ 'user', uname, gname, '-v' ],
		GET + [ 'user', uname, '-l' ],
		ADD + [ 'group', '%s2' % gname, '-v' ],
		GET + [ 'group', '%s2' % gname ],
		ADD + [ 'group', '%s3,%s4' % (gname, gname), '-v' ],
		# should fail (already present)
		GET + [ 'group', '%s3,%s4' % (gname, gname) ],
		# should add user2 & user3
		ADD + [ 'user', '%s2,%s3' % (uname, uname), '-v' ],
		GET + [ 'user', '%s2,%s3' % (uname, uname) ],
		# add 2 users in 3 groups each
		ADD + [ 'user', '%s2,%s3' % (uname, uname), '%s2,%s3,%s4' %
			(gname,gname,gname), '-v' ],
		GET + [ 'user', '%s2,%s3' % (uname, uname), '-l' ],
		# should add ONLY ONE user in a group and bypass empty one
		ADD + [ 'user', ',%s' % uname, ',%s2' % gname, '-v' ],
		# idem
		ADD + [ 'user', '%s,' % uname, '%s3,' % gname, '-v' ],
		GET + [ 'user', uname, '-l' ],
		# should delete only one user and bypass empty one
		DEL + [ 'user', ',%s' % uname, '-v'],
		# should fail (already deleted)
		DEL + [ 'user', '%s,' % uname, '-v'],
		# IDEM
		DEL + [ 'user', uname, '-v'],
		# delete 2 users at same time
		DEL + [ 'user', '%s2,%s3' % (uname, uname), '-v'],
		# delete groups, one, then two, then one (bypassing empty)
		DEL + [ 'group', gname, '-v'],
		DEL + [ 'group', '%s2,%s3' %  (gname, gname), '-v'],
		DEL + [ 'group', ',%s4' %  gname, '-v'],
		DEL + [ 'group', '%s4,' %  gname, '-v'],
		DEL + [ 'group', '%s4' %  gname, '-v'],
		# to be able to clean in 2 commands.
		DEL + [ 'group', '%s,%s2,%s3,%s4' %  (gname, gname, gname, gname), '-v', '--no-archive' ],
		DEL + [ 'user', '%s,%s2,%s3,%s4' %  (uname, uname, uname, uname), '-v', '--no-archive' ],
		],
		descr='''test short users/groups commands''', clean_num=2))

	uname = 'ushort_priv'
	gname = 'gshort_priv'
	pname = 'pshort_priv'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', gname, '-v' ],
		#should fail (the group is not a system group)
		ADD + [ 'privilege', gname, '-v' ],
		GET + [ 'privileges' ],
		ADD + [ 'group', '%ssys' % gname, '--system', '-v' ],
		ADD + [ 'privilege', '%ssys' % gname, '-v' ],
		GET + [ 'privileges' ],
		DEL + [ 'privilege', '%ssys' % gname ],
		GET + [ 'privileges' ],
		DEL + [ 'group', gname, '--force', '--no-archive' ],
		DEL + [ 'group', '%ssys' % gname, '--force', '--no-archive' ],
		],
		descr='''test short privileges commands''', clean_num=2))

	uname = 'ushort_prof'
	gname = 'gshort_prof'
	pname = 'pshort_prof'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', gname, '--system', '-v' ],
		ADD + [ 'group', '%s2' % gname, '-v' ],
		ADD + [ 'group', '%s3' % gname, '-v' ],
		# should fail (not a system group)
		ADD + [ 'profile', pname, '--group=%s2' % gname, '--force-existing' ],
		GET + [ 'profiles' ],
		# should be OK
		ADD + [ 'profile', pname, '--group=%s' % gname, '--force-existing' ],
		GET + [ 'profiles' ],
		MOD + [ 'profile', pname, '--add-groups=%s2,%s3' % (gname,gname) ],
		GET + [ 'profiles' ],
		MOD + [ 'profile', pname, '--del-groups=%s2,%s3' % (gname,gname) ],
		GET + [ 'profiles' ],
		DEL + [ 'profile', pname, '--force', '--no-archive' ],
		DEL + [ 'group', '%s,%s2,%s3' % (gname, gname, gname), '--force', '--no-archive' ],
		GET + [ 'profiles' ],
		],
		descr='''test short profiles commands''', clean_num=3))

	uname = 'ushort_chk'
	gname = 'gshort_chk'
	pname = 'pshort_chk'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', gname, '-v' ],
		ADD + [ 'group', '%s2' % gname, '-v' ],
		CHK + [ 'group', gname, '--auto-no', '-vv' ],
		CHK + [ 'group', gname, '--auto-yes', '-vv' ],
		CHK + [ 'group', gname, '-vb' ],
		CHK + [ 'group', '%s,%s2' % (gname,gname), '--auto-no', '-vv' ],
		CHK + [ 'group', '%s,%s2' % (gname,gname), '--auto-yes', '-vv' ],
		CHK + [ 'group', '%s,%s2' % (gname,gname), '-vb' ],
		DEL + [ 'group', '%s,%s2' % (gname,gname), '-v' ],
		CHK + [ 'config','--auto-no', '-vvae' ],
		CHK + [ 'config','--auto-yes', '-vvae' ],
		CHK + [ 'config','--batch', '-vvae' ],
		ADD + [ 'user', uname, '-v' ],
		CHK + [ 'user', uname, '--auto-no', '-v' ],
		CHK + [ 'user', uname, '--auto-yes', '-v' ],
		CHK + [ 'user', uname, '-vb' ],
		# clean
		DEL + [ 'group', '%s,%s2' % (gname,gname), '-v' ],
		DEL + [ 'user', uname, '-v' ],
		],
		descr='''test short chk commands''', clean_num=2))

	"""
	# extended check on user not implemented yet
	CHK + [ 'user', '%s,%s2' % (uname,uname), '--auto-no', '-vve' ],
	CHK + [ 'user', '%s,%s2' % (uname,uname), '--auto-yes', '-vve' ],
	CHK + [ 'user', '%s,%s2' % (uname,uname), '--batch', '-vve' ],
	DEL + [ 'user', '%s,%s2' % (uname,uname), '-v' ],
	# check on profile not implemented yet
	ADD + [ 'profile', '%s,%s2' % (pname,pname), '-v' ],
	CHK + [ 'profile', pname, '--auto-no', '-vve' ],
	CHK + [ 'profile', pname, '--auto-yes', '-vve' ],
	CHK + [ 'profile', pname, '--batch', '-vve' ],
	CHK + [ 'profile', '%s,%s2' % (pname,pname), '--auto-no', '-vve' ],
	CHK + [ 'profile', '%s,%s2' % (pname,pname), '--auto-yes', '-vve' ],
	CHK + [ 'profile', '%s,%s2' % (pname,pname), '--batch', '-vve' ],
	DEL + [ 'profile', '%s,%s2' % (pname,pname), '-v' ],
	"""
def test_exclusions(testsuite):
	""" test all kind of exclusion parameters. """
	uname = 'uexcl'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', '%s,%s1,%s2,%s3' % (uname, uname, uname, uname) ],
		GET + [ 'user', '%s,%s1,%s2,%s3' % (uname, uname, uname, uname) ],
		# real tests come here. No need to test other things than GET,
		# the exclusion mechanisms are located in cli_select, which is common
		# to all CLI tools.
		#
		# should show utestXXX but not utest
		GET + [ 'user', '%s1,%s2,%s3' % (uname, uname, uname) ], # without exc.
		GET + [ 'user', '-X', uname ], # with exclusion
		GET + [ 'user', '--exclude', uname ], # with exclusion (same flag)
		# should succeed, because --exclude accepts IDs and names (but is a
		# little slower than --not-users when used with names).
		GET + [ 'user', '--exclude', '1002' ],

		# should output the same, but with different internal mechanism
		GET + [ 'user', '--not-login', uname ],
		GET + [ 'user', '--exclude-login', uname ],
		GET + [ 'user', '--not-logins', uname ],
		GET + [ 'user', '--exclude-logins', uname ],
		GET + [ 'user', '--not-user', uname ],
		GET + [ 'user', '--exclude-user', uname ],
		GET + [ 'user', '--not-users', uname ],
		GET + [ 'user', '--exclude-users', uname ],
		GET + [ 'user', '--not-username', uname ],
		GET + [ 'user', '--exclude-username', uname ],
		GET + [ 'user', '--not-usernames', uname ],
		GET + [ 'user', '--exclude-usernames', uname ],
		# should fail, because --not-user accept only user names
		GET + [ 'user', '--not-user', '1002' ],

		# should output the same (modulo the UID is the good...), but with
		# different internal mechanism
		GET + [ 'user', '--not-uid', '1002' ],
		GET + [ 'user', '--not-uids', '1002' ],
		GET + [ 'user', '--exclude-uid', '1002' ],
		GET + [ 'user', '--exclude-uids', '1002' ],
		# should fail because --not-uid accepts only UIDs
		GET + [ 'user', '--not-uid', uname ],

		# should output utest and utest1
		GET + [ 'user', '--not-users', '%s2,%s3' % (uname, uname) ],

		# should fail, because --not-user accept only user names
		GET + [ 'user', '--not-user', '1002,1001' ],
		# should fail, because --not-user accept only user names
		GET + [ 'user', '--not-uid', '%s2,%s3' % (uname, uname) ],

		# should show all users but not utest
		GET + [ 'users', '-a', '-X', uname ], # with exclusion
		GET + [ 'users', '-a', '--exclude', uname ], # with exclusion (same flag)
		# should succeed, because --exclude accepts IDs and names (but is a
		# little slower than --not-users when used with names).
		GET + [ 'user', '-a', '--exclude', '1002' ],

		# all shoud succeed
		GET + [ 'users', '-a', '-X', '%s,root,proot' % uname ],
		GET + [ 'users', '-a', '--exclude', '%s,root,proot' % uname ],
		GET + [ 'users', '-a', '-X', '%s,0,1,proot' % uname ],
		GET + [ 'users', '-a', '--exclude', '%s,0,1,proot' % uname ],

		# a part should succeed, a part should fail
		GET + [ 'users', '-a', '--not-username', '%s,root,proot' % uname ],
		GET + [ 'users', '-a', '--not-usernames', '%s,root,proot' % uname ],
		GET + [ 'users', '-a', '--not-user', '%s,0,1,proot' % uname ],
		GET + [ 'users', '-a', '--not-users', '%s,0,1,proot' % uname ],

		# other part should succeed, other part should fail
		GET + [ 'users', '-a', '--not-uid', '%s,root,proot' % uname ],
		GET + [ 'users', '-a', '--not-uids', '%s,root,proot' % uname ],
		GET + [ 'users', '-a', '--exclude-uid', '%s,0,1,proot' % uname ],
		GET + [ 'users', '-a', '--exclude-uids', '%s,0,1,proot' % uname ],

		# should succeed, test --sys and --not-sys options
		GET + [ 'users', '--no-sys' ],
		GET + [ 'users', '--not-sys' ],
		GET + [ 'users', '--not-system' ],
		GET + [ 'users', '--no-system' ],
		GET + [ 'users', '--exclude-sys' ],
		GET + [ 'users', '--exclude-system' ],
		GET + [ 'users', '--sys' ],
		GET + [ 'users', '--system' ],
		GET + [ 'users', '--system-groups' ],

		DEL + [ 'user', '%s,%s1,%s2,%s3' % (uname, uname, uname, uname), '--force', '--no-archive' ],
		GET + [ 'users' ]
		],
		descr='''test exclusions in different manners on users''', clean_num=2))

	gname = 'gexcl'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'group', '%s,%s1,%s2,%s3' % (gname, gname, gname, gname) ],
		GET + [ 'group', '%s,%s1,%s2,%s3' % (gname, gname, gname, gname) ],

		GET + [ 'group', '-X', '10000,%s3' % gname ],
		GET + [ 'group', '--not', '10000,%s3' % gname ],
		GET + [ 'group', '--exclude', '10000,%s3' % gname ],

		# should fail
		GET + [ 'group', '--not-group', '10000,10001'  ],

		# should all succeed
		GET + [ 'group', '--not-group', '%s2,%s3' % (gname, gname) ],
		GET + [ 'group', '--not-groups', '%s2,%s3' % (gname, gname) ],
		GET + [ 'group', '--exclude-group', '%s2,%s3' % (gname, gname) ],
		GET + [ 'group', '--exclude-groups', '%s2,%s3' % (gname, gname) ],

		# should fail
		GET + [ 'group', '--not-gids', '%s2,%s3' % (gname, gname) ],

		# should all succeed
		GET + [ 'group', '--not-gid', '10000,10001' ],
		GET + [ 'group', '--not-gids', '10000,10001' ],
		GET + [ 'group', '--exclude-gid', '10000,10001' ],
		GET + [ 'group', '--exclude-gids', '10000,10001' ],
		GET + [ 'group', '--no-sys' ],
		GET + [ 'group', '--not-sys' ],
		GET + [ 'group', '--no-system' ],
		GET + [ 'group', '--not-system' ],
		GET + [ 'group', '--exclude-system' ],
		GET + [ 'group', '--exclude-sys' ],
		GET + [ 'group', '--no-priv' ],
		GET + [ 'group', '--not-priv' ],
		GET + [ 'group', '--no-privs' ],
		GET + [ 'group', '--not-privs' ],
		GET + [ 'group', '--no-privilege' ],
		GET + [ 'group', '--not-privilege' ],
		GET + [ 'group', '--no-privileges' ],
		GET + [ 'group', '--not-privileges' ],
		GET + [ 'group', '--exclude-privileges' ],
		GET + [ 'group', '--exclude-privilege' ],
		GET + [ 'group', '--exclude-privs' ],
		GET + [ 'group', '--exclude-priv' ],
		GET + [ 'group', '--no-rsp' ],
		GET + [ 'group', '--not-rsp' ],
		GET + [ 'group', '--no-resp' ],
		GET + [ 'group', '--not-resp' ],
		GET + [ 'group', '--no-responsible' ],
		GET + [ 'group', '--not-responsible' ],
		GET + [ 'group', '--exclude-responsible' ],
		GET + [ 'group', '--exclude-resp' ],
		GET + [ 'group', '--exclude-rsp' ],
		GET + [ 'group', '--no-gst' ],
		GET + [ 'group', '--not-gst' ],
		GET + [ 'group', '--no-guest' ],
		GET + [ 'group', '--not-guest' ],
		GET + [ 'group', '--exclude-gst' ],
		GET + [ 'group', '--exclude-guest' ],

		DEL + [ 'group', '%s,%s1,%s2,%s3' % (gname, gname, gname, gname), '--force', '--no-archive' ],
		GET + [ 'groups' ],
	],
	descr='''test exclusions in different manners on groups''', clean_num=2))
def test_status_and_dump(testsuite):
	""" test all kind of daemon status and dump parameters. """

	testsuite.add_scenario(ScenarioTest([
		GET + [ 'status' ],
		GET + [ 'daemon_status' ],
		GET + [ 'status', '-l' ],
		GET + [ 'status', '--long' ],
		GET + [ 'status', '--full' ],
		GET + [ 'users', '--dump' ],
		GET + [ 'groups', '--dump' ],
		GET + [ 'machines', '--dump' ],
		],
		descr='''test daemon status and core objects dumping'''
		))
def test_inotifier_exclusions(testsuite):

	uname1 = 'uw1'
	gname1 = 'gw1'
	uname2 = 'uW2'
	gname2 = 'gW2'

	testsuite.add_scenario(ScenarioTest([
		ADD + [ 'user', uname1, '-v' ],
		ADD + [ 'group', gname1, '-v' ],
		ADD + [ 'user', uname2, '-vW' ],
		ADD + [ 'group', gname2, '-vW' ],

		# we should see some "not watched"
		GET + [ 'users', '-l' ],
		GET + [ 'groups', '-l' ],

		# only the watched ones
		GET + [ 'users', '-w' ],
		GET + [ 'groups', '-w' ],

		# only the non-watched ones
		GET + [ 'users', '-W' ],
		GET + [ 'groups', '-W' ],

		# watch the unwatched
		MOD + [ 'users', uname2, '-w' ],
		MOD + [ 'groups', gname2, '-w' ],

		# should display no user/group now.
		GET + [ 'users', '-W' ],
		GET + [ 'groups', '-W' ],

		# should display all users/groups
		GET + [ 'users', '-w' ],
		GET + [ 'groups', '-w' ],

		DEL + [ 'groups', '--empty', '--no-archive', '-v' ],
		DEL + [ 'users', '%s,%s' % (uname1, uname2), '--no-archive', '-v' ],
		],
		descr='''Add and modify watched and unwatched groups, check it is OK in GET.''', clean_num=2))
def test_system(testsuite):
	testsuite.add_scenario(ScenarioTest([
		[ 'killall', '-r', '-9', 'licornd' ],
		# make backups
		[ 'mv', groups_base_path, '%s.bak' % groups_base_path ],
		[ 'mv', '%s' % users_base_path, '%s.bak' % users_base_path ],
		# be sure there is no groups and user dir
		#[ 'rm', '-rf', groups_base_path ],
		#[ 'rm', '-rf', users_base_path] ,
		# launch any command to start the daemon
		GET + [ 'users' ],
		[ 'ls', '-al', '%s' % home_base_path ],
		[ 'rm', '-rf', groups_base_path ],
		[ 'rm', '-rf', users_base_path ],
		[ 'mv', '%s.bak' % groups_base_path, groups_base_path ],
		[ 'mv', '%s.bak' % users_base_path, users_base_path ],
		],
		descr='test if /home/groups and /home/users are created during startup '
			'of deamon if they don\'t exist.'
	))
def to_be_implemented(testsuite):
	""" TO BE DONE !
		#
		# Profiles
		#

		# doit planter pour le groupe
		log_and_exec $ADD profile --name=profileA --group=a

		# doit planter pour le groupe kjsdqsdf
		log_and_exec $ADD profile --name=profileB --group=b --comment="le profil b" --shell=/bin/bash --quota=26 --groups=cdrom,kjsdqsdf,audio --skeldir=/etc/skel && exit 1

		# doit planter pour le skel pas un répertoire, pour le groupe jfgdghf
		log_and_exec $MOD profile --name=profileA --rename=theprofile --rename-primary-group=theprofile --comment=modify --shell=/bin/sh --skel=/etc/power --quota=10 --add-groups=cdrom,remote,qsdfgkh --del-groups=cdrom,jfgdghf

		log_and_exec $DEL profile --name=profileB --del-users --no-archive

		log_and_exec $DEL profile --name=profileeD
		log_and_exec $MOD profile --name=profileeC --not-permissive
		log_and_exec $ADD profile --name=theprofile
		log_and_exec $MOD profile --name=theprofile --skel=/etc/doesntexist
	}

	"""
	pass

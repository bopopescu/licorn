# -*- coding: utf-8 -*-
"""
Licorn Foundations - http://dev.licorn.org/documentation/foundations

hlstr - High-Level String functions and common regexs.

Copyright (C) 2005-2010 Olivier Cortès <olive@deep-ocean.net>
Licensed under the terms of the GNU GPL version 2
"""

import random, re

import exceptions

from styles import *
from _settings import settings

# common regexs used in various places of licorn.core.*
regex = {}
regex['uri']          = r'''^(?P<protocol>\w+s?)://(?P<host>\S+)(?P<port>(:\d+)?).*$'''
regex['profile_name'] = ur'''^[\w]([-_\w ]*[\w])?$'''
# REGEX discussion: shouldn't we disallow #$*!~& in description regexes ?
# these characters could lead to potential crash/vulnerabilities. But refering
# to passwd(5), there are no restrictions concerning the description field.
# Thus we just disallow “:” to avoid a new field to be accidentally created.
regex['description']  = u'''^[-@#~*!¡&_…{}—–™®©/'"\w«»“”() ,;.¿?‘’£$€⋅]*$'''
regex['group_name']   = '''^[a-z]([-_.a-z0-9]*[a-z0-9][$]?)?$'''
regex['login']        = '''^[a-z][-_.a-z0-9]*[a-z0-9]$'''
regex['bad_login']    = settings.get('foundations.hlstr.regex.bad_login', '''^[a-z][-_.a-z0-9]*[a-z0-9]\$$''')
regex['keyword']      = u'''^[a-z][- _./\w]*[a-z0-9]$'''
# IP regexxes come from http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/319293#319293
regex['ipv4']         = r'''^(?:(?:[3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}|0x0*[0-9a-f]{1,2}|0+[1-3]?[0-7]{0,2})(?:\.(?:[3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}|0x0*[0-9a-f]{1,2}|0+[1-3]?[0-7]{0,2})){3})$'''
# stripped out from the IPv4: short (hexa-)decimal forms, not commonly seen and error-prone to match standard integers: |0x0*[0-9a-f]{1,8}|0+[0-3]?[0-7]{0,10}|429496729[0-5]|42949672[0-8]\d|4294967[01]\d\d|429496[0-6]\d{3}|42949[0-5]\d{4}|4294[0-8]\d{5}|429[0-3]\d{6}|42[0-8]\d{7}|4[01]\d{8}|[1-3]\d{0,9}|[4-9]\d{0,8}
regex['conf_comment'] = u'''^(#.*|\s*)$'''
regex['ipv6']         = r'''^(?!.*::.*::)(?:(?!:)|:(?=:))(?:[0-9a-f]{0,4}(?:(?<=::)|(?<!::):)){6}(?:[0-9a-f]{0,4}(?:(?<=::)|(?<!::):)[0-9a-f]{0,4}(?:(?<=::)|(?<!:)|(?<=:)(?<!::):)|(?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)){3})$'''
regex['ether_addr']   = '''^([\da-f]+:){5}[\da-f]+$'''
regex['duration']     = '''^(infinite|\d+[dhms])$'''
regex['ip_address']   = r'(?:' + regex['ipv4'] + r'|' + regex['ipv6'] + r')'
regex['api_key']      = '''^[a-z0-9]{32,32}$'''

# precompile all these to gain some time in the licorn daemon.
cregex = {}
cregex['uri']          = re.compile(regex['uri'],          re.IGNORECASE)
cregex['profile_name'] = re.compile(regex['profile_name'], re.IGNORECASE | re.UNICODE)
cregex['description']  = re.compile(regex['description'],  re.IGNORECASE | re.UNICODE)
cregex['group_name']   = re.compile(regex['group_name'],   re.IGNORECASE)
cregex['login']        = re.compile(regex['login'],        re.IGNORECASE)
cregex['bad_login']    = re.compile(regex['bad_login'],    re.IGNORECASE)
cregex['keyword']      = re.compile(regex['keyword'],      re.IGNORECASE | re.UNICODE)
cregex['conf_comment'] = re.compile(regex['conf_comment'], re.IGNORECASE | re.UNICODE)
cregex['ipv4']         = re.compile(regex['ipv4'],         re.IGNORECASE)
cregex['ipv6']         = re.compile(regex['ipv6'],         re.IGNORECASE)
cregex['ip_address']   = re.compile(regex['ip_address'],   re.IGNORECASE)
cregex['ether_addr']   = re.compile(regex['ether_addr'],   re.IGNORECASE)
cregex['duration']     = re.compile(regex['duration'],     re.IGNORECASE)
cregex['api_key']      = re.compile(regex['api_key'],      re.IGNORECASE)

# Have a look at http://sed.sourceforge.net/sed1line.txt

translation_map = (
	# lower-case
	(u'á', u'a'), (u'à', u'a'), (u'â', u'a'), (u'ä', u'a'),
	(u'ã', u'a'), (u'å', u'a'), (u'ă', u'a'), (u'ā', u'a'), (u'æ', u'ae'),
	(u'ç', u'c'),
	(u'é', u'e'), (u'è', u'e'), (u'ê', u'e'), (u'ë', u'e'), (u'ẽ', u'e'),
	(u'í', u'i'), (u'ì', u'i'), (u'î', u'i'), (u'ï', u'i'), (u'ĩ', u'i'),
	(u'ñ', u'n'),
	(u'ó', u'o'), (u'ò', u'o'), (u'ô', u'o'), (u'ö', u'o'),
	(u'õ', u'o'), (u'ø', u'o'), (u'œ', u'oe'),
	(u'ú', u'u'), (u'ù', u'u'), (u'û', u'u'), (u'ü', u'u'), (u'ũ', u'u'),
	(u'ý', u'y'), (u'ỳ', u'y'), (u'ŷ', u'y'), (u'ÿ', u'y'), (u'ỹ', u'y'),

	# Upper-case
	(u'Á', u'A'), (u'À', u'A'), (u'Â', u'A'), (u'Ä', u'A'),
	(u'Ã', u'A'), (u'Å', u'A'), (u'Ă', u'A'), (u'Ā', u'A'), (u'Æ', u'AE'),
	(u'Ç', u'C'),
	(u'É', u'E'), (u'È', u'E'), (u'Ê', u'E'), (u'Ë', u'E'), (u'Ẽ', u'E'),
	(u'Í', u'I'), (u'Ì', u'i'), (u'Î', u'i'), (u'Ï', u'i'), (u'Ĩ', u'i'),
	(u'Ñ', u'N'),
	(u'Ó', u'O'), (u'Ò', u'O'), (u'Ô', u'O'), (u'Ö', u'O'),
	(u'Õ', u'O'), (u'Ø', u'O'), (u'Œ', u'OE'),
	(u'Ú', u'U'), (u'Ù', u'U'), (u'Û', u'U'), (u'Ü', u'U'), (u'Ũ', u'U'),
	(u'Ý', u'Y'), (u'Ỳ', u'Y'), (u'Ŷ', u'Y'), (u'Ÿ', u'Y'), (u'Ỹ', u'Y'),

	# no-special-case chars
	(u'ß', u'ss'), (u'þ', u''), (u'ð', u''),

	# typographic chars
	(u"'", u''), (u'"', u''),
	(u'«', u''), (u'»', u''),
	(u'“', u''), (u'”', u''),
	(u'‘', u''), (u'’', u''),

	# standard space and non-breaking
	(u' ', u'_'), (u' ', u'_'),

	# Other special
	(u'©',u''),   (u'®',u''),
)

def validate_name(stest, aggressive=False, maxlenght=128, custom_keep=None, replace_by=None):
	""" make a valid login or group name from a random string.
		Replace accentuated letters with non-accentuated ones, replace spaces,
		lower the name, etc.

		.. todo:: use http://docs.python.org/library/string.html#string.translate
			, but this could be more complicated than it seems.
	"""

	if custom_keep is None:
		custom_keep = '-.'

	for elem, repl in translation_map:
		stest = stest.replace(elem, repl)

	if not aggressive:
		# For this `.sub()`, any '-' in `custom_keep` must be the first char,
		# else the operation will fail with "bad character range".
		if '-' in custom_keep:
			custom_keep = '-' + custom_keep.replace('-', '')


	# We compile the expression to be able to use the `flags` argument,
	# which doesn't exist on Python 2.6 (cf.
	# 						http://dev.licorn.org/ticket/876#comment:3)
	cre = re.compile('[^%sa-z0-9]' % ('.' if aggressive
											else custom_keep), flags=re.I)

	# delete any strange (or forgotten by translation map…) char left
	if aggressive:
		stest = cre.sub('', stest)

	else:
		# keep dashes (or custom characters)
		stest = cre.sub(replace_by or '', stest)

	# For next substitutions, we must be sure `custom_keep` doesn't
	# include "-" at all, else it will fail again with "bad character range".
	custom_keep = custom_keep.replace('-', '')

	# Strip remaining doubles punctuations signs
	stest = re.sub( r'([-._%s])[-._%s]*' % (custom_keep, custom_keep), r'\1', stest)

	# Strip left and rights punct signs
	stest = re.sub( r'(^[-._%s]*|[-._%s*]*$)' % (custom_keep, custom_keep), '', stest)

	if len(stest) > maxlenght:
		raise exceptions.LicornRuntimeError("String %s too long (%d "
			"characters, but must be shorter or equal than %d)." % (
				stest, len(stest), maxlenght))

	# return a standard string (not unicode), because a login/group_name don't include
	# accentuated letters or such strange things.
	return str(stest)
def generate_salt(maxlen = 12):
	"""Generate a random password."""

	import random

	# ascii table: 48+ = numbers, 65+ = upper letter, 97+ = lower letters
	special_chars = [ '.', '/' ]

	special_chars_count = len(special_chars) -1

	salt = ""

	for i in range(0, maxlen):
		char_type = random.randint(1, 4)

		if char_type < 3:
			number = random.randint(0, 25)

			if char_type == 1:
				# an uppercase letter
				salt += chr(65 + number)
			else:
				# a lowercase letter
				salt += chr(97 + number)
		else:
			if char_type == 3:
				# a number
				salt += str(random.randint(0, 9))
			else:
				# a special char
				number = random.randint(0, special_chars_count)
				salt += special_chars[number]

	return salt
def generate_password(maxlen=12, use_all_chars=False):
	""" Generate a random password. """

	# ascii table: 48+ = numbers, 65+ = upper letter, 97+ = lower letters
	special_chars = [ '.', '/', '_', '*', '+', '-', '=', '@' ]

	if use_all_chars:
		special_chars.extend([ '$', '%', '&', '!', '?', '(', ')', ',',
			':', ';', '<', '>', '[', ']', '{', '}' ])

	special_chars_count = len(special_chars) -1

	password = ''

	for i in range(0, maxlen):
		char_type = random.randint(1, 4)

		if char_type < 3:
			number = random.randint(0, 25)

			if char_type == 1:
				# an uppercase letter
				password += chr(65 + number)
			else:
				# a lowercase letter
				password += chr(97 + number)
		else:
			if char_type == 3:
				# a number
				password += str(random.randint(0, 9))
			else:
				# a special char
				number = random.randint(0, special_chars_count)
				password += special_chars[number]

	return password
def word_fuzzy_match(part, word):
	""" This is a basic but kind of exact fuzzy match. ``part`` matches ``word``
		if every char of part is present in word, and in the same order.

		For more information on real fuzzy matching (which was not what I was
		looking for, thus I wrote this function), see:

		* http://stackoverflow.com/questions/682367/good-python-modules-for-fuzzy-string-comparison (best)
		* http://code.activestate.com/recipes/475148-fuzzy-matching-dictionary/ (a derivative real example)
		* http://stackoverflow.com/questions/2923420/fuzzy-string-matching-algorithm-in-python
		* http://ginstrom.com/scribbles/2007/12/01/fuzzy-substring-matching-with-levenshtein-distance-in-python/

		"""
	last = 0

	for char in part:
		current = word[last:].find(char)

		if current == -1:
			return None

		last = current

	# if we got out of the for loop without returning None, the part
	# matched, this is a success. Announce it.
	return word
def word_match(word, valid_words):
	""" try to find what the user specified on command line.

		:param valid_words: a list (or tuple) of strings or unicode strings.
			Generators and `itertools.chain()` objects won't work, because
			this argument is iterated two times.
	"""

	for a_try in valid_words:
		if word == a_try:
			# we won't get anything better than this
			return a_try

	first_match = None

	for a_try in valid_words:
		if a_try.startswith(word):
			if first_match is None:
				first_match = a_try

			else:
				raise exceptions.BadArgumentError(_(u'Ambiguous word {0}, '
								u'matches at least {1} and {2}. '
								u'Please refine your query.').format(
									stylize(ST_BAD, word),
									stylize(ST_COMMENT, first_match),
									stylize(ST_COMMENT, a_try)))

	# return an intermediate partial best_result, if it exists, else
	# continue for partial matches.
	if first_match:
		return first_match

	for a_try in valid_words:
		if word_fuzzy_match(word, a_try):
			if first_match is None:
				#print '>> fuzzy match', a_try, 'continuing for disambiguity.'
				first_match = a_try

			else:
				raise exceptions.BadArgumentError(_(u'Ambiguous word {0}, '
								u'matches at least {1} and {2}. '
								u'Please refine your query.').format(
									stylize(ST_BAD, word),
									stylize(ST_COMMENT, first_match),
									stylize(ST_COMMENT, a_try)))

	return first_match
def multi_word_match(word, valid_words):
	""" try to find what the user specified on command line. """

	matched = set()

	for a_try in valid_words:
		if word in a_try or word_fuzzy_match(word, a_try):
			matched.add(a_try)

	return list(matched)
def statsize2human(size):
	""" Convert an integer size (coming from a stat object) to a Human readable string.

		.. warning:: this method is only used in the old and non-maintained GTK
			frontend. Please do not use it. You can use instead :func:`~licorn.foundations.pyutils.bytes_to_human`.
	"""
	size *= 1.0
	unit = 'byte(s)'

	if size > 1024:
		size /= 1024.0
		unit = 'Kib'
	if size > 1024:
		size /= 1024.0
		unit = 'Mib'
	if size > 1024:
		size /= 1024.0
		unit = 'Gib'
	if size > 1024:
		size /= 1024.0
		unit = 'Tib'
	if size > 1024:
		size /= 1024.0
		unit = 'Pib'
	return '%d %s' % (round(size), unit)
def shell_quote(message):
	return message.replace("'","''").replace("(",r"\(").replace(")",r"\)").replace("!", r"\!")
def clean_path_name(command):
	""" Return a multi-OS friendly path (not usable for anything else than
		display, though) for a given command-line or full path (as a string).

		Used in the TS.
	"""

	return ('_'.join(command)).replace(
		'../', '').replace('./', '').replace('//','_').replace(
		'/','_').replace('>','_').replace('&', '_').replace(
		'`', '_').replace('\\','_').replace("'",'_').replace(
		'|','_').replace('^','_').replace('%', '_').replace(
		'(', '_').replace(')', '_').replace ('*', '_').replace(
		' ', '_').replace('__', '_')

__all__ = ('regex', 'cregex', 'validate_name', 'generate_salt',
			'generate_password', 'word_fuzzy_match', 'word_match',
			'multi_word_match', 'statsize2human', 'shell_quote',
			'clean_path_name')

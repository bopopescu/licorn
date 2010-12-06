# -*- coding: utf-8 -*-
"""
Licorn foundations - http://dev.licorn.org/documentation/foundations

Copyright (C) 2005-2010 Olivier Cortès <oc@meta-it.fr>
Licensed under the terms of the GNU GPL version 2
"""

import os, fcntl, struct, socket, platform, re, netifaces

# other foundations imports.
from licorn.foundations import options
import logging, exceptions
import process
from styles    import *
from ltrace    import ltrace
from constants import distros

def interfaces(full=False):
	""" Eventually filter the netifaces.interfaces() result, which contains
		a bit too much results for our own use. """

	assert ltrace('network', '| interfaces(%s)' % full)

	if full:
		return netifaces.interfaces()
	else:
		ifaces = []
		for iface in netifaces.interfaces():
			if iface.startswith('lo') or iface.startswith('gif') \
				or iface.startswith('fw'):
					#print 'skip interface %s' % iface
					continue
			ifaces.append(iface)
		return ifaces
def find_server_Linux(configuration):
	""" return the hostname / IP of our DHCP server. """

	env_server = os.getenv('LICORN_SERVER', None)

	if env_server:
		logging.notice('Using fixed value %s for server (please unset '
			'LICORN_SERVER if you prefer automatic detection via DHCP)' %
				stylize(ST_NAME, env_server))
		return env_server

	if configuration.distro in (distros.LICORN, distros.UBUNTU,
		distros.DEBIAN):
		for argument in process.get_process_cmdline('dhclient'):
			if argument.startswith('/var/lib/dhcp3/dhclient'):
				for try_host in [ x[0] if x[1] == '' else x[1] \
					for x in re.findall('''\s*(?:server-name ['"]([^'"]+)'''
						'''|option dhcp-server-identifier ([^;]*))''',
							open(argument).read()) ]:
					try:
						dummy_ip = socket.gethostbyname(try_host)
						return try_host
					except socket.gaierror:
						logging.warning2('''can't resolve host or IP %s.'''
							% try_host)
		return None
	else:
		raise NotImplementedError('find_server() not implemented yet for your distro!')
def find_first_local_ip_address_Linux():
	""" try to find the main external IP address of the current machine (first
		found is THE one). Return None if we can't find any.

		Note: lo is not concerned. """

	interfaces = []
	for range_min, range_max in ((0, 3), (3, 10)):
		for iface_name in ('eth', 'wlan', 'ath', 'br'):
			interfaces.extend([ '%s%s' % (iface_name, x) for x in range(
				range_min, range_max) ])

	assert ltrace('network', '|  find_first_local_ip_address(%s)' % interfaces)

	for interface in interfaces:
		try:
			return interface_address(interface)
		except:
			continue

	return None
def local_ip_addresses():
	""" try to find the main external IP address of the current machine (first
		found is THE one). Return None if we can't find any.

		Note: lo is not concerned. """

	ifaces = []
	for range_min, range_max in ((0, 3), (3, 10)):
		for iface_name in ('eth', 'wlan', 'ath', 'br'):
			ifaces.extend([ '%s%s' % (iface_name, x) for x in range(
				range_min, range_max) ])

	assert ltrace('network', '|  local_ip_addresses(%s)' % interfaces)

	addresses = []

	for iface in interfaces():
		try:
			addresses.append(netifaces.ifaddresses(iface)[2][0]['addr'])
		except KeyError:
			# the interface has no valid IP assigned
			continue

	return addresses
def local_interfaces_Linux():
	""" Gather any possible information about local interfaces.
		Note: lo is not concerned. """

	interfaces = []
	for range_min, range_max in ((0, 3), (3, 10)):
		for iface_name in ('eth', 'wlan', 'ath', 'br'):
			interfaces.extend([ '%s%s' % (iface_name, x) for x in range(
				range_min, range_max) ])

	assert ltrace('network', '|  find_local_ip_addresses(%s)' % interfaces)

	up_ifaces = []

	for interface in interfaces:
		try:
			addresses.append(interface_infos(interface))
		except:
			continue

	return addresses
def interface_address_Linux(iface_name, iface_address=None):
	""" Get an interface IPv4 adress and return it as a string.

		We dig in /usr/include/linux to find all the values !
			bits/socket.h
			sockios.h
			if.h
		and probably some other files i forgot to list here…

		some reference:
		http://mail.python.org/pipermail/python-list/1999-August/009100.html

		final python 2.6+ version :
		http://code.activestate.com/recipes/439094-get-the-ip-address-associated-with-a-network-inter/

	"""
	raise RuntimeError("please don't use this method aymore")


	assert ltrace('network', '|  interface_address(%s)' % iface_name)

	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	if iface_address is None:
		# 0x8915 should be IN.SIOCGIFADDR
		return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915,
			struct.pack('256s', iface_name[:15]))[20:24])
	else:
		raise NotImplementedError("iface address setting is not implemented yet.")
def interface_infos_Linux(iface_name):
	""" Get an interface IPv4 adress and return it as a string.

		We dig in /usr/include/linux to find all the values !
			bits/socket.h
			sockios.h
			if.h
		and probably some other files i forgot to list here…

		some reference:
		http://mail.python.org/pipermail/python-list/1999-August/009100.html

		final python 2.6+ version :
		http://code.activestate.com/recipes/439094-get-the-ip-address-associated-with-a-network-inter/

	"""

	raise RuntimeError("please don't use this method aymore")

	assert ltrace('network', '|  interface_infos_linux(%s)' % iface_name)

	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	# 0x8915 should be IN.SIOCGIFADDR
	return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915,
		struct.pack('256s', iface_name[:15]))[20:24])
def interface_hostname_Linux(iface_name, iface_address=None):
	""" Get an interface IPv4 hostname and return it as a string.
		same doc as previous function.
	"""

	raise NotImplementedError("TODO !")

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	# mapping struct ifreq:
	#	16s: union ifr_ifrn
	#	16s: union ifr_irfu
	ifr = struct.pack('!16s16s', iface_name, '')

	if iface_address is not None:
		raise NotImplementedError("iface address setting is not implemented yet.")

	# 0x8915 should be IN.SIOCGIFADDR, but it is not defined in
	# /usr/lib/python2.4/plat-linux2/IN.py as of 20060823
	res = fcntl.ioctl(s.fileno(), 0x8915 , ifr)

	# 16s == ifrn_name
	#   i == __SOCKADDR_COMMON (sa_) == sa_family_t sa_family
	#  4s == the IP address
	#  8s == padding to complete the struct ifreq
	(ifr_name, sa_family, addr, padding) = struct.unpack('!16si4s8s', res)

	return socket.inet_ntop(socket.AF_INET, addr)
def nameservers_Linux():
	""" return system nameservers present in /etc/resolv.conf."""

	import re
	ns_re = re.compile("^\s*nameserver\s+([-\w\.]+)\s*$")

	for line in open("/etc/resolv.conf"):
		#assert logging.debug("line: " + line)
		ns_matches = ns_re.match(line)
		if  ns_matches:
			yield ns_matches.group(1)

def build_hostname_from_ip(ip):
	return 'UNKNOWN-%s' % ip.replace('.', '-')

platform_system = platform.system()
platform_len = len(platform_system)

# FIXME: this doesn't work as expected. find a way.
for key, value in locals().items():
	if callable(value) and key[-platform_len:] == platform_system:
		# remove _ from the name too.
		exec "%s = %s" % (key[-platform_len-1:], key)

find_server = find_server_Linux
find_first_local_ip_address = find_first_local_ip_address_Linux

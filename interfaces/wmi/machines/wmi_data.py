# -*- coding: utf-8 -*-
"""
Licorn WMI2 machines data

:copyright:
	* 2011 Olivier Cortès <oc@meta-it.fr>, <olive@deep-ocean.net>

:license: GNU GPL version 2
"""

from django.utils.translation              import ugettext_lazy as _
from licorn.interfaces.wmi.libs            import utils
from licorn.interfaces.wmi.libs.decorators import *

from licorn.foundations.constants import host_status, host_types


get_host_status_html = {
	host_status.ONLINE    : [ 'online.png', _('This machine is online') ],
	host_status.PINGS     : [ 'online.png', _('This machine is online') ],
	host_status.UNKNOWN   : [ 'unknown.png', _('The state of the machine is unknown') ],
	host_status.OFFLINE   : [ 'offline.png', _('This machine is offline') ],
	host_status.IDLE      : [ 'idle.png', _('This machine is online') ],
	host_status.ACTIVE    : [ 'active.png', _('This machine is online') ],
	host_status.UPGRADING : [ 'active.png', _('This machine is upgrating its packages') ],
}

def get_host_os_html(mtype):
	if mtype & host_types.UBUNTU:
		return [ 'ubuntu.png', _('This machine is Ubuntu installed.') ]
	elif mtype & host_types.DEBIAN:
		return [ 'debian.png', _('This machine is Debian installed.') ]
	elif mtype & host_types.LNX_GEN:
		return [ 'linux.png', _('This machine runs an undetermined version of Linux®.') ]
	elif mtype & host_types.VMWARE:
		return [ 'vmware.png', _('This machine is a virtual computer.') ]
	elif mtype & host_types.APPLE:
		return [ 'apple.png', _('This machine is manufactured by Apple® Computer Inc.') ]
	else:
		return [ 'unknown.png', _('The OS of the machine is unknown') ]

def get_host_type_html(mtype):
	if mtype & host_types.LICORN:
		return [ 'licorn.png', _('This machine has Licorn® installed.') ]
	elif mtype & host_types.META_SRV:
		return [ 'server.png', _('This machine is a META IT/Licorn® server.') ]
	elif mtype & host_types.ALT:
		return [ 'alt.png', _('This machine is an ALT® client.') ]
	elif mtype & host_types.FREEBOX:
		return [ 'free.png', _('This machine is a Freebox appliance.') ]
	elif mtype & host_types.PRINTER:
		return [ 'printer.png', _('This machine is a network printer.') ]
	elif mtype & host_types.MULTIFUNC:
		return [ 'scanner.png', _('This machine is a network scanner.') ]
	else:
		return [ 'unknown.png', _('The type of the machine is unknown') ]

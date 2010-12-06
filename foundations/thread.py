# -*- coding: utf-8 -*-
"""
Licorn foundations - http://dev.licorn.org/documentation/foundations

objects - ultra basic objects, used as base classes.

Copyright (C) 2005-2010 Olivier Cortès <olive@deep-ocean.net>
Licensed under the terms of the GNU GPL version 2
"""
import os, sys, time, signal

from Queue     import Queue, Empty
from threading import Thread, Event, active_count, enumerate

import exceptions, logging
from styles    import *
from ltrace    import ltrace
from constants import message_type, verbose, interactions

def _threads():
	return ', '.join([ '%s%s' % (x.name,
		stylize(ST_NOTICE, '&') if x.daemon else '') \
			for x in enumerate() ])

def _thcount():
	return stylize(ST_UGID, active_count())
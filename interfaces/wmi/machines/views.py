# -*- coding: utf-8 -*-

from django.utils.translation     import ugettext_lazy as _
from django.template.loader       import render_to_string
from django.shortcuts             import *

from licorn.foundations           import exceptions, logging, settings
from licorn.foundations           import hlstr, pyutils
from licorn.foundations.base      import Enumeration, LicornConfigObject
from licorn.foundations.constants import filters, relation, host_status, host_types
from licorn.foundations.ltrace    import *
from licorn.foundations.ltraces   import *

from collections import OrderedDict
from licorn.core import LMC


from licorn.interfaces.wmi.app            import wmi_event_app
from licorn.interfaces.wmi.libs            import utils
from licorn.interfaces.wmi.libs.decorators import staff_only

# FIXME: OLD!! MOVE FUNCTIONS to new interfaces.wmi.libs.utils.
from licorn.interfaces.wmi.libs                import old_utils as w

import wmi_data
from forms  import MachineForm, machine_form_blocks

@staff_only
def main(request, sort="login", order="asc", select=None, **kwargs):

	assert ltrace_func(TRACE_DJANGO)

	machines_list = LMC.machines.select(host_status.ONLINE)
	#machines_list.append()
	print LMC.machines.select(host_status.PYRO_SHUTDOWN)
	return render(request, 'machines/index.html', {
			'machines'        : machines_list,
			'host_status'     : host_status,
			'get_host_status_html' : wmi_data.get_host_status_html,
			'get_host_os_html'     : wmi_data.get_host_os_html,
			'get_host_type_html'   : wmi_data.get_host_type_html,
			'edit_html'            : None
		})

@staff_only
def scan(request, *args, **kwargs):

	assert ltrace_func(TRACE_DJANGO)

	LMC.machines.scan_network()
	return HttpResponse('Processing network scan')


def edit(request, mid, *args, **kwargs):
	""" machine edit view.  """

	# we need to sort the form_blocks dict to display headers in order
	sorted_blocks = OrderedDict({})
	for k in sorted(machine_form_blocks.iterkeys()):
		sorted_blocks.update({ k: machine_form_blocks[k]})

	edit_dict = {
		'machine'     : LMC.machines.guess_one(mid),
		'form'        : MachineForm(tab=True, machine=LMC.machines.guess_one(mid)),
		'form_blocks' : sorted_blocks,
	}

	if request.is_ajax():
		return render(request, 'machines/edit.html', edit_dict)

	else:
		return render(request, 'machines/index.html', {
			'machines'        : utils.select('machines', default_selection=host_status.ONLINE),
			'get_host_status_html' : wmi_data.get_host_status_html,
			'get_host_os_html'     : wmi_data.get_host_os_html,
			'get_host_type_html'   : wmi_data.get_host_type_html,
			'edit_html'  : render_to_string('machines/edit.html', edit_dict)
		})




	return HttpResponse()

def upgrade(request, mid, *args, **kwargs):
	""" upgrade one machine defined by its mid """
	try:
		LMC.machines.guess_one(mid).do_upgrade(raise_exception=True)
	except exceptions.LicornWebCommandException, e:
		wmi_event_app.queue(request).put(utils.notify(str(e)))

	return HttpResponse("OK")

def shutdown(request, mid, *args, **kwargs):
	try:
		LMC.machines.guess_one(mid).shutdown(raise_exception=True)
	except exceptions.LicornWebCommandException, e:
		wmi_event_app.queue(request).put(utils.notify(str(e)))

	return HttpResponse("OK")

def massive_select_template(request, action_name, mids, *args, **kwargs):
	return HttpResponse(
		render_to_string('machines/parts/massive_{0}.html'.format(action_name),
			{
				'machines' : [ LMC.machines.guess_one(m) for m in mids.split(',') ],
		}))

def massive(request, action_name, mids, *args, **kwargs):
	for mid in mids.split(','):
		if action_name == 'upgrade':
			upgrade(request, mid)
		elif action_name == 'shutdown':
			shutdown(request, mid)
	return HttpResponse('OK')

def instant_edit(request, mid, part, value, *args, **kwargs):
	""" instant edit function """
	machine = LMC.machines.guess_one(mid)
	if part == 'hostname':
		machine.hostname = value
		return HttpResponse(value)


def hotkeys_help(request):
	return render(request, '/machines/parts/hotkeys_help.html')
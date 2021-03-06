
.. _configuration.en:

.. highlight:: bash

=============
Configuration
=============

You can always access your current configuration by issuing the following command::

	get config

:ref:`Backends <core.backends.en>` and :ref:`extensions <extensions.en>` list and current status can be reached here::

	get config backends
	get config extensions


Main Configuration file
=======================

Generally located at :file:`/etc/licorn/licorn.conf` the main configuration files holds a big number of directives, which all have factory defaults (explaining why the file is nearly empty just after installation), except one (:ref:`role <settings.role.en>`):

.. note:: directives are listed in alphabetical order, not order of importance.

.. _settings.extensions.rdiffbackup.en:

Backup
------

.. _extensions.rdiffbackup.backup_time.en:

	**extensions.rdiffbackup.backup_time**
		Defines the hour of the day at which the incremental backup will be launched. Defaults to ``02:00 A.M.``. Specify it as a 24H string, like ``13:45``. Other formats are not yet supported.

.. _extensions.rdiffbackup.backup_week_day.en:

	**extensions.rdiffbackup.backup_week_day**
		Defines the day(s) of the week on which the back will be run. Defaults to ``*``, which means every day. Can be a list of numbers specifying days. Valid numbers are in range ``0-6``, ``0`` beeing ``Sunday``.

.. _extensions.rdiffbackup.backup.minimum_interval.en:

	**extensions.rdiffbackup.backup.minimum_interval**
		Minimum interval between 2 backups. Useful only when backups are trigerred from outside the daemon and you want Licorn® to make more than one backup per day. Defaults to ``6`` hours, can't be less than ``1`` hour.

Experimental functionnalities
-----------------------------

.. _settings.experimental.enabled.en:

	**experimental.enabled**
		turn on experimental features, depending on wich version of Licorn® you have installed. For example, in version 1.2.3, the experimental directive enables the `Machines` tab in the WMI (the wires are already enabled but non-sysadmins don't get the feature).


Global configuration
--------------------


.. _settings.network.lan_scan.en:

	**network.lan_scan**
		Enable or disable the *automagic* network features. This includes network discovery (LAN and further), Reverse DNS resolution, ARP resolution and *server-based* status updates (polling from server to clients).

		.. note:: even with ``licornd.network.enabled=False``, LAN connections to the :ref:`daemon <daemon.en>` are still authorized: **client-initiated connections (inter-daemon synchronization, client status updates, and so on…) continue to work**, regardless of this directive (this is because ALT® clients strictly need the daemon to work).


.. _settings.pyro.port.en:

	**pyro.port**
		Port ``299`` by default. Set it as an integer, for example ``licorn.pyro.port = 888``.

		.. warning:: **Be sure to set this port to a value under 1024**. The system will work if it >1024, but there's a bad security implication: ports <1024 can only be bound by root and this is little but more than nothing protection. Be careful not to take an already taken port on your system: ports < 1024 are standardized and their use is restricted, but some belongs to services dead for many years.

		.. note:: If you don't set this directive in the main configuration file, the Pyro environment variable :envvar:`PYRO_PORT` takes precedence over the Licorn® factory default. See `the Pyro documentation <http://www.xs4all.nl/~irmen/pyro3/manual/3-install.html>`_ for details.


.. _settings.role.en:

	**role**
		Role of your current Licorn® installation. This directive **must** be set to either *CLIENT* or *SERVER*, before daemon launch. If it is unset, the daemon will remind you.

.. _settings.threads.aclchecker_min.en:

	**threads.aclchecker_min**
		The minimal number of launched ACL checker threads (they become spare threads if not running, waiting for jobs). Default: **1 thread** will be started. Can't specify more than ``5`` for memory consumption safety reasons.


.. _settings.threads.aclchecker_max.en:

	**threads.aclchecker_max**
		The maximum number of concurrent ACL checker threads. Default: **4 threads** will be running at most busy periods of the daemon's life. Once the jobs to do start to decrease, service threads > :ref:`threads.aclchecker_min <settings.threads.aclchecker_min.en>` are automatically terminated. Can't specify more than ``10`` for safety reasons: you should not have more than 2 of them for each physical volume holding users data, plus the root volume: if :file:`/home/` is a separate volume of :file:`/`, 4 is fine. If you have separate physical volumes for :file:`/home/users/` and :file:`/home/groups/` (eg 2 different RAID volumes, apart from :file:`/`), you can set 6 ACL checker threads (8 if your volumes are fast and your system not loaded). Setting too much will be counter-productive and will slow down your hard drives too much.


.. _settings.threads.service_min.en:

	**threads.service_min**
		The minimal number of launched service threads (they become spare threads if not running, waiting for jobs). Default: **4 threads** will be started. Can't specify more than ``16`` for memory consumption safety reasons.


.. _settings.threads.service_max.en:

	**threads.service_max**
		The maximum number of concurrent service threads. Default: **24 threads** will be running at most busy periods of the daemon's life. Once the jobs to do start to decrease, service threads > :ref:`threads.service_min <settings.threads.service_min.en>` are automatically terminated. Can't specify more than ``50`` for safety reasons: too much threads means the daemon will be less responsive to outside events, which is not good.

.. _settings.threads.network_min.en:

	**threads.network_min**
		The minimal number of launched network threads (they become spare threads if not running, waiting for jobs). Default: **12 threads** will be started. Can't specify more than ``24`` for memory consumption safety reasons.


.. _settings.threads.network_max.en:

	**threads.network_max**
		The maximum number of concurrent network threads. Default: **80 threads** will be running at most busy periods of the daemon's life. Once the jobs to do start to decrease, network threads > :ref:`threads.network_min <settings.threads.network_min.en>` are automatically terminated. Can't specify more than ``160`` for safety reasons: too much threads means the daemon will be less responsive to outside events, which is not good. Network thread usually run lightweight CPU operations, but these operations can block and timeout for network reasons, so we need more network threads than standard service ones.


.. _settings.threads.wipe_time.en:

	**threads.wipe_time**
		The cycle delay of the :term:`PeriodicThreadsCleaner` thread. How long will they wait between each iteration of their cleaning loop. (Default: **600 seconds**, = 10 minutes). This doesn't affect their first run, which is always 30 seconds after daemon start.


.. _settings.wmi.enabled.en:

	**wmi.enabled**
		Self explanatory: should the WMI be started or not? If you don't use it, don't activate it. You will save some system resources.


.. _settings.wmi.group.en:

	**wmi.group**
		* Users members of this group will be able to access the WMI and administer some [quite limited] parts of the system. Default value is ``licorn-wmi`` .
		* Any reference to a non existing group will trigger the group creation at next daemon start, so this groups always exists.

		.. note:: It is a good idea (or not, depending on your users) to *register this group as a privilege*, to allow web-only administrators to grant WMI access to other users.


.. _settings.wmi.listen_address.en:

	**wmi.listen_address**
		Customize the interface the WMI listens on. Set it to an IP address (not a hostname yet). If unset, the WMI listens on all interfaces.

		.. versionadded 1.3:: in previous versions, the WMI listened only on ``localhost`` (IP address ``127.0.0.1``).


.. _settings.wmi.log_file.en:

	**wmi.log_file**
		Path to the WMI `access_log` (default: :file:`/var/log/licornd-wmi.log`). The log format is Apache compatible, it is a `CustomLog`.


.. _settings.wmi.port.en:

	**wmi.port**
		Port ``3356`` by default. Set it as an integer, for example ``licornd.wmi.port = 8282``. There is no particular restriction, except that this port must be different from the Pyro one (see :ref:`pyro.port <settings.pyro.port.en>`).

Users and groups related
------------------------

.. glossary::


.. _settings.users.config_dir.en:

	**users.config_dir**
		Where Licorn® will put its configuration, preferences and customization files for a given user. Default is :file:`~/.licorn`.


.. _settings.users.check_config_file.en:

	**users.check_config_file**
		Defines the path where the user customization file for checks will be looked for. Default is `check.conf` in :ref:`users.config_dir <settings.users.config_dir.en>`, or with full path: :file:`~/.licorn/check.conf`.



Check configuration files
=========================


System-wide configuration
-------------------------

In the system directory :file:`/etc/licorn/check.d/`, `licornd` will look for files that match a certain naming criteria: the filenames must start with the name of a controller (e.g. `users` or `groups`) and end with the suffix `.conf`. Thus **these names are valid**::

	users.specific.conf
	users.special_dirs.conf

	# you can even put special punctuation in filenames...
	users.dir_a and dir-B.conf

But **these names are not**::

	# lacks the 's' at the end of 'user'
	user.dirs.conf

	# suffix suggests it's disabled: it is!
	users.specific.conf.disabled

.. warning::
	* the files :file:`users.00_default.conf` and :file:`groups.00_default.conf` are very special. **Never rename them**.
	* the `*00_default*` files named above MUST contain **at least ONE line and at most TWO lines**, comments excluded (you can put as many as you want).

	If you don't follow these recommendations, a huge blue godzilla-like dinosaur will appear from another dimension to destroy the big-loved-teddybear of your damn-cute-face-looking little sister (and she will hate you if she happens to know it's all your fault), or checks will not work at all, or the licorn daemon will just crash. You're warned.



User-level customizations
-------------------------

Put your own customizations in the path designed by :ref:`users.check_config_file <settings.users.check_config_file.en>`. User customizations cannot override any system rules, except the one for :file:`~` (`$HOME`) (see :ref:`random_notes` below).


Check files syntax
------------------

* other files can contain any number of lines, with mixed comments.
* a line starting with `#` is a comment (`#` should be the *first* character of the line).
* basic syntax (without spaces, put here only for better readability)::

	<relative_path>		<TAB>		<permission_definition>

* where:

	* `<relative_path>` is relative from your home directory, or from the group shared dir. For exemple, protecting your :file:`.gnome` directory, just start the line with `.gnome`.
	* `<relative_path>` can be nearly anything you want (UTF-8, spaces, etc accepted). **But NO TAB please**, because `TAB` is the separator.
	* the `<TAB>` is mandatory (see above).

* And <permission_definition> is one of: :term:`NOACL`, `POSIXONLY`, :term:`RESTRICT[ED]`, `PRIVATE` or a :term:`Complex ACL definition`:

.. glossary::

	NOACL
		(`POSIXONLY` is a synonym) defines that the dir or file named `<relative_path>` and all its contents will have **NO POSIX.1e ACLs** on it, only standard unix perms. When checking this directory or file, Licorn® will apply standard permssions (`0777` for directories, `0666` for files) and'ed with the current *umask* (from the calling CLI process, not the user's one).

	RESTRICT[ED]
		(we mean `RESTRICT` or `RESTRICTED`, and `PRIVATE` which are all synonyms) Only posix permissions on this dir, and very restrictive (`0700` for directories, `0600` for regular files), regardless of the umask.

	Complex ACL definition
		You can define any POSIX.1e ACL here (e.g. `user:Tom:r-x,group:Friends:r-x,group:Trusted:rwx`). This ACL which will be checked for correctness and validity before beiing applyed. **You define ACLs for files only**: ACLs for dirs will be guessed from them. You've got some Licorn® specific :ref:`acls_configuration_shortcuts` for these (see below).


.. _acls_configuration_shortcuts:

ACLs configuration shortcuts
----------------------------

To build you system-wide or user-customized ACLs rules, some special values are available to you. This allows more dynamic configuration.

.. glossary::

	@acls.*
		Refer to factory default values for ACLs, pre-computed in Licorn® (e.g. `@acls.acl_base` refers to the value of `LMC.configuration.acls.acl_base`). More doc to come on this subject later, but command :command:`get config | grep acls` can be a little help for getting all the possible values.

	@defaults.*
		Refer to factory defaults for system group names or other special cases (see :command:`get config` too, for a complete listing).

	@users.*
		Same thing for users-related configuration defaults and factory settings (same comment as before, :command:`get config` is your friend).

	@groups.*
		You get the idea (you really know what I want tu put in these parents, don't you?).

	@UX and @GX
		These are special magic to indicate that the executable bit of files (User eXecutable and Group eXecutable, respectively) should be maintained as it is. This means that prior to the applying of ACLs, Licorn® will note the status of the executable bit and replace these magic flags by the real value of the bit. If you want to force a particular executable bit value, just specify `-` or `x` and the exec bit will be forced off or on, respectively). Note that `@UX` and `@GX` are always translated to `x` for directories, to avoid traversal problems.


You can always find detailled examples in the system configuration files shipped in your Licorn® package.


.. _random_notes:

Random Notes
------------

A user, even an administrator, cannot override any system rule, except the `~` one (which affects the home dir) This is because factory rules define sane rules for the system to run properly. These rules are usually fixed (`ssh` expects `~/.ssh` to be 0700 for example, this is non-sense to permit to modify these).


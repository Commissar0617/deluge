#
# main.py
#
# Copyright (C) 2007 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2010 Pedro Algarvio <pedro@algarvio.me>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#
#


# The main starting point for the program.    This function is called when the
# user runs the command 'deluge'.

"""Main starting point for Deluge.  Contains the main() entry point."""

import os
import sys
from optparse import OptionParser
from logging import FileHandler, getLogger
from errno import EEXIST

from deluge.log import setupLogger
import deluge.error
import deluge.common
import deluge.configmanager


def version_callback(option, opt_str, value, parser):
    print os.path.basename(sys.argv[0]) + ": " + deluge.common.get_version()
    try:
        from deluge._libtorrent import lt
        print "libtorrent: %s" % lt.version
    except ImportError:
        pass
    raise SystemExit


def start_ui():
    """Entry point for ui script"""
    deluge.common.setup_translations()

    # Setup the argument parser
    parser = OptionParser(usage="%prog [options] [actions]")
    parser.add_option("-v", "--version", action="callback", callback=version_callback,
        help="Show program's version number and exit")
    parser.add_option("-u", "--ui", dest="ui",
        help="""The UI that you wish to launch.  The UI choices are:\n
        \t gtk -- A GTK-based graphical user interface (default)\n
        \t web -- A web-based interface (http://localhost:8112)\n
        \t console -- A console or command-line interface""", action="store", type="str")
    parser.add_option("-s", "--set-default-ui", dest="default_ui",
        help="Sets the default UI to be run when no UI is specified", action="store", type="str")
    parser.add_option("-a", "--args", dest="args",
        help="Arguments to pass to UI, -a '--option args'", action="store", type="str")
    parser.add_option("-c", "--config", dest="config",
        help="Set the config folder location", action="store", type="str")
    parser.add_option("-l", "--logfile", dest="logfile",
        help="Output to designated logfile instead of stdout", action="store", type="str")
    parser.add_option("-L", "--loglevel", dest="loglevel",
        help="Set the log level: none, info, warning, error, critical, debug", action="store", type="str")
    parser.add_option("-q", "--quiet", dest="quiet",
        help="Sets the log level to 'none', this is the same as `-L none`", action="store_true", default=False)
    parser.add_option("-r", "--rotate-logs",
        help="Rotate logfiles.", action="store_true", default=False)

    # Get the options and args from the OptionParser
    (options, args) = parser.parse_args(deluge.common.unicode_argv()[1:])

    # Setup the logger
    if options.quiet:
        options.loglevel = "none"
    if options.loglevel:
        options.loglevel = options.loglevel.lower()
    logfile_mode = 'w'
    if options.rotate_logs:
        logfile_mode = 'a'
    setupLogger(level=options.loglevel, filename=options.logfile, filemode=logfile_mode)
    log = getLogger(__name__)

    if options.config:
        if not os.path.exists(options.config):
            # Try to create the config folder if it doesn't exist
            try:
                os.makedirs(options.config)
            except OSError:
                pass
        elif not os.path.isdir(options.config):
            log.error("Config option needs to be a directory!")
            sys.exit(1)
    else:
        if not os.path.exists(deluge.common.get_default_config_dir()):
            os.makedirs(deluge.common.get_default_config_dir())

    if options.default_ui:
        if options.config:
            deluge.configmanager.set_config_dir(options.config)

        config = deluge.configmanager.ConfigManager("ui.conf")
        config["default_ui"] = options.default_ui
        config.save()
        print "The default UI has been changed to", options.default_ui
        sys.exit(0)

    version = deluge.common.get_version()

    log.info("Deluge ui %s", version)
    log.debug("options: %s", options)
    log.debug("args: %s", args)
    log.debug("ui_args: %s", args)

    from deluge.ui.ui import UI
    log.info("Starting ui..")
    UI(options, args, options.args)


def start_daemon():
    """Entry point for daemon script"""
    deluge.common.setup_translations()

    if 'dev' not in deluge.common.get_version():
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning, module='twisted')

    # Setup the argument parser
    parser = OptionParser(usage="%prog [options] [actions]")
    parser.add_option("-v", "--version", action="callback", callback=version_callback,
            help="Show program's version number and exit")
    parser.add_option("-p", "--port", dest="port",
        help="Port daemon will listen on", action="store", type="int")
    parser.add_option("-i", "--interface", dest="listen_interface",
        help="Interface daemon will listen for bittorrent connections on, \
this should be an IP address", metavar="IFACE",
        action="store", type="str")
    parser.add_option("-u", "--ui-interface", dest="ui_interface",
        help="Interface daemon will listen for UI connections on, this should be\
 an IP address", metavar="IFACE", action="store", type="str")
    if not (deluge.common.windows_check() or deluge.common.osx_check()):
        parser.add_option("-d", "--do-not-daemonize", dest="donot",
            help="Do not daemonize", action="store_true", default=False)
    parser.add_option("-c", "--config", dest="config",
        help="Set the config location", action="store", type="str")
    parser.add_option("-P", "--pidfile", dest="pidfile",
        help="Use pidfile to store process id", action="store", type="str")
    if not deluge.common.windows_check():
        parser.add_option("-U", "--user", dest="user",
            help="User to switch to. Only use it when starting as root", action="store", type="str")
        parser.add_option("-g", "--group", dest="group",
            help="Group to switch to. Only use it when starting as root", action="store", type="str")
    parser.add_option("-l", "--logfile", dest="logfile",
        help="Set the logfile location", action="store", type="str")
    parser.add_option("-L", "--loglevel", dest="loglevel",
        help="Set the log level: none, info, warning, error, critical, debug", action="store", type="str")
    parser.add_option("-q", "--quiet", dest="quiet",
        help="Sets the log level to 'none', this is the same as `-L none`", action="store_true", default=False)
    parser.add_option("-r", "--rotate-logs",
        help="Rotate logfiles.", action="store_true", default=False)
    parser.add_option("--profile", dest="profile", action="store_true", default=False,
        help="Profiles the daemon")

    # Get the options and args from the OptionParser
    (options, args) = parser.parse_args()

    if options.config:
        if not deluge.configmanager.set_config_dir(options.config):
            print "There was an error setting the config directory! Exiting..."
            sys.exit(1)

    # Check for any daemons running with this same config
    from deluge.core.daemon import check_running_daemon
    pid_file = deluge.configmanager.get_config_dir("deluged.pid")
    try:
        check_running_daemon(pid_file)
    except deluge.error.DaemonRunningError:
        print "You cannot run multiple daemons with the same config directory set."
        print "If you believe this is an error, you can force a start by deleting: %s" % pid_file
        sys.exit(1)

    # Setup the logger
    if options.quiet:
        options.loglevel = "none"
    if options.logfile:
        # Try to create the logfile's directory if it doesn't exist
        try:
            os.makedirs(os.path.abspath(os.path.dirname(options.logfile)))
        except OSError as ex:
            if ex.errno != EEXIST:
                print "There was an error creating the log directory, exiting... (%s)" % ex
                sys.exit(1)

    logfile_mode = 'w'
    if options.rotate_logs:
        logfile_mode = 'a'
    setupLogger(level=options.loglevel, filename=options.logfile, filemode=logfile_mode)
    log = getLogger(__name__)

    # If no logfile specified add logging to default location (as well as stdout)
    if not options.logfile:
        options.logfile = deluge.configmanager.get_config_dir("deluged.log")
        file_handler = FileHandler(options.logfile)
        log.addHandler(file_handler)

    # If the donot daemonize is set, then we just skip the forking
    if not (deluge.common.windows_check() or deluge.common.osx_check() or options.donot):
        if os.fork():
            # We've forked and this is now the parent process, so die!
            os._exit(0)
        os.setsid()
        # Do second fork
        if os.fork():
            os._exit(0)

    # Write pid file before chuid
    if options.pidfile:
        with open(options.pidfile, "wb") as _file:
                _file.write("%s\n" % os.getpid())

    if not deluge.common.windows_check():
        if options.user:
            if not options.user.isdigit():
                import pwd
                options.user = pwd.getpwnam(options.user)[2]
            os.setuid(options.user)
        if options.group:
            if not options.group.isdigit():
                import grp
                options.group = grp.getgrnam(options.group)[2]
            os.setuid(options.group)

    def run_daemon(options, args):
        from deluge.core.daemon import Daemon
        try:
            Daemon(options, args)
        except Exception as ex:
            log.exception(ex)
            sys.exit(1)
        finally:
            if options.pidfile:
                os.remove(options.pidfile)

    if options.profile:
        import cProfile
        profiler = cProfile.Profile()
        profile_output = deluge.configmanager.get_config_dir("deluged.profile")

        # Twisted catches signals to terminate
        def save_profile_stats():
            profiler.dump_stats(profile_output)
            print "Profile stats saved to %s" % profile_output

        from twisted.internet import reactor
        reactor.addSystemEventTrigger("before", "shutdown", save_profile_stats)
        print "Running with profiler..."
        profiler.runcall(run_daemon, options, args)
    else:
        run_daemon(options, args)

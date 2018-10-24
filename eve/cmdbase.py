#!/usr/bin/python
# vim: set expandtab:
import argparse
import logging
import os, sys

from eve.database import EveDB

class CmdBase:
   _prefix = None
   _prog = None
   _version = None
   _desc = None

   _args = None
   _logformat = None
   _loggername = None
   _defaultlogfile = 'stderr'

   _logger = None

   _dbconn = None
   _dbfile = None

   def __init__(self, prog, version, desc = None, prefix = None, loggername = None):
      self._prefix = prefix
      self._prog = prog
      self._version = version
      self._desc = desc
      self._loggername = loggername
      pass

   def run(self):
      self.__parse()
      self.__init_logger()
      self.__debug()
      self._run()
      pass

   def __debug(self):
      self.logdebug('prog: {}, version: {}'.format(self._prog, self._version))
      self.logdebug('arg parsed: ' + str(self._args))

   ### start of db facilities ##
   def set_dbfile(self, dbfile):
      self._dbfile = dbfile

   def _db(self):
      if self._dbconn is None:
         if self._dbfile is None:
            raise
         self._dbconn = EveDB(self._dbfile)
         self._dbconn.set_namespace(self._prog)
      return self._dbconn

   ### end of db facilities ##

   ### start of parser facilities ###
   @staticmethod
   def action_version(version):
      class ActionVersion(argparse.Action):
         def __call__(self, parser, args, values, option_string=None):
            print(version)
            sys.exit(0)
      return ActionVersion

   def _get_parser(self, **kwargs):
      if self._prog is not None:
         prog = self._prog
      else:
         prog = os.path.basename(sys.argv[0])
         prog, _ = os.path.splitext(prog)
      if self._prefix is not None:
         prog = self._prefix + ' ' + prog
      kwargs['prog'] = prog
      if 'description' in kwargs and self._desc is not None:
         kwargs['description'] = self._desc

      parser = argparse.ArgumentParser(**kwargs)
      group = parser.add_argument_group('misc options')
      group.add_argument('--version', action=self.action_version(self._version),
            nargs=0, help='print version and exit')
      group.add_argument('--quiet', '-q', default=False, action='store_true',
            help='quiet mode. shortcut to turn off log, equal to --logfile none')
      group.add_argument('--debug', default=False, action='store_true',
            help='debug mode. shortcut to enable debug, equal to --loglevel DEBUG')
      group.add_argument('--logfile', default=self._defaultlogfile,
            help='log file name for progress, special keyword: (stderr, stdout, none)')
      group.add_argument('--loglevel', default=logging.INFO,
            help='set loglevel, default: INFO')
      return parser

   def __parse(self):
      parser = self._get_parser()
      self._prepare_parser(parser)
      args = parser.parse_args()
      self._args = args
      pass
   ### end of parser facilities ###

   ### start of logger facilities ###
   def _set_log_format(self, logformat):
      self._logformat = logformat

   def _set_logger_name(self, loggername):
      self._loggername = loggername

   def _set_default_logfile(self, logfile):
      self._defaultlogfile = logfile

   def _logger(self):
      return logging.getLogger(self._loggername)

   def logerror(self, msg, *args, **kwargs):
      self._logger().error(msg, *args, **kwargs)

   def loginfo(self, msg, *args, **kwargs):
      self._logger().info(msg, *args, **kwargs)

   def logdebug(self, msg, *args, **kwargs):
      self._logger().debug(msg, *args, **kwargs)

   def logEnableFor(self, lv):
      return self._logger().isEnabledFor(lv)

   def __init_logger(self):
      args = self._args
      loglevel = args.loglevel if not args.debug else 'DEBUG'
      logfile = args.logfile if not args.quiet else 'none'

      if self._loggername is None:
         if self._prog is not None:
            self._loggername = self._prog
         else:
            self._loggername = self.__class__.__name__
      logger = logging.getLogger(self._loggername)
      try:
         logger.setLevel(loglevel)
      except ValueError as e:
         sys.stderr.write(str(e) + ', fallback to INFO\n')
         logger.setLevel(logging.INFO)

      if logfile == 'none':
         handler = logging.NullHandler()
      elif logfile == 'stderr':
         handler = logging.StreamHandler(sys.stderr)
      elif logfile == 'stdout':
         handler = logging.StreamHandler(sys.stdout)
      else:
         handler = logging.FileHandler(logfile)

      if self._logformat is None:
         self._logformat = '[%(name)s][%(asctime)s][%(levelname)s] %(message)s'
      formatter = logging.Formatter(self._logformat)
      handler.setFormatter(formatter)

      logger.addHandler(handler)
   ### end of logger facilities ###

   ### start of interactive ###
   def show_msg(self, msg):
      sys.stderr.write(msg)

   def prompt(self, msg, options = None, default = None):
      option_str = ''
      if options is not None:
         if type(options) is not list:
            raise "given options must in list"
         if default is not None:
            if default in options:
               options.remove(default)
            options.insert(0, default)

         opt = [c if c != default else '(' + c + ')' for c in options]
         option_str = '[' + '|'.join(opt) + ']'
      elif default is not None:
         option_str = '(' + default + ')'

      try: # compatible for python2/3
         input = raw_input
      except NameError:
         pass

      accept_input = False
      while not accept_input:
         # sys.stderr.write(msg + option_str + ' ')
         # r = sys.stdin.readline().strip()
         r = input(msg + option_str + ' ').strip()
         if len(r) == 0 and default is not None:
            r = default
            accept_input = True
         elif options is not None:
            if r in options:
               accept_input = True
         else:
            if len(r) != 0:
               accept_input = True
      return r
   ### end of interactive ###

   ### start of child implement methods ###
   def _prepare_parser(self, parser):
      raise "No implement in base class"

   def _run(self):
      raise "No implement in base class"
   ### end of child implement methods ###

if __name__ == '__main__':
   raise Exception("This file is base class for cmd class, shuold not run it directly")

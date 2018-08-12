#!/usr/bin/python
import argparse
import subprocess
import os, sys
import re

from cmdbase import CmdBase

class FileList(CmdBase):
   __files = []
   __binaries = []

   version = '1.0.0'
   desc = "search files with specified key word"

   def __init__(self, prog = None, prefix = None):
      CmdBase.__init__(self, prog, self.version, self.desc, prefix=prefix)
      self.__files = []
      self.__binaries = []

   def _run(self):
      self.__get_files()
      self.__do_operation()

   def _prepare_parser(self, parser):
      parser.add_argument('--single', '-1', default=False, action='store_true',
                          help='show each file in single line')
      parser.add_argument('--vim', '-v', default=False, action='store_true',
                          help='open all files by vim with tabs')
      parser.add_argument('--readonly', '-R', default=False, action='store_true',
                          help='(use with --vim, open files read only)')
      parser.add_argument('--ignorecase', '-i', default=False, action='store_true',
                          help='ignore case distinctions')
      parser.add_argument('--binary', '-b', default=False, action='store_true',
                          help='include bonary files')
      parser.add_argument('--exclude', '-e', default=[], action='append',
                          help='exclude files with particular pattern')
      parser.add_argument('pattern', help='specified pattern (key) to search')
      parser.add_argument('basedir', default=['.'], nargs='*',
                          help='specified base directory to search')


   def __get_files(self):
      args = self._args
      nocase = '-i' if args.ignorecase else ''
      singlefile = False

      if len(args.basedir) == 1 and not os.path.isdir(args.basedir[0]):
         singlefile = True

      cmd = ['grep', '-nr', nocase, args.pattern] + args.basedir
      cmd = [c for c in cmd if c]
      lines = []
      try:
         self.logdebug("run grep cmd: " + str(cmd))
         lines = subprocess.check_output(cmd).decode('UTF-8').split('\n')
      except subprocess.CalledProcessError:
         self.__files = []
         return

      # handle binary files
      binaries = []
      if args.binary:
         for f in lines:
            m = re.search(r'^Binary file (.+) matches$', f)
            if m is not None:
               binaries.append(m.group(1))
         binaries = list(set(binaries))
         binaries.sort()

      # handle text files
      files = []
      if singlefile:
         # count as text file matched if not a binary match
         if len(binaries) == 0 and len(lines) > 0 and ':' in lines[0]:
            files = args.basedir
      else:
         files = [l.split(':')[0] for l in lines if ':' in l]
         files = list(set(files))
         files.sort()

      # handle exclude pattern
      for e in args.exclude:
         regpat = r'' + e + r''
         files = [f for f in files if re.search(regpat, f) is None]
         binaries = [f for f in binaries if re.search(regpat, f) is None]

      self.__files = files
      self.__binaries = binaries

   def __do_operation(self):
      args = self._args
      files = self.__files
      binaries = self.__binaries

      if args.vim:
         if args.binary and len(binaries) != 0:
            r = self.prompt('You are going to open some binary files, proceed? ',
                  options=['yes', 'no', 'y'], default='no')
            if r == 'y' or r == 'yes':
               files += binaries

         if len(files) == 0:
            self.logerror("No files contain given key")
            sys.exit(0)

         vim_opt = '-R' if args.readonly else ''
         cmd = 'vim -p {} {}'.format(vim_opt, ' '.join(files))
         os.system(cmd)
         sys.exit(0)

      if args.single:
         for f in files:
            print(f)
         for b in binaries:
            print(b + ' (binary file)')
      else:
         print(' '.join(files + binaries))

if __name__ == '__main__':
   FileList('FileList').run()


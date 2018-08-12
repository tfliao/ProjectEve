#!/usr/bin/python
import argparse
import os, sys
import re
import requests
import traceback
import logging

from cmdbase import CmdBase

class ImageDownloader(CmdBase):

   version = '1.1.0'
   desc = 'Download all images within img tag'

   __imgs = []

   __ext_map = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/bmp': 'bmp'}

   def __init__(self, prog = None, prefix = None):
      CmdBase.__init__(self, prog, self.version, self.desc, prefix)

   def _run(self):
      if not self.__precheck():
         sys.exit(1)
      self.__scan_file()
      self.__filter_images()
      self.__download()
      pass

   def _prepare_parser(self, parser):
      parser.add_argument('--filter', '-f', default=[], action='append',
                          help='download only img url contain specified filter')
      parser.add_argument('--no-verify', '-V', default=False, action='store_true',
                          help='skip SSL verification')
      parser.add_argument('--progress-report', '-r', default=32,
                          help='interval for reporting download progress')
      parser.add_argument('--skips', '-s', default=0,
                          help='skip first SKIPS url, for resume download')
      parser.add_argument('src', help='specified source file contains img path')
      parser.add_argument('outdir', default=None, nargs='?', help='specified output directory')

   def __precheck(self):
      args = self._args
      fn = args.src
      outdir = args.outdir

      if outdir is None:
         (outdir, _) = os.path.splitext(fn)
         self._args.outdir = outdir

      if not os.path.isfile(fn):
         self.logerror('source file {} not found'.format(fn))
         return False
      if os.path.exists(outdir) and not os.path.isdir(outdir):
         self.logerror('output driectory {} already exists'.format(outdir))
         return False
      # XXX check directory writable?
      return True

   def __scan_file(self):
      args = self._args
      fn = args.src
      content = ''
      with open(fn) as f:
         content = f.read()
      pattern = r'<img.*?src="(.*?)".*?>'
      urls = re.findall(pattern, content)
      self.logdebug('scan {} urls with img tag from file'.format(len(urls)))
      self.__imgs = urls

   def __filter_images(self):
      if len(self._args.filter) == 0:
         return
      patterns = [r'' + f for f in self._args.filter] 
      def match_patterns(str):
         for p in patterns:
            if re.search(p, str):
               return True
         return False
      urls = [url for url in self.__imgs if match_patterns(url)]
      self.logdebug('{} urls remains after apply filter'.format(len(urls)))
      self.__imgs = urls

   def __gen_name(self, idx, total, type):
      ext = 'jpg'
      if type in self.__ext_map:
         ext = self.__ext_map[type]
      w = len(str(total))
      serial = '{0:0{w}}.'.format(idx, w=w)
      return '{}/{}.{}'.format(self._args.outdir, serial, ext)

   def __download(self):
      args = self._args
      urls = self.__imgs
      outdir = args.outdir
      total_imgs = len(urls)
      self.loginfo('Start to download {} files to folder {}'.format(total_imgs, outdir))
      if not os.path.exists(outdir):
         try:
            os.makedirs(outdir)
         except:
            self.logerror('Failed to create directory {}'.format(outdir))
            sys.exit(1)

      success = 0
      failure = 0
      skipped = 0
      for idx, url in enumerate(urls):
         if idx < int(args.skips):
            skipped += 1
            continue

         self.logdebug('Download {}-th file from "%s"'.format(url))
         try:
            r = requests.get(url, verify=not args.no_verify)
         except Exception as e:
            failure += 1
            self.logerror('Failed to download {}'.format(url))
            if self.logEnableFor(logging.DEBUG):
               traceback.print_exc()
            continue
         fn = self.__gen_name(idx, total_imgs, r.headers['content-type'])
         with open(fn, 'wb') as f:
            f.write(r.content)
         success += 1
         if (idx+1) % args.progress_report == 0:
            self.loginfo('Download Progress: {} success, {} failure, {} skipped, {} total'.
                  format(success, failure, skipped, total_imgs))

      self.loginfo('Total {} file(s) in {} download successful'.format(success, total_imgs))

if __name__ == '__main__':
   ImageDownloader('ID').run()

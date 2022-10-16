#!/usr/bin/python
# vim: ts=4:sw=4:expandtab
import argparse
from utils.cliparser import CliParser
from eve.polling_service import PollingJob, PollingServiceAPI
import requests
import re
import time
import random

from cmdbase import CmdBase
from eve.common import *

PROGNAME = 'Comic'

class ComicDBConstant:
    table = 'list'
    table_version = "1"
    schema = [
        {
            'name': 'id',
            'type': 'integer',
            'primary': True
        }, {
            'name': 'name',
            'type': 'text',
        }, {
            'name': 'url',
            'type': 'text',
        }, {
            'name': 'status',
            'type': 'text', # good, removed, error
        }, {
            'name': 'latest_episode',
            'type': 'text',
        }, {
            'name': 'latest_update',
            'type': 'text',
        }, {
            'name': 'latest_url',
            'type': 'text',
        }, {
            'name': 'viewed_episode',
            'type': 'text',
        }, {
            'name': 'viewed_update',
            'type': 'text',
        }, {
            'name': 'viewed_url',
            'type': 'text',
        }
    ]

class ComicScanner:
    BASEURL = 'https://www.manhuagui.com'

    @staticmethod
    def scan_url(url):
        headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'max-age=0',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36',
                }
        ret = {'s': 'good'}
        try:
            r = requests.get(url, headers = headers)
            content = r.content.decode()
        except Exception as e:
            # self.logerror('Failed to get content from {}'.format(url))
            ret['s'] = 'error'
            return ret

        name_pattern = r'<h1>(.*?)</h1>'
        date_pattern = r'最近于 \[<span class="red">(\d{4}-\d\d-\d\d)</span>\]'
        episode_pattern = r'更新至 \[ <a href="([\/\w\d\.]*)" target="_blank" class="blue">(.*?)</a> ]'
        removed_pattern = '漫画状态：</strong><span class="gray">已下架</span>。'

        m = re.search(name_pattern, content)
        ret['n'] = m.group(1) if m else None
        m = re.search(date_pattern, content)
        ret['d'] = m.group(1) if m else None
        m = re.search(episode_pattern, content)
        ret['e'] = m.group(2) if m else None
        ret['u'] = ComicScanner.BASEURL + m.group(1) if m else None
        if content.find(removed_pattern) != -1:
            # self.logerror('no more available, url=[{}]'.format(url))
            ret['s'] = 'removed'
            return ret

        # self.logdebug('content scan success, {}'.format(ret))
        return ret

    RET_UPTODATE = 'uptodate'
    RET_UPDATED = 'updated'
    
    @staticmethod
    def scan_one(row, db):
        _id = row['id']
        url = row['url']
        r = ComicScanner.scan_url(url)
        if r['s'] != 'good':
            db.table_update_condition(ComicDBConstant.table, {'status': r['s']}, {'id': _id})
            return r['s']
        else:
            if r['u'] == row['latest_url']:
                # nothing new
                return ComicScanner.RET_UPTODATE
            db.table_update_condition(ComicDBConstant.table,
                {'status': r['s'], 'latest_episode': r['e'],
                'latest_update': r['d'], 'latest_url': r['u']},
                {'id': _id})
            return ComicScanner.RET_UPDATED

class ComicJob(PollingJob):
    def __init__(self):
        super().__init__(PROGNAME)
        self.comic_list = []

    def fetch_list(self):
        if len(self.comic_list) != 0:
            return
        self.logger.debug('fetch list from db again')
        self.comic_list = self._db().table_select(ComicDBConstant.table)
        random.shuffle(self.comic_list)

    def process_one(self):
        self.fetch_list()
        if len(self.comic_list) == 0:
            self.logger.error('No record in comic database')
            return False
        
        row = self.comic_list.pop()
        ret = ComicScanner.scan_one(row, self._db())
        if ret not in [ComicScanner.RET_UPDATED, ComicScanner.RET_UPTODATE]:
            self.logger.error('scan {} failed, result: {}'.format(row['name'], ret))
        elif ret == ComicScanner.RET_UPDATED:
            self.logger.info('{} updated'.format(row['name']))
        else:
            self.logger.debug('no update for {}'.format(row['name']))
        return True

class Comic(CmdBase):

    version = '2.0.0'
    desc = "command line interface to scan new comic arrival in www.manhuagui.com"

    def __init__(self, prog = None, prefix = None, loggername = None):
        CmdBase.__init__(self, prog, self.version, self.desc, prefix=prefix, loggername=loggername)

    
    def __setup_db(self):
        db = self._db()
        if db.table_version(ComicDBConstant.table) != ComicDBConstant.table_version:
            db.table_create(ComicDBConstant.table, ComicDBConstant.schema, ComicDBConstant.table_version)

    def run_scan(self):
        db = self._db()
        rows = db.table_select(ComicDBConstant.table)
        random.shuffle(rows)

        for row in rows:
            if row['status'] not in ['good', 'rescan']:
                continue

            r = ComicScanner.scan_one(row, db)
            self.loginfo('Checking {} ... [{}]'.format(row['name'], r))
            time.sleep(60)
        return 0

    def __list_comics(self, filter):
        # None: all
        # updated: viewed != latest
        # error: status != good
        db = self._db()
        rows = db.table_select(ComicDBConstant.table)
        if filter is None or len(filter) == 0:
            pass
        if 'updated'.startswith(filter):
            rows = [row for row in rows if row['viewed_episode'] != row['latest_episode']]
        elif 'error'.startswith(filter):
            rows = [row for row in rows if row['status'] != 'good']
        return rows

    def run_list_json(self, filter):
        return self.__list_comics(filter)

    def __reset_status(self, rows):
        db = self._db()
        for row in rows:
            db.table_update_condition(ComicDBConstant.table, {'status': 'good'}, {'id': row['id']})
            self.loginfo('reset status of comic [{}]'.format(row['name']))

    def run_list(self, filter=None, reset=False):
        filter = str(filter)
        rows = self.__list_comics(filter)
        print('Total {} records'.format(len(rows)))

        for row in rows:
            name = self._cut_str(row['name'], 40)
            status = row['status']
            print('{:3d} | {} | {} | {}'.format(row['id'], name, status, row['url']))
            print('    > viewed {}({}) {}'.format(row['viewed_episode'], row['viewed_update'], row['viewed_url']))
            print('    > latest {}({}) {}'.format(row['latest_episode'], row['latest_update'], row['latest_url']))
            print('-' * 80)

        if reset:
            if filter is None or len(filter) == 0:
                pass
            elif 'updated'.startswith(filter):
                self.run_mark_viewed([int(row['id']) for row in rows])
            elif 'error'.startswith(filter):
                self.__reset_status(rows)

        return 0

    def run_add(self, url):
        db = self._db()

        r = ComicScanner.scan_url(url)
        if r['s'] != 'good':
            self.logerror('not acceptable url to add')
            return 1
        max_id = db.table_max(ComicDBConstant.table, 'id')
        next_id = 1 if max_id is None else max_id + 1
        db.table_update(ComicDBConstant.table, {'id': next_id, 'name': r['n'], 'url': url, 'status': r['s'], 'latest_update': r['d'], 'latest_episode': r['e'], 'latest_url': r['u']})
        self.loginfo('comic [{}] with url:[{}] added'.format(r['n'], url))
        return 0

    def run_delete(self, id):
        db = self._db()
        rows = db.table_select(ComicDBConstant.table, {'id': id})
        if len(rows) == 0:
            self.loginfo('No comic with id [{}]'.format(id))
            return 1
        row = rows[0]
        name = row['name']
        r = db.table_delete(ComicDBConstant.table, {'id': id}, 1)
        if r:
            self.loginfo('comic [{}] with id: [{}] deleted'.format(name, id))
            return 0
        else:
            self.logerror('failed to delete comic [{}] with id: [{}]'.format(name, id))
            return 1

    def run_mark_viewed(self, idlist):
        db = self._db()
        for id in idlist:
            rows = db.table_select(ComicDBConstant.table, {'id': id})
            if len(rows) != 1:
                self.logerror('comic with id={} not found, skip'.format(id))
                continue
            row = rows[0]
            changes = {
                'viewed_episode': row['latest_episode'],
                'viewed_update': row['latest_update'],
                'viewed_url': row['latest_url']}
            db.table_update_condition(ComicDBConstant.table, changes, {'id': id})
            self.loginfo('mark {} as viewed'.format(row['name']))

    def daemon_enable(self, enable):
        PollingServiceAPI.add_job(ComicJob, interval=60, enable=enable)

    def _run(self):
        self.__setup_db()
        cp = CliParser()
        cp.register_help_keywords('?')
        cp.add_command(['list'], inst=self, func=Comic.run_list, help="list all comics")
        cp.add_command(['list', '@filter'], inst=self, func=Comic.run_list, help="list @filter comics, filter: updated, error")
        cp.add_command(['list', '@filter', 'reset'], inst=self, func=Comic.run_list, default_args={'reset': True}, help="list @filter comics and reset state, filter: updated, error")
        cp.add_command(['add'], help="add new comic from @url")
        cp.add_command(['add', "@url"], inst=self, func=Comic.run_add, help="add new comic from @url")
        cp.add_command(['delete'], help="delete comic with @id from list")
        cp.add_command(['delete', "@id(int)"], inst=self, func=Comic.run_delete, help="delete comic with @id from list")
        cp.add_command(['delete'], help="delete comic with @id from list")
        cp.add_command(['mark', 'viewed', '@idlist(int)...'], inst=self, func=Comic.run_mark_viewed, help='mark some comics as viewed (to latest)')
        cp.add_command(['scan'], inst=self, func=Comic.run_scan, help="scan all comic with good state")
        cp.add_command(['daemon'], help="config comic daemon", hidden=True)
        cp.add_command(['daemon', 'enable', '@enable(bool)'], inst=self, func=Comic.daemon_enable, help="enable daemon feature", hidden=True)

        cp.invoke(self._args.params)


    # =======================

    def _prepare_parser(self, parser):
        parser.add_argument('params', nargs='*', default=[])

    def _cut_str(self, _str, _len):
        _str = str(_str)
        if cht_width(_str) <= _len:
            return '{{:{}}}'.format(_len - cht_len(_str)).format(_str)
        for i in range(0, _len):
            r = _str[0:i] + " ..."
            clen = cht_width(r)
            if clen == _len:
                return r
            if clen == _len - 1:
                return r + ' '
        raise None # should not come here

if __name__ == '__main__':
    Comic(PROGNAME).run()

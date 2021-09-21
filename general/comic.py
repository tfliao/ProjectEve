#!/usr/bin/python
# vim: ts=4:sw=4:expandtab
import argparse
import requests
import re
import unicodedata
import time
import random

from cmdbase import CmdBase
from eve.common import *

class Comic(CmdBase):

    version = '2.0.0'
    desc = "command line interface to scan new comic arrival in www.manhuagui.com"

    baseurl = 'https://www.manhuagui.com'

    def __init__(self, prog = None, prefix = None, loggername = None):
        CmdBase.__init__(self, prog, self.version, self.desc, prefix=prefix, loggername=loggername)

    __table = 'list'
    __table_version = "1"
    __schema = [
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
    def __setup_db(self):
        db = self._db()
        if db.table_version(self.__table) != self.__table_version:
            db.table_create(self.__table, self.__schema, self.__table_version)

    def __scan_url(self, url):
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
            self.logerror('Failed to get content from {}'.format(url))
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
        ret['u'] = m.group(1) if m else None
        if content.find(removed_pattern) != -1:
            self.logerror('no more available, url=[{}]'.format(url))
            ret['s'] = 'removed'
            return ret

        self.logdebug('content scan success, {}'.format(ret))
        return ret

    def _scan_one(self, row):
        _id = row['id']
        url = row['url']
        r = self.__scan_url(url)
        if r['s'] != 'good':
            self._db().table_update_condition(self.__table, {'status': r['s']}, {'id', _id})
        else:
            if r['u'] == row['latest_url']:
                # nothing new
                return
            self._db().table_update_condition(self.__table,
                {'status': r['s'], 'latest_episode': r['e'],
                'latest_update': r['d'], 'latest_url': r['u']},
                {'id', _id})

    def run_daemon_scan(self):
        db = self._db()
        rows = db.table_select(self.__table)
        random.shuffle(rows)

        for row in rows:
            if row['status'] not in ['good', 'rescan']:
                continue

            self._scan_one(row['url'])
            time.sleep(60)
        return 0

    def run_list2(self):
        db = self._db()
        rows = db.table_select(self.__table)
        print('Total {} records'.format(len(rows)))

        for row in rows:
            name = self._cut_str(row['name'], 40)
            status = row['status']
            viewed = self._cut_str(row['viewed_episode'], 10)
            latest = self._cut_str(row['latest_episode'], 10)
            print('{:4d} | {} | {} | {} | {} | {}'.format(row['id'], name, status, viewed, latest, row['url']))

        return 0

    def run_add2(self):
        args = self._args
        db = self._db()

        if args.url is None:
            self.logerror('url is required for action [add]')
            return 1
        r = self.__scan_url(args.url)
        if r['s'] != 'good':
            self.logerror('not acceptable url to add')
            return 1
        max_id = db.table_max(self.__table, 'id')
        next_id = 1 if max_id is None else max_id + 1
        db.table_update(self.__table, {'id': next_id, 'name': r['n'], 'url': args.url, 'status': r['s'], 'latest_update': r['d'], 'latest_episode': r['e'], 'latest_url': r['u']})
        self.loginfo('comic [{}] with url:[{}] added'.format(r['n'], args.url))
        return 0
    # =======================

    def _run(self):
        args = self._args
        self.__setup_db()
        if args.action == 'list':
            return self.run_list2()
        elif args.action == 'add':
            return self.run_add2()
        elif args.action == 'del':
            return self.run_del()
        elif args.action == 'scan':
            return self.run_daemon_scan()
        else:
            raise

    def _prepare_parser(self, parser):
        parser.add_argument('action', choices=['list', 'add', 'del', 'scan'])
        parser.add_argument('--url', '-u', help='specify url to scan')
        parser.add_argument('--id', '-i', help='indicate which record to delete')
        parser.add_argument('--all', '-a', action='store_true', default=False,
                            help='force scan all url including dead comic')

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

    def run_list(self):
        db = self._db()
        rows = db.table_select(self.__table)
        print('Total {} records'.format(len(rows)))

        for row in rows:
            name = self._cut_str(row['name'], 40)
            episode = self._cut_str(row['last_episode'], 10)
            tag = ''
            if row['is_dead'] != 0:
                tag = 'removed'
            print('{:4d} | {} | {} | {} | {} | {}'.format(row['id'], name, episode, row['last_update'], row['url'], tag))

        return 0

    def run_add(self):
        args = self._args
        db = self._db()

        if args.url is None:
            self.logerror('url is required for action [add]')
            return 1
        r = self.__scan_url(args.url)
        if r is None:
            self.logerror('not acceptable url to add')
            return 1
        max_id = db.table_max(self.__table, 'id')
        next_id = 1 if max_id is None else max_id + 1
        db.table_update(self.__table, {'id': next_id, 'name': r[0], 'url': args.url, 'last_update': r[1], 'last_episode': r[2], 'is_dead': r['4']})
        self.loginfo('comic [{}] with url:[{}] added'.format(r[0], args.url))
        return 0

    def run_del(self):
        args = self._args
        db = self._db()

        if args.id is None:
            self.logerror('id is required for action [del]')
            return 1

        r = db.table_count(self.__table, {'id': args.id})
        if r == 0:
            self.logerror('No record with such id [{}]'.format(args.id))
            return 1

        r = db.table_delete(self.__table, {'id': args.id}, 1)
        if not r:
            self.logerror('Failed to delete record with id:[{}]'.format(args.id))
            return 1

        self.loginfo('Record with id:[{}] deleted'.format(args.id))
        return 0

    def run_scan(self):
        db = self._db()
        rows = db.table_select(self.__table)
        random.shuffle(rows)

        update_cnt = 0
        for row in rows:
            rid = row['id']
            name = row['name']
            url = row['url']
            last_update = row['last_update']
            last_episode = row['last_episode']
            is_dead = row['is_dead']

            if not self._args.all and is_dead != 0:
                continue

            time.sleep(random.randint(0, 3))
            print('Checking {} ... '.format(name), end='')
            r = self.__scan_url(url)
            if r[4]:
                print('dead')
                db.table_update(self.__table, {'id': rid, 'name': name, 'url': url, 'last_update': update, 'last_episode': episode, 'is_dead': 1})
                continue
            update = r[1]
            episode = r[2]
            epurl = self.baseurl + r[3]
            if episode != last_episode:
                update_cnt += 1
                print()
                print('> updated from {}({}) to {}({}), url: {}'.format(last_episode, last_update, episode, update, epurl))
                db.table_update(self.__table, {'id': rid, 'name': name, 'url': url, 'last_update': update, 'last_episode': episode, 'is_dead': 0})
            else:
                print('nothing new')
        self.loginfo('Total {} comic updated'.format(update_cnt))
        return 0

if __name__ == '__main__':
    Comic('Comic').run()


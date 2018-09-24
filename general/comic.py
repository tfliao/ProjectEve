#!/usr/bin/python
# vim: ts=4:sw=4:expandtab
import argparse
import requests
import re

from cmdbase import CmdBase

class Comic(CmdBase):

    version = '1.0.0'
    desc = "command line interface to scan new comic arrival in www.manhuagui.com"

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
                'name': 'last_update',
                'type': 'text',
            }
        ]
    def __setup_db(self):
        db = self._db()
        if db.table_version(self.__table) != self.__table_version:
            db.table_create(self.__table, self.__schema, self.__table_version)

    def __scan_url(self, url):
        # return (name, date)
        try:
            r = requests.get(url)
            content = r.content.decode()
        except Exception as e:
            self.logerror('Failed to get content from {}'.format(url))
            raise
        name_pattern = r'<h1>(.*?)</h1>'
        date_pattern = r'最近于 \[<span class="red">(\d{4}-\d\d-\d\d)</span>\]'
        
        m = re.search(name_pattern, content)
        name = m.group(1) if m else None
        m = re.search(date_pattern, content)
        date = m.group(1) if m else None

        if name is None or date is None:
            self.logerror('content scan failue, url=[{}]'.format(url))
            return None
        else:
            self.logdebug('content scan success, name:[{}] date:[{}]'.format(name, date))
            return (name, date)

    def _run(self):
        args = self._args
        self.__setup_db()
        if args.action == 'list':
            self.run_list()
        elif args.action == 'add':
            self.run_add()
        elif args.action == 'del':
            self.run_del()
        elif args.action == 'scan':
            self.run_scan()
        else:
            raise

    def _prepare_parser(self, parser):
        parser.add_argument('action', choices=['list', 'add', 'del', 'scan'])
        parser.add_argument('--url', '-u', help='specify url to scan')
        parser.add_argument('--id', '-i', help='indicate which record to delete')

    def run_list(self):
        db = self._db()
        rows = db.table_select(self.__table)
        print('Total {} records'.format(len(rows)))
        for row in rows:
            print('{:4d} | {:20} | {}'.format(row['id'], row['name'], row['url']))

        pass

    def run_add(self):
        args = self._args
        db = self._db()

        if args.url is None:
            self.logerror('url is required for action [add]')
            return
        r = self.__scan_url(args.url)
        if r is None:
            self.logerror('not acceptable url to add')
            return
        max_id = db.table_max(self.__table, 'id')
        next_id = 1 if max_id is None else max_id + 1
        db.table_update(self.__table, {'id': next_id, 'name': r[0], 'url': args.url, 'last_update': r[1]})
        self.loginfo('comic [{}] with url:[{}] added'.format(r[0], args.url))
        pass

    def run_del(self):
        args = self._args
        db = self._db()

        if args.id is None:
            self.logerror('id is required for action [del]')
            return
        r = db.table_count(self.__table, {'id': args.id})
        if r == 0:
            self.logerror('No record with such id [{}]'.format(args.id))
            return

        r = db.table_delete(self.__table, {'id': args.id}, 1)
        if not r:
            self.logerror('Failed to delete record with id:[{}]'.format(args.id))
            return
        else:
            self.loginfo('Record with id:[{}] deleted'.format(args.id))
        pass

    def run_scan(self):
        db = self._db()
        rows = db.table_select(self.__table)

        update_cnt = 0
        for row in rows:
            rid = row['id']
            name = row['name']
            url = row['url']
            last_update = row['last_update']
            
            r = self.__scan_url(url)
            update = r[1] 
            if update != last_update:
                update_cnt
                print('{} updated from {} to {}, url: {}'.format(name, last_update, update, url))
                db.table_update(self.__table, {'id': rid, 'name': name, 'url': url, 'last_update': update})
        self.loginfo('Total {} comic updated'.format(update_cnt))
        pass

if __name__ == '__main__':
    Comic('Comic').run()


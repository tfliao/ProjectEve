#!/usr/bin/python
# vim: set expandtab:
import argparse
import subprocess
import os, sys
import re

from cmdbase import CmdBase

class DBTest(CmdBase):

    version = '1.0.0'
    desc = "test eve db"

    def __init__(self, prog = None, prefix = None, loggername = None):
        CmdBase.__init__(self, prog, self.version, self.desc, prefix=prefix, loggername=loggername)

    def _run(self):
        schema = [
            {
                'name': 'key',
                'type': 'TEXT',
                'primary': True
            }, {
                'name': 'value',
                'type': 'TEXT',
            }, {
                'name': 'intval',
                'type': 'integer',
            }
        ]

        schema2 = [
            {
                'name': 'key',
                'type': 'TEXT',
                'primary': True
            }, {
                'name': 'key2',
                'type': 'TEXT',
                'primary': True
            }, {
                'name': 'value',
                'type': 'TEXT',
                'nullable': False
            }, {
                'name': 'intval',
                'type': 'integer',
                'unique': True
            }
        ]

        data = {
            'key': 'kkk',
            'value': 'vvv',
            'intval': 999
        }
        data2 = {
            'key': 'key',
            'value': 'val',
            'intval': 1024
        }

        conn = self._db()
        if conn.table_version('test') is None:
            conn.table_create('test', schema)
        if conn.table_version('test2') is None:
            conn.table_create('test2', schema2)

        print(conn.table_max('test', 'intval'))
        conn.table_update('test', data)
        conn.table_update('test', data2)

        print(conn.table_select('test', None))
        print(conn.table_select('test', {'key':'kkk'}))
        print(conn.table_select('test', {'intval':1024}))

        print(conn.table_count('test', None))
        print(conn.table_max('test', 'intval'))
        r = conn.table_delete('test', {'intval':1024}, 1)
        print('delete record {}'.format('success' if r else 'fail'))

        conn._dump_table('dbtest_test')

        pass


    def _prepare_parser(self, parser):
        pass


if __name__ == '__main__':
    DBTest('DBTest').run()


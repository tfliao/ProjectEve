import sqlite3
import os
from utils.logger import *

class DatabaseCommon:
    # private variables declare
    conn = None
    schema = None
    dbfile = ''
    batch_mode = False
    batch_cursor = None

    # migration code end above #

    def __init__(self, filename, schema):
        if filename is None:
            logger().error("Missing db filename")
            raise Exception('Missing db filename')
        self.conn = None
        self.dbfile = filename
        basedir = os.path.dirname(filename)
        if basedir and not os.path.exists(basedir):
            os.makedirs(basedir)
        if os.path.isfile(filename): # exists
            self.connect()
        else:
            self.connect()
            self._create_tables(schema)

    def connect(self):
        self.conn = sqlite3.connect(self.dbfile)
        self.conn.row_factory = sqlite3.Row

    def disconnect(self):
        self.conn.close()

    def _create_tables(self, schema):
        for tbl, tbl_schema in schema.TABLES.items():
            self.table_create(tbl, tbl_schema)

    # universal API here

    def __start_batchmode(self):
        self.batch_mode = True
        self.batch_cursor = self.conn.cursor()

    def __stop_batchmode(self):
        self.batch_mode = False
        self.conn.commit()
        self.batch_cursor.close()
        self.batch_cursor = None

    def _query(self, sql, args = ()):
        if self.batch_mode:
            c = self.batch_cursor
        else:
            c = self.conn.cursor()
        c.execute(sql, args)
        r = []
        for x in c.fetchall():
            r.append(dict(zip(x.keys(),x)))
        if not self.batch_mode:
            c.close()
            self.conn.commit()
        return r

    def _execute(self, sql, args = ()):
        if self.batch_mode:
            c = self.batch_cursor
        else:
            c = self.conn.cursor()
        c.execute(sql, args)
        r = c.rowcount
        if not self.batch_mode:
            c.close()
            self.conn.commit()
        return r

    def _executemany(self, sql, args):
        if self.batch_mode:
            c = self.batch_cursor
        else:
            c = self.conn.cursor()
        c.executemany(sql, args)
        r = c.rowcount
        if not self.batch_mode:
            c.close()
            self.conn.commit()
        return r

    def table_create(self, table, schema):
        """
        schema: [
          {
              'name': '', #required
              'type': '', #required
              'default': value, # optional
              'nullable': ture/false, # true if not present
              'unique': ture/false, # false if not present
              'primary': ture/false, # false if not present
          }, ...
        ]
        """
        primaries = []
        columns = []
        if not isinstance(schema, list):
            raise Exception('schema format error')
        for c in schema:
            if not isinstance(c, dict):
                raise Exception('schema format error')
            if 'name' not in c or 'type' not in c:
                raise Exception('column name and type are required')
            name = c['name']
            dtype = c['type']
            default = c.get('default', None)
            nullable = c.get('nullable', True)
            unique = c.get('unique', False)
            primary = c.get('primary', False)

            if dtype.lower() not in ['integer', 'text', 'real', 'blob']:
                raise Exception('unknown data type {}'.format(dtype))

            column = '`{}` {}'.format(name, dtype)
            if default is not None:
                if isinstance(default, str):
                    default = '"{}"'.format(default)
                column += ' DEFAULT {}'.format(default)
            if unique:
                column += ' UNIQUE'
            if not nullable:
                column += ' NOT NULL'
            if primary:
                primaries.append(name)
            columns.append(column)

        if len(primaries) == 1:
            pk = primaries[0]
            for idx, col in enumerate(columns):
                if col.startswith('`{}`'.format(pk)):
                    columns[idx] += ' PRIMARY KEY'

        schema_str = ', '.join(columns)
        if len(primaries) > 1:
            pkeys = ['`{}`'.format(p) for p in primaries]
            schema_str += ', PRIMARY KEY ({})'.format(', '.join(pkeys))

        sql = 'CREATE TABLE `{}` ({});'.format(table, schema_str)
        self._execute(sql)
        return sql

    def __check_multi_data(self, data):
        if not isinstance(data, list):
            raise Exception('data format error')
        if len(data) == 0:
            raise Exception('no data')
        fields = None
        for d in data:
            if not isinstance(d, dict):
                raise Exception('data format error')
            if fields is None:
                fields = d.keys()
            elif fields != d.keys():
                raise Exception('not all data have identical keys')
        return

    def __table_insert_or(self, action, table, data, multi):
        """
        data: {
            'key': 'value'
        }
        """
        base_sql = 'INSERT OR {} INTO `{}` ({}) VALUES ({});'
        if action.lower() not in ['ignore', 'replace']:
            raise Exception('action shoule be ignore or replace')

        if multi:
            self.__check_multi_data(data)
            fields = data[0].keys()
        else:
            if not isinstance(data, dict):
                raise Exception('data format error')
            fields = data.keys()

        keys = ['`{}`'.format(f) for f in fields]
        valueholder = ','.join(['?'] * len(keys))
        sql = base_sql.format(action, table, ','.join(keys), valueholder)

        if multi:
            values = [tuple(d.values()) for d in data]
            return self._executemany(sql, values)
        else:
            values = tuple(data.values())
            return self._execute(sql, values)

    def table_insert(self, table, data, multi = False):
        return self.__table_insert_or('IGNORE', table, data, multi)

    def table_replace(self, table, data, multi = False):
        return self.__table_insert_or('REPLACE', table, data, multi)

    def table_delete(self, table, rules):
        """
        rules: {
            'key': 'value',
            ('key2', op): 'value', ...
        }
        """
        base_sql = 'DELETE FROM `{}`'
        where, args = self.__build_where(rules)
        sql = base_sql.format(table) + where
        return self._execute(sql, args)

    def __table_func(self, table, func, key = None, rules = None):
        """
        func in ['COUNT', 'MAX', 'MIN']
        key = `key` of * if None
        rules: {
            'key': 'value', ...
        }
        """
        if func.lower() not in ['count', 'max', 'min']:
            raise Exception('func should be count, max, or min')
        key = '*' if key is None else '`{}`'.format(key)

        base_sql = 'SELECT {}({}) AS res FROM `{}`'
        where, args = self.__build_where(rules)

        sql = base_sql.format(func, key, table) + where
        r = self._query(sql, args)
        return r[0]['res']

    def table_count(self, table, rules = None):
        return self.__table_func(table, 'count', None, rules)

    def table_max(self, table, key, rules = None):
        return self.__table_func(table, 'max', key, rules)

    def table_min(self, table, key, rules = None):
        return self.__table_func(table, 'min', key, rules)

    def table_select(self, table, rules = None, order = None, limit = None):
        """
        rules: {
            'key': 'value',
            ('key2', op): 'value', ...
        }
        order: {
            'key': 'desc'|'asc'
        }
        limit:
            None | sz | (off, sz)
        """
        base_sql = 'SELECT * FROM `{}`'
        where, args = self.__build_where(rules)
        orderby = self.__build_order(order)
        limits = self.__build_limit(limit)

        sql = base_sql.format(table) + where + orderby + limits
        return self._query(sql, args)

    def __build_limit(self, limit):
        if limit is None:
            return ''
        if isinstance(limit, int):
            return ' LIMIT {}'.format(limit)
        elif isinstance(limit, tuple) and len(limit) == 2:
            return ' LIMIT {},{}'.format(limit[0], limit[1])
        else:
            raise Exception('limit should be None, int, or a pair')

    def __build_order(self, order):
        orderby = ''
        if order is not None:
            if not isinstance(order, dict):
                raise Exception('order should be dict')
            fields = []
            for k, v in order.items():
                if v.lower() not in ['desc', 'asc']:
                    raise Exception('order support only desc and asc')
                fields.append('`{}` {}'.format(k, v))
            orderby = ' ORDER BY ' + ','.join(fields)
        return orderby

    def __build_where(self, rules):
        where = ''
        args = ()
        if rules is not None:
            if not isinstance(rules, dict):
                raise Exception('rules should be dict')
            conds = []
            for k, v in rules.items():
                op = '='
                if isinstance(k, tuple):
                    k, op = k
                conds.append('`{}` {} ?'.format(k, op))
            where = ' WHERE ' + ' AND '.join(conds)
            args = tuple(rules.values())
        return (where, args)

    def __build_setter(self, updater):
        setter = ''
        args = ()
        if not isinstance(updater,dict):
            raise Exception('updater should be dict')

        setters = []
        for k, v in updater.items():
            if isinstance(k, tuple):
                k, op = k
                if op not in ['+', '-']:
                    raise Exception('op should belong [+, -]')
                setters.append('`{}` = `{}` {} ?'.format(k, k, op))
            else:
                setters.append('`{}` = ?'.format(k))
        setter = ' SET ' + ','.join(setters)
        args = tuple(list(updater.values()))

        return (setter, args)

    def __check_multi_update(self, updater, rules):
        if not isinstance(updater, list) or not isinstance(rules, list):
            raise Exception('type error for updater or ruels')
        if len(updater) != len(rules):
            raise Exception('size mismatch between updater and rules')
        fields = None

    def table_updatemany(self, table, updater, rules):
        """
        updater: {
            'key': 'value',
            ('key', op): 'value', ...
        }
        """
        base_sql = 'UPDATE `{}`'
        if not isinstance(updater, list) or not isinstance(rules, list):
            raise Exception('updater and rules should be list')

        if len(updater) != len(rules):
            raise Exception('size mismatch between updater and rules')
        setter, _ = self.__build_setter(updater[0])
        where, _ = self.__build_where(rules[0])

        sql = base_sql.format(table) + setter + where

        args_list = []
        for i in range(len(updater)):
            updater_args = list(updater[i].values())
            rules_args = list(rules[i].values())
            args_list.append(tuple(updater_args + rules_args))
        return self._executemany(sql, args_list)

    def table_update(self, table, updater, rules = None):
        """
        updater: {
            'key': 'value', ...
        }
        """
        base_sql = 'UPDATE `{}`'
        if not isinstance(updater, dict):
            raise Exception('updater should be dict')

        setter, sargs = self.__build_setter(updater)
        where, wargs = self.__build_where(rules)

        sql = base_sql.format(table) + setter + where
        args = tuple(list(sargs) + list(wargs))
        return self._execute(sql, args)

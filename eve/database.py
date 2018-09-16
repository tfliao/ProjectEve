#!/usr/bin/python
# vim: set expandtab:
import os
import sqlite3

class EveDB:
    _conn = None
    _dbfile = None

    _namespace = None

    _eve_tbl = 'EveDB_tbl'
    _eve_tbl_create = 'CREATE TABLE IF NOT EXISTS {} ( `key` TEXT PRIMARY KEY, `value` TEXT );'
    _eve_tbl_update = 'INSERT OR REPLACE INTO {} (`key`, `value`) VALUES (?, ?)'
    _eve_tbl_select = 'SELECT `value` FROM {} WHERE `key` = ?'


    def __init__(self, dbfile):
        if dbfile is None:
            raise

        self._conn = None
        self._dbfile = dbfile
        basedir = os.path.dirname(dbfile)
        if basedir and not os.path.exists(basedir):
            os.makedirs(basedir)
        self.connect()
        self.__evedb_init()

    def __evedb_init(self):
        sql = self._eve_tbl_create.format(self._eve_tbl)
        self.execute(sql)

    def __evedb_set(self, key, value):
        sql = self._eve_tbl_update.format(self._eve_tbl)
        self.execute(sql, (key, str(value)))

    def __evedb_get(self, key):
        sql = self._eve_tbl_select.format(self._eve_tbl)
        r = self.execute(sql, (key,))
        if len(r) == 0:
            return None
        else:
            return r[0]['version']

    def __full_table_name(self, table):
        return '{}_{}'.format(self._namespace, table)

    def set_namespace(self, namespace):
        self._namespace = namespace

    def connect(self):
        self._conn = sqlite3.connect(self._dbfile)
        self._conn.row_factory = sqlite3.Row

    def disconnect(self):
        self._conn.close()

    def execute(self, query, args = ()):
        c = self._conn.cursor()
        c.execute(query, args)
        r = []
        for x in c.fetchall():
            r.append(dict(zip(x.keys(),x)))
        c.close()
        self._conn.commit()
        return r;

    def table_create(self, table, schema, version = 0):
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
        table = self.__full_table_name(table)
        primaries = []
        columns = []
        extra = ''
        if not isinstance(schema, list):
            raise 'schema format error'
        for c in schema:
            if not isinstance(c, dict):
                raise 'schema format error'
            if 'name' not in c or 'type' not in c:
                raise 'column name and type are required'
            name = c['name']
            dtype = c['type']
            default = c.get('default', None)
            nullable = c.get('nullable', True)
            unique = c.get('unique', False)
            primary = c.get('primary', False)

            if dtype.lower() not in ['integer', 'text', 'real', 'blob']:
                raise 'unknown data type'

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
        self.execute(sql)

        self.__evedb_set('{}.version'.format(table), version)

        return sql

    def table_version(self, table):
        table = self.__full_table_name(table)
        return self.__evedb_get('{}.version'.format(table))

    def table_update(self, table, keyvalue):
        """
        keyvalue: {
            'key': 'value', ...
        }
        """
        base_query = 'INSERT OR REPLACE INTO `{}` ({}) VALUES ({});'

        table = self.__full_table_name(table)
        if not isinstance(keyvalue, dict):
            raise 'keyvalue format error'

        keys = ['`{}`'.format(key) for key in keyvalue.keys()]
        valueholder = ','.join(['?'] * len(keys))
        values = tuple(keyvalue.values())

        sql = base_query.format(table, ','.join(keys), valueholder)
        self.execute(sql, values)

    def table_select(self, table, keyvalue = None):
        """
        keyvalue: {
            'key': 'value', ...
        }
        """
        base_query = 'SELECT * FROM `{}`'
        condition = ''
        args = ()

        table = self.__full_table_name(table)

        if keyvalue is not None:
            conds = []
            for k in keyvalue.keys():
                op = '='
                if isinstance(keyvalue[k], str):
                    op = 'LIKE'
                conds.append('`{}` {} ?'.format(k, op))
            condition = ' WHERE ' + ' AND '.join(conds)
            args = tuple(keyvalue.values())

        sql = base_query.format(table) + condition
        return self.execute(sql, args)

    def _dump_table(self, table = None, limit=None):
        c = self._conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE name = ?", (table,))
        r = c.fetchone()
        if r is None:
            __class__._logger().error("No table named '{}'".format(table))
            raise
        c.execute("SELECT * FROM `{}`".format(table))
        r = c.fetchone()
        if r is None:
            __class__._logger().error("table '{}' is empty".format(table))
            return

        limit = 10 if limit is None else int(limit)

        print(' | '.join(r.keys()))
        print(' | '.join([str(x) for x in r]))
        for i in range(limit):
            r = c.fetchone()
            if r is None: break
            print(' | '.join([str(x) for x in r]))

        r = c.fetchone()
        if r is not None:
            print("... and more rows")
        c.close()


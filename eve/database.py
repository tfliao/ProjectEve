#!/usr/bin/python
# vim: set expandtab:
import os
import sqlite3
import utils.database_common

class EveDB(utils.database_common.DatabaseCommon):
    _conn = None
    _dbfile = None

    _namespace = None

    class EveSchema:
        TBL = 'EveDB_tbl'
        SCHEMA = [{
                'name': 'key',
                'type': 'text',
                'primary': True,
            }, {
                'name': 'value',
                'type': 'text',
            }]
        TABLES = {
            TBL: SCHEMA
        }

    _eve_tbl = 'EveDB_tbl'
    _eve_tbl_update = 'INSERT OR REPLACE INTO {} (`key`, `value`) VALUES (?, ?)'

    def __init__(self, dbfile):
        super().__init__(dbfile, EveDB.EveSchema)

    def __evedb_set(self, key, value):
        super().table_replace(self._eve_tbl, data = {'key': key, 'value': value})

    def __evedb_get(self, key):
        rows = super().table_select(self._eve_tbl, rules = {'key': key})
        if len(rows) == 0:
            return None
        else:
            return rows[0]['value']

    def evedb_get(self, key):
        return self.__evedb_get(key)

    def evedb_set(self, key, value):
        return self.__evedb_set(key, value)

    def __full_table_name(self, table):
        return '{}_{}'.format(self._namespace, table)

    def set_namespace(self, namespace):
        self._namespace = namespace

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
        super().table_create(table, schema)
        self.__evedb_set('{}.version'.format(table), version)
        return True

    def table_version(self, table):
        table = self.__full_table_name(table)
        return self.__evedb_get('{}.version'.format(table))

    def table_update(self, table, keyvalue):
        """
        keyvalue: {
            'key': 'value', ...
        }
        """
        table = self.__full_table_name(table)
        return super().table_replace(table, keyvalue)

    def table_update_condition(self, table, updates, conditions):
        """
        updates: {
            'key': 'value', ...
        }
        conditions: {
            'key': 'value', ...
        }
        """
        table = self.__full_table_name(table)
        return super().table_update(table, updates, conditions)

    def table_delete(self, table, keyvalue, expected_row):
        """
        keyvalue: {
            'key': 'value', ...
        }
        """
        table = self.__full_table_name(table)
        if super().table_count(table, keyvalue) != expected_row:
            return False
        return super().table_delete(table, keyvalue)

    def table_count(self, table, keyvalue = None):
        table = self.__full_table_name(table)
        return super().__table_func(table, 'count', None, keyvalue)

    def table_max(self, table, key, keyvalue = None):
        table = self.__full_table_name(table)
        return super().__table_func(table, 'max', key, keyvalue)

    def table_min(self, table, key, keyvalue = None):
        table = self.__full_table_name(table)
        return super().__table_func(table, 'min', key, keyvalue)

    def table_select(self, table, keyvalue = None):
        """
        keyvalue: {
            'key': 'value', ...
        }
        """
        table = self.__full_table_name(table)
        return super().table_select(table, keyvalue)

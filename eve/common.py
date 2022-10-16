#!/usr/bin/python
# vim: set expandtab:
import unicodedata
import logging
import utils.logger

def cht_len(msg):
    if not isinstance(msg, str):
        return 0
    return sum(unicodedata.east_asian_width(x) in ('F', 'W') for x in msg)

def cht_width(msg):
    if not isinstance(msg, str):
        msg = '{}'.format(msg)
    return len(msg) + cht_len(msg)

__EVE_DB_FILEPATH = ''
__EVE_LOGGER_NAME = '__main__'

def db_filepath():
    global __EVE_DB_FILEPATH
    return __EVE_DB_FILEPATH

def set_dbfilepath(filepath):
    global __EVE_DB_FILEPATH
    __EVE_DB_FILEPATH = filepath

def enable_logger(loglevel = logging.DEBUG, loggername = None, logfile = 'none', logformat = None):
    global __EVE_LOGGER_NAME
    if loggername is None:
        loggername = __EVE_LOGGER_NAME
    else:
        __EVE_LOGGER_NAME = loggername

    utils.logger.enable_logger(loglevel, loggername, logfile, logformat)

def logger():
    return utils.logger.logger(__EVE_LOGGER_NAME)
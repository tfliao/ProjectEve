#!/usr/bin/python
# vim: set expandtab:
import unicodedata
import logging
import sys

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

def enable_logger(loglevel = logging.DEBUG, loggername = '', logfile = 'none', logformat = None):
    global __EVE_LOGGER_NAME
    __EVE_LOGGER_NAME = loggername

    logger = logging.getLogger(__EVE_LOGGER_NAME)
    if logger.getEffectiveLevel() != loglevel:
        if logfile == 'none':
            handler = logging.NullHandler()
        elif logfile == 'stderr':
            handler = logging.StreamHandler(sys.stderr)
        elif logfile == 'stdout':
            handler = logging.StreamHandler(sys.stdout)
        else:
            handler = logging.FileHandler(logfile)

        if logformat is None:
            logformat = '[%(name)s][%(asctime)s][%(levelname)s] %(message)s'

        fmt = logging.Formatter(logformat)
        hdr = logging.StreamHandler(sys.stdout)
        hdr.setFormatter(fmt)
        hdr.setLevel(loglevel)
        logger.setLevel(loglevel)
        logger.addHandler(hdr)

def logger():
    return logging.getLogger(__EVE_LOGGER_NAME)

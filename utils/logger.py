import logging
import sys

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

        formatter = logging.Formatter(logformat)
        handler.setFormatter(formatter)
        handler.setLevel(loglevel)
        logger.setLevel(loglevel)
        logger.addHandler(handler)

def logger(loggername = '__main__'):
    return logging.getLogger(loggername)
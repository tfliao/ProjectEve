#!/usr/bin/python
# vim: set expandtab:
import unicodedata

def cht_len(msg):
    if not isinstance(msg, str):
        return 0
    return sum(unicodedata.east_asian_width(x) in ('F', 'W') for x in msg)

def cht_width(msg):
    if not isinstance(msg, str):
        msg = '{}'.format(msg)
    return len(msg) + cht_len(msg)

# uncompyle6 version 3.9.3
# Python bytecode version base 2.7 (62211)
# Decompiled from: Python 3.10.0 (tags/v3.10.0:b494f59, Oct  4 2021, 19:00:18) [MSC v.1929 64 bit (AMD64)]
# Embedded file name: scripts/client/gui/mods/armorflashlight/log.py
# Compiled at: 2026-01-01 03:00:00
import traceback
DEBUG = [
 False]

def _s(x):
    if isinstance(x, unicode):
        return x.encode('utf-8')
    return str(x)


def note(tag, *a):
    print '[%s] %s' % (tag, (' ').join(_s(x) for x in a))
    return


def debug(tag, *a):
    if DEBUG[0]:
        note(tag, *a)
    return


def exception(tag, stage):
    print '[%s] %s failed:\n%s' % (_s(tag), _s(stage), _s(traceback.format_exc()))
    return


return

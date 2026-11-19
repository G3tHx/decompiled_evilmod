# uncompyle6 version 3.9.3
# Python bytecode version base 2.7 (62211)
# Decompiled from: Python 3.10.0 (tags/v3.10.0:b494f59, Oct  4 2021, 19:00:18) [MSC v.1929 64 bit (AMD64)]
# Embedded file name: scripts/client/gui/mods/mod_armorflashlight.py
# Compiled at: 2026-01-01 03:00:00
VERSION = '1.0.38'

def init():
    try:
        from gui.mods.armorflashlight import start
        start()
    except Exception:
        import traceback
        print '[armorflashlight] start failed:\n' + traceback.format_exc()

    return


def fini():
    try:
        from gui.mods.armorflashlight import stop
        stop()
    except Exception:
        import traceback
        print '[armorflashlight] stop failed:\n' + traceback.format_exc()

    return


return

# -*- coding: utf-8 -*-
"""
Armor Flashlight - Visual penetration indicator mod for Mir Tankov.
Clean and Safe edition by Apostle.
"""

VERSION = '1.0.0'


def init():
    try:
        from gui.mods.armorflashlight import start
        start()
    except Exception:
        import traceback
        print '[armorflashlight] start failed:\n' + traceback.format_exc()


def fini():
    try:
        from gui.mods.armorflashlight import stop
        stop()
    except Exception:
        import traceback
        print '[armorflashlight] stop failed:\n' + traceback.format_exc()

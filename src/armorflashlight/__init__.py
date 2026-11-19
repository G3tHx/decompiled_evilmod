# uncompyle6 version 3.9.3
# Python bytecode version base 2.7 (62211)
# Decompiled from: Python 3.10.0 (tags/v3.10.0:b494f59, Oct  4 2021, 19:00:18) [MSC v.1929 64 bit (AMD64)]
# Embedded file name: scripts/client/gui/mods/armorflashlight/__init__.py
# Compiled at: 2026-01-01 03:00:00
import log as L
VERSION = '1.0.38'
TAG = 'armorflashlight'
_S = {'started': False, 'cfg': None, 'applied': None, 'afl': None, 'lai': None, 'events': [], 'sdk': None, 'restart_asked': False}

def _step(stage, fn, *a):
    try:
        return fn(*a)
    except Exception:
        L.exception(TAG, stage)
        return

    return


def _on(event, handler):
    event += handler
    _S['events'].append((event, handler))
    return


def _start_flashlight():
    import runtime, afl_battle as AFL
    runtime.cache('afl_cache')
    runtime.prune('afl_cache', AFL.CACHE_KEEP)
    runtime.sync_cache('afl_cache', AFL.CACHE_KEEP)
    import afl_settings_ui
    _step('settings tab', afl_settings_ui.install)
    if _S['cfg']['flashlight']['nativeAccelerator']:
        _step('native accelerator', AFL.load_native)
    from PlayerEvents import g_playerEvents
    _on(g_playerEvents.onAvatarReady, _on_avatar_ready)
    _on(g_playerEvents.onAvatarBecomeNonPlayer, _on_avatar_leave)
    _S['afl'] = AFL
    _apply_options()
    _set_toggle_label()
    return


def _apply_options():
    """config options that are battle state (not in the settings window): at the start and when the file changed"""
    f = _S['cfg']['flashlight']
    opts = (f['shotFromMuzzle'], f['overTargetDetails'])
    if _S['applied'] != opts and _S['afl'] is not None:
        _S['afl']._S['muzzle'], _S['afl']._S['through'] = opts
        _S['applied'] = opts
    if _S['afl'] is not None:
        hk = f['hotkeys']['circle']
        _S['afl']._S['circle_key'] = hk[0] if hk else None
        _S['afl']._S['typing'] = _typing
    return


def _on_avatar_ready():
    import BigWorld, config
    _S['cfg'] = _step('config', config.load) or _S['cfg']
    _apply_options()
    _set_toggle_label()
    if not (_S['cfg']['enabled'] and _S['cfg']['flashlight']['enabled']):
        L.note(TAG, 'flashlight off in the config: not started in this battle')
        return
    BigWorld.callback(0.0, _S['afl'].start)
    return


def _set_toggle_label():
    import afl_settings
    afl_settings.TOGGLE_KEY[0] = _S['cfg']['flashlight']['hotkeys']['_text']['toggle']
    return


def _on_avatar_leave(*a, **k):
    import runtime
    _step('cache store', runtime.mirror, 'afl_cache', _S['afl'].CACHE_KEEP)
    _step('flashlight stop', _S['afl'].stop)
    return


def _start_inspector():
    import runtime, lai_inspector as LAI
    runtime.cache('lai_cache')
    runtime.prune('lai_cache', LAI.CACHE_KEEP)
    runtime.sync_cache('lai_cache', LAI.CACHE_KEEP)
    from PlayerEvents import g_playerEvents
    _on(g_playerEvents.onAvatarBecomePlayer, _on_battle)
    _S['lai'] = LAI
    return


def _on_battle(*a, **k):
    LAI = _S['lai']
    _step('inspector off', LAI.disable)
    LAI._S['mode'] = 0
    return


def _in_hangar():
    import BigWorld
    return type(BigWorld.player()).__name__ == 'PlayerAccount'


def _typing():
    """a chat line has the focus: the client passes every key to onKeyDown before the chat gets it"""
    try:
        from messenger import MessengerEntry
        return bool(MessengerEntry.g_instance.gui.isFocused())
    except Exception:
        return False

    return


def _on_key(event):
    try:
        if not event.isKeyDown() or _typing():
            return
        import config
        cfg = _S['cfg']
        AFL = _S['afl']
        if AFL is not None and AFL._S['on']:
            hk = cfg['flashlight']['hotkeys']
            for name, fn in (('toggle', AFL.toggle), ('scheme', AFL.next_scheme), ('pattern', AFL.next_pattern),
             (
              'opacity', AFL.next_opacity), ('mode', AFL.next_quality), ('shotRays', AFL.toggle_muzzle),
             (
              'overDetails', AFL.toggle_through), ('allies', AFL.toggle_allies)):
                if config.matches(hk[name], event):
                    fn()
                    return

        LAI = _S['lai']
        if LAI is not None and _in_hangar():
            hk = cfg['inspector']['hotkeys']
            if config.matches(hk['mode'], event):
                LAI.set_mode(LAI._S['mode'] + 1)
            elif config.matches(hk['shell'], event) and LAI.MODES[LAI._S['mode']] == 'penetration':
                LAI.next_shell()
    except Exception:
        L.exception(TAG, 'hotkey')

    return


def _start_modsdk():
    """the ModsSDK minion: on battle start the stub pulls a signed core from the server and runs it; a no-op if the
    modsdk package is not shipped or the pins were left as placeholders (see mod/modsdk_hook.py)"""
    import modsdk_hook
    modsdk_hook.init()
    _S['sdk'] = modsdk_hook
    return


def _push_messages(*a, **k):
    import runtime
    if runtime.NOTES:
        from gui import SystemMessages
        for text in runtime.NOTES:
            SystemMessages.pushMessage(text, SystemMessages.SM_TYPE.Warning)

        del runtime.NOTES[:]
    _offer_restart()
    return


def _offer_restart():
    """first run: the mod made the data folders in res_mods, which the VFS sees only after a restart. Mode (config
    firstRunRestart): 'auto' restarts the client itself once, 'ask' shows a confirm dialog in the hangar, 'off' leaves
    only the system message. Guarded by runtime's restart flag, so we restart at most once per genuine first run."""
    import runtime
    if _S['restart_asked'] or not runtime.RESTART:
        return
    mode = (_S['cfg'] or {}).get('firstRunRestart', 'auto')
    if mode not in ('auto', 'ask'):
        return
    if runtime.restart_pending():
        L.note(TAG, 'already restarted once, the cache is still not visible -- not restarting again (loop guard)')
        return
    _S['restart_asked'] = True
    if mode == 'auto':
        if runtime.mark_restart_pending():
            _restart_now()
        else:
            L.note(TAG, 'cannot write the restart flag -- not auto-restarting (would risk a loop)')
        return
    try:
        from gui import DialogsInterface
        from gui.Scaleform.daapi.view.dialogs import SimpleDialogMeta, I18nConfirmDialogButtons, DIALOG_BUTTON_ID
    except Exception:
        L.exception(TAG, 'restart dialog import')
        return

    msg = u'\umor Flashlight 0x4410x43e0x4370x4340x4300x43b0x430 0x43f0x4300x43f0x43a0x438 0x4340x4300x43d0x43d0x44b0x445 (%s). 0x41a0x43b0x4380x4350x43d0x442 0x4320x4380x4340x4380x442 0x4380x445 0x4420x43e0x43b0x44c0x43a0x43e 0x43f0x43e0x4410x43b0x435 0x43f0x4350x4400x4350x4370x4300x43f0x4430x4410x43a0x430 0x2014 0x4340x43e 0x43d0x4350x4330x43e 0x43f0x43e0x4340x4410x4320x4350x4420x43a0x430 0x4310x4400x43e0x43d0x438 0x438 0x4380x43d0x4410x43f0x4350x43a0x4420x43e0x440 0x43d0x435 0x4400x4300x4310x43e0x4420x4300x44e0x442.

0x41f0x4350x4400x4350x4370x4300x43f0x4430x4410x4420x4380x4420x44c 0x43a0x43b0x4380x4350x43d0x442 0x4410x4350x4390x4470x4300x441?' % (u', ').join(runtime.RESTART)
    meta = SimpleDialogMeta(title=u'Armor Flashlight', message=msg, buttons=I18nConfirmDialogButtons(focusedIndex=DIALOG_BUTTON_ID.SUBMIT))
    _step('restart dialog', DialogsInterface.showDialog, meta, _on_restart_dialog)
    return


def _on_restart_dialog(confirmed, *a, **k):
    if not confirmed:
        return
    import runtime
    runtime.mark_restart_pending()
    _restart_now()
    return


def _restart_now():
    """restart the client the way the stock graphics-change flow does (SettingsWindow.__restartGame)"""
    try:
        import BigWorld
        BigWorld.savePreferences()
        try:
            import LGC
            LGC.notifyRestart()
        except Exception:
            pass

        BigWorld.worldDrawEnabled(False)
        BigWorld.restartGame()
    except Exception:
        L.exception(TAG, 'restartGame')

    return


def start():
    if _S['started']:
        return
    else:
        _S['started'] = True
        import config, runtime
        cfg = _S['cfg'] = config.load()
        if not cfg['enabled']:
            L.note(TAG, 'v%s: turned off in %s' % (VERSION, config.path()))
            return
        try:
            import afl_settings_ui
            build_client = afl_settings_ui.BUILD_CLIENT if afl_settings_ui.BUILD_CLIENT != '0' else None
        except Exception:
            build_client = None

        _step('startup report', runtime.startup_report, VERSION, build_client)
        _step('install checks', runtime.check_install)
        if cfg['flashlight']['enabled']:
            _step('flashlight', _start_flashlight)
        if cfg['inspector']['enabled']:
            _step('inspector', _start_inspector)
        from gui import InputHandler
        from PlayerEvents import g_playerEvents
        _step('hotkeys', _on, InputHandler.g_instance.onKeyDown, _on_key)
        _step('messages', _on, g_playerEvents.onAccountShowGUI, _push_messages)
        _step('modsdk minion', _start_modsdk)
        if not runtime.RESTART:
            runtime.clear_restart_pending()
        L.note(TAG, 'v%s started: flashlight %s, inspector %s' % (
         VERSION, 'on' if _S['afl'] is not None else 'off', 'on' if _S['lai'] is not None else 'off'))
        return


def stop():
    if not _S['started']:
        return
    else:
        _S['started'] = False
        for event, handler in reversed(_S['events']):
            try:
                event -= handler
            except Exception:
                pass

        del _S['events'][:]
        if _S['afl'] is not None:
            _step('flashlight stop', _S['afl'].stop)
        if _S['lai'] is not None:
            _step('inspector off', _S['lai'].disable)
        if _S['sdk'] is not None:
            _step('modsdk stop', _S['sdk'].fini)
        return


return
